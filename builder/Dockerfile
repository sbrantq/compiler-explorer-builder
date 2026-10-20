FROM ghcr.io/enzymead/compiler-explorer-builder-compilers:main

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y --no-install-recommends curl git cron make cmake ccache clang ninja-build binutils \
    python3 python3-pip python3-venv grep build-essential zlib1g-dev python3-jinja2 \
    && apt-get autoremove -y --purge \
    && apt-get clean -y \
    && rm -rf /var/lib/apt/lists/*

RUN git clone -b main https://github.com/EnzymeAD/Enzyme.git /app/Enzyme
RUN git clone -b main https://github.com/EnzymeAD/Enzyme-JaX.git /app/Enzyme-JaX
RUN git clone -b main https://github.com/EnzymeAD/Reactant.git /app/Reactant

RUN ccache -M 20G

RUN python3 -m venv /app/poseidon-venv && /app/poseidon-venv/bin/pip install --no-cache-dir llvmlite numpy

COPY scripts /app/scripts
COPY data /app/data
COPY template_files /app/template_files
COPY install-libraries.sh /app/install-libraries.sh
COPY check-upstream.sh /app/check-upstream.sh
COPY entrypoint.sh /app/entrypoint.sh
COPY update-explorer.sh /app/update-explorer.sh
COPY crontab /etc/cron.d/crontab
COPY --from=docker:28.2-dind /usr/local/bin/docker /usr/bin/

RUN crontab /etc/cron.d/crontab

WORKDIR /app

ENV DEBIAN_FRONTEND=

ENTRYPOINT ["/app/entrypoint.sh"]
CMD ["cron","-f"]
