"""
WorkLog Tray - 시스템 트레이 앱
- 트레이 아이콘에서 WorkLog HTML 열기
- 백그라운드 Windows 이벤트 로그 자동 수집
- 출퇴근 알림 (아침/저녁)
"""

import sys
import os
import json
import threading
import webbrowser
import subprocess
import time
import datetime
import ctypes

try:
    import pystray
    from PIL import Image, ImageDraw, ImageFont
except ImportError:
    print("pystray / Pillow not installed.")
    sys.exit(1)

# ── 경로 설정
if getattr(sys, 'frozen', False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

HTML_PATH   = os.path.join(BASE_DIR, 'WorkLog.html')
LOG_PATH    = os.path.join(BASE_DIR, 'worklog_winlog.json')
CONFIG_PATH = os.path.join(BASE_DIR, 'worklog_config.json')
PS_PATH     = os.path.join(BASE_DIR, 'WorkLog_GetWindowsLog.ps1')

# ── 설정
DEFAULT_CONFIG = {
    "auto_collect_interval_min": 60,
    "collect_days_back": 30,
    "notify_checkin_time": "09:00",
    "notify_checkout_time": "18:00",
    "auto_open_on_start": True,
    "notify_enabled": True,
}

def load_config():
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
                return {**DEFAULT_CONFIG, **json.load(f)}
        except Exception:
            pass
    return dict(DEFAULT_CONFIG)

def save_config(cfg):
    with open(CONFIG_PATH, 'w', encoding='utf-8') as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)

config = load_config()

# ── 아이콘 이미지 생성
def make_icon(color=(74, 158, 255)):
    size = 64
    img  = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    draw.ellipse([2, 2, size-2, size-2], fill=color)
    try:
        font = ImageFont.truetype(
            os.path.join(os.environ.get('WINDIR','C:/Windows'), 'Fonts', 'arialbd.ttf'), 30
        )
    except Exception:
        font = ImageFont.load_default()
    draw.text((size//2, size//2), 'W', fill='white', font=font, anchor='mm')
    return img

# ── 토스트 알림
def toast(title,
