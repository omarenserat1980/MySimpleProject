from brain_v12.marketing.skill_passport import SkillEvidence, assess_skill, expert_claim_allowed

def test_no_evidence_is_unassessed():
    s=assess_skill("copywriting",())
    assert s.level=="UNASSESSED"
    assert not expert_claim_allowed(s)

def test_course_score_does_not_make_expert():
    s=assess_skill("copywriting",(SkillEvidence("copywriting","course",.95,False),))
    assert s.level=="ADVANCED"
    assert not expert_claim_allowed(s)

def test_expert_requires_real_world_evidence():
    s=assess_skill("copywriting",(
        SkillEvidence("copywriting","exp1",.95,True),
        SkillEvidence("copywriting","exp2",.92,True),
    ))
    assert s.level=="EXPERT"
    assert expert_claim_allowed(s)
