#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
OUT_DIR="${ROOT}/cinematic_output/5s_movie"
mkdir -p "${OUT_DIR}"

IMAGE="${OUT_DIR}/hero.png"
VIDEO="${OUT_DIR}/hero_5s.mp4"

command -v termux-diffusion >/dev/null 2>&1 || {
  echo "ERROR: termux-diffusion is not installed."
  exit 1
}
command -v ffmpeg >/dev/null 2>&1 || {
  echo "ERROR: ffmpeg is not installed. Run: pkg install ffmpeg -y"
  exit 1
}

PROMPT="cinematic photorealistic futuristic superhero standing on a rain-soaked rooftop at night, realistic human face and skin, dark city skyline, atmospheric mist, subtle wind moving the cape, dramatic blockbuster lighting, 35mm lens, shallow depth of field, ultra detailed, no text, no logos"

echo "[1/2] Generating master image..."
termux-diffusion generate "${PROMPT}" \
  -m cyberrealistic-lcm \
  --cpu -W 512 -H 512 --steps 6 \
  -o "${IMAGE}"

test -s "${IMAGE}" || {
  echo "ERROR: image generation completed without creating ${IMAGE}"
  exit 1
}

echo "[2/2] Building 5-second cinematic clip..."
ffmpeg -y -hide_banner -loglevel error \
  -loop 1 -i "${IMAGE}" \
  -vf "scale=1280:720:force_original_aspect_ratio=increase,crop=1280:720,zoompan=z='min(zoom+0.0008,1.08)':d=120:s=1280x720:fps=24,fade=t=in:st=0:d=0.35,fade=t=out:st=4.65:d=0.35" \
  -t 5 -an -c:v libx264 -pix_fmt yuv420p -movflags +faststart \
  "${VIDEO}"

test -s "${VIDEO}" || {
  echo "ERROR: ffmpeg did not create ${VIDEO}"
  exit 1
}

echo
echo "DONE"
echo "IMAGE: ${IMAGE}"
echo "VIDEO: ${VIDEO}"
ls -lh "${IMAGE}" "${VIDEO}"
