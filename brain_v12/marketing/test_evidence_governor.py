from brain_v12.marketing.evidence_governor import (
    EvidenceGrade, EvidenceItem, allow_for_action, grade
)

def test_course_like_weak_evidence_does_not_become_truth():
    e=EvidenceItem("course-1","course",.55,1,False)
    assert grade(e) is EvidenceGrade.WEAK
    assert not allow_for_action((e,),high_impact=True)

def test_real_result_can_be_strong():
    e=EvidenceItem("exp-1","experiment",.90,2,True)
    assert grade(e) is EvidenceGrade.STRONG
    assert allow_for_action((e,),high_impact=True)
