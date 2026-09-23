from brain_v7.braincore_v2.continuous_goal_engine import next_goal, goal_snapshot


def test_goal_changes_over_cycles():
    a = next_goal(0, now=1)
    b = next_goal(1, now=2)
    assert a.goal_id != b.goal_id
    assert a.title != b.title


def test_snapshot_marks_continuous_generation():
    s = goal_snapshot(5, next_goal(5, now=10))
    assert s["continuous_generation"] is True
    assert s["next_goal_generated"] is True
