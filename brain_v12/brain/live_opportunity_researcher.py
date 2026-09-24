"""Live public opportunity researcher for Electronic Brain V12.

It reads public job-listing pages, extracts concrete listing URLs/titles, and
hands only fresh evidence to IncomeEngine. It never submits offers or logs in.
"""
from __future__ import annotations
from datetime import datetime, timezone
from html.parser import HTMLParser
import re
import httpx
from urllib.parse import urljoin


class _Links(HTMLParser):
    def __init__(self):
        super().__init__(); self.items=[]; self.href=None; self.buf=[]
    def handle_starttag(self, tag, attrs):
        if tag.lower() == "a":
            d=dict(attrs); self.href=d.get("href"); self.buf=[]
    def handle_data(self, data):
        if self.href is not None: self.buf.append(data)
    def handle_endtag(self, tag):
        if tag.lower()=="a" and self.href is not None:
            text=re.sub(r"\s+"," "," ".join(self.buf)).strip()
            if text and self.href: self.items.append((self.href,text[:500]))
            self.href=None; self.buf=[]


class LiveOpportunityResearcher:
    SOURCES = (
        ("Mostaql Programming", "https://mostaql.com/projects/skill/برمجة"),
        ("Mostaql Python", "https://mostaql.com/projects/skill/python?page=1"),
        ("Mostaql API", "https://mostaql.com/projects/skill/API"),
        ("Upwork WhatsApp API", "https://www.upwork.com/freelance-jobs/whatsapp-api/"),
        ("Freelancer WordPress", "https://www.freelancer.com/jobs/wordpress"),
        ("AI Trainer Arabic", "https://www.aitrainer.work/jobs/arabic"),
    )
    def __init__(self, income_engine, store):
        self.income_engine=income_engine; self.store=store
    def _fetch(self,url):
        r=httpx.get(url,headers={"User-Agent":"ElectronicBrainV12/1.0 (+public-opportunity-research)"},timeout=25,follow_redirects=True)
        r.raise_for_status(); return r.text
    def _extract(self,source,url,html):
        parser=_Links(); parser.feed(html); now=datetime.now(timezone.utc).isoformat()
        out=[]; seen=set()
        for href,title in parser.items:
            low=title.lower()
            if len(title)<8 or len(title)>300: continue
            if any(x in low for x in ("login","sign up","register","privacy","cookie","home","categories","search jobs")): continue
            if not any(x in href.lower() for x in ("/jobs/","/project/","/projects/","/freelance-jobs/apply/")): continue
            if href.startswith("/"):
                href=urljoin(url, href)
            if not href.startswith("http") or href in seen: continue
            seen.add(href)
            out.append({"title":title,"url":href,"source":source,"retrieved_at":now,
                        "requirements":f"تفاصيل المتطلبات موجودة في الإعلان الأصلي: {href}","evidence":f"Public listing link extracted from {url}: {href}","category":"FREELANCE_JOB","score":0.7})
            if len(out)>=30: break
        return out
    def run_once(self):
        found=[]; errors=[]
        for source,url in self.SOURCES:
            try: found.extend(self._extract(source,url,self._fetch(url)))
            except Exception as exc: errors.append({"source":source,"error":str(exc)[:500]})
        accepted=self.income_engine.ingest_live_opportunities(found,max_age_hours=72)
        result={"ok":bool(accepted) or not errors,"received":len(found),"accepted":len(accepted),"errors":errors,
                "retrieved_at":datetime.now(timezone.utc).isoformat()}
        self.store.event("LIVE_INCOME_SEARCH_COMPLETED",result)
        return result
