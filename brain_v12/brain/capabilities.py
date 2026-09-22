from __future__ import annotations

CAPABILITIES = [
    {"id":"self_improvement","name":"التطوير الذاتي المراقب","icon":"🔄","category":"cognitive","status":"sandbox"},
    {"id":"chat","name":"المحادثة والحوار","icon":"💬","category":"communication","status":"ready"},
    {"id":"voice","name":"الصوت","icon":"🎙️","category":"media","status":"browser"},
    {"id":"camera","name":"الكاميرا","icon":"📷","category":"media","status":"browser"},
    {"id":"images","name":"الصور والرؤية","icon":"🖼️","category":"ai","status":"ready"},
    {"id":"video","name":"الفيديو","icon":"🎬","category":"media","status":"ready"},
    {"id":"vision_ai","name":"تحليل الصور","icon":"👁️","category":"ai","status":"provider"},
    {"id":"speech_ai","name":"تحويل الكلام/النص","icon":"🗣️","category":"ai","status":"provider"},
    {"id":"image_ai","name":"توليد وتعديل الصور","icon":"🎨","category":"ai","status":"provider"},
    {"id":"video_ai","name":"توليد الفيديو","icon":"🎞️","category":"ai","status":"provider"},
    {"id":"web_tools","name":"الويب والبحث","icon":"🌐","category":"tools","status":"plugin"},
    {"id":"developer","name":"البرمجة والبناء","icon":"💻","category":"tools","status":"ready"},
    {"id":"files","name":"الملفات","icon":"📁","category":"tools","status":"ready"},
    {"id":"memory","name":"الذاكرة","icon":"🧠","category":"cognitive","status":"ready"},
    {"id":"planner","name":"التخطيط والقرار","icon":"🎯","category":"cognitive","status":"ready"},
    {"id":"flight","name":"الطيران والمحاكاة الجوية","icon":"✈️","category":"simulation","status":"safe"},
    {"id":"robotics","name":"الروبوتات والتحكم","icon":"🤖","category":"engineering","status":"safe"},
    {"id":"cybersecurity","name":"الأمن السيبراني الدفاعي","icon":"🛡️","category":"security","status":"safe"},
    {"id":"ethical_hacking_lab","name":"مختبر الاختبار الأمني المصرح","icon":"🔐","category":"security","status":"sandbox"},
    {"id":"network_diagnostics","name":"تشخيص الشبكات","icon":"🌐","category":"security","status":"safe"},
    {"id":"digital_forensics","name":"التحليل الجنائي الرقمي","icon":"🔎","category":"security","status":"safe"},
    {"id":"time_simulation","name":"محاكاة السفر عبر الزمن","icon":"⏳","category":"simulation","status":"simulation"},
    {"id":"future_scenarios","name":"محاكاة السيناريوهات المستقبلية","icon":"🔮","category":"simulation","status":"simulation"},
    {"id":"science_simulation","name":"المحاكاة العلمية","icon":"🧪","category":"science","status":"safe"},
    {"id":"computer_vision","name":"الرؤية الحاسوبية","icon":"👁️","category":"ai","status":"provider"},
    {"id":"multimodal_reasoning","name":"الاستدلال متعدد الوسائط","icon":"🧩","category":"ai","status":"provider"},
    {"id":"automation","name":"الأتمتة وسير العمل","icon":"⚡","category":"tools","status":"sandbox"},
    {"id":"data_analysis","name":"تحليل البيانات","icon":"📊","category":"tools","status":"ready"},
    {"id":"translation","name":"الترجمة متعددة اللغات","icon":"🌍","category":"ai","status":"ready"},
    {"id":"document_ai","name":"فهم المستندات","icon":"📄","category":"ai","status":"provider"},
]

PLUGINS = [
    {"id":"browser","name":"Web/Search","icon":"🌐","enabled":False,"permission":"search"},
    {"id":"image-tools","name":"Image Tools","icon":"🖼️","enabled":True,"permission":"media"},
    {"id":"camera","name":"Camera","icon":"📷","enabled":True,"permission":"camera"},
    {"id":"video-tools","name":"Video Tools","icon":"🎬","enabled":True,"permission":"media"},
    {"id":"voice","name":"Voice","icon":"🎙️","enabled":True,"permission":"microphone"},
    {"id":"developer-agent","name":"Developer Agent","icon":"💻","enabled":True,"permission":"sandbox"},
    {"id":"canva","name":"Canva","icon":"🎨","enabled":False,"permission":"external"},
]

TOOLS = [
    {"id":"self-improvement","name":"Self Improvement Planner","icon":"🔄","risk":"high"},
    {"id":"chat","name":"Chat","icon":"💬","risk":"low"},
    {"id":"upload","name":"Upload Media","icon":"📤","risk":"low"},
    {"id":"camera","name":"Camera Capture","icon":"📷","risk":"medium"},
    {"id":"voice","name":"Voice Input/Output","icon":"🎙️","risk":"low"},
    {"id":"agent","name":"Sandbox Agent","icon":"⚙️","risk":"high"},
    {"id":"builder","name":"Software Builder","icon":"🛠️","risk":"medium"},
]
