import json
from pathlib import Path
from generate_ad import TITLE, PRICE, CONTACT

CONFIG = Path('config.json')

def load_config():
    if CONFIG.exists():
        return json.loads(CONFIG.read_text(encoding='utf-8'))
    return {
        'product_name': TITLE,
        'price': PRICE,
        'contact': CONTACT,
        'youtube': {'enabled': False},
        'facebook': {'enabled': False},
    }

def main():
    config = load_config()
    print('\n=== Foras P100 Mobile Ad ===')
    print('1 - إنشاء فيديو الإعلان')
    print('2 - عرض الإعدادات')
    print('3 - تجهيز النشر على YouTube')
    print('4 - تجهيز النشر على Facebook')
    print('5 - تجهيز النشر على الاثنين')
    choice = input('اختر رقم العملية: ').strip()

    if choice == '1':
        import subprocess, sys
        subprocess.run([sys.executable, 'generate_ad.py'], check=False)
    elif choice == '2':
        print(json.dumps(config, ensure_ascii=False, indent=2))
    elif choice in {'3', '4', '5'}:
        print('سيتم استخدام publisher.py بعد إعداد OAuth ومفاتيح المنصات.')
        print('لا تضع Access Token أو client secret داخل GitHub.')
    else:
        print('اختيار غير صحيح.')

if __name__ == '__main__':
    main()
