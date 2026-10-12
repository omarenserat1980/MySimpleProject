from brain_v12.marketing.learning_system import (
    LearningType, Mastery, mastery_level, next_learning_action
)

def test_mastery_weighting():
    m=Mastery("growth",.8,.7,.6,.5)
    assert round(m.score,2)==.68

def test_learning_progression():
    assert next_learning_action(Mastery("seo",.4,.8,.8,.8)) is LearningType.LESSON
    assert next_learning_action(Mastery("seo",.8,.4,.8,.8)) is LearningType.PROJECT
    assert next_learning_action(Mastery("seo",.8,.8,.4,.8)) is LearningType.CASE_STUDY
    assert next_learning_action(Mastery("seo",.8,.8,.8,.4)) is LearningType.EXPERIMENT

def test_levels():
    assert mastery_level(.92)=="EXPERT"
