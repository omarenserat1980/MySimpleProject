# BRAIN Short Video Factory — OSS Integration

## الهدف

تحويل ما وصلنا إليه — **صورة واحدة + كلام + تحريك الفم + صوت + MP4** — إلى خط إنتاج قصير قابل للتكرار داخل Brain.

## البنية

```
Human command
  -> Short Video Plan
  -> TTS adapter (optional/local)
  -> audio timing
  -> Lip-sync adapter
  -> BRAIN Media Engine / FFmpeg
  -> ffprobe + independent verification
  -> VERIFIED_COMPLETED
```

### المكوّنات المرجعية

| المكوّن | الدور | الترخيص المسجل |
|---|---|---|
| MuseTalk | lip-sync | MIT |
| SadTalker | single-image talking head | Apache-2.0 |
| LivePortrait | portrait animation | MIT* |
| VOICEVOX Core | local TTS core | MIT |
| BlueMagpie-TTS | Taiwan Mandarin/code-switching TTS | Apache-2.0 |
| RHVoice | Russian/local TTS | GPL/LGPL بحسب المكوّن |
| NileTTS | Arabic TTS research | Apache-2.0 |
| Chitralekha | video transcreation / subtitles / voice-over | MIT |

* يجب فحص تراخيص النماذج التابعة/الـdependencies قبل أي استخدام إنتاجي.

## قاعدة مهمة

Brain لا ينسخ كود هذه المشاريع إلى مستودعه لمجرد أنها مفتوحة المصدر؛ بل يستخدم **adapter contracts** ويحتفظ بالمصدر والترخيص في provenance. هذا يقلل تلوث التراخيص ويجعل تبديل المحركات ممكنًا.

## التشغيل

المحركات الثقيلة اختيارية. بدون أي API مدفوع أو نموذج خارجي، يعمل التخطيط والمسار المحلي مع FFmpeg/ffprobe.

لتفعيل MuseTalk لاحقًا:

`BRAIN_MUSETALK_CMD`

ولـ SadTalker:

`BRAIN_SADTALKER_CMD`

ولـ VOICEVOX:

`BRAIN_VOICEVOX_URL`

ولـ RHVoice:

`BRAIN_RHVOICE_CMD`

ولـ BlueMagpie:

`BRAIN_BLUEMAGPIE_CMD`

لا يتم اعتبار backend جاهزًا للإنتاج إلا بعد تشغيل الاختبارات ومرور بوابة التحقق المستقلة.
