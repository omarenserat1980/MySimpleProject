"""Twenty-role YouTube production team for the Electronic Brain.

The team is an internal workforce/routing layer. It can plan, draft, produce,
review, and analyze content, but it does not receive credentials, money-moving,
contract-signing, or irreversible publishing authority.
"""
from __future__ import annotations

from typing import Any

from .employee_hierarchy import EmployeeHierarchy


YOUTUBE_ROLES: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("YouTube Executive Producer", ("youtube_strategy", "coordination", "priorities")),
    ("Channel Strategist", ("channel_strategy", "audience", "positioning")),
    ("Topic Researcher", ("research", "topic_discovery", "sources")),
    ("Trend Analyst", ("trends", "youtube_analytics", "content_gaps")),
    ("Script Writer", ("scripts", "storytelling", "hooks")),
    ("Story Editor", ("story_structure", "retention", "editing")),
    ("Title Specialist", ("titles", "ctr", "copywriting")),
    ("Thumbnail Designer", ("thumbnails", "visual_design", "branding")),
    ("Cinematic Director", ("cinematic_direction", "shots", "continuity")),
    ("Video Producer", ("video_production", "workflow", "assets")),
    ("Video Editor", ("editing", "ffmpeg", "pacing")),
    ("Motion Graphics Designer", ("motion_graphics", "captions", "effects")),
    ("Audio Engineer", ("audio", "mixing", "voice")),
    ("Voiceover Specialist", ("voiceover", "pronunciation", "delivery")),
    ("SEO Specialist", ("youtube_seo", "keywords", "metadata")),
    ("Community Manager", ("comments", "community", "feedback")),
    ("Shorts Producer", ("shorts", "repurposing", "vertical_video")),
    ("Quality Assurance Reviewer", ("qa", "fact_checking", "policy_review")),
    ("Analytics Scientist", ("analytics", "experiments", "retention")),
    ("Publishing Operations Coordinator", ("publishing", "scheduling", "release_checklists")),
)

TEAM_DEPARTMENT_ID = "DEPT-YOUTUBE"
TEAM_MANAGER_ID = "MGR-YOUTUBE"
TEAM_GOAL = "grow the user's YouTube channel through useful, original, high-quality content and measurable learning"


class YouTubeTeam:
    """Provision and coordinate exactly twenty specialized YouTube employees."""

    def __init__(self, organization: EmployeeHierarchy) -> None:
        self.organization = organization
        self.registry = self._provision()

    def _provision(self) -> dict[str, Any]:
        return self.organization.ensure_team(
            department_id=TEAM_DEPARTMENT_ID,
            name="YOUTUBE_CHANNEL",
            manager_id=TEAM_MANAGER_ID,
            manager_title="YouTube Department Manager",
            roles=YOUTUBE_ROLES,
            goal=TEAM_GOAL,
        )

    def assign_content_pipeline(self, objective: str) -> list[dict[str, Any]]:
        """Create one internal task per role for a content pipeline."""
        tasks: list[dict[str, Any]] = []
        employees = [
            self.organization.employees[eid]
            for eid in self.registry["employee_ids"]
            if eid in self.organization.employees
        ]
        for employee in employees:
            task = self.organization.assign_task(
                f"YouTube role: {employee.title}. Objective: {objective}",
                department_id=TEAM_DEPARTMENT_ID,
            )
            tasks.append({
                "employee_id": employee.employee_id,
                "role": employee.title,
                "task_id": task.task_id,
                "status": task.status,
            })
        return tasks

    def snapshot(self) -> dict[str, Any]:
        employees = [
            self.organization.employees[eid]
            for eid in self.registry["employee_ids"]
            if eid in self.organization.employees
        ]
        return {
            "department_id": TEAM_DEPARTMENT_ID,
            "manager_id": TEAM_MANAGER_ID,
            "employee_count": len(employees),
            "target_employee_count": 20,
            "employees": [
                {
                    "employee_id": e.employee_id,
                    "title": e.title,
                    "skills": list(e.skills),
                    "status": e.status,
                }
                for e in employees
            ],
            "pipeline": [
                "strategy", "research", "topic", "script", "story",
                "title", "thumbnail", "cinematic", "production", "editing",
                "motion", "audio", "voice", "seo", "community", "shorts",
                "qa", "analytics", "publishing"
            ],
            "external_side_effects": False,
            "money_movement": False,
            "credential_storage": False,
            "publishing_requires_authorization": True,
        }
