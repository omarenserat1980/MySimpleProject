# V5.1 Local Runtime Bridge

V5.1 is the orchestration layer. The repository does not bundle a large image model.

The bridge discovers a real local executable on Android/Termux and invokes it with:

    --prompt "..."
    --output "/absolute/path/file.png"

Preferred configuration:

    export EB_IMAGE_ADAPTER=/absolute/path/to/your-generator

Then run:

    ./cinematic_image_engine_v51/run_termux.sh script.txt --project ./projects/myfilm

The engine never marks a shot VERIFIED unless the output file exists and passes its QC contract.

The existing PHONE-ONLY cinematic factory can then consume the approved stills and build motion/audio with its existing FFmpeg stage.

To inspect the phone runtime:

    python -m cinematic_image_engine_v51.runtime_probe

No fake model, fake QC score, or placeholder image is treated as a successful generation.
