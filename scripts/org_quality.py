"""What the organization's quality scripts share.

The GitHub CLI, the latest maestro-rust-workflows release, every repository with its
`stack`, and the pull request, one signed
commit, that publishes a change. Standard library only; `gh` reads its token
from GH_TOKEN.
"""

import base64
import json
import subprocess
import uuid
from pathlib import Path

ORG = "Orchestration-Maestro"
WORKFLOWS = "maestro-rust-workflows"
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
    """The latest maestro-rust-workflows release: its tag and the commit it names."""
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
    temporary = f"fix/sync-build-{uuid.uuid4().hex}"
    # A path gone from the checkout is a deletion; every other one is an addition.
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
                "branch": {"repositoryNameWithOwner": f"{ORG}/{repo}", "branchName": temporary},
                "expectedHeadOid": head,
                "message": {"headline": title},
                "fileChanges": {"additions": additions, "deletions": deletions},
            }
        },
    }
    # Keep GitHub's signed commit, without ever emptying an existing PR branch.
    run(["gh", "api", "-X", "POST", f"repos/{ORG}/{repo}/git/refs",
         "-f", f"ref=refs/heads/{temporary}", "-f", f"sha={head}"])
    try:
        result = gh_json("api", "graphql", "--input", "-", stdin=json.dumps(body))
        commit = result["data"]["createCommitOnBranch"]["commit"]["oid"]
        try:
            run(["gh", "api", "-X", "PATCH", reference,
                 "-f", f"sha={commit}", "-F", "force=true"])
        except RuntimeError:
            run(["gh", "api", "-X", "POST", f"repos/{ORG}/{repo}/git/refs",
                 "-f", f"ref=refs/heads/{branch}", "-f", f"sha={commit}"])
    finally:
        run(["gh", "api", "-X", "DELETE",
             f"repos/{ORG}/{repo}/git/refs/heads/{temporary}"])
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
