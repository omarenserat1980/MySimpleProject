#!/usr/bin/env python3
"""Room 13 / Stage 7 component registry.

This registry defines 100 operational components used to structure and
validate the cinematic production pipeline. The first four map to the
existing supervisor, media health gate, renderer, and QC systems; the
remaining components provide explicit support contracts for validation,
media generation, resilience, observability, CI, and delivery.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Iterable


@dataclass(frozen=True)
class Component:
    id: int
    name: str
    purpose: str
    status: str = "defined"


COMPONENTS = (
    Component(01, "Pipeline Supervisor", "يدير دورة المرحلة 7 من البداية للنهاية"),
    Component(02, "Media Health Gate", "يفحص جاهزية أدوات الوسائط قبل الإنتاج"),
    Component(03, "Renderer", "ينشئ المقاطع ويجمعها"),
    Component(04, "Quality Control", "يفحص الفيديو والصوت والمخرجات"),
    Component(05, "Plan Validator", "يتحقق من بنية خطة الفيلم"),
    Component(06, "Shot Validator", "يتحقق من جاهزية كل لقطة"),
    Component(07, "Beat Validator", "يتحقق من تسلسل النبضات السردية"),
    Component(08, "Duration Guard", "يتحقق من المدد"),
    Component(09, "Resolution Guard", "يتحقق من الدقة"),
    Component(10, "Frame Rate Guard", "يتحقق من معدل الإطارات"),
    Component(11, "Codec Guard", "يتحقق من الترميز"),
    Component(12, "Container Guard", "يتحقق من حاوية MP4"),
    Component(13, "Audio Stream Guard", "يتحقق من مسار الصوت"),
    Component(14, "AAC Guard", "يتحقق من AAC"),
    Component(15, "Loudness Guard", "يراقب مستوى الصوت"),
    Component(16, "Silence Detector", "يكشف الصمت غير المقصود"),
    Component(17, "Black Frame Detector", "يكشف الشاشة السوداء"),
    Component(18, "Freeze Detector", "يكشف تجمد الصورة"),
    Component(19, "Corruption Detector", "يكشف تلف الوسائط"),
    Component(20, "FFmpeg Resolver", "يوحّد مسار FFmpeg"),
    Component(21, "FFprobe Resolver", "يوحّد مسار FFprobe"),
    Component(22, "TTS Resolver", "يتحقق من محرك النطق"),
    Component(23, "Arabic Voice Validator", "يتحقق من الصوت العربي"),
    Component(24, "Voice Synthesis Worker", "ينشئ الصوت لكل لقطة"),
    Component(25, "Voice Cache", "يمنع إعادة توليد الصوت بلا حاجة"),
    Component(26, "Voice Duration Sync", "يوازن الصوت مع مدة اللقطة"),
    Component(27, "Narration Mixer", "يمزج السرد مع الخلفية"),
    Component(28, "Audio Bed Generator", "ينشئ طبقة صوتية هادئة"),
    Component(29, "Audio Fade Controller", "يدير التلاشي الصوتي"),
    Component(30, "Audio Peak Guard", "يمنع الذروة الصوتية"),
    Component(31, "Visual Asset Factory", "ينشئ أصول المشاهد"),
    Component(32, "Hospital Scene Builder", "يبني مشاهد المستشفى"),
    Component(33, "Door Scene Builder", "يبني مشاهد الباب"),
    Component(34, "Corridor Scene Builder", "يبني مشاهد الممر"),
    Component(35, "Character Scene Builder", "يبني الشخصيات"),
    Component(36, "Clock Scene Builder", "يبني الساعة"),
    Component(37, "Room Scene Builder", "يبني الغرفة"),
    Component(38, "Wall Scene Builder", "يبني الجدار"),
    Component(39, "Recorder Scene Builder", "يبني المسجل"),
    Component(40, "Lighting Engine", "يدير الإضاءة"),
    Component(41, "Vignette Engine", "يدير الحواف البصرية"),
    Component(42, "Motion Engine", "ينشئ الحركة البصرية"),
    Component(43, "Camera Composer", "يبني حركة الكاميرا"),
    Component(44, "Transition Composer", "يدير الانتقالات"),
    Component(45, "Color Consistency Guard", "يحافظ على اتساق الصورة"),
    Component(46, "Aspect Ratio Guard", "يتحقق من نسبة العرض"),
    Component(47, "Asset Existence Guard", "يتحقق من وجود الأصول"),
    Component(48, "Asset Freshness Guard", "يتحقق من حداثة الأصول"),
    Component(49, "Asset Manifest", "يسجل الأصول"),
    Component(50, "Shot Manifest", "يسجل اللقطات"),
    Component(51, "Render Queue", "ينظم طابور الرندر"),
    Component(52, "Segment Renderer", "يرندر المقاطع"),
    Component(53, "Concat Worker", "يجمع المقاطع"),
    Component(54, "Retry Controller", "يعيد المحاولة عند الفشل"),
    Component(55, "Failure Classifier", "يصنف الأخطاء"),
    Component(56, "Transient Error Guard", "يميز الأخطاء المؤقتة"),
    Component(57, "Determinism Guard", "يتحقق من قابلية التكرار"),
    Component(58, "Idempotency Guard", "يمنع التكرار الضار"),
    Component(59, "Partial Cleanup", "ينظف المخرجات الجزئية"),
    Component(60, "Atomic Output Writer", "يكتب المخرج بشكل ذري"),
    Component(61, "Progress Tracker", "يتابع التقدم"),
    Component(62, "State Store", "يحفظ حالة الإنتاج"),
    Component(63, "Run Journal", "يسجل أحداث التشغيل"),
    Component(64, "Diagnostic Collector", "يجمع التشخيصات"),
    Component(65, "Error Reporter", "ينظم تقارير الأخطاء"),
    Component(66, "Metrics Collector", "يجمع المقاييس"),
    Component(67, "Timing Profiler", "يقيس زمن المراحل"),
    Component(68, "Resource Guard", "يراقب الموارد"),
    Component(69, "Disk Space Guard", "يراقب مساحة القرص"),
    Component(70, "Process Guard", "يراقب العمليات"),
    Component(71, "Timeout Guard", "يفرض حدود الزمن"),
    Component(72, "Dependency Guard", "يتحقق من الاعتماديات"),
    Component(73, "Python Compile Guard", "يتحقق من ترجمة بايثون"),
    Component(74, "Unit Test Runner", "يشغل الاختبارات"),
    Component(75, "Smoke Test Runner", "يشغل اختبار الدخان"),
    Component(76, "Integration Test Runner", "يشغل التكامل"),
    Component(77, "Regression Guard", "يمنع تراجع الوظائف"),
    Component(78, "Schema Guard", "يتحقق من المخططات"),
    Component(79, "JSON Validator", "يتحقق من JSON"),
    Component(80, "Path Safety Guard", "يتحقق من المسارات"),
    Component(81, "Artifact Packager", "يحزم المخرجات"),
    Component(82, "Manifest Writer", "ينشئ بيان الفيلم"),
    Component(83, "Final MP4 Publisher", "يضع النسخة النهائية"),
    Component(84, "Artifact Uploader", "يرفع آثار التشغيل"),
    Component(85, "GitHub Actions Bridge", "يربط التشغيل بـ GitHub Actions"),
    Component(86, "Push Trigger Bridge", "يربط تغييرات الكود بالإنتاج"),
    Component(87, "Workflow Summary", "ينشئ ملخص التشغيل"),
    Component(88, "CI Failure Diagnostics", "يعرض تشخيص CI"),
    Component(89, "Release Readiness Gate", "يفحص جاهزية الإصدار"),
    Component(90, "Output Naming Guard", "يوحد أسماء المخرجات"),
    Component(91, "Security Path Guard", "يحمي مسارات العمل"),
    Component(92, "Environment Guard", "يتحقق من البيئة"),
    Component(93, "Configuration Guard", "يتحقق من الإعدادات"),
    Component(94, "Version Stamp", "يثبت إصدار المكونات"),
    Component(95, "Health Snapshot", "ينشئ لقطة صحة"),
    Component(96, "Pipeline Heartbeat", "يراقب استمرار التشغيل"),
    Component(97, "Recovery Planner", "يحدد مسار التعافي"),
    Component(98, "Production Audit", "يدقق مراحل الإنتاج"),
    Component(99, "End-to-End Verifier", "يتحقق من السلسلة كاملة"),
    Component(100, "Cinematic Completion Gate", "لا يعلن الاكتمال إلا بعد اجتياز الفحوص"),
)


def all_components() -> tuple[Component, ...]:
    return COMPONENTS


def validate_registry() -> list[str]:
    errors: list[str] = []
    ids = [c.id for c in COMPONENTS]
    if len(COMPONENTS) != 100:
        errors.append(f"expected 100 components, found {len(COMPONENTS)}")
    if sorted(ids) != list(range(1, 101)):
        errors.append("component IDs must be exactly 1..100")
    names = [c.name for c in COMPONENTS]
    if len(names) != len(set(names)):
        errors.append("component names must be unique")
    if any(not c.purpose.strip() for c in COMPONENTS):
        errors.append("every component needs a purpose")
    return errors


def snapshot() -> dict:
    errors = validate_registry()
    return {
        "status": "READY" if not errors else "BLOCKED",
        "count": len(COMPONENTS),
        "components": [asdict(c) for c in COMPONENTS],
        "errors": errors,
    }


def main() -> int:
    import json
    print(json.dumps(snapshot(), ensure_ascii=False, indent=2))
    return 0 if not validate_registry() else 2


if __name__ == "__main__":
    raise SystemExit(main())
