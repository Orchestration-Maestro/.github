"""What the organization's quality scripts share.

The GitHub CLI, the latest rust-workflows release, every repository with its
`stack`, and rust-gate built at that release. Standard library only; `gh` reads
its token from GH_TOKEN.
"""

import hashlib
import json
import os
import subprocess
import sys
import urllib.request
from pathlib import Path

ORG = "Orchestration-Maestro"
WORKFLOWS = "rust-workflows"

# The stacks `rust-gate sync` holds. `workflows` is rust-workflows itself, the
# home of the gate, whose caller, Dependabot settings and hooks are its own.
SYNCED = {"rust", "other"}

# jaq, the TOML and JSON reader rust-gate runs, at the version and digest
# rust-workflows pins in its own ci.yml.
JAQ_URL = (
    "https://github.com/01mf02/jaq/releases/download/v3.1.1/"
    "jaq-x86_64-unknown-linux-gnu"
)
JAQ_SHA256 = "5922c7b67d9bd6841d6676d1f954410c6bf04b47203dcb661c4f052dfef7f454"


def run(args, cwd=None, env=None, stdin=None):
    """Run a command and return its stdout; stop the script when it fails."""
    result = subprocess.run(
        args, cwd=cwd, env=env, input=stdin, capture_output=True, text=True
    )
    if result.returncode != 0:
        raise RuntimeError(f"{' '.join(args[:3])} failed: {result.stderr.strip()}")
    return result.stdout


def gh_json(*args, stdin=None):
    """A `gh` call whose output is JSON."""
    return json.loads(run(["gh", *args], stdin=stdin) or "null")


def latest_release():
    """The latest rust-workflows release: its tag and the commit it names."""
    tag = gh_json("release", "view", "-R", f"{ORG}/{WORKFLOWS}", "--json", "tagName")[
        "tagName"
    ]
    sha = gh_json("api", f"repos/{ORG}/{WORKFLOWS}/commits/{tag}")["sha"]
    return tag, sha


def repositories():
    """Every repository that is not archived, with its `stack` or None."""
    values = gh_json("api", "--paginate", f"orgs/{ORG}/properties/values")
    stacks = {
        entry["repository_name"]: next(
            (p["value"] for p in entry["properties"] if p["property_name"] == "stack"),
            None,
        )
        for entry in values
    }
    listed = gh_json(
        "repo", "list", ORG, "--no-archived", "--limit", "500", "--json", "name"
    )
    return sorted((repo["name"], stacks.get(repo["name"])) for repo in listed)


def install_gate(tag, directory):
    """rust-gate built at `tag` and the pinned jaq, in `directory`/bin."""
    directory = Path(directory)
    run(
        [
            "cargo", "install", "--locked", "--quiet",
            "--git", f"https://github.com/{ORG}/{WORKFLOWS}",
            "--tag", tag, "--root", str(directory), "rust-gate",
        ]
    )
    binary = directory / "bin" / "jaq"
    with urllib.request.urlopen(JAQ_URL, timeout=60) as response:
        data = response.read()
    if hashlib.sha256(data).hexdigest() != JAQ_SHA256:
        sys.exit("jaq does not match the digest rust-workflows pins")
    binary.write_bytes(data)
    binary.chmod(0o755)
    return directory / "bin"


def with_gate(gate_bin, **extra):
    """The environment rust-gate runs in: its directory first on PATH."""
    env = dict(os.environ, **extra)
    env["PATH"] = f"{gate_bin}{os.pathsep}{env.get('PATH', '')}"
    return env


def clone(repo, directory):
    """A shallow clone of `repo`'s default branch in `directory`."""
    run(["gh", "repo", "clone", f"{ORG}/{repo}", str(directory), "--", "--depth", "1", "--quiet"])
    return Path(directory)


def sync_pull_request(repo):
    """The open pull request from `maestro/sync`, or None."""
    found = gh_json(
        "pr", "list", "-R", f"{ORG}/{repo}", "--head", "maestro/sync",
        "--state", "open", "--json", "number,createdAt,url",
    )
    return found[0] if found else None
