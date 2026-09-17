import subprocess
import sys
from pathlib import Path

root = Path(__file__).resolve().parent
print('Foras Ads - Mobile Server')
print('افتح المتصفح على الهاتف على: http://127.0.0.1:8080')
print('أوقف البرنامج بـ Ctrl+C')
subprocess.run([sys.executable, str(root / 'webapp' / 'server.py')], cwd=root)
