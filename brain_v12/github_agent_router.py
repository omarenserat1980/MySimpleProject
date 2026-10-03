"""Brain GitHub Agent Router: map intent to the unified GitHub control plane."""
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
        "code_write": GitHubRoute("contents","code.write","write_contents",True),
    }
    def __init__(self, control_plane: GitHubControlPlane | None = None):
        self.github = control_plane or GitHubControlPlane()
    def plan(self, intent: str) -> GitHubRoute:
        key=intent.strip().lower().replace("-","_").replace(" ","_")
        if key not in self.ROUTES: raise ValueError(f"UNSUPPORTED_GITHUB_INTENT:{intent}")
        return self.ROUTES[key]
    def catalog(self):
        return {"ok":True,"routes":{k:{"domain":v.domain,"capability":v.capability,"action":v.action,"requires_approval":v.requires_approval} for k,v in self.ROUTES.items()}}
