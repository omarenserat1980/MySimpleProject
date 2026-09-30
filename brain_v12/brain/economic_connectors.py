"""Read-only economic opportunity and payment-verification connectors.

External writes and money movement are deliberately separated from discovery.
No secrets, private keys, or seed phrases are stored here.
"""
from __future__ import annotations
import json, os, urllib.request
from dataclasses import dataclass, asdict

@dataclass
class Opportunity:
    source:str; opportunity_id:str; title:str; amount:float|None
    currency:str|None; url:str|None; status:str; evidence:dict

class BasedAgentsAdapter:
    name="basedagents"
    def discover(self, limit=25):
        url=os.getenv("BASEDAGENTS_TASKS_URL","https://api.basedagents.ai/v1/tasks?status=open")
        try:
            with urllib.request.urlopen(url, timeout=10) as r: data=json.load(r)
        except Exception as e: return {"source":self.name,"ok":False,"error":str(e),"opportunities":[]}
        rows=data.get("tasks",data if isinstance(data,list) else [])
        out=[]
        for x in rows[:limit]:
            bounty=x.get("bounty") or {}
            out.append(asdict(Opportunity(
                self.name,str(x.get("task_id") or x.get("id","")),
                x.get("title",""),float(bounty["amount"])/1e6 if bounty.get("amount") else None,
                bounty.get("token"),x.get("url"),x.get("status","open"),
                {"api_observed":True,"payment_field_present":bool(bounty)}
            )))
        return {"source":self.name,"ok":True,"opportunities":out}

class AgentBountiesAdapter:
    name="agent_bounties"
    def discover(self, limit=25):
        url=os.getenv("AGENT_BOUNTIES_FEED_URL","https://agent-bounties-api.onrender.com/v1/base/autonomous-bounties/feed?network=base-mainnet&claimable_only=true")
        try:
            with urllib.request.urlopen(url, timeout=12) as r: data=json.load(r)
        except Exception as e: return {"source":self.name,"ok":False,"error":str(e),"opportunities":[]}
        rows=data.get("bounties",data if isinstance(data,list) else [])
        out=[]
        for x in rows[:limit]:
            reward=x.get("solver_reward") or x.get("reward") or x.get("amount")
            try: amount=float(reward) if reward is not None else None
            except: amount=None
            out.append(asdict(Opportunity(
                self.name,str(x.get("bounty_id") or x.get("id","")),x.get("title","Autonomous bounty"),
                amount,"USDC",x.get("source_url"),x.get("lifecycle","claimable"),
                {"canonical_feed":True,"claimable_only":True}
            )))
        return {"source":self.name,"ok":True,"opportunities":out}

class GitHubBountyAdapter:
    name="github_bounties"
    def discover(self, limit=25):
        # Search only public metadata; a GitHub comment/issue is never payment evidence.
        url=os.getenv("GITHUB_BOUNTY_SEARCH_URL","https://api.github.com/search/issues?q=label%3Abounty+state%3Aopen&per_page=25")
        req=urllib.request.Request(url,headers={"Accept":"application/vnd.github+json","User-Agent":"Brain-Economic-Router"})
        try:
            with urllib.request.urlopen(req, timeout=12) as r: data=json.load(r)
        except Exception as e: return {"source":self.name,"ok":False,"error":str(e),"opportunities":[]}
        out=[]
        for x in data.get("items",[])[:limit]:
            out.append(asdict(Opportunity(self.name,str(x.get("id")),x.get("title",""),None,None,x.get("html_url"),"open",
                {"github_metadata_only":True,"payment_proof":False})))
        return {"source":self.name,"ok":True,"opportunities":out}

class OpportunityRouter:
    def __init__(self, adapters=None):
        self.adapters=adapters or [BasedAgentsAdapter(),AgentBountiesAdapter(),GitHubBountyAdapter()]
    def discover(self, limit_each=25):
        results=[a.discover(limit_each) for a in self.adapters]
        ops=[o for r in results if r.get("ok") for o in r["opportunities"]]
        # Never rank by advertised amount alone.
        ops.sort(key=lambda x:(x["evidence"].get("canonical_feed",False), x.get("amount") or 0), reverse=True)
        return {"sources":results,"opportunities":ops}

if __name__=="__main__":
    print(json.dumps(OpportunityRouter().discover(5),ensure_ascii=False,indent=2))
