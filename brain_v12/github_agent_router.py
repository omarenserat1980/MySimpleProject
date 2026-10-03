"""Brain GitHub Agent Router: map natural intents to the unified GitHub control plane."""
from __future__ import annotations
from dataclasses import dataclass
from .github_control_plane import GitHubControlPlane

@dataclass(frozen=True)
class GitHubRoute:
    domain: str
    capability: str
    action: str
    requires_approval: bool

class GitHubAgentRouter:
    ROUTES = {
        "repository": GitHubRoute("repositories","repo.read","repository",False),
        "code": GitHubRoute("contents","code.read","contents",False),
        "issue": GitHubRoute("issues","issues.read","issues",False),
        "pull_request": GitHubRoute("pull-requests","pulls.read","pull_request",False),
        "actions": GitHubRoute("actions","actions.read","actions_runs",False),
        "release": GitHubRoute("releases","releases.read","releases",False),
        "search": GitHubRoute("search","search.read","search",False),
        "branch": GitHubRoute("branches","repo.read","search_branches",False),
        "commit": GitHubRoute("commits","code.read","search_commits",False),
        "review": GitHubRoute("reviews","pulls.read","reviews",False),
        "code_write": GitHubRoute("contents","code.write","write_contents",True),
        "issue_write": GitHubRoute("issues","issues.write","update_issue",True),
        "pull_request_write": GitHubRoute("pull-requests","pulls.write","update_pull_request",True),
        "branch_write": GitHubRoute("branches","repo.write","create_branch",True),
        "release_write": GitHubRoute("releases","releases.write","create_release",True),
        "workflow_write": GitHubRoute("actions","actions.write","rerun_workflow_job",True),
    }
    KEYWORD_ALIASES = {
        "pr":"pull_request", "pull":"pull_request", "pull_request":"pull_request",
        "issue":"issue", "issues":"issue", "workflow":"actions", "workflows":"actions",
        "action":"actions", "actions":"actions", "release":"release", "releases":"release",
        "repo":"repository", "repository":"repository", "code":"code", "file":"code", "files":"code",
        "branch":"branch", "branches":"branch", "commit":"commit", "commits":"commit",
        "review":"review", "reviews":"review", "search":"search", "find":"search",
        "edit":"code_write", "modify":"code_write", "write":"code_write",
        "issue_write":"issue_write", "pr_write":"pull_request_write", "branch_write":"branch_write",
        "release_write":"release_write", "workflow_write":"workflow_write",
    }
    def __init__(self, control_plane: GitHubControlPlane | None = None):
        self.github = control_plane or GitHubControlPlane()
    def plan(self, intent: str) -> GitHubRoute:
        key=intent.strip().lower().replace("-","_").replace(" ","_")
        key=self.KEYWORD_ALIASES.get(key,key)
        if key not in self.ROUTES: raise ValueError(f"UNSUPPORTED_GITHUB_INTENT:{intent}")
        return self.ROUTES[key]
    def catalog(self):
        return {"ok":True,"routes":{k:{"domain":v.domain,"capability":v.capability,"action":v.action,"requires_approval":v.requires_approval} for k,v in self.ROUTES.items()},"keyword_aliases":self.KEYWORD_ALIASES}
