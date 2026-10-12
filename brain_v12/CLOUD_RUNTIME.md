# Brain Cloud-Owned Runtime

## هدف

يجعل Brain التنفيذ الإنتاجي سحابيًا بالكامل من خلال Cloud VM/Container مملوك
لـBrain، وليس من خلال جهاز المستخدم أو GitHub-hosted runner.

### التقسيم

- **Brain Cloud Runtime:** التنفيذ، الطوابير، checkpoints، evidence، recovery.
- **GitHub:** source-of-truth، versioning، review، audit، artifacts فقط.
- **GitHub Actions:** اختبارات/تحقق control-plane فقط، وليس منفذًا للإنتاج.
- **Local device:** اختياري للإدارة والمراقبة، وليس شرطًا للتشغيل.

## التشغيل

على أي Linux x86_64 Cloud VM:

```bash
export BRAIN_INTERNAL_RUNNER_FLAG=1
./tools/run_brain_cloud_runtime.sh
```

أو باستخدام Docker Compose:

```bash
docker compose -f docker-compose.brain-cloud.yml up -d --build
```

الحاوية تتضمن QEMU/OVMF وxorriso/wimlib/dosfstools/mtools اللازمة لمسارات
Windows/QEMU، وتستخدم volume دائمًا للـruntime state.

## شرط مهم

هذا **ليس GitHub Actions self-hosted runner**. لا يتم تسجيل هذه الآلة كـGitHub
runner. GitHub لا يملك عملية التنفيذ.

## Windows Real Boot

يحتاج Cloud VM إلى x86_64 Linux، ويفضل KVM/nested virtualization. إذا لم يتوفر
KVM، يمكن استخدام QEMU TCG كمسار أبطأ. لا تعتبر Brain وجود الـVM دليلًا على نجاح
Windows boot؛ الدليل لا يصبح VERIFIED إلا بعد تشغيل الاختبار وإنتاج evidence
صالح.

## الحالة

`BRAIN_CLOUD_RUNTIME=STARTING` تعني بدء العامل فقط.

الاستقلال الفعلي يتطلب:
1. Cloud runtime online.
2. Preflight verified.
3. task executed.
4. evidence written.
5. recovery tested.
6. authority boundary tested.
7. autonomy certification accepted.

لا يجوز إعلان `AUTONOMOUS_WITHIN_AUTHORITY` قبل هذه الأدلة.
