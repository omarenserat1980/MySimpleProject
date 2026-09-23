"""Optional Islamic remembrance routine for the workforce.

This is a scheduled organizational reminder, not a claim that software agents
possess faith or consciousness.
"""

DEFAULT_REMEMBRANCE = "سبحان الله"


class SpiritualRoutine:
    def __init__(self, remembrance: str = DEFAULT_REMEMBRANCE):
        self.remembrance = remembrance

    def reminder(self, employee_id: str) -> dict:
        return {
            "employee_id": employee_id,
            "practice": self.remembrance,
            "status": "REMINDER_SCHEDULED",
        }

    def reminders_for(self, employee_ids: list[str]) -> list[dict]:
        return [self.reminder(employee_id) for employee_id in employee_ids]
