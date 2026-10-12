from brain_v12.marketing.university import (
    COURSES, AssessmentKind, AssessmentResult, course_complete, next_courses
)

def test_foundation_exists():
    assert COURSES[0].course_id=="MKT-101"

def test_completion_requires_all_assessments():
    c=COURSES[0]
    assert not course_complete(c,(AssessmentResult("MKT-101",AssessmentKind.QUIZ,.9),))
    assert course_complete(c,(
        AssessmentResult("MKT-101",AssessmentKind.QUIZ,.9,"q1"),
        AssessmentResult("MKT-101",AssessmentKind.CASE,.8,"case1"),
    ))

def test_next_course_respects_prerequisites():
    nxt=next_courses({"MKT-101"})
    assert any(c.course_id=="MKT-201" for c in nxt)
