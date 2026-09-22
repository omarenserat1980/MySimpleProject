from .planner import build_tasks

class SoftwareBuilder:
    def plan(self,project,objective):
        return {"project":project,"objective":objective,"steps":build_tasks(objective)}

    def next_step(self,plan,completed):
        for step in plan["steps"]:
            if step["id"] not in completed:
                return step
        return None
