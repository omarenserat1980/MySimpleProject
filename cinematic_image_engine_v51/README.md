# ELECTRONIC BRAIN — CINEMATIC IMAGE ENGINE V5.1

Android/Termux-first orchestration layer:

SCRIPT -> SCENES -> SHOTS -> LOCAL IMAGE EXECUTOR -> QC -> MASTER -> RESUME

Implemented:
- persistent project_state.json
- zero-redundancy verified-shot skip
- automatic scene/shot planning
- continuity-aware prompt assembly
- local model router
- retry loop and NEEDS_REVIEW
- atomic state saves
- manifest.json
- sequential generation to reduce RAM pressure

The orchestration layer never claims a generated image exists unless a configured local adapter creates it.

Set EB_IMAGE_ADAPTER to an executable accepting:
--prompt "..." --output /path/to/file.png

Example:
EB_IMAGE_ADAPTER=/data/local/bin/my_local_generator ./cinematic_image_engine_v51/run_termux.sh script.txt --project ./projects/myfilm
