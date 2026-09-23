from brain_v7.braincore_v2.solution_forge import forge, generate_ideas, review_frontier


def test_generates_multiple_distinct_ideas():
    ideas = generate_ideas("increase earning capability")
    assert len(ideas) >= 5
    assert len({i.title for i in ideas}) == len(ideas)


def test_frontier_is_ranked_without_claiming_profit():
    result = forge("increase verified earning capability", rounds=2)
    assert result["status"] in {"READY_FOR_SELECTION", "REQUEST_MORE_IDEAS"}
    assert result["ideas"]
    assert result["requires_execution_approval"] is True
    assert "realized_profit_jod" not in result


def test_weak_frontier_requests_more_ideas():
    ideas = generate_ideas("hard problem")
    result = review_frontier(ideas, minimum_score=101)
    assert result["status"] == "REQUEST_MORE_IDEAS"


def test_later_round_adds_new_combinations():
    first = generate_ideas("problem", 1)
    second = generate_ideas("problem", 2)
    assert len(second) > len(first)
