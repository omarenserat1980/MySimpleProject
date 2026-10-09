from platform_foundation.persistent_state import SQLiteStateStore
from platform_foundation.research_agent import ResearchAgent

def test_ingest_deduplicates(tmp_path):
    a=ResearchAgent(SQLiteStateStore(tmp_path/"r.db"))
    data=[{"title":"A","url":"https://example.com/a#x","excerpt":"e","confidence":0.9},{"title":"A","url":"https://example.com/a#y","excerpt":"e","confidence":0.9},{"title":"B","url":"https://example.org/b","excerpt":"e2","confidence":0.7}]
    r=a.ingest(query="test   query",results=data)
    assert len(r.evidence)==2
    assert r.unique_sources==2
    assert len(a.evidence("test query"))==2

def test_requires_adapter(tmp_path):
    a=ResearchAgent(SQLiteStateStore(tmp_path/"r.db"))
    try: a.search("x"); assert False
    except RuntimeError: pass

def test_rejects_invalid_source(tmp_path):
    a=ResearchAgent(SQLiteStateStore(tmp_path/"r.db"))
    try: a.ingest(query="x",results=[{"url":"file:///secret","title":"x","excerpt":"y","confidence":1}]); assert False
    except ValueError: pass

def test_injected_search(tmp_path):
    def fetch(q):
        return [{"title":q,"url":"https://example.com","excerpt":"verified","confidence":0.8}]
    a=ResearchAgent(SQLiteStateStore(tmp_path/"r.db"),fetch=fetch)
    assert a.search("hello").confidence==0.8
