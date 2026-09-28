# Movie Summary Factory — BRAIN V12

## الهدف
إضافة خط إنتاج متخصص لتحويل معلومات فيلم إلى ملخص سينمائي أصلي، مع نفس فلسفة Cinematic Timeline Engine المستخدمة في أفلام BRAIN.

## Pipeline
INPUT
→ Movie Research/Source Pack
→ Story Extraction
→ Character Bible
→ Event Graph
→ Summary Script
→ Cinematic Beat Planner
→ Shot Planner
→ Voice Timing
→ Music/SFX Plan
→ Continuity QC
→ HTML Film

## Movie Summary Mode
- يطلب اسم الفيلم أو مصدرًا يقدمه المستخدم.
- يبني ملخصًا زمنيًا منظمًا بدل نسخ الفيلم.
- يحافظ على Cause → Effect → Consequence → Escalation.
- يحدد الشخصيات والأحداث المحورية فقط.
- يقسم كل فصل إلى Establishing / Wide / Medium / Close / Detail / Reaction / Transition.
- يربط التعليق الصوتي بالـbeats بدل تشغيله فوق صور ثابتة بلا توقيت.
- يدعم J-Cut / L-Cut / Match Cut / Cross Dissolve / Sound Bridge.
- يفرض حدًا أدنى من النشاط البصري/الصوتي في كل beat.
- يسجل continuity metadata للشخصيات والمكان والزمن وحالة الأشياء.
- يرفض تلقائيًا المخرجات التي تتحول إلى slideshow أو تحتوي على dead air.

## حقوق المحتوى
النظام مخصص لإنشاء تعليق/تحليل وملخص أصلي، وليس لإعادة إنتاج الفيلم أو حواراته أو مشاهد طويلة منه. عند الاعتماد على معلومات خارجية يجب حفظ المصدر والوقت الذي تم التحقق فيه.

## Quality Gates
1. Story: الأحداث مترابطة وليست قائمة أحداث.
2. Visual: تغير framing/camera/depth بصورة تخدم السرد.
3. Audio: voice/music/ambient/SFX متزامنة مع الـtimeline.
4. Continuity: لا تغييرات غير مبررة في الشخصية أو المكان أو الزمن.
5. Runtime: المدة المعروضة يجب أن تطابق المحتوى الفعلي، ولا يجوز إظهار 60 دقيقة إذا كان المحتوى أقصر.

## Default presets
- Short: 5–8 min
- Standard: 10–15 min
- Deep: 20–30 min

## API contract المقترح
MovieSummaryJob {
  title,
  language,
  target_minutes,
  source_pack,
  chapters[],
  characters[],
  events[],
  beats[],
  shots[],
  voiceover[],
  audio[],
  continuity[],
  qc
}

## Definition of Done
لا يعتبر الملخص جاهزًا إلا إذا اجتاز Story + Visual + Audio + Continuity + Runtime QC.

## CINEMATIC V3 PRO

V3 upgrades the existing factory without replacing it. It adds a shot-level cinematic planner, camera-motion vocabulary, rhythm-aware editing, audio ducking metadata, SFX binding, subtitle timing fields, character/location continuity gates, mobile/GPU-friendly rendering requirements, and an anti-slideshow QC gate. The V3 API endpoint is `POST /api/movie-summary/v3/plan` and the browser UI is `/movie-summary-v3.html`.

### V3 Quality Gate
The plan is rejected unless it has multiple shots per beat, camera motion, voiceover, music, event-bound SFX, subtitles, transitions, continuity metadata, and a non-static presentation path.
