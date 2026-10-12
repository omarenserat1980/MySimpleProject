# Electronic Brain V12

هذا المستودع أصبح مخصصًا لـ **العقل الإلكتروني V12**.

## البنية
- `brain_v12/` — النواة والخدمات والواجهة.
- `brain_v12/web/index.html` — واجهة V12 العربية RTL.
- `brain_v12/start_brain.sh` — تشغيل الخدمة محليًا.
- `.github/workflows/brain-v12-pages.yml` — نشر واجهة V12 على GitHub Pages.

## الحلقة المعرفية
Perceive → Understand → Memory → Goal → Plan → Decide → Act → Observe → Learn

تمت إزالة ملفات مشروع المضخة من جذر المشروع حتى لا تبقى واجهة أو تشغيلات خاصة بالمضخات ضمن المشروع الحالي.

## Brain Cloud runtime

المسار التشغيلي المعتمد للإنتاج هو **Brain Cloud فقط**. الإنتاج السينمائي، الطوابير، التخزين، التحقق، وعمليات النشر الاختيارية تعمل داخل Cloud Runtime.

- لا يعتمد الإنتاج على Termux أو جهاز خارجي.
- DeviceBridge موجود للتوافق البرمجي فقط، وتنفيذ مهام الأجهزة معطّل في Cloud.
- لا يُعتبر الفيلم ناجحًا إلا بعد إنشاء MP4 حقيقي واجتياز FFprobe/QC مستقل للصوت والصورة.
- FFmpeg وFFprobe يمران عبر عقد Brain-native toolchain (`BRAIN_FFMPEG_BIN` و`BRAIN_FFPROBE_BIN`).

## Mining Economics
أضيفت طبقة **Mining Economics** للعقل V12 للتحليل الحسابي فقط، دون تشغيل تعدين أو شراء أجهزة أو ربط محافظ.

### ما الذي تحسبه؟
- استهلاك الكهرباء اليومي بالكيلوواط-ساعة.
- تكلفة الكهرباء بالدينار الأردني.
- عمولة مجمع التعدين والتكاليف اليومية الأخرى.
- صافي الإيراد الحسابي يوميًا ولفترة 30 يومًا.
- تكلفة الجهاز وفترة استرداد رأس المال عندما تكون المدخلات موجبة.
- مقارنة عدة إعدادات على أساس صافي الناتج المحسوب من المدخلات.

### واجهة API
- GET /api/mining/status
- POST /api/mining/analyze
- POST /api/mining/compare

**حدود مهمة:** النتائج ليست بيانات سوق حية، ولا تُسجل كدخل محقق. أي ربح فعلي يبقى صفرًا حتى يوجد دليل دفع قابل للمطابقة في نظام الإيرادات.

## GitHub Cloud verification

يستخدم Brain الآن مسار تحقق موحدًا:

**Supervisor → Reusable Brain Cloud → Tests → VerificationGate → Evidence**

- نجاح التنفيذ (`ACTION_VERIFIED`) لا يساوي إكمال الهدف (`OBJECTIVE_VERIFIED`).
- لا يُسمح لـBrain بإعلان الإكمال الموضوعي دون دليل غير فارغ وشرط تحقق صريح.
- `brain-github-supervisor.yml` يستدعي `brain-github-cloud.yml` مباشرة كـReusable Workflow.
- Evidence الناتج يجب أن يحتوي على عقدة التحقق وسجل المهمة قبل اعتباره صالحًا.

## CI Repair Sprint (Pilot Service)

Electronic Brain includes a **draft, owner-reviewed pilot service package** for diagnosing one bounded GitHub Actions / Python CI failure. The package is documentation only; it is not a published service listing or evidence of customer demand, completed external work, or revenue.

- [Service page draft](examples/ci-repair-sprint/SERVICE_PAGE.md)
- [Customer intake template](examples/ci-repair-sprint/INTAKE_TEMPLATE.md)
- [Delivery checklist](examples/ci-repair-sprint/README.md)
- [Illustrative sample report](examples/ci-repair-sprint/SAMPLE_REPORT.md)

The proposed USD 49–99 pilot price is indicative only and must be agreed before any work starts. Do not share secrets in logs. Record revenue only after independently verified payment.


## Software-only execution nodes

Brain's worker registry now defaults to software nodes. Physical-device/Termux workers are an optional compatibility adapter and are disabled unless `BRAIN_ENABLE_DEVICE_WORKERS=1` is explicitly configured. The registry remains usable when an optional device adapter is absent or fails.

- Contract and limitations: [Software-only nodes](brain_v12/docs/SOFTWARE_ONLY_NODES.md)
- Focused hosted CI: [Brain Software-Only Node Verification](.github/workflows/brain-software-only-nodes.yml)
- This is an incremental decoupling step, not a claim that every Brain workload has already migrated or that virtual resources provide unlimited compute.
