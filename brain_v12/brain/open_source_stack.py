"""Open-source capability registry for Brain.

Brain integrates through adapters rather than copying third-party applications.
Each entry records license and deployment requirements so future upgrades can
be evaluated without silently introducing proprietary dependencies.
"""
TOOLS = [
 {"id":"comfyui","name":"ComfyUI","license":"GPL-3.0","role":"visual_media_engine",
  "capabilities":["image","video","audio","3d","workflow_graph","local_api"],
  "endpoint":"http://127.0.0.1:8188/system_stats",
  "repo":"https://github.com/Comfy-Org/ComfyUI",
  "mode":"optional_local_service"},
 {"id":"ltx2","name":"LTX-2","license":"Apache-2.0","role":"video_audio_generation",
  "capabilities":["text_to_video","image_to_video","audio_video","keyframes","loras"],
  "repo":"https://github.com/Lightricks/LTX-Video",
  "mode":"optional_local_model"},
 {"id":"whisper","name":"Whisper","license":"MIT","role":"speech_pipeline",
  "capabilities":["transcription","language_detection","speech_translation","timestamps"],
  "repo":"https://github.com/openai/whisper",
  "mode":"optional_local_model"},
 {"id":"ollama","name":"Ollama","license":"MIT","role":"local_llm_runtime",
  "capabilities":["local_llm","chat","embeddings","agent_backend","rest_api"],
  "endpoint":"http://127.0.0.1:11434/api/tags",
  "repo":"https://github.com/ollama/ollama",
  "mode":"optional_local_service"},
 {"id":"llama_cpp","name":"llama.cpp","license":"MIT","role":"portable_llm_runtime",
  "capabilities":["llm","vlm","quantized_inference","openai_compatible_server"],
  "endpoint":"http://127.0.0.1:8080/health",
  "repo":"https://github.com/ggml-org/llama.cpp",
  "mode":"optional_local_service"},
 {"id":"qdrant","name":"Qdrant","license":"Apache-2.0","role":"semantic_memory",
  "capabilities":["vector_search","hybrid_search","payload_filtering","local_edge_memory"],
  "endpoint":"http://127.0.0.1:6333/readyz",
  "repo":"https://github.com/qdrant/qdrant",
  "mode":"optional_local_service"},
 {"id":"livekit_agents","name":"LiveKit Agents","license":"Apache-2.0","role":"realtime_agent_transport",
  "capabilities":["voice_agents","video_agents","webrtc","telephony","realtime_tools"],
  "repo":"https://github.com/livekit/agents",
  "mode":"optional_service"},
]

def get_tool(tool_id: str):
    return next((x for x in TOOLS if x["id"] == tool_id), None)

def capabilities():
    return TOOLS
