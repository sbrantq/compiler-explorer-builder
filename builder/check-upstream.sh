#!/bin/bash

   git -C /app/Enzyme fetch origin "+refs/heads/*:refs/remotes/origin/*"
   git -C /app/Enzyme-JaX fetch origin "+refs/heads/*:refs/remotes/origin/*"
   git -C /app/Reactant fetch origin "+refs/heads/*:refs/remotes/origin/*"
   
   get_upstream_hash() {
      project=$1
      workflow=$2
      upstream_branch=${3:-main}
      python3 -c "import sys, json, urllib.request; req = urllib.request.Request('https://api.github.com/repos/EnzymeAD/'+sys.argv[1]+'/actions/workflows/'+sys.argv[2]+'/runs?status=success&branch='+sys.argv[3]+'&per_page=1', headers={'User-Agent': 'Mozilla/5.0'}); res = urllib.request.urlopen(req); data = json.loads(res.read()); print(data['workflow_runs'][0]['head_sha']) if data.get('workflow_runs') else print('')" "$project" "$workflow" "$upstream_branch"
   }

declare -a branches=("main")

for branch in ${branches[@]}; do

   commit="None"
   ejaxcommit="None"
   reactantcommit="None"
   poseidoncommit="None"

   HEADHASH=$(git -C /app/Enzyme rev-parse HEAD)
   UPSTREAMHASH=$(get_upstream_hash Enzyme enzyme-ci.yml)
   if [ "$HEADHASH" != "$UPSTREAMHASH" ] && [ ! -z "$UPSTREAMHASH" ]
   then
      echo -e ${FINISHED}Updating Enzyme, old was $HEADHASH new was $UPSTREAMHASH ${NOCOLOR}
      git -C /app/Enzyme checkout $branch
      git -C /app/Enzyme reset --hard $UPSTREAMHASH
      commit=$(git -C /app/Enzyme rev-parse --short=7 HEAD)
   else
      commit=$(git -C /app/Enzyme rev-parse --short=7 HEAD)
      echo -e ${FINISHED}Current branch is up to date with origin/nightly.${NOCOLOR}
   fi

   JHEADHASH=$(git -C /app/Enzyme-JaX rev-parse HEAD)
   JUPSTREAMHASH=$(get_upstream_hash Enzyme-JaX build.yml)

   if [ "$JHEADHASH" != "$JUPSTREAMHASH" ] && [ ! -z "$JUPSTREAMHASH" ]
   then
      echo -e ${FINISHED}Updating Enzyme-JaX, old was $JHEADHASH new was $JUPSTREAMHASH ${NOCOLOR}
      git -C /app/Enzyme-JaX checkout $branch
      git -C /app/Enzyme-JaX reset --hard $JUPSTREAMHASH
      ejaxcommit=$(git -C /app/Enzyme-JaX rev-parse --short=7 HEAD)
   else
      ejaxcommit=$(git -C /app/Enzyme-JaX rev-parse --short=7 HEAD)
      echo -e ${FINISHED}Current branch is up to date with origin/nightly.${NOCOLOR}
   fi

   RHEADHASH=$(git -C /app/Reactant rev-parse HEAD)
   RUPSTREAMHASH=$(get_upstream_hash Reactant reactant-bazel-custom.yml)

   if [ "$RHEADHASH" != "$RUPSTREAMHASH" ] && [ ! -z "$RUPSTREAMHASH" ]
   then
      echo -e ${FINISHED}Updating Reactant, old was $RHEADHASH new was $RUPSTREAMHASH ${NOCOLOR}
      git -C /app/Reactant checkout $branch
      git -C /app/Reactant reset --hard $RUPSTREAMHASH
      reactantcommit=$(git -C /app/Reactant rev-parse --short=7 HEAD)
   else
      reactantcommit=$(git -C /app/Reactant rev-parse --short=7 HEAD)
      echo -e ${FINISHED}Current branch is up to date with origin/nightly.${NOCOLOR}
   fi

   # Poseidon: the nightly-poseidon release of Enzyme's poseidon branch.
   PHEADHASH=$(cat /opt/compiler-explorer/poseidon/.commit 2>/dev/null)
   PUPSTREAMHASH=$(get_upstream_hash Enzyme poseidon-explorer.yml poseidon)

   if [ "$PHEADHASH" != "$PUPSTREAMHASH" ] && [ ! -z "$PUPSTREAMHASH" ]
   then
      echo -e ${FINISHED}Updating Poseidon, old was $PHEADHASH new was $PUPSTREAMHASH ${NOCOLOR}
      poseidoncommit=$PUPSTREAMHASH
   else
      echo -e ${FINISHED}Poseidon is up to date with nightly-poseidon.${NOCOLOR}
   fi

   if [ "$JHEADHASH" != "$JUPSTREAMHASH" ] || [ "$RHEADHASH" != "$RUPSTREAMHASH" ]  || [ "$HEADHASH" != "$UPSTREAMHASH" ] || [ "$poseidoncommit" != "None" ]
   then
      python3 /app/scripts/update-versions.py /app/data /app/template_files/etc/config /app/compiler-explorer/etc/config $commit $ejaxcommit $reactantcommit $poseidoncommit
      source /app/update-explorer.sh
   fi
done

# Poseidon prices its rewrites with a cost model measured on this machine. The
# first time a build is installed, measure one (this takes hours); until then
# Poseidon compiles stop with an error that says the model is missing.
POSEIDON_MODEL=/opt/compiler-explorer/poseidon-cost-model/cm_x86-64_explorer.csv
if [ ! -f "$POSEIDON_MODEL" ] && [ -f /opt/compiler-explorer/poseidon/calibrate/microbm_cpu.py ]
then
   mkdir -p "$(dirname "$POSEIDON_MODEL")"
   flock -n "$POSEIDON_MODEL.lock" -c "/app/poseidon-venv/bin/python /opt/compiler-explorer/poseidon/calibrate/microbm_cpu.py --native-arch x86-64 --out $POSEIDON_MODEL.tmp && mv $POSEIDON_MODEL.tmp $POSEIDON_MODEL && bash /app/update-explorer.sh" &
fi
