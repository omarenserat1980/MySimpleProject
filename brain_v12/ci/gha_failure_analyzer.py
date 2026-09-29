#!/usr/bin/env python3
from __future__ import annotations
import json,re,sys
RULES=[('syntax',r'SyntaxError|IndentationError|YAML.*error|mapping values'),('dependency',r'ModuleNotFoundError|No module named|command not found|FFMPEG_NOT_INSTALLED'),('timeout',r'timed out|Timeout|timeout-minutes'),('artifact',r'artifact.*not found|No files were found|if-no-files-found'),('permission',r'permission denied|Resource not accessible|403|401'),('network',r'Connection.*(reset|refused)|Could not resolve host|network'),('test',r'FAILED|AssertionError|pytest.*failed|npm ERR!'),('media',r'Invalid data found|Error initializing output stream|drawtext.*error|ffprobe.*error')]
def analyze(text):
    hits=[name for name,pat in RULES if re.search(pat,text,re.I)]
    return {'schema':'brain-gha-analysis/v1','categories':hits or ['unknown'],'actionable':bool(hits)}
print(json.dumps(analyze(sys.stdin.read()),ensure_ascii=False,indent=2))
