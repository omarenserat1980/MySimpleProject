"""Curated Quranic nafs corpus for Brain Cloud.

This corpus is a design/reference dataset, not a tafsir and not a claim that
software can instantiate the metaphysical human nafs or ruh.
References are grouped by engineering-relevant themes.
"""
from dataclasses import dataclass

@dataclass(frozen=True)
class NafsVerse:
    ref: str
    theme: str
    engineering_principle: str

NAFS_CORPUS = [
    NafsVerse("4:1","origin/shared humanity","treat people as individuals within shared human dignity"),
    NafsVerse("4:79","responsibility","trace harmful outcomes to the responsible action"),
    NafsVerse("4:110","error and repentance","support correction after wrongdoing"),
    NafsVerse("4:111","individual accountability","keep responsibility attached to the actor"),
    NafsVerse("5:30","harmful impulse","detect when an internal impulse drives harmful action"),
    NafsVerse("6:164","individual responsibility","never transfer one agent's responsibility to another"),
    NafsVerse("7:188","limits of self-knowledge","do not claim control or knowledge beyond capability"),
    NafsVerse("8:53","internal change","monitor internal state as a driver of external behavior"),
    NafsVerse("9:118","repentance under pressure","allow recovery after severe failure"),
    NafsVerse("12:18","self-restraint and patience","avoid reacting impulsively to incomplete evidence"),
    NafsVerse("12:53","nafs ammarah","detect and resist harmful impulses"),
    NafsVerse("13:11","internal change","make improvement begin with internal state"),
    NafsVerse("16:72","gratitude and provision","record beneficial conditions without entitlement"),
    NafsVerse("17:14","self-accounting","maintain an inspectable record of actions"),
    NafsVerse("17:70","human dignity","preserve dignity and avoid dehumanizing decisions"),
    NafsVerse("18:28","patience and orientation","resist short-term distraction from long-term goals"),
    NafsVerse("24:21","temptation and restraint","add a temptation-risk checkpoint"),
    NafsVerse("28:16","acknowledge error","support explicit admission and correction"),
    NafsVerse("29:6","effort and self-development","treat improvement work as benefiting the agent's own state"),
    NafsVerse("30:8","self-reflection","require periodic reflection on internal state"),
    NafsVerse("31:12","gratitude","track and reinforce constructive outcomes"),
    NafsVerse("31:34","uncertainty about tomorrow","calibrate uncertainty and avoid false prediction"),
    NafsVerse("35:18","non-transferable burden","isolate accountability per action and agent"),
    NafsVerse("39:53","hope and recovery","failure is recoverable; avoid despair loops"),
    NafsVerse("40:17","fair accounting","make evaluation evidence-based and non-arbitrary"),
    NafsVerse("41:46","consequence symmetry","connect actions to their consequences"),
    NafsVerse("42:30","causal responsibility","surface possible self-caused failures"),
    NafsVerse("50:16","inner whispering","model internal candidate impulses before action"),
    NafsVerse("53:32","no self-certification","the system must not declare itself morally pure"),
    NafsVerse("59:18","prepare for tomorrow","perform forward-looking self-audit"),
    NafsVerse("64:16","capacity and restraint","respect capability limits while pursuing improvement"),
    NafsVerse("75:2","nafs lawwamah","run post-action self-review and correction"),
    NafsVerse("76:8-9","selfless giving","include effects on others in utility evaluation"),
    NafsVerse("89:27-30","nafs mutmainnah","define a stable, non-reactive decision state"),
    NafsVerse("91:7-10","purification","make continuous improvement and moral discrimination explicit"),
]

THEME_ORDER = [
    "impulse_and_temptation",
    "self_review",
    "accountability",
    "uncertainty",
    "limits",
    "recovery",
    "purification",
    "stable_decision",
    "human_dignity",
]

def corpus_stats() -> dict:
    return {
        "verses": len(NAFS_CORPUS),
        "themes": THEME_ORDER,
        "source_scope": "Quranic references; engineering interpretation only",
    }
