from brain_v12.intelligence.domains import *
from brain_v12.intelligence.social import *
from brain_v12.intelligence.political import *
from brain_v12.intelligence.economic import *
from brain_v12.intelligence.defense import *

def test_assessment():
    a=IntelligenceAssessment(IntelligenceDomain.SOCIAL,"q",("fact",),(),("s",),.8,("source",))
    assert validate(a)

def test_domains():
    assert ready(SocialAnalysis("p",("i",),("d",),("m",),.8))
    assert ready(PoliticalAnalysis("J","2026",("i",),("policy",),("position",),("source",)))
    assert ready(EconomicAnalysis("J","2026",("GDP",),("d",),("r",),("source",)))
    assert ready(DefenseAnalysis("R","2026",("a",),("strategy",),("risk",),("source",)))
