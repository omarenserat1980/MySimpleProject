from pathlib import Path
from flask import Flask, request, jsonify, send_from_directory
from werkzeug.utils import secure_filename
import subprocess, sys, shutil

ROOT = Path(__file__).resolve().parent.parent
ASSETS = ROOT / 'assets'
OUTPUT = ROOT / 'output'
ASSETS.mkdir(exist_ok=True)
OUTPUT.mkdir(exist_ok=True)
app = Flask(__name__, static_folder='.')

@app.get('/')
def home():
    return send_from_directory(Path(__file__).parent, 'index.html')

@app.post('/api/generate')
def generate():
    image = request.files.get('image')
    product = request.form.get('product', 'مضخة مياه FORAS P100')
    price = request.form.get('price', '')
    contact = request.form.get('contact', '')
    if not image:
        return jsonify(error='اختر صورة المنتج أولاً'), 400
    filename = secure_filename(image.filename or 'product.jpg')
    target = ASSETS / 'foras_p100.jpg'
    image.save(target)
    # Generate using the existing lightweight MoviePy pipeline.
    result = subprocess.run([sys.executable, str(ROOT / 'generate_ad.py')], cwd=ROOT, capture_output=True, text=True)
    if result.returncode != 0:
        return jsonify(error=result.stderr or result.stdout), 500
    return jsonify(ok=True, video='/api/video', message='تم إنشاء الفيديو')

@app.get('/api/video')
def video():
    return send_from_directory(OUTPUT, 'foras_p100_ad.mp4', mimetype='video/mp4', as_attachment=False)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080, debug=False)
