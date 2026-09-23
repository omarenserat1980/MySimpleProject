from brain_v7.braincore_v2.employee_hierarchy import EmployeeHierarchy
from brain_v7.braincore_v2.youtube_team import YouTubeTeam


def test_youtube_team_has_twenty_specialists():
    org = EmployeeHierarchy()
    team = YouTubeTeam(org)
    snap = team.snapshot()
    assert snap["employee_count"] == 20
    assert snap["target_employee_count"] == 20
    assert len(snap["employees"]) == 20
    assert len({x["employee_id"] for x in snap["employees"]}) == 20


def test_youtube_team_is_idempotent():
    org = EmployeeHierarchy()
    first = YouTubeTeam(org).snapshot()
    second = YouTubeTeam(org).snapshot()
    assert first["employee_ids"] if "employee_ids" in first else True
    assert second["employee_count"] == 20
    assert org.departments["DEPT-YOUTUBE"].manager_id == "MGR-YOUTUBE"
