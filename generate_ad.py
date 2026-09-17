import argparse
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
from moviepy.editor import ImageClip, concatenate_videoclips

W, H = 1080, 1920
FPS = 30

parser = argparse.ArgumentParser()
parser.add_argument('--product', default='مضخة مياه FORAS P100')
parser.add_argument('--price', default='')
parser.add_argument('--contact', default='')
parser.add_argument('--copy', default='حل عملي لضخ المياه. جودة واعتمادية للاستخدام اليومي.')
parser.add_argument('--image', default='assets/foras_p100.jpg')
parser.add_argument('--output', default='output/foras_p100_ad.mp4')
args = parser.parse_args()

PRODUCT = Path(args.image)
OUT = Path(args.output)
OUT.parent.mkdir(parents=True, exist_ok=True)
TITLE, PRICE, CONTACT = args.product, args.price, args.contact


def font(size):
    candidates = [
        '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf',
        '/system/fonts/NotoSansArabic-Bold.ttf',
        '/system/fonts/NotoNaskhArabic-Regular.ttf',
        'C:/Windows/Fonts/arialbd.ttf',
    ]
    for p in candidates:
        if Path(p).exists():
            return ImageFont.truetype(p, size)
    return ImageFont.load_default()


def make_scene(text, seconds, product=False):
    img = Image.new('RGB', (W, H), 'white')
    d = ImageDraw.Draw(img)
    d.text((W // 2, 180), TITLE, font=font(72), anchor='ma', fill='black')
    if product:
        if not PRODUCT.exists():
            raise FileNotFoundError(f'صورة المنتج غير موجودة: {PRODUCT}')
        p = Image.open(PRODUCT).convert('RGB')
        p.thumbnail((900, 1050))
        img.paste(p, ((W - p.width) // 2, 430))
    d.text((W // 2, 1450), text, font=font(58), anchor='ma', align='center', fill='black', spacing=18)
    if PRICE:
        d.text((W // 2, 1640), PRICE, font=font(65), anchor='ma', fill='black')
    if CONTACT:
        d.text((W // 2, 1770), CONTACT, font=font(48), anchor='ma', fill='black')
    return img

scenes = [
    (args.copy, 3, False),
    ('جودة واعتمادية\nللاستخدام اليومي', 4, True),
    ('اطلبها الآن\nوتواصل معنا', 3, True),
]

clips = []
for text, seconds, product in scenes:
    clips.append(ImageClip(make_scene(text, seconds, product)).set_duration(seconds))

video = concatenate_videoclips(clips, method='compose')
video.write_videofile(str(OUT), fps=FPS, codec='libx264', audio=False)
print(f'تم إنشاء الفيديو: {OUT}')
