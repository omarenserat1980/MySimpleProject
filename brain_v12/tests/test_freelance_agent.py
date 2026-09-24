from brain_v12.brain.freelance_agent import FreelanceAgent, PROFILE


class StoreStub:
    def __init__(self):
        self.events = []
        self.verified = 0

    def event(self, name, payload):
        self.events.append((name, payload))

    def income_summary(self):
        return {"verified": self.verified}


def test_profile_and_fit():
    agent = FreelanceAgent(StoreStub())
    result = agent.analyze({
        "title": "تطوير موقع ASP.NET وربط WhatsApp",
        "requirements": "C# .NET REST API",
    })
    assert result["fit_score"] >= 55
    assert "web" in result["categories"]
    assert "C#" in result["matched_skills"]


def test_offer_is_prepared_but_not_submitted():
    agent = FreelanceAgent(StoreStub())
    result = agent.prepare_offer({
        "title": "إضافة منتجات إلى متجر",
        "requirements": "إدخال المنتجات والأسعار والوصف",
    })
    assert result["ok"] is True
    assert result["submission_status"] == "NOT_SUBMITTED"
    assert "proposal" in result


def test_external_status_requires_evidence():
    store = StoreStub()
    agent = FreelanceAgent(store)
    assert agent.record_application("x", "SUBMITTED")["status"] == "EVIDENCE_REQUIRED"
    assert agent.record_application("x", "SUBMITTED", "لقطة/رابط موثق")["ok"] is True


def test_payment_requires_positive_amount_and_evidence():
    agent = FreelanceAgent(StoreStub())
    assert agent.record_verified_payment("x", 0, "")["ok"] is False
    result = agent.record_verified_payment("x", 10, "إثبات دفع قابل للمراجعة")
    assert result["status"] == "VERIFIED"
