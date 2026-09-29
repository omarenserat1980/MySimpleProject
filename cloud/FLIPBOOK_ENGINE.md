# Brain Cloud Digital Flipbook Engine

The Flipbook Engine turns a sequence of drawings on white-paper-like pages into motion. Each page is one video frame; consecutive pages contain small changes in pose or position, and FFmpeg displays them in order.

## Pipeline
1. Create a deterministic page/frame sequence.
2. Keep frames numbered with a fixed-width pattern.
3. Verify the sequence is complete and readable.
4. Encode the sequence with FFmpeg.
5. Verify that the MP4 exists and is non-empty.
6. Hand the artifact to the existing Brain Cloud media/QC pipeline.

## Reference implementation
cloud/flipbook_renderer.py provides a deterministic bouncing-ball scene so CI can exercise the complete frame-to-video path without an external image service.

Run:
python -m cloud.flipbook_renderer --output /tmp/brain-flipbook --frames 24 --fps 12

The same engine can later accept generated drawings instead of the reference drawing function while preserving the frame numbering and verification contract.

## Production contract
- Runtime is Brain Cloud only.
- No Termux or Android execution is required.
- Frame names are frame_0001.png, frame_0002.png, ...
- Output is H.264 MP4 with yuv420p.
- A failed frame or failed encode is a failed production artifact, not a success.
