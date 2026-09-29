#!/usr/bin/env python3
"""Fast deterministic tests for the Room 13 production pipeline."""
from __future__ import annotations

import ast
import json
import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[2]
PLAN = ROOT / "brain_v12/movie_summary_factory/jobs/room-13-horror-10m-cinematic-v3.json"
RENDERER = ROOT / "brain_v12/movie_summary_factory/render_room13_animatic.py"
QC = ROOT / "brain_v12/movie_summary_factory/room13_qc.py"
REGISTRY = ROOT / "brain_v12/movie_summary_factory/room13_components.py"


class Room13PipelineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.plan = json.loads(PLAN.read_text(encoding="utf-8"))
        cls.renderer = RENDERER.read_text(encoding="utf-8")
        cls.qc = QC.read_text(encoding="utf-8")

    def test_plan_shape(self):
        self.assertEqual(len(self.plan["beats"]), 8)
        self.assertEqual(len(self.plan["shots"]), 32)
        self.assertEqual(self.plan["target_minutes"], 10)
        ids = [s["id"] for s in self.plan["shots"]]
        self.assertEqual(len(ids), len(set(ids)))

    def test_shots_are_production_ready(self):
        for shot in self.plan["shots"]:
            for key in ("visual", "voice", "subtitle", "camera", "transition"):
                self.assertTrue(shot.get(key), f"{shot.get('id')}: missing {key}")
            self.assertGreater(float(shot.get("duration_s", 0)), 0)

    def test_python_sources_compile(self):
        ast.parse(self.renderer, filename=str(RENDERER))
        ast.parse(self.qc, filename=str(QC))
        ast.parse(REGISTRY.read_text(encoding="utf-8"), filename=str(REGISTRY))

    def test_renderer_has_integrity_qc(self):
        for token in ("ROOM13_OUTPUT_INVALID", "ROOM13_QC_FAILED", "RENDERED"):
            self.assertIn(token, self.renderer)

    def test_renderer_audio_is_dynamic(self):
        self.assertIn("afade=t=out:st=", self.renderer)
        self.assertIn("amix=inputs=2", self.renderer)
        self.assertIn("loudnorm=", self.renderer)

    def test_renderer_creates_real_visual_assets(self):
        for token in ("make_ppm", "hospital", "door", "corridor", "character", "clock"):
            self.assertIn(token, self.renderer)
        self.assertNotIn("drawtext=", self.renderer)

    def test_renderer_has_arabic_voice_pipeline(self):
        self.assertIn("espeak-ng", self.renderer)
        self.assertIn('"ar"', self.renderer)
        self.assertIn('"voiceover": True', self.renderer)

    def test_stage7_self_healing_gate_exists(self):
        p = ROOT / "brain_v12/movie_summary_factory/room13_stage7_repair.py"
        self.assertTrue(p.is_file())
        ast.parse(p.read_text(encoding="utf-8"))
        text = p.read_text(encoding="utf-8")
        for token in ("MAX_REPAIRS", r"Component\(0([1-9])", "UNSUPPORTED_STAGE7_SYNTAX", "READY"):
            self.assertIn(token, text)

    def test_media_health_gate_exists(self):
        gate = ROOT / "brain_v12/movie_summary_factory/room13_media_health.py"
        self.assertTrue(gate.is_file())
        ast.parse(gate.read_text(encoding="utf-8"), filename=str(gate))
        source = gate.read_text(encoding="utf-8")
        for token in ("READY", "BLOCKED", "espeak-ng", "make_ppm", "ROOM13_QC_FAILED", "component_count"):
            self.assertIn(token, source)

    def test_component_registry_has_100_components(self):
        source = REGISTRY.read_text(encoding="utf-8")
        namespace = {}
        exec(compile(source, str(REGISTRY), "exec"), namespace)
        errors = namespace["validate_registry"]()
        self.assertEqual(errors, [])
        self.assertEqual(len(namespace["all_components"]()), 100)

    def test_brain_toolchain_is_required(self):
        self.assertIn("brain_ffmpeg", self.renderer)
        self.assertIn("brain_ffmpeg", self.qc)
        self.assertNotIn('shutil.which("ffmpeg")', self.renderer)
        self.assertNotIn('shutil.which("ffprobe")', self.renderer)


if __name__ == "__main__":
    unittest.main(verbosity=2)
