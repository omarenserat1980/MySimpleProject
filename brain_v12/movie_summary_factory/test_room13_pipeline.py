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

    def test_renderer_has_integrity_qc(self):
        for token in ("ROOM13_OUTPUT_INVALID", "ROOM13_QC_FAILED", "RENDERED"):
            self.assertIn(token, self.renderer)

    def test_renderer_audio_is_dynamic(self):
        self.assertIn("afade=t=out:st={max(0, d-1)}", self.renderer)

    def test_brain_toolchain_is_required(self):
        self.assertIn("brain_ffmpeg", self.renderer)
        self.assertIn("brain_ffmpeg", self.qc)
        self.assertNotIn('shutil.which("ffmpeg")', self.renderer)
        self.assertNotIn('shutil.which("ffprobe")', self.renderer)

if __name__ == "__main__":
    unittest.main(verbosity=2)
