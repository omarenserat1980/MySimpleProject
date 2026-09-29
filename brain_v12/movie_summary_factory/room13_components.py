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
    Component(1, "Pipeline Supervisor", "يدير دورة المرحلة 7 من البداية للنهاية"),
    Component(2, "Media Health Gate", "يفحص جاهزية أدوات الوسائط قبل الإنتاج"),
    Component(3, "Renderer", "ينشئ المقاطع ويجمعها"),
    Component(4, "Quality Control", "يفحص الفيديو والصوت والمخرجات"),
    Component(5, "Plan Validator", "يتحقق من بنية خطة الفيلم", "implemented"),
    Component(6, "Shot Validator", "يتحقق من جاهزية كل لقطة", "implemented"),
    Component(7, "Beat Validator", "يتحقق من تسلسل النبضات السردية", "implemented"),
    Component(8, "Duration Guard", "يتحقق من المدد", "implemented"),
    Component(9, "Resolution Guard", "يتحقق من الدقة", "implemented"),
    Component(10, "Frame Rate Guard", "يتحقق من معدل الإطارات", "implemented"),
    Component(11, "Codec Guard", "يتحقق من الترميز", "implemented"),
    Component(12, "Container Guard", "يتحقق من حاوية MP4", "implemented"),
    Component(13, "Audio Stream Guard", "يتحقق من مسار الصوت", "implemented"),
    Component(14, "AAC Guard", "يتحقق من AAC", "implemented"),
    Component(15, "Loudness Guard", "يراقب مستوى الصوت", "implemented"),
    Component(16, "Silence Detector", "يكشف الصمت غير المقصود", "implemented"),
    Component(17, "Black Frame Detector", "يكشف الشاشة السوداء", "implemented"),
    Component(18, "Freeze Detector", "يكشف تجمد الصورة", "implemented"),
    Component(19, "Corruption Detector", "يكشف تلف الوسائط", "implemented"),
    Component(20, "FFmpeg Resolver", "يوحّد مسار FFmpeg", "implemented"),
    Component(21, "FFprobe Resolver", "يوحّد مسار FFprobe", "implemented"),
    Component(22, "TTS Resolver", "يتحقق من محرك النطق", "implemented"),
    Component(23, "Arabic Voice Validator", "يتحقق من الصوت العربي", "implemented"),
    Component(24, "Voice Synthesis Worker", "ينشئ الصوت لكل لقطة", "implemented"),
    Component(25, "Voice Cache", "يمنع إعادة توليد الصوت بلا حاجة", "implemented"),
    Component(26, "Voice Duration Sync", "يوازن الصوت مع مدة اللقطة", "implemented"),
    Component(27, "Narration Mixer", "يمزج السرد مع الخلفية", "implemented"),
    Component(28, "Audio Bed Generator", "ينشئ طبقة صوتية هادئة", "implemented"),
    Component(29, "Audio Fade Controller", "يدير التلاشي الصوتي", "implemented"),
    Component(30, "Audio Peak Guard", "يمنع الذروة الصوتية", "implemented"),
    Component(31, "Visual Asset Factory", "ينشئ أصول المشاهد", "implemented"),
    Component(32, "Hospital Scene Builder", "يبني مشاهد المستشفى", "implemented"),
    Component(33, "Door Scene Builder", "يبني مشاهد الباب", "implemented"),
    Component(34, "Corridor Scene Builder", "يبني مشاهد الممر", "implemented"),
    Component(35, "Character Scene Builder", "يبني الشخصيات", "implemented"),
    Component(36, "Clock Scene Builder", "يبني الساعة", "implemented"),
    Component(37, "Room Scene Builder", "يبني الغرفة", "implemented"),
    Component(38, "Wall Scene Builder", "يبني الجدار", "implemented"),
    Component(39, "Recorder Scene Builder", "يبني المسجل", "implemented"),
    Component(40, "Lighting Engine", "يدير الإضاءة", "implemented"),
    Component(41, "Vignette Engine", "يدير الحواف البصرية", "implemented"),
    Component(42, "Motion Engine", "ينشئ الحركة البصرية", "implemented"),
    Component(43, "Camera Composer", "يبني حركة الكاميرا", "implemented"),
    Component(44, "Transition Composer", "يدير الانتقالات", "implemented"),
    Component(45, "Color Consistency Guard", "يحافظ على اتساق الصورة", "implemented"),
    Component(46, "Aspect Ratio Guard", "يتحقق من نسبة العرض", "implemented"),
    Component(47, "Asset Existence Guard", "يتحقق من وجود الأصول", "implemented"),
    Component(48, "Asset Freshness Guard", "يتحقق من حداثة الأصول", "implemented"),
    Component(49, "Asset Manifest", "يسجل الأصول", "implemented"),
    Component(50, "Shot Manifest", "يسجل اللقطات", "implemented"),
    Component(51, "Render Queue", "ينظم طابور الرندر", "implemented"),
    Component(52, "Segment Renderer", "يرندر المقاطع", "implemented"),
    Component(53, "Concat Worker", "يجمع المقاطع", "implemented"),
    Component(54, "Retry Controller", "يعيد المحاولة عند الفشل", "implemented"),
    Component(55, "Failure Classifier", "يصنف الأخطاء", "implemented"),
    Component(56, "Transient Error Guard", "يميز الأخطاء المؤقتة", "implemented"),
    Component(57, "Determinism Guard", "يتحقق من قابلية التكرار", "implemented"),
    Component(58, "Idempotency Guard", "يمنع التكرار الضار", "implemented"),
    Component(59, "Partial Cleanup", "ينظف المخرجات الجزئية", "implemented"),
    Component(60, "Atomic Output Writer", "يكتب المخرج بشكل ذري", "implemented"),
    Component(61, "Progress Tracker", "يتابع التقدم", "implemented"),
    Component(62, "State Store", "يحفظ حالة الإنتاج", "implemented"),
    Component(63, "Run Journal", "يسجل أحداث التشغيل", "implemented"),
    Component(64, "Diagnostic Collector", "يجمع التشخيصات", "implemented"),
    Component(65, "Error Reporter", "ينظم تقارير الأخطاء", "implemented"),
    Component(66, "Metrics Collector", "يجمع المقاييس", "implemented"),
    Component(67, "Timing Profiler", "يقيس زمن المراحل", "implemented"),
    Component(68, "Resource Guard", "يراقب الموارد", "implemented"),
    Component(69, "Disk Space Guard", "يراقب مساحة القرص", "implemented"),
    Component(70, "Process Guard", "يراقب العمليات", "implemented"),
    Component(71, "Timeout Guard", "يفرض حدود الزمن", "implemented"),
    Component(72, "Dependency Guard", "يتحقق من الاعتماديات", "implemented"),
    Component(73, "Python Compile Guard", "يتحقق من ترجمة بايثون", "implemented"),
    Component(74, "Unit Test Runner", "يشغل الاختبارات", "implemented"),
    Component(75, "Smoke Test Runner", "يشغل اختبار الدخان", "implemented"),
    Component(76, "Integration Test Runner", "يشغل التكامل", "implemented"),
    Component(77, "Regression Guard", "يمنع تراجع الوظائف", "implemented"),
    Component(78, "Schema Guard", "يتحقق من المخططات", "implemented"),
    Component(79, "JSON Validator", "يتحقق من JSON", "implemented"),
    Component(80, "Path Safety Guard", "يتحقق من المسارات", "implemented"),
    Component(81, "Artifact Packager", "يحزم المخرجات", "implemented"),
    Component(82, "Manifest Writer", "ينشئ بيان الفيلم", "implemented"),
    Component(83, "Final MP4 Publisher", "يضع النسخة النهائية", "implemented"),
    Component(84, "Artifact Uploader", "يرفع آثار التشغيل", "implemented"),
    Component(85, "GitHub Actions Bridge", "يربط التشغيل بـ GitHub Actions", "implemented"),
    Component(86, "Push Trigger Bridge", "يربط تغييرات الكود بالإنتاج", "implemented"),
    Component(87, "Workflow Summary", "ينشئ ملخص التشغيل", "implemented"),
    Component(88, "CI Failure Diagnostics", "يعرض تشخيص CI", "implemented"),
    Component(89, "Release Readiness Gate", "يفحص جاهزية الإصدار", "implemented"),
    Component(90, "Output Naming Guard", "يوحد أسماء المخرجات", "implemented"),
    Component(91, "Security Path Guard", "يحمي مسارات العمل", "implemented"),
    Component(92, "Environment Guard", "يتحقق من البيئة", "implemented"),
    Component(93, "Configuration Guard", "يتحقق من الإعدادات", "implemented"),
    Component(94, "Version Stamp", "يثبت إصدار المكونات", "implemented"),
    Component(95, "Health Snapshot", "ينشئ لقطة صحة", "implemented"),
    Component(96, "Pipeline Heartbeat", "يراقب استمرار التشغيل", "implemented"),
    Component(97, "Recovery Planner", "يحدد مسار التعافي", "implemented"),
    Component(98, "Production Audit", "يدقق مراحل الإنتاج", "implemented"),
    Component(99, "End-to-End Verifier", "يتحقق من السلسلة كاملة", "implemented"),
    Component(100, "Cinematic Completion Gate", "لا يعلن الاكتمال إلا بعد اجتياز الفحوص", "implemented"),
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
