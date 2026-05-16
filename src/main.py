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

# ── 경로 설정 ──────────────────────────────────────────────────────────────────
if getattr(sys, 'frozen', False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

HTML_PATH   = os.path.join(BASE_DIR, 'WorkLog.html')
LOG_PATH    = os.path.join(BASE_DIR, 'worklog_winlog.json')
CONFIG_PATH = os.path.join(BASE_DIR, 'worklog_config.json')
PS_PATH     = os.path.join(BASE_DIR, 'WorkLog_GetWindowsLog.ps1')

# ── 설정 ──────────────────────────────────────────────────────────────────────
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

# ── 아이콘 이미지 생성 ─────────────────────────────────────────────────────────
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

# ── 토스트 알림 ────────────────────────────────────────────────────────────────
def toast(title, message):
    try:
        from win10toast import ToastNotifier
        ToastNotifier().show_toast(title, message, duration=4, threaded=True,
                                   icon_path=None)
    except Exception:
        pass  # 알림 실패해도 앱은 계속 동작

# ── Windows 로그 수집 ──────────────────────────────────────────────────────────
def collect_win_logs(days_back=None, show_toast=True):
    if days_back is None:
        days_back = config.get('collect_days_back', 30)

    if not os.path.exists(PS_PATH):
        if show_toast:
            toast("WorkLog", "PowerShell 스크립트를 찾을 수 없습니다.")
        return False

    try:
        cmd = [
            'powershell', '-NonInteractive', '-WindowStyle', 'Hidden',
            '-ExecutionPolicy', 'Bypass',
            '-File', PS_PATH,
            '-DaysBack', str(days_back),
            '-OutputPath', LOG_PATH
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)

        if os.path.exists(LOG_PATH):
            with open(LOG_PATH, 'r', encoding='utf-8') as f:
                data = json.load(f)
            count = data.get('totalCount', 0)
            if show_toast:
                toast("WorkLog", f"Windows 로그 수집 완료: {count}건")
            return True
        else:
            if show_toast:
                toast("WorkLog", "로그 수집 실패 — 관리자 권한으로 실행해보세요.")
            return False
    except subprocess.TimeoutExpired:
        if show_toast:
            toast("WorkLog", "로그 수집 시간 초과")
        return False
    except Exception as e:
        if show_toast:
            toast("WorkLog", f"수집 오류: {str(e)[:60]}")
        return False

# ── 백그라운드 스레드 ──────────────────────────────────────────────────────────
stop_event = threading.Event()

def auto_collect_loop():
    """주기적 자동 수집"""
    while True:
        interval = config.get('auto_collect_interval_min', 60) * 60
        if stop_event.wait(interval):
            break
        collect_win_logs(show_toast=False)

def reminder_loop():
    """출퇴근 시간 알림"""
    notified = {'in': False, 'out': False}
    last_date = None

    while not stop_event.is_set():
        if not config.get('notify_enabled', True):
            stop_event.wait(60)
            continue

        now  = datetime.datetime.now()
        date = now.date()
        if date != last_date:
            notified = {'in': False, 'out': False}
            last_date = date

        t = now.strftime('%H:%M')
        if not notified['in'] and t == config.get('notify_checkin_time', '09:00'):
            toast("WorkLog ⏰", "출근 시간! WorkLog에서 출근 버튼을 눌러주세요.")
            notified['in'] = True
        if not notified['out'] and t == config.get('notify_checkout_time', '18:00'):
            toast("WorkLog ⏰", "퇴근 시간! 오늘 하루도 수고하셨습니다.")
            notified['out'] = True

        stop_event.wait(30)

# ── 메뉴 액션 ─────────────────────────────────────────────────────────────────
def open_html(icon=None, item=None):
    if os.path.exists(HTML_PATH):
        webbrowser.open('file:///' + HTML_PATH.replace('\\', '/'))
    else:
        toast("WorkLog", f"WorkLog.html을 찾을 수 없습니다.\n{HTML_PATH}")

def open_folder(icon=None, item=None):
    subprocess.Popen(['explorer', BASE_DIR])

def collect_now(icon=None, item=None):
    toast("WorkLog", "Windows 로그 수집 시작...")
    threading.Thread(target=collect_win_logs, daemon=True).start()

def set_interval(mins):
    config['auto_collect_interval_min'] = mins
    save_config(config)
    toast("WorkLog", f"자동 수집 간격: {mins}분으로 변경됨")

def toggle_notify(icon=None, item=None):
    config['notify_enabled'] = not config.get('notify_enabled', True)
    save_config(config)
    state = "켜짐" if config['notify_enabled'] else "꺼짐"
    toast("WorkLog", f"출퇴근 알림: {state}")

def quit_app(icon, item):
    stop_event.set()
    icon.stop()

# ── 트레이 메뉴 빌드 ──────────────────────────────────────────────────────────
def build_menu():
    return pystray.Menu(
        pystray.MenuItem('📋  WorkLog 열기', open_html, default=True),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem('🖥  Windows 로그 지금 수집', collect_now),
        pystray.MenuItem('📁  폴더 열기', open_folder),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem('⚙  자동 수집 주기', pystray.Menu(
            pystray.MenuItem('30분마다',
                lambda i, it: set_interval(30),
                checked=lambda i: config.get('auto_collect_interval_min') == 30),
            pystray.MenuItem('1시간마다',
                lambda i, it: set_interval(60),
                checked=lambda i: config.get('auto_collect_interval_min') == 60),
            pystray.MenuItem('3시간마다',
                lambda i, it: set_interval(180),
                checked=lambda i: config.get('auto_collect_interval_min') == 180),
            pystray.MenuItem('수집 안 함',
                lambda i, it: set_interval(0),
                checked=lambda i: config.get('auto_collect_interval_min') == 0),
        )),
        pystray.MenuItem('🔔  출퇴근 알림',
            toggle_notify,
            checked=lambda i: config.get('notify_enabled', True)),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem('❌  종료', quit_app),
    )

# ── 시작프로그램 등록 ──────────────────────────────────────────────────────────
def register_startup():
    """Windows 시작프로그램에 자기 자신을 등록"""
    try:
        import winreg
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r'Software\Microsoft\Windows\CurrentVersion\Run',
            0, winreg.KEY_SET_VALUE
        )
        exe_path = sys.executable if getattr(sys, 'frozen', False) else __file__
        winreg.SetValueEx(key, 'WorkLog', 0, winreg.REG_SZ, f'"{exe_path}"')
        winreg.CloseKey(key)
    except Exception:
        pass

# ── 메인 ─────────────────────────────────────────────────────────────────────
def main():
    # 중복 실행 방지
    try:
        mutex = ctypes.windll.kernel32.CreateMutexW(None, False, "WorkLogTrayMutex_v1")
        if ctypes.windll.kernel32.GetLastError() == 183:
            open_html()
            return
    except Exception:
        pass

    # 시작프로그램 자동 등록
    register_startup()

    # 백그라운드 스레드 시작
    threading.Thread(target=auto_collect_loop, daemon=True).start()
    threading.Thread(target=reminder_loop,     daemon=True).start()

    # 시작 시 로그 1회 수집
    threading.Thread(
        target=lambda: collect_win_logs(show_toast=False), daemon=True
    ).start()

    # 시작 시 HTML 자동 열기
    if config.get('auto_open_on_start', True):
        open_html()

    # 트레이 실행
    icon = pystray.Icon(
        name='WorkLog',
        icon=make_icon(),
        title='WorkLog — 클릭해서 열기',
        menu=build_menu()
    )
    toast("WorkLog", "WorkLog가 트레이에서 실행 중입니다.")
    icon.run()

if __name__ == '__main__':
    main()
