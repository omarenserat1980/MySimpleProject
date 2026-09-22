import os
from brain.openai_provider import OpenAIProvider

def test_openai_provider_requires_server_key(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    p=OpenAIProvider()
    result=p.respond("مرحبا")
    assert result["error"]=="OPENAI_NOT_CONFIGURED"

def test_openai_provider_parses_response(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY","test-key")
    monkeypatch.setenv("OPENAI_MODEL","gpt-test")
    class Response:
        status_code=200
        def json(self):
            return {"id":"resp_test","output_text":"مرحبا من ChatGPT"}
    class Client:
        def __init__(self, *args, **kwargs): pass
        def __enter__(self): return self
        def __exit__(self,*args): pass
        def post(self,*args,**kwargs): return Response()
    monkeypatch.setattr("brain.openai_provider.httpx.Client",Client)
    result=OpenAIProvider().respond("مرحبا")
    assert result["ok"] is True
    assert result["reply"]=="مرحبا من ChatGPT"
    assert result["model"]=="gpt-test"
