"""Brain Marketing University: competency-based curriculum."""
from __future__ import annotations
from dataclasses import dataclass
from enum import Enum

class AssessmentKind(str, Enum):
    QUIZ="QUIZ"
    CASE="CASE"
    PROJECT="PROJECT"
    EXPERIMENT="EXPERIMENT"

@dataclass(frozen=True)
class Course:
    course_id: str
    domain: str
    title: str
    prerequisites: tuple[str, ...]
    assessments: tuple[AssessmentKind, ...]
    competency_threshold: float = .75

COURSES=(
    Course("MKT-101","strategy","Marketing Foundations",(),(AssessmentKind.QUIZ,AssessmentKind.CASE)),
    Course("MKT-201","consumer","Consumer Psychology",("MKT-101",),(AssessmentKind.QUIZ,AssessmentKind.CASE)),
    Course("MKT-301","brand","Positioning & Brand",("MKT-101","MKT-201"),(AssessmentKind.CASE,AssessmentKind.PROJECT)),
    Course("MKT-401","content","Content Strategy & Copy",("MKT-301",),(AssessmentKind.PROJECT,)),
    Course("MKT-402","seo","SEO & Search Growth",("MKT-401",),(AssessmentKind.QUIZ,AssessmentKind.PROJECT)),
    Course("MKT-501","growth","Growth Systems",("MKT-402",),(AssessmentKind.CASE,AssessmentKind.EXPERIMENT)),
    Course("MKT-601","analytics","Marketing Analytics & Experiments",("MKT-501",),(AssessmentKind.QUIZ,AssessmentKind.EXPERIMENT)),
    Course("MKT-701","ai_marketing","AI Marketing Systems",("MKT-601",),(AssessmentKind.PROJECT,AssessmentKind.EXPERIMENT)),
    Course("MKT-801","leadership","Marketing Leadership & Governance",("MKT-701",),(AssessmentKind.CASE,AssessmentKind.PROJECT)),
)

@dataclass(frozen=True)
class AssessmentResult:
    course_id: str
    kind: AssessmentKind
    score: float
    evidence_ref: str = ""

def course_complete(course: Course, results: tuple[AssessmentResult,...]) -> bool:
    relevant=[r for r in results if r.course_id==course.course_id]
    if any(not 0 <= r.score <= 1 for r in relevant):
        raise ValueError("assessment score must be between 0 and 1")
    for kind in course.assessments:
        matches=[r for r in relevant if r.kind is kind]
        if not matches or max(r.score for r in matches) < course.competency_threshold:
            return False
    return True

def next_courses(completed: set[str], results: tuple[AssessmentResult,...]=()) -> tuple[Course,...]:
    return tuple(
        c for c in COURSES
        if c.course_id not in completed
        and all(p in completed for p in c.prerequisites)
        and not course_complete(c,results)
    )
