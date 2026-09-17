import argparse
import json
from pathlib import Path
from publisher import youtube_upload, facebook_upload

parser = argparse.ArgumentParser(description="Publish the generated ad to YouTube/Facebook")
parser.add_argument("video", nargs="?", default="output/foras_p100_ad.mp4")
parser.add_argument("--youtube", action="store_true")
parser.add_argument("--facebook", action="store_true")
parser.add_argument("--title", default="مضخة مياه FORAS P100")
parser.add_argument("--description", default="مضخة مياه FORAS P100")
parser.add_argument("--privacy", default="private", choices=["private", "public", "unlisted"])
args = parser.parse_args()

video = Path(args.video)
if not video.exists():
    raise SystemExit(f"الفيديو غير موجود: {video}. أنشئ الفيديو أولاً.")

if not (args.youtube or args.facebook):
    raise SystemExit("استخدم --youtube أو --facebook أو الاثنين معاً.")

if args.youtube:
    print("YouTube:", youtube_upload(str(video), args.title, args.description, ["FORAS", "P100", "مضخة", "مضخات"], args.privacy))
if args.facebook:
    print("Facebook:", json.dumps(facebook_upload(str(video), args.title, args.description), ensure_ascii=False))
