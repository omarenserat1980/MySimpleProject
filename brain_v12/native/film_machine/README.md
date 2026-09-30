# Brain Film Machine Language

The Brain Film Machine Language (BFML) is the intermediate representation between story planning and native rendering.

Pipeline:

Story -> BFML -> C++ Raster/Cinema Engine -> MP4 -> C# Film Hub API -> dedicated Film UI

BFML is deterministic, auditable and provider-free. It describes scenes, camera keyframes, layers, primitives, timing and audio cues. It is not a human programming language; it is a machine instruction format designed for Brain.

The C++ engine is the executor. C# is the service/UI layer and never replaces the verified render stage.
