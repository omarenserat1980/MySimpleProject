def options_for(goal):
    return [
        {"id":"inspect","action":"INSPECT","risk":0.05,"expected":"فحص الهدف والسياق"},
        {"id":"plan","action":"PLAN","risk":0.10,"expected":"بناء خطة قابلة للتحقق"},
        {"id":"research","action":"RESEARCH","risk":0.15,"expected":"سد فجوة المعلومات"},
    ]

def choose(goal, options):
    return max(options, key=lambda x:(1.0-x["risk"])*0.7+float(goal["priority"])*0.3)

def build_tasks(objective):
    return [
        {"id":"inspect","title":"فحص المشروع","requires_execution":False},
        {"id":"design","title":"تصميم الحل","requires_execution":False},
        {"id":"implement","title":"تنفيذ التعديل","requires_execution":True},
        {"id":"test","title":"اختبار التعديل","requires_execution":True},
        {"id":"verify","title":"التحقق النهائي","requires_execution":False},
    ]
