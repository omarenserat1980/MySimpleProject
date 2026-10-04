"""Renderer contract shared by native BRAIN renderers."""
RENDER_SPEC={"version":1,"inputs":["project.json","storyboard.json"],"outputs":["frames","audio","master.mp4","manifest.json"],"required_video":["width","height","fps","duration"],"required_audio":["codec","sample_rate","channels"],"release_rule":"commercial_gate_required"}
