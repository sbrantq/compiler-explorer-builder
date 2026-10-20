#!/usr/bin/env python3

import os
import re
import shutil
from pathlib import Path
from jinja2 import Environment, FileSystemLoader, ChoiceLoader

import sys
import tarfile
import urllib.request


if len(sys.argv) < 4:
    print("Usage: update-versions.py <data dir> <template dir> <source config dir>")
    sys.exit(1)

print("Called update-versions.py with ", sys.argv)

# --- Configuration ---
CLANG_VERSIONS_FILE = Path(sys.argv[1]) / "clang-versions.txt"
JULIA_VERSIONS_FILE = Path(sys.argv[1]) / "julia-versions.txt"
TRUNK_VERSION_FILE = Path(sys.argv[1]) / "trunk-llvm-version.txt"
SOURCE_CONFIG_DIR = Path(sys.argv[3])
TEMPLATE_DIR = Path(sys.argv[2])
commit = None
if len(sys.argv) > 4:
    commit = sys.argv[4]
    if commit == "None":
        commit = None

ejaxcommit = None
if len(sys.argv) > 5:
    ejaxcommit = sys.argv[5]
    if ejaxcommit == "None":
        ejaxcommit = None

reactant_commit = None
if len(sys.argv) > 6:
    reactant_commit = sys.argv[6]
    if reactant_commit == "None":
        reactant_commit = None

poseidon_commit = None
if len(sys.argv) > 7:
    poseidon_commit = sys.argv[7]
    if poseidon_commit == "None":
        poseidon_commit = None

POSEIDON_DIR = Path("/opt/compiler-explorer/poseidon")
POSEIDON_MODEL = Path("/opt/compiler-explorer/poseidon-cost-model/cm_x86-64_explorer.csv")

def install_poseidon(commit):
    """Unpack the nightly-poseidon build beside the live tree and swap it in.
    The cost model lives outside the tree, measured once on this machine, and
    the tree links to it."""
    url = "https://github.com/EnzymeAD/Enzyme/releases/download/nightly-poseidon/poseidon-explorer-llvm21.tar.gz"
    tmp_path = Path("/tmp/poseidon-explorer.tar.gz")
    new_dir = POSEIDON_DIR.with_name("poseidon.new")
    old_dir = POSEIDON_DIR.with_name("poseidon.old")
    print(f"Downloading {url} to {tmp_path}")
    try:
        urllib.request.urlretrieve(url, tmp_path)
        shutil.rmtree(new_dir, ignore_errors=True)
        new_dir.mkdir(parents=True)
        with tarfile.open(tmp_path) as tar:
            for member in tar.getmembers():
                parts = Path(member.name).parts[1:]
                if not parts:
                    continue
                member.name = str(Path(*parts))
                tar.extract(member, new_dir, filter="tar")
        (new_dir / ".commit").write_text(commit + "\n")
        model = new_dir / "cost_models" / POSEIDON_MODEL.name
        model.parent.mkdir(exist_ok=True)
        model.unlink(missing_ok=True)
        model.symlink_to(POSEIDON_MODEL)
        shutil.rmtree(old_dir, ignore_errors=True)
        if POSEIDON_DIR.exists():
            POSEIDON_DIR.rename(old_dir)
        new_dir.rename(POSEIDON_DIR)
        shutil.rmtree(old_dir, ignore_errors=True)
    except Exception as e:
        print(f"Error installing Poseidon {commit}: {e}")

def get_compiler_info(raw_name, trunk_val):
    """Extracts version and semver from strings like 'clang-15.0.0' or 'clang-assertions-trunk'."""
    # Matches digits or 'trunk'
    version_match = re.search(r'(\d+|trunk)', raw_name)
    major_version = version_match.group(1) if version_match else "unknown"
    
    if major_version == "trunk":
        major_version = trunk_val
    
    # Remove leading zeros if any
    major_version = major_version.lstrip('0')
    semver = raw_name.replace("clang-", "")
    
    return int(major_version), semver

def installed_poseidon():
    try:
        return (POSEIDON_DIR / ".commit").read_text().strip()[:7]
    except OSError:
        return "<unknown>"

def main():
    # Read input files
    trunk_val = TRUNK_VERSION_FILE.read_text().strip()
    compilers_raw = [c.strip() for c in CLANG_VERSIONS_FILE.read_text().splitlines() if c.strip()]
    julia_versions = [c.strip() for c in JULIA_VERSIONS_FILE.read_text().splitlines() if c.strip()]

    if poseidon_commit is not None:
        install_poseidon(poseidon_commit)

    # 3. Generate context for templates
    env = Environment(loader=ChoiceLoader([
        FileSystemLoader(str(TEMPLATE_DIR)),
        FileSystemLoader(sys.argv[1])
    ]))
    
    branch = "main"
    compiler_data = []
    for c_raw in compilers_raw:
        version, semver = get_compiler_info(c_raw, trunk_val)
        compiler_data.append({
            "raw_name": c_raw,
            "version": version,
            "semver": semver,
            "enzyme_commit": commit if commit is not None else "<unknown>",
        })

        if commit is not None:
            os.makedirs(f"/opt/compiler-explorer/{branch}", exist_ok=True)
            for lib in ["ClangEnzyme", "LLVMEnzyme"]:
                filename = f"{lib}-{version}.so"
                url = f"https://github.com/EnzymeAD/Enzyme/releases/download/nightly/{filename}"
                tmp_path = Path("/tmp") / filename
                dest_path = Path(f"/opt/compiler-explorer/{branch}") / filename
                
                print(f"Downloading {url} to {tmp_path}")
                try:
                    urllib.request.urlretrieve(url, tmp_path)
                    print(f"Moving {tmp_path} to {dest_path}")
                    shutil.move(str(tmp_path), str(dest_path))
                except Exception as e:
                    print(f"Error handling {filename}: {e}")

        if ejaxcommit is not None:
            os.makedirs(f"/opt/compiler-explorer/{branch}", exist_ok=True)

            for (filename, target) in [
                ("enzymexlamlir-opt", "enzyme-opttrunk"),
                ("hlo-translate", "hlo-translate"),
            ]:
                url = f"https://github.com/EnzymeAD/Enzyme-JAX/releases/download/nightly/{filename}"
                tmp_path = Path("/tmp") / filename
                dest_path = Path(f"/opt/compiler-explorer/{branch}") / target

                print(f"Downloading {url} to {tmp_path}")
                try:
                    urllib.request.urlretrieve(url, tmp_path)
                    os.chmod(str(tmp_path), 0o755)
                    print(f"Moving {tmp_path} to {dest_path}")
                    shutil.move(str(tmp_path), str(dest_path))
                except Exception as e:
                    print(f"Error handling {filename}: {e}")

        if reactant_commit is not None:
            os.makedirs(f"/opt/compiler-explorer/{branch}", exist_ok=True)

            for (filename, target) in [
                ("reactant-clang", "reactant-clang"),
            ]:
                url = f"https://github.com/EnzymeAD/Reactant/releases/download/nightly/{filename}"
                tmp_path = Path("/tmp") / filename
                dest_path = Path(f"/opt/compiler-explorer/{branch}") / target

                print(f"Downloading {url} to {tmp_path}")
                try:
                    urllib.request.urlretrieve(url, tmp_path)
                    os.chmod(str(tmp_path), 0o755)
                    print(f"Moving {tmp_path} to {dest_path}")
                    shutil.move(str(tmp_path), str(dest_path))
                except Exception as e:
                    print(f"Error handling {filename}: {e}")

    context = {
        "compilers": compiler_data,
        "julia_versions": julia_versions,
        "trunk_val": trunk_val,
        "enzymejax_commit": ejaxcommit if ejaxcommit is not None else "<unknown>",
        "reactant_commit": reactant_commit if reactant_commit is not None else "<unknown>",
        "poseidon_commit": installed_poseidon(),
    }


    # Map of internal group keys to their respective property files
    FILES_MAP = []

    if commit is not None or reactant_commit is not None or poseidon_commit is not None or len(sys.argv) == 4:
        FILES_MAP.append(("cuda", "cuda.enzyme.properties"))
        FILES_MAP.append(("cpp",  "c++.enzyme.properties"))
        FILES_MAP.append(("c",    "c.enzyme.properties"))
        FILES_MAP.append(("llvm", "llvm.enzyme.properties"))
    
    if ejaxcommit is not None or len(sys.argv) == 4:
        FILES_MAP.append(("mlir", "mlir.enzyme.properties"))
        FILES_MAP.append(("julia", "julia.enzyme.properties"))

    # 4. Render and write properties files
    for f_key, f_name in FILES_MAP:
        template_name = f"{f_name}.j2"
        template = env.get_template(template_name)
        rendered_content = template.render(context)
        
        output_path = SOURCE_CONFIG_DIR / f_name
        output_path.write_text(rendered_content)

    print("Successfully updated all configurations using Jinja2 templates.")

if __name__ == "__main__":
    main()
