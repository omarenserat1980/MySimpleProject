from brain_v12.youtube.channel_strategy import ChannelProfile
from brain_v12.youtube.content_integrity import ContentFingerprint
from brain_v12.youtube.control_plane import control_video
from brain_v12.youtube.execution_plan import PlanStep, compile_execution_plan
from brain_v12.youtube.qc_gate import QcReport
from brain_v12.youtube.revenue_factory import VideoCandidate
from brain_v12.youtube.video_economics import VideoEconomics


def build():
    channel = ChannelProfile("c", "ar", "ai", .9, .9, .4, .9, .8, .9)
    candidate = VideoCandidate("v", "ai", "story", .9, .1, .1, .9)
    economics = VideoEconomics("v", 2, 1, 0, 10000, 5, .8, .8)
    qc = QcReport(True, True, 120, True, True, True, .1)
    fingerprint = ContentFingerprint("v", "ai", "story", "script", "assets")
    return control_video(channel, candidate, economics, qc, fingerprint, [])


def test_publish_plan_is_ordered_and_requires_authorization():
    plan = compile_execution_plan(build())
    assert plan.steps == (
        PlanStep.DRAFT, PlanStep.RENDER, PlanStep.QC,
        PlanStep.PUBLISH, PlanStep.MEASURE, PlanStep.LEARN,
    )
    assert plan.requires_publish_authorization is True
    assert plan.side_effects is False


def test_duplicate_compiles_to_empty_plan():
    decision = build()
    duplicate = control_video(
        ChannelProfile("c", "ar", "ai", .9, .9, .4, .9, .8, .9),
        VideoCandidate("v", "ai", "story", .9, .1, .1, .9),
        VideoEconomics("v", 2, 1, 0, 10000, 5, .8, .8),
        QcReport(True, True, 120, True, True, True, .1),
        ContentFingerprint("v", "ai", "story", "script", "assets"),
        [ContentFingerprint("v", "ai", "story", "script", "assets")],
    )
    plan = compile_execution_plan(duplicate)
    assert plan.steps == ()
    assert plan.requires_publish_authorization is False
