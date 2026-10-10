"""Curated reasoning pathways inspired by Qur'anic passages.

These are operational interpretations for the Brain, not claims that the listed
software workflow is a literal Qur'anic algorithm or a substitute for tafsir.
Each record separates textual anchors from the engineering application.
"""
import json

PATHWAYS = [
    {
        "id": "verify_before_action",
        "title": "التثبت قبل الحكم أو الفعل",
        "stages": [
            "تحديد الادعاء وما هو معلوم فعلًا",
            "تحديد المصدر وفحص موثوقيته",
            "طلب قرائن إضافية عند احتمال الضرر",
            "فصل الحقيقة عن الظن والاستنتاج",
            "تأجيل الفعل المؤثر إذا كانت الأدلة غير كافية",
            "تسجيل القرار ودليله ومراجعته عند ظهور معلومات جديدة",
        ],
        "anchors": [
            {"reference": "الإسراء: 36", "role": "النهي عن اتباع ما ليس للمرء به علم"},
            {"reference": "الحجرات: 6", "role": "التبيّن من النبأ لتجنب إصابة قوم بجهالة"},
            {"reference": "يونس: 36", "role": "التحذير من أن الظن لا يغني من الحق شيئًا"},
        ],
        "textual_claim": "هذه الآيات تتناول العلم والتبيّن وحدود الظن في سياقاتها الخاصة.",
        "engineering_application": "مسار تحقق مقترح؛ ليس تسلسلًا تقنيًا منصوصًا عليه حرفيًا في القرآن.",
        "limits": "لا يستبدل التفسير المتخصص، ولا يجعل الاستنتاج البشري نصًا مقدسًا.",
    },
    {
        "id": "context_and_cross_reference",
        "title": "فهم النص في سياقه وربط المواضع",
        "stages": [
            "حفظ النص المرجعي مضبوطًا مع مرجعه",
            "قراءة السياق القريب قبل استخلاص المعنى",
            "جمع المواضع ذات الصلة بالموضوع",
            "مقارنة أوجه الاتفاق والاختلاف والسياقات",
            "وسم العلاقة بأنها صريحة أو تفسيرية أو فرضية",
            "عدم اعتماد فرضية غير متحققة كحقيقة",
        ],
        "anchors": [
            {"reference": "محمد: 24", "role": "الدعوة إلى تدبر القرآن"},
            {"reference": "النساء: 82", "role": "الحث على التدبر في سياق الآية"},
        ],
        "textual_claim": "الآيتان تحثان على تدبر القرآن في سياق كل منهما.",
        "engineering_application": "مسار بحث مقترح يمنع عزل الاقتباس ويُظهر درجة ثبوت الروابط.",
        "limits": "التشابه اللفظي وحده لا يثبت علاقة تفسيرية محددة؛ يلزم الرجوع للتفسير الموثوق.",
    },
    {
        "id": "justice_under_bias",
        "title": "الإنصاف رغم الميل أو الخصومة",
        "stages": [
            "تحديد معيار التقييم قبل النظر إلى هوية الطرف",
            "جمع الأدلة المؤيدة والمعارضة بالمعيار نفسه",
            "فحص احتمال تأثير الميل أو الخصومة",
            "توضيح أسباب الحكم وعدم إخفاء الأدلة المخالفة",
            "مراجعة الحكم إذا ظهرت أدلة معتبرة جديدة",
        ],
        "anchors": [
            {"reference": "المائدة: 8", "role": "الأمر بالعدل وعدم حمل الشنآن على تركه"},
            {"reference": "النحل: 90", "role": "الأمر بالعدل والإحسان"},
        ],
        "textual_claim": "هذه المواضع تتناول العدل، وآية المائدة تربط العدل صراحة بعدم التأثر بالشنآن.",
        "engineering_application": "مسار تدقيق للانحياز في قرارات النظام، مستوحى من المعنى لا من نص تقني حرفي.",
        "limits": "لا يغني عن تحديد معايير العدالة المناسبة للمجال ومراجعتها بشريًا.",
    },
    {
        "id": "consult_decide_review",
        "title": "المشاورة ثم العزم ومتابعة القرار",
        "stages": [
            "صياغة المسألة والهدف والقيود",
            "جمع الخيارات والأدلة ذات الصلة",
            "استشارة أصحاب المعرفة عند الحاجة",
            "موازنة المنافع والمخاطر والصلاحيات",
            "اختيار إجراء متناسب مع الأدلة والموافقة اللازمة",
            "التحقق من النتيجة وتعلم الدرس دون تزوير سجل التنفيذ",
        ],
        "anchors": [
            {"reference": "آل عمران: 159", "role": "المشاورة ثم العزم والتوكل في سياق الآية"},
            {"reference": "الشورى: 38", "role": "وصف الشورى ضمن صفات المؤمنين"},
        ],
        "textual_claim": "الآيتان تذكران الشورى، وآل عمران: 159 تذكر المشاورة والعزم والتوكل في سياقها.",
        "engineering_application": "مسار لاتخاذ القرار قابل للمراجعة، وليس ادعاءً بأن ترتيبًا برمجيًا محددًا هو التفسير الوحيد.",
        "limits": "نوع القرار والسياق والصلاحيات تحدد ما يلزم من مشاورة أو موافقة.",
    },
]


def register_quranic_reasoning_paths(store):
    """Idempotently place curated pathway records into the existing memory table."""
    registered = []
    for pathway in PATHWAYS:
        key = "reasoning_path.quranic." + pathway["id"]
        value = json.dumps({
            "kind": "reasoning_path",
            "source_family": "Quran",
            "source_references": pathway["anchors"],
            "title": pathway["title"],
            "stages": pathway["stages"],
            "textual_claim": pathway["textual_claim"],
            "engineering_application": pathway["engineering_application"],
            "limits": pathway["limits"],
            "epistemic_status": "curated_application_not_literal_scriptural_algorithm",
        }, ensure_ascii=False, sort_keys=True)
        store.save_memory(key, value)
        registered.append(key)
    return registered
