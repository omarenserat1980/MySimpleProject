from .commerce_neuron import build_commerce_plan


def options_for(goal):
    text = str(goal.get("text", ""))
    commerce = any(k in text.lower() for k in ("متجر", "موقع", "منتجات رقمية", "commerce", "store", "website"))
    options = [
        {"id":"inspect","action":"INSPECT","risk":0.05,"expected":"فحص الهدف والسياق"},
        {"id":"plan","action":"PLAN","risk":0.10,"expected":"بناء خطة قابلة للتحقق"},
        {"id":"research","action":"RESEARCH","risk":0.15,"expected":"سد فجوة المعلومات"},
    ]
    if commerce:
        options.append({
            "id":"commerce_orchestrate",
            "action":"ORCHESTRATE_COMMERCE",
            "risk":0.10,
            "expected":"تشغيل خط المتجر: الموقع ثم المنتجات ثم الكتالوج ثم التسويق ثم الدفع أخيرًا",
            "plan":build_commerce_plan(text),
        })
    return options


def choose(goal, options):
    commerce = any(k in str(goal.get("text", "")).lower() for k in ("متجر", "موقع", "منتجات رقمية", "commerce", "store", "website"))
    if commerce:
        for option in options:
            if option["id"] == "commerce_orchestrate":
                return option
    return max(options, key=lambda x:(1.0-x["risk"])*0.7+float(goal["priority"])*0.3)


def build_tasks(objective):
    return [
        {"id":"inspect","title":"فحص المشروع","requires_execution":False},
        {"id":"design","title":"تصميم الحل","requires_execution":False},
        {"id":"implement","title":"تنفيذ التعديل","requires_execution":True},
        {"id":"test","title":"اختبار التعديل","requires_execution":True},
        {"id":"verify","title":"التحقق النهائي","requires_execution":False},
    ]
