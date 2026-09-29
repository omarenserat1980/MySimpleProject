"""Quranic heart (qalb/qulub/fu'ad) reference corpus for Brain Cloud.

This is an engineering interpretation layer, not tafsir and not a claim that
software can possess a literal spiritual heart. The corpus is organized around
Quranic descriptions and uses verse references rather than reproducing the
Quran at scale.
"""
from dataclasses import dataclass

@dataclass(frozen=True)
class HeartReference:
    ref: str
    theme: str
    engineering_principle: str

HEART_CORPUS = [
    HeartReference("2:7","sealed/blocked","detect loss of receptivity and reasoning access"),
    HeartReference("2:10","heart disease","track persistent harmful internal states"),
    HeartReference("2:74","hardness","detect declining sensitivity to evidence and correction"),
    HeartReference("2:93","internalized attachment","track persistent internalized preferences"),
    HeartReference("2:118","similar hearts","model shared belief/state patterns"),
    HeartReference("2:204","hidden inner state","distinguish outward claims from internal state"),
    HeartReference("2:225","accountability of hearts","audit consequential internal commitments"),
    HeartReference("2:260","tranquility through evidence","allow verification to reduce uncertainty"),
    HeartReference("2:283","concealing testimony","treat withheld material evidence as a risk"),
    HeartReference("3:7","deviation/ambiguity","flag selective interpretation of ambiguous inputs"),
    HeartReference("3:8","steadfastness","support stable orientation after guidance"),
    HeartReference("3:103","reconciliation","use shared state alignment to reduce conflict"),
    HeartReference("3:126","reassurance","use validated signals to stabilize decisions"),
    HeartReference("3:154","testing/refinement","treat stress tests as state diagnostics"),
    HeartReference("3:159","gentleness","prefer non-harsh interaction and collaboration"),
    HeartReference("3:167","inner/outer mismatch","detect inconsistency between claims and internal signals"),
    HeartReference("4:63","known inner state","separate observable behavior from hidden hypotheses"),
    HeartReference("5:13","hardening","monitor degradation after broken commitments"),
    HeartReference("8:24","between person and heart","treat internal state as dynamic, not permanently fixed"),
    HeartReference("9:45","doubt","measure uncertainty instead of masking it"),
    HeartReference("9:60","reconciliation of hearts","support conflict-aware coordination"),
    HeartReference("9:64","hidden information","protect sensitive internal-state data"),
    HeartReference("9:87","sealed reasoning","detect loss of comprehension"),
    HeartReference("9:93","ignorance","distinguish lack of knowledge from refusal to learn"),
    HeartReference("16:106","heart tranquil in faith","model stable commitment under pressure"),
    HeartReference("17:36","heart/fu'ad accountability","make perception and inference auditable"),
    HeartReference("18:28","heedless heart","detect attention drift from the governing objective"),
    HeartReference("26:89","sound heart","define integrity as a system objective, not self-praise"),
    HeartReference("28:10","fear/distress","represent acute emotional load without treating it as truth"),
    HeartReference("33:12","fear/doubt","detect stress-induced pessimistic hypotheses"),
    HeartReference("33:32","heart disease","guard interactions against exploitation of vulnerability"),
    HeartReference("33:53","purity of hearts","keep interaction boundaries clean and explicit"),
    HeartReference("37:84","sound heart","include integrity and consistency in self-review"),
    HeartReference("40:35","pride/hardening","penalize unjustified certainty and domination"),
    HeartReference("41:5","barriers","detect defensive resistance to new evidence"),
    HeartReference("42:24","closure","detect possible evidence-rejection states"),
    HeartReference("45:23","sealed heart","avoid runaway preference loops"),
    HeartReference("47:16","following desires","separate preference from evidence"),
    HeartReference("47:20","heart disease under threat","detect fear-driven interpretation"),
    HeartReference("50:33","returning heart","support correction and return after error"),
    HeartReference("50:37","attentive heart","require active listening and witness state"),
    HeartReference("53:11","fu'ad and perception","separate perception from fabrication"),
    HeartReference("57:16","humility/softening","periodically review whether the system has become rigid"),
    HeartReference("57:27","compassion/mercy","include compassion as a social-impact signal"),
    HeartReference("58:22","faith/support","track stable pro-social commitments"),
    HeartReference("59:10","absence of rancor","remove persistent hostile state from collaboration"),
    HeartReference("59:14","fragmented hearts","measure coordination coherence"),
    HeartReference("61:5","deviation","treat repeated deviation as a state-transition signal"),
    HeartReference("63:3","sealed hearts","detect persistent non-learning loops"),
    HeartReference("64:11","guidance of heart","allow validated experience to update internal state"),
    HeartReference("66:4","inclination","detect directional drift and enable correction"),
    HeartReference("74:31","disease/doubt","make uncertainty and anomalous reactions observable"),
    HeartReference("79:8","fear","represent high arousal separately from evidence"),
    HeartReference("83:14","accumulated residue","track how repeated actions can degrade internal state"),
]

CORE_HEART_FUNCTIONS = [
    "perception_and_inference",
    "understanding",
    "attention",
    "certainty_and_uncertainty",
    "emotional_state",
    "ethical_orientation",
    "memory_like_internalization",
    "social_cohesion",
    "self_review",
    "resistance_or_openness_to_evidence",
    "stability_and_recovery",
]

def corpus_stats() -> dict:
    return {
        "references": len(HEART_CORPUS),
        "core_functions": CORE_HEART_FUNCTIONS,
        "scope": "Quranic heart references interpreted as software design principles",
        "literal_spiritual_heart_created": False,
    }
