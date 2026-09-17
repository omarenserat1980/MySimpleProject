from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
from moviepy.editor import ImageClip, concatenate_videoclips

W, H = 1080, 1920
FPS = 30
PRODUCT = Path('assets/foras_p100.jpg')
OUT = Path('output/foras_p100_ad.mp4')
OUT.parent.mkdir(exist_ok=True)

# عدّل هذه البيانات قبل التشغيل
TITLE = 'مضخة مياه FORAS P100'
PRICE = ''
CONTACT = ''


def font(size):
    candidates = [
        '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf',
        'C:/Windows/Fonts/arialbd.ttf',
    ]
    for p in candidates:
        if Path(p).exists():
            return ImageFont.truetype(p, size)
    return ImageFont.load_default()


def make_scene(text, seconds, product=False):
    img = Image.new('RGB', (W, H), 'white')
    d = ImageDraw.Draw(img)
    d.text((W//2, 180), TITLE, font=font(72), anchor='ma', fill='black')

    if product:
        if not PRODUCT.exists():
            raise FileNotFoundError('ضع صورة المنتج في assets/foras_p100.jpg')
        p = Image.open(PRODUCT).convert('RGB')
        p.thumbnail((900, 1050))
        x = (W - p.width)//2
        y = 430
        img.paste(p, (x, y))

    d.text((W//2, 1450), text, font=font(58), anchor='ma', align='center', fill='black', spacing=18)
    if PRICE:
        d.text((W//2, 1640), PRICE, font=font(65), anchor='ma', fill='black')
    if CONTACT:
        d.text((W//2, 1770), CONTACT, font=font(48), anchor='ma', fill='black')
    return img


scenes = [
    ('حل عملي لضخ المياه\nFORAS P100', 3, False),
    ('جودة واعتمادية\nللاستخدام اليومي', 4, True),
    ('اطلبها الآن\nوتواصل معنا', 3, True),
]

clips = []
for text, seconds, product in scenes:
    frame = make_scene(text, seconds, product)
    clips.append(ImageClip(frame).set_duration(seconds))

video = concatenate_videoclips(clips, method='compose')
video.write_videofile(str(OUT), fps=FPS, codec='libx264', audio=False)
print(f'تم إنشاء الفيديو: {OUT}')
