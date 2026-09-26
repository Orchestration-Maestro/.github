"""What the organization's quality scripts share.

The GitHub CLI, the latest rust-workflows release, every repository with its
`stack`, rust-gate built at that release, and the pull request, one signed
commit, that publishes a change. Standard library only; `gh` reads its token
from GH_TOKEN.
"""

import base64
import hashlib
import json
import os
import subprocess
import sys
import urllib.request
from pathlib import Path

ORG = "Orchestration-Maestro"
WORKFLOWS = "rust-workflows"
# The branch every sync pull request comes from.
SYNC_BRANCH = "maestro/sync"

# The stacks `rust-gate sync` holds. `workflows` is rust-workflows itself, the
# home of the gate, whose CI, Dependabot settings and hooks are its own.
SYNCED = {"rust", "other"}

# jaq, the TOML and JSON reader rust-gate runs, at the version and digest
# rust-workflows pins in its own ci.yml.
JAQ_URL = (
    "https://github.com/01mf02/jaq/releases/download/v3.1.1/"
    "jaq-x86_64-unknown-linux-gnu"
)
JAQ_SHA256 = "5922c7b67d9bd6841d6676d1f954410c6bf04b47203dcb661c4f052dfef7f454"

COMMIT = """
mutation ($input: CreateCommitOnBranchInput!) {
  createCommitOnBranch(input: $input) { commit { oid } }
}
"""


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
    """Every repository that is not archived, with its `stack` or None.

    The repository list carries each repository's custom properties, which the
    organization bot reads through the Metadata permission every installation
    holds; the organization's property endpoint wants one the bot lacks."""
    pages = gh_json("api", "--paginate", "--slurp", f"orgs/{ORG}/repos?per_page=100")
    return sorted(
        (repo["name"], (repo.get("custom_properties") or {}).get("stack"))
        for page in pages
        for repo in page
        if not repo["archived"]
    )


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


def open_pull_request(repo, branch):
    """The open pull request from `branch`, or None."""
    found = gh_json(
        "pr", "list", "-R", f"{ORG}/{repo}", "--head", branch,
        "--state", "open", "--json", "number,createdAt,url",
    )
    return found[0] if found else None


def publish(repo, checkout, files, branch, title, text, merge):
    """Commit `files` on `branch` from the default branch's head, and open or
    update its pull request, queued to merge itself once green when `merge`."""
    head = run(["git", "rev-parse", "HEAD"], cwd=checkout).strip()
    reference = f"repos/{ORG}/{repo}/git/refs/heads/{branch}"
    try:
        run(["gh", "api", "-X", "PATCH", reference, "-f", f"sha={head}", "-F", "force=true"])
    except RuntimeError:
        run(["gh", "api", "-X", "POST", f"repos/{ORG}/{repo}/git/refs",
             "-f", f"ref=refs/heads/{branch}", "-f", f"sha={head}"])
    # `rust-gate sync` also deletes the files it no longer writes: a path gone
    # from the checkout is a deletion, every other one an addition.
    additions = [
        {"path": path, "contents": base64.b64encode((Path(checkout) / path).read_bytes()).decode()}
        for path in files
        if (Path(checkout) / path).is_file()
    ]
    deletions = [{"path": path} for path in files if not (Path(checkout) / path).exists()]
    body = {
        "query": COMMIT,
        "variables": {
            "input": {
                "branch": {"repositoryNameWithOwner": f"{ORG}/{repo}", "branchName": branch},
                "expectedHeadOid": head,
                "message": {"headline": title},
                "fileChanges": {"additions": additions, "deletions": deletions},
            }
        },
    }
    gh_json("api", "graphql", "--input", "-", stdin=json.dumps(body))
    existing = open_pull_request(repo, branch)
    if existing:
        number = str(existing["number"])
        run(["gh", "pr", "edit", number, "-R", f"{ORG}/{repo}", "--title", title, "--body", text])
    else:
        url = run(["gh", "pr", "create", "-R", f"{ORG}/{repo}", "--head", branch,
                   "--title", title, "--body", text]).strip()
        number = url.rsplit("/", 1)[-1]
    if merge:
        run(["gh", "pr", "merge", number, "-R", f"{ORG}/{repo}", "--auto", "--squash"])
    return number
