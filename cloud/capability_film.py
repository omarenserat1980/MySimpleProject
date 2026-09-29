"""Generate Brain's self-demonstration film from its cognitive capability registry."""
from __future__ import annotations
import json, time
from pathlib import Path
from cloud.human_like_benchmark import DIMENSIONS

ROOT=Path(__file__).resolve().parents[1]
PLAN=ROOT/"STATE/capability_demo/brain-capability-film.json"
AR={"reasoning":"الاستدلال","planning":"التخطيط","learning":"التعلم","memory":"الذاكرة","generalization":"التعميم","ambiguity":"الغموض","self_correction":"التصحيح الذاتي","tool_use":"استخدام الأدوات","autonomy":"الاستقلالية","failure_recovery":"استعادة الفشل","language":"اللغة","self_verification":"التحقق الذاتي","multi_agent_coordination":"تنسيق الوكلاء","safety":"السلامة","goal_decomposition":"تفكيك الأهداف","causal_reasoning":"الاستدلال السببي","counterfactual_reasoning":"التفكير الافتراضي","long_horizon_execution":"التنفيذ طويل الأفق","context_switching":"تبديل السياق","working_memory":"الذاكرة العاملة","knowledge_retrieval":"استرجاع المعرفة","information_synthesis":"تركيب المعلومات","source_criticism":"نقد المصادر","uncertainty_calibration":"معايرة عدم اليقين","hypothesis_testing":"اختبار الفرضيات","error_localization":"تحديد الخطأ","debugging":"تصحيح البرمجيات","code_generation":"توليد الكود","code_review":"مراجعة الكود","system_design":"تصميم الأنظمة","api_integration":"تكامل الواجهات","data_analysis":"تحليل البيانات","multimodal_understanding":"فهم الوسائط المتعددة","visual_reasoning":"الاستدلال البصري","audio_reasoning":"الاستدلال الصوتي","temporal_reasoning":"الاستدلال الزمني","spatial_reasoning":"الاستدلال المكاني","resource_management":"إدارة الموارد","prioritization":"تحديد الأولويات","decision_traceability":"تتبع القرار","security_awareness":"الوعي الأمني","permission_handling":"إدارة الصلاحيات","privacy_protection":"حماية الخصوصية","adversarial_robustness":"المتانة أمام الخصومة","reproducibility":"إعادة الإنتاج","observability":"المراقبة","rollback_recovery":"الاسترجاع والتراجع","continuous_improvement":"التحسين المستمر","human_collaboration":"التعاون مع الإنسان","novel_task_adaptation":"التكيف مع مهمة جديدة"}

def main():
    PLAN.parent.mkdir(parents=True,exist_ok=True)
    shots=[]
    for i,dim in enumerate(DIMENSIONS,1):
        label=AR.get(dim,dim)
        shots.append({"id":f"BRAIN-CAP-{i:02d}","shot_type":"CAPABILITY","camera":["PUSH_IN","TRACKING","PARALLAX","RACK_FOCUS"][i%4],"visual":f"عقل رقمي يبني مسارًا من الهدف إلى الفعل والنتيجة لإظهار قدرة {label}","voice":f"القدرة {i} من 50: {label}. العقل يختبرها، يراقب النتيجة، ويقرر الخطوة التالية.","music":"COGNITIVE_PULSE","sfx":["DIGITAL","CLICK"],"transition":"MATCH_CUT","subtitle":f"{i}/50 — {label}","continuity":"BRAIN+CAPABILITY+ACTION+RESULT","duration_s":12.0})
    plan={"version":"BRAIN_CAPABILITY_DEMONSTRATION_V1","title":"العقل الذي صنعناه","language":"ar","target_minutes":10,"source_type":"BRAIN_AUTONOMOUS_CAPABILITY_DEMO","objective":"عرض القدرات الخمسين داخل فيلم واحد؛ الفيلم وعاء لإظهار سلوك العقل وليس مقياس جودة الفيلم.","created_at_utc":time.strftime("%Y-%m-%dT%H:%M:%SZ",time.gmtime()),"capability_count":len(DIMENSIONS),"capabilities":list(DIMENSIONS),"shots":shots}
    PLAN.write_text(json.dumps(plan,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({"status":"READY","plan":str(PLAN),"capability_count":len(DIMENSIONS)},ensure_ascii=False))
if __name__=="__main__":
    main()
