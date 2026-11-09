"""Inspect local release artifacts without network access or package execution."""

import ast
import configparser
import hashlib
import re
import stat
import tarfile
import tomllib
from email import message_from_bytes
from pathlib import Path, PurePosixPath
from zipfile import ZipFile


def safe_path(name):
    path = PurePosixPath(name)
    assert not path.is_absolute() and ".." not in path.parts, "Unsafe archive path"


def main():
    project = tomllib.loads(Path("pyproject.toml").read_text())["project"]
    version = project["version"]
    assert re.fullmatch(r"(?:0|[1-9][0-9]*)(?:\.(?:0|[1-9][0-9]*)){2}", version), (
        "Release versions must use x.y.z without prefixes or suffixes"
    )
    tree = ast.parse(Path("src/jupyhop/__init__.py").read_text())
    declared = next(
        ast.literal_eval(node.value)
        for node in tree.body
        if isinstance(node, ast.Assign)
        and any(
            isinstance(target, ast.Name) and target.id == "__version__" for target in node.targets
        )
    )
    assert version == declared, "Client and package versions differ"
    wheels = list(Path("dist").glob("*.whl"))
    sources = list(Path("dist").glob("*.tar.gz"))
    assert len(wheels) == len(sources) == 1, "Keep exactly one release wheel/sdist in dist"
    wheel, source = wheels[0], sources[0]
    assert wheel.name == f"jupyhop-{version}-py3-none-any.whl"
    assert source.name == f"jupyhop-{version}.tar.gz"
    with ZipFile(wheel) as artifact:
        names = artifact.namelist()
        assert len(set(names)) == len(names), "Duplicate wheel members"
        for entry in artifact.infolist():
            safe_path(entry.filename)
            assert not stat.S_ISLNK(entry.external_attr >> 16), "Wheel symlink"
            assert entry.filename.startswith(("jupyhop/", f"jupyhop-{version}.dist-info/"))
        prefix = f"jupyhop-{version}.dist-info/"
        meta = message_from_bytes(artifact.read(prefix + "METADATA"))
        assert meta["Name"] == "jupyhop" and meta["Version"] == version
        assert meta["License-Expression"] == "MIT"
        assert meta["Requires-Python"] == project["requires-python"]
        assert set(meta.get_all("Project-URL", [])) == {
            f"{label}, {url}" for label, url in project["urls"].items()
        }
        assert all("extra ==" in dependency for dependency in meta.get_all("Requires-Dist", []))
        assert {f"Programming Language :: Python :: 3.{minor}" for minor in range(11, 15)} <= set(
            meta.get_all("Classifier", [])
        )
        assert artifact.read(prefix + "licenses/LICENSE") == Path("LICENSE").read_bytes()
        entrypoints = configparser.ConfigParser()
        entrypoints.read_string(artifact.read(prefix + "entry_points.txt").decode())
        assert dict(entrypoints["console_scripts"]) == {"jupyhop": "jupyhop.cli:main"}
        for path in Path("src/jupyhop").glob("*.py"):
            assert artifact.read("jupyhop/" + path.name) == path.read_bytes()
        assert "jupyhop/py.typed" in names
    with tarfile.open(source) as artifact:
        entries = artifact.getmembers()
        names = [entry.name for entry in entries]
        assert len(set(names)) == len(names), "Duplicate sdist members"
        for entry in entries:
            safe_path(entry.name)
            assert not entry.name.startswith(f"jupyhop-{version}/docs/_build/"), (
                "Generated documentation must not enter source distributions"
            )
            assert entry.isdir() or entry.isfile(), "Unexpected sdist member type"
            assert entry.name == f"jupyhop-{version}" or entry.name.startswith(
                f"jupyhop-{version}/"
            )
        required = [
            Path(name)
            for name in (
                "LICENSE",
                "README.md",
                "CHANGELOG.md",
                "CONTRIBUTING.md",
                "SECURITY.md",
                "pyproject.toml",
                "docs/Makefile",
            )
        ]
        for root, pattern in (
            ("src/jupyhop", "*.py"),
            ("docs", "*.md"),
            ("docs", "*.py"),
            ("docs", "*.css"),
            ("devguide", "*.md"),
            ("tests", "*.py"),
            ("experiments", "*.py"),
            ("experiments", "*.md"),
            ("devtools", "*.yaml"),
            ("devtools", "*.sh"),
            (".github", "*.yml"),
            (".github", "*.yaml"),
        ):
            required.extend(
                path for path in Path(root).rglob(pattern) if not path.is_relative_to("docs/_build")
            )
        for path in required:
            stream = artifact.extractfile(f"jupyhop-{version}/" + path.as_posix())
            assert stream is not None and stream.read() == path.read_bytes(), path
    checksums = []
    for artifact in (wheel, source):
        line = hashlib.sha256(artifact.read_bytes()).hexdigest() + "  " + artifact.name
        checksums.append(line)
        print(line)
    Path("dist/SHA256SUMS").write_text("\n".join(checksums) + "\n", encoding="ascii")
    print(
        "PASS: matching release versions, MIT metadata, entrypoint, zero mandatory dependencies and complete safe artifacts"
    )


if __name__ == "__main__":
    main()
