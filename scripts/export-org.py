#!/usr/bin/env python3
"""Export every Orchestration-Maestro setting that differs from GitHub's defaults.

Rewrites org/ from the live API. Run it again later and `git diff org/`: any
difference is drift between what is reviewed here and what GitHub enforces.
Needs `gh` authenticated with the admin:org scope. Standard library only.
"""

import json
import subprocess
import sys
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

ORG = "Orchestration-Maestro"
OUT = Path(__file__).resolve().parent.parent / "org"

# GitHub's defaults for a new organization. A field is exported only when the
# live value differs, so every line of org/settings.json is a decision.
ORG_DEFAULTS = {
    "advanced_security_enabled_for_new_repositories": False,
    "default_repository_branch": "main",
    "default_repository_permission": "read",
    "dependabot_alerts_enabled_for_new_repositories": False,
    "dependabot_security_updates_enabled_for_new_repositories": False,
    "dependency_graph_enabled_for_new_repositories": False,
    "deploy_keys_enabled_for_repositories": True,
    "display_commenter_full_name_setting_enabled": False,
    "has_organization_projects": True,
    "has_repository_projects": True,
    "members_can_change_repo_visibility": True,
    "members_can_create_internal_repositories": False,
    "members_can_create_pages": True,
    "members_can_create_private_pages": True,
    "members_can_create_private_repositories": True,
    "members_can_create_public_pages": True,
    "members_can_create_public_repositories": True,
    "members_can_create_repositories": True,
    "members_can_create_teams": True,
    "members_can_delete_issues": False,
    "members_can_delete_repositories": True,
    "members_can_fork_private_repositories": False,
    "members_can_invite_outside_collaborators": True,
    "members_can_view_dependency_insights": True,
    "readers_can_create_discussions": True,
    "secret_scanning_enabled_for_new_repositories": False,
    "secret_scanning_push_protection_custom_link_enabled": False,
    "secret_scanning_push_protection_enabled_for_new_repositories": False,
    "secret_scanning_validity_checks_enabled": False,
    "two_factor_requirement_enabled": False,
    "web_commit_signoff_required": False,
}

# Profile, identity and counters: not policy, never exported. billing_email is
# personal data and this repository is public.
ORG_IGNORED = {
    "archived_at", "avatar_url", "billing_email", "blog", "collaborators",
    "company", "created_at", "description", "disk_usage", "email",
    "events_url", "followers", "following", "hooks_url", "html_url", "id",
    "is_verified", "issues_url", "location", "login", "members_allowed_repository_creation_type",
    "members_url", "name", "node_id", "owned_private_repos", "plan",
    "private_gists", "public_gists", "public_members_url", "public_repos",
    "repos_url", "secret_scanning_push_protection_custom_link",
    "total_private_repos", "twitter_username", "type", "updated_at", "url",
}

# Actions endpoint -> its defaults. selected-actions has none: it only exists
# once allowed_actions is "selected", and is then exported whole.
ACTIONS_DEFAULTS = {
    "permissions": {"allowed_actions": "all", "enabled_repositories": "all", "sha_pinning_required": False},
    "permissions/workflow": {"can_approve_pull_request_reviews": False, "default_workflow_permissions": "read"},
    "permissions/artifact-and-log-retention": {"days": 90},
    "permissions/fork-pr-contributor-approval": {"approval_policy": "first_time_contributors"},
    "permissions/self-hosted-runners": {"enabled_repositories": "all"},
}

VOLATILE = {"_links", "created_at", "current_user_can_bypass", "html_url", "id", "node_id",
            "source", "source_type", "target_type", "updated_at", "url"}


def gh(path):
    return subprocess.run(["gh", "api", f"orgs/{ORG}{path}"], capture_output=True, text=True)


def parsed(path, stdout):
    try:
        return json.loads(stdout)
    except json.JSONDecodeError as error:
        # A partial export would read as a reviewed state; stop instead.
        sys.exit(f"orgs/{ORG}{path} did not return JSON: {error}")


def api(path):
    result = gh(path)
    if result.returncode != 0:
        sys.exit(f"orgs/{ORG}{path} failed: {result.stderr.strip()}")
    return parsed(path, result.stdout)


def api_optional(path):
    result = gh(path)
    return parsed(path, result.stdout) if result.returncode == 0 else None


def write(relative, data):
    path = OUT / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"wrote org/{relative}")


def differing(live, defaults):
    return {key: live[key] for key in defaults if key in live and live[key] != defaults[key]}


def stripped(obj):
    return {key: value for key, value in obj.items() if key not in VOLATILE}


def webhook(hook):
    config = hook.get("config", {})
    url = urlsplit(config.get("url", ""))
    host = f"{url.hostname}:{url.port}" if url.port else (url.hostname or "")
    return {
        "active": hook.get("active"),
        "content_type": config.get("content_type"),
        "events": sorted(hook.get("events", [])),
        "insecure_ssl": config.get("insecure_ssl"),
        "name": hook.get("name"),
        # Scheme, host and path only: user-info or a query string can carry a credential.
        "url": urlunsplit((url.scheme, host, url.path, "", "")),
    }


def main():
    org = api("")
    unknown = sorted(set(org) - set(ORG_DEFAULTS) - ORG_IGNORED)
    if unknown:
        # A field GitHub added since this table was written: review it rather than drop it.
        print(f"warning: unclassified organization fields: {', '.join(unknown)}", file=sys.stderr)
    write("settings.json", differing(org, ORG_DEFAULTS))

    actions = {}
    for endpoint, defaults in ACTIONS_DEFAULTS.items():
        changed = differing(api(f"/actions/{endpoint}"), defaults)
        if changed:
            actions[endpoint.replace("permissions/", "") or endpoint] = changed
    if actions.get("permissions", {}).get("allowed_actions") == "selected":
        actions["selected-actions"] = api("/actions/permissions/selected-actions")
    write("actions.json", actions)

    write("custom-properties.json", [stripped(p) for p in api("/properties/schema")])

    defaults = {d["configuration"]["name"]: d["default_for_new_repos"]
                for d in api("/code-security/configurations/defaults")}
    configurations = []
    for config in api("/code-security/configurations?per_page=100"):
        if config.get("target_type") != "organization":
            continue  # GitHub's built-in configurations are not decisions made here.
        entry = stripped(config)
        entry["default_for_new_repos"] = defaults.get(config["name"], "none")
        configurations.append(entry)
    write("security-configurations.json", configurations)

    rulesets_dir = OUT / "rulesets"
    live_names = set()
    for summary in api("/rulesets?per_page=100"):
        ruleset = stripped(api(f"/rulesets/{summary['id']}"))
        live_names.add(ruleset["name"])
        write(f"rulesets/{ruleset['name']}.json", ruleset)
    for stale in rulesets_dir.glob("*.json"):
        if stale.stem not in live_names:
            stale.unlink()  # Deleted live: the removal shows up in git diff.
            print(f"removed org/rulesets/{stale.name}")

    hooks = api_optional("/hooks?per_page=100")
    if hooks is None:
        # Needs the admin:org_hook scope, or "Webhooks" read on a fine-grained token.
        print("warning: webhooks not readable with this token; org/webhooks.json left as is",
              file=sys.stderr)
    else:
        write("webhooks.json", sorted((webhook(h) for h in hooks), key=lambda h: h["url"]))


if __name__ == "__main__":
    main()
