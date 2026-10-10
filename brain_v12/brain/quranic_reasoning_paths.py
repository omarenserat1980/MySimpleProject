"""Curated reasoning patterns inspired by Quranic meanings, not tafsir or literal algorithms.

Each record separates the verse reference from a bounded engineering analogy. The
application is a modern design inference and must never be presented as Quran text.
"""
import json

PATHWAYS = [
    {
        "id": "verify_before_action",
        "title": "التحقق قبل الحكم أو الفعل",
        "stages": ["جمع الدليل", "فحص المصدر والسياق", "تمييز المعلوم من المجهول", "تقدير الضرر", "اتخاذ خطوة متناسبة", "تسجيل النتيجة"],
        "source_references": [{"reference": "الحجرات 49:6", "url": "https://quran.com/al-hujurat/6", "role": "التثبت من الخبر قبل الإضرار بالآخرين"}, {"reference": "الإسراء 17:36", "url": "https://quran.com/al-isra/36", "role": "عدم اتباع ما لا علم به"}],
        "engineering_application": "لا تعتبر الادعاء حقيقة قبل فحص مصدره؛ افصل الملاحظة عن الاستنتاج، واربط كل قرار بالدليل المتاح.",
        "limits": "هذا تطبيق هندسي معاصر لمعنى عام؛ الآيات ليست مواصفة تقنية أو خوارزمية برمجية."
    },
    {
        "id": "review_and_accountability",
        "title": "مراجعة العمل ومحاسبة النتيجة",
        "stages": ["تحديد الهدف", "تسجيل ما نُفّذ", "مقارنة النتيجة بالهدف", "كشف الفجوة", "استخلاص درس محدد", "تعديل المحاولة التالية"],
        "source_references": [{"reference": "الحشر 59:18", "url": "https://quran.com/al-hashr/18", "role": "نظر النفس فيما قدمت لغد"}],
        "engineering_application": "بعد كل دورة، خزّن الهدف والفعل والدليل وحالة التحقق والدرس؛ لا تسمِّ النتيجة نجاحًا بلا تحقق.",
        "limits": "المحاسبة القرآنية أوسع من مراجعة البرمجيات؛ هذا تشبيه تشغيلي محدود."
    },
    {
        "id": "contextual_cross_check",
        "title": "قراءة السياق وربط الأجزاء",
        "stages": ["قراءة المعلومة", "استرجاع السياق السابق واللاحق", "مقارنة الشواهد", "اختبار الاتساق", "تسجيل ما بقي غير محسوم"],
        "source_references": [{"reference": "النساء 4:82", "url": "https://quran.com/an-nisa/82", "role": "التدبر والنظر في الاتساق"}],
        "engineering_application": "لا تستنتج من مقطع منفرد إذا كان السياق أو ملفات أخرى قد تغير المعنى؛ قارن المصدر والاختبارات والسلوك الفعلي.",
        "limits": "الآية في سياق تدبر القرآن؛ تعميمها إلى فحص الكود قياس هندسي وليس تفسيرًا حصريًا."
    },
    {
        "id": "consult_then_resolve",
        "title": "المشاورة ثم العزم والمتابعة",
        "stages": ["تحديد المسألة", "جمع وجهات نظر مستقلة", "وزن الأدلة", "اختيار مسؤول واضح", "العزم على خطوة", "متابعة الأثر"],
        "source_references": [{"reference": "آل عمران 3:159", "url": "https://quran.com/ali-imran/159", "role": "المشاورة ثم العزم والتوكل"}, {"reference": "الشورى 42:38", "url": "https://quran.com/ash-shuraa/38", "role": "التشاور في الأمر"}],
        "engineering_application": "اجمع بدائل حقيقية عند الغموض، ثم اختر خطوة قابلة للتحقق بدل الدوران بين الآراء.",
        "limits": "المشاورة لا تعني تصويتًا آليًا؛ القرار يحتاج مسؤولية وصلاحيات وحدودًا واضحة."
    },
    {
        "id": "fairness_under_bias",
        "title": "العدل رغم الميل أو الخصومة",
        "stages": ["تحديد أصحاب المصلحة", "كشف التحيز المحتمل", "تطبيق معيار واحد", "فحص الأثر على الأطراف", "توثيق سبب القرار"],
        "source_references": [{"reference": "المائدة 5:8", "url": "https://quran.com/al-maidah/8", "role": "العدل وعدم حمل الخصومة على الجور"}, {"reference": "النحل 16:90", "url": "https://quran.com/an-nahl/90", "role": "الأمر بالعدل والإحسان"}],
        "engineering_application": "لا تجعل تفضيلًا سابقًا أو خصومة أو نجاحًا قديمًا يغيّر معيار فحص الأدلة؛ قيّم الخيارات بمعيار معلن.",
        "limits": "هذا مبدأ أخلاقي في تصميم القرار، وليس بديلًا عن المتطلبات القانونية أو مراجعة الانحياز المتخصصة."
    },
    {
        "id": "preserve_knowledge",
        "title": "تثبيت المعرفة ونقلها",
        "stages": ["التقاط المعلومة", "حفظ المصدر", "تمييز الأصل عن التعليق", "تنظيمها بمفتاح قابل للبحث", "استرجاعها عند الحاجة", "مراجعة صلاحيتها"],
        "source_references": [{"reference": "العلق 96:4-5", "url": "https://quran.com/al-alaq/4-5", "role": "التعليم بالقلم وتعليم الإنسان ما لم يعلم"}],
        "engineering_application": "لا تعتمد على ذاكرة الجلسة وحدها؛ خزّن المعرفة مع مصدرها ووقتها وحدودها، ثم استرجعها حسب صلة الهدف.",
        "limits": "الآيات تذكر التعليم والقلم؛ بنية قاعدة البيانات والاسترجاع هي استنباط هندسي معاصر."
    },
    {
        "id": "learn_from_cases",
        "title": "استخراج العبرة من الحالات السابقة",
        "stages": ["تحديد الحالة", "حفظ الوقائع ذات الصلة", "تمييز السبب عن المصادفة", "استخلاص درس محدود", "اختبار الدرس في حالة جديدة"],
        "source_references": [{"reference": "يوسف 12:111", "url": "https://quran.com/yusuf/111", "role": "العبرة في قصص السابقين لأولي الألباب"}],
        "engineering_application": "استرجع الدروس السابقة ذات الصلة فقط، ولا تعمم تجربة واحدة على كل الحالات قبل اختبارها.",
        "limits": "العبرة من القصص ليست مطابقة لتحليل تجريبي؛ السببية تحتاج أدلة مستقلة."
    },
    {
        "id": "observe_then_infer",
        "title": "التأمل في المشاهدات قبل الاستنتاج",
        "stages": ["جمع المشاهدات", "وصفها دون تفسير", "اقتراح تفسيرات بديلة", "مقارنة الأدلة", "اختيار التفسير الأقوى مؤقتًا"],
        "source_references": [{"reference": "آل عمران 3:190-191", "url": "https://quran.com/ali-imran/190-191", "role": "التفكر في خلق السماوات والأرض"}],
        "engineering_application": "افصل قياسات النظام وسجلاته عن تفسير السبب، واحتفظ ببدائل عندما لا تحسم الأدلة بينها.",
        "limits": "الآيات تدعو إلى التفكر في الخلق؛ هذا تطبيق منهجي وليس وصفًا حرفيًا لمنهج علمي حديث."
    },
    {
        "id": "plan_resources_over_time",
        "title": "التخطيط للموارد عبر الزمن",
        "stages": ["تقدير الموارد", "توقع الاحتياجات", "تحديد الأولويات", "حفظ احتياطي مناسب", "مراجعة الخطة عند تغير الواقع"],
        "source_references": [{"reference": "يوسف 12:47-49", "url": "https://quran.com/yusuf/47-49", "role": "تدبير سنوات الزرع والادخار والشدّة في سياق القصة"}],
        "engineering_application": "خطط للذاكرة والوقت والقدرة الحسابية؛ لا تستهلك كل الموارد في الطلب الحالي وتجاهل الاستمرارية.",
        "limits": "التطبيق على موارد الحوسبة قياس تنظيمي، وليس المعنى الوحيد أو المباشر للآيات."
    },
    {
        "id": "capacity_and_recovery",
        "title": "مراعاة القدرة والتدرج",
        "stages": ["تقدير القدرة الحالية", "تقسيم العمل", "اختيار خطوة ممكنة", "رصد الإجهاد أو الفشل", "التعافي ثم الاستمرار"],
        "source_references": [{"reference": "البقرة 2:286", "url": "https://quran.com/al-baqarah/286", "role": "لا يكلف الله نفسًا إلا وسعها"}],
        "engineering_application": "قسّم العمل الكبير إلى خطوات قابلة للتنفيذ، وحدد حدود الوقت والذاكرة، وتعامل مع الفشل دون الادعاء بأن العمل اكتمل.",
        "limits": "المعنى الديني أوسع من إدارة الموارد التقنية؛ هذا تطبيق محدود."
    }
]

# Retrieval synonyms are engineering labels, not Quranic wording.
PATHWAY_KEYWORDS = {
    "verify_before_action": ["تحقق", "تثبت", "مصدر", "خبر", "دليل", "معلومة", "verify", "source", "evidence", "check", "fact"],
    "review_and_accountability": ["مراجعة", "محاسبة", "نتيجة", "تقييم", "تعلم", "راجع", "review", "audit", "outcome", "lesson"],
    "contextual_cross_check": ["سياق", "اتساق", "ربط", "مقارنة", "شواهد", "context", "consistency", "cross-check", "compare"],
    "consult_then_resolve": ["مشاورة", "استشارة", "بدائل", "قرار", "خطة", "consult", "options", "decision", "plan"],
    "fairness_under_bias": ["عدل", "تحيز", "انحياز", "خصومة", "معيار", "fairness", "bias", "fair", "criteria"],
    "preserve_knowledge": ["ذاكرة", "حفظ", "معرفة", "مصدر", "استرجاع", "تذكر", "memory", "preserve", "retrieve", "knowledge"],
    "learn_from_cases": ["عبرة", "حالات", "تجارب", "دروس", "سابقة", "lesson", "case", "history", "learn"],
    "observe_then_infer": ["ملاحظة", "مشاهدة", "استنتاج", "دليل", "فرضية", "observe", "infer", "evidence", "hypothesis"],
    "plan_resources_over_time": ["موارد", "تخطيط", "ذاكرة", "وقت", "قدرة", "resource", "planning", "capacity", "time"],
    "capacity_and_recovery": ["قدرة", "تدرج", "فشل", "تعافي", "استمرار", "capacity", "recovery", "failure", "resilience"],
}

def register_quranic_reasoning_paths(store):
    """Idempotently seed curated paths into persistent memory."""
    existing = {item.get("key"): item.get("value") for item in store.memories()}
    registered = 0
    for path in PATHWAYS:
        key = f"reasoning_path.quranic.{path['id']}"
        value = json.dumps({**path, "interpretation_type": "bounded_engineering_inference"}, ensure_ascii=False, sort_keys=True)
        if existing.get(key) != value:
            store.save_memory(key, value)
            registered += 1
    return {"registered": registered, "total": len(PATHWAYS)}

def select_reasoning_path(goal, memories):
    """Select a path only when multiple meaningful query terms overlap."""
    from .memory import MemoryStore
    query_terms = MemoryStore._memory_terms(goal)
    if len(query_terms) < 1:
        return None
    ranked = []
    for memory in memories or []:
        key = str(memory.get("key", ""))
        if not key.startswith("reasoning_path.quranic."):
            continue
        try:
            path = json.loads(memory.get("value", "{}"))
        except (TypeError, ValueError):
            continue
        searchable = " ".join([
            path.get("title", ""), path.get("engineering_application", ""),
            " ".join(path.get("stages", [])),
            " ".join(PATHWAY_KEYWORDS.get(path.get("id", ""), []))
        ])
        path_terms = MemoryStore._memory_terms(searchable)
        overlap = query_terms & path_terms
        # Arabic inflections commonly differ by a prefix/suffix; permit a
        # bounded prefix match only for terms long enough to be distinctive.
        matched = set(overlap)
        for query_term in query_terms - overlap:
            if len(query_term) >= 4 and any(
                len(path_term) >= 4 and (query_term.startswith(path_term) or path_term.startswith(query_term))
                for path_term in path_terms
            ):
                matched.add(query_term)
        score = len(matched)
        if score:
            ranked.append((score, path.get("id", ""), path))
    if not ranked:
        return None
    ranked.sort(key=lambda item: (-item[0], item[1]))
    score, _, path = ranked[0]
    if score < 2:
        return None
    return {**path, "key": f"reasoning_path.quranic.{path['id']}", "match_score": score}
