# WorkLog 🗂

개인 출퇴근 기록 · 업무 관리 · Windows 사용 로그 트래킹 앱

[![Build WorkLog.exe](https://github.com/YOUR_USERNAME/worklog/actions/workflows/build.yml/badge.svg)](https://github.com/YOUR_USERNAME/worklog/actions/workflows/build.yml)

---

## 다운로드

→ [Releases 페이지](https://github.com/YOUR_USERNAME/worklog/releases/latest)에서 `WorkLog_release.zip` 다운로드

---

## 파일 구성

```
WorkLog/
├── WorkLog.exe                   ← 트레이 앱 (더블클릭으로 실행)
├── WorkLog.html                  ← 출퇴근/업무 기록 앱
├── WorkLog_GetWindowsLog.ps1     ← Windows 이벤트 로그 수집 스크립트
└── worklog_config.json           ← 설정 파일 (자동 생성)
```

> **모든 파일은 같은 폴더에 있어야 합니다.**

---

## 사용 방법

### 1. WorkLog.exe 실행
- 시스템 **트레이 아이콘** 생성
- 브라우저에서 `WorkLog.html` 자동 열림
- **Windows 시작프로그램 자동 등록** (다음 부팅부터 자동 실행)
- 백그라운드에서 Windows 이벤트 로그 주기적 수집

### 2. 트레이 아이콘 우클릭 메뉴

| 메뉴 | 기능 |
|------|------|
| 📋 WorkLog 열기 | 브라우저에서 앱 열기 |
| 🖥 Windows 로그 지금 수집 | 즉시 로그 수집 후 JSON 저장 |
| 📁 폴더 열기 | 앱 폴더 열기 |
| ⚙ 자동 수집 주기 | 30분 / 1시간 / 3시간 / 사용 안 함 |
| 🔔 출퇴근 알림 | 켜기/끄기 |
| ❌ 종료 | 트레이 앱 종료 |

### 3. WorkLog 앱 내 Windows 로그 확인
관리자 모드 → **Windows 사용 로그** 섹션 → `JSON 불러오기`
→ `worklog_winlog.json` 선택

---

## Windows 로그 수집 항목

| 분류 | 이벤트 |
|------|--------|
| 로그인/아웃 | 로그인 성공, 로그아웃 (로컬/원격 구분) |
| 잠금 | 화면 잠금/해제, 화면보호기 |
| 전원 | 절전 진입/복귀 |
| 시스템 | 부팅, 정상/비정상 종료, 재시작 |

> Security 이벤트 로그 수집은 **관리자 권한**이 필요합니다.

---

## 빌드 방법 (개발자)

```bash
# 의존성 설치
pip install -r requirements.txt

# 로컬 테스트 실행
python src/main.py

# exe 빌드
pyinstaller WorkLog.spec --clean --noconfirm
# → dist/WorkLog.exe 생성
```

### GitHub Actions 자동 빌드

`main` 브랜치에 push하면 자동으로 빌드됩니다.
버전 태그 push 시 GitHub Release가 자동 생성됩니다:

```bash
git tag v1.0.0
git push origin v1.0.0
```

---

## 설정 파일 (worklog_config.json)

```json
{
  "auto_collect_interval_min": 60,
  "collect_days_back": 30,
  "notify_checkin_time": "09:00",
  "notify_checkout_time": "18:00",
  "auto_open_on_start": true,
  "notify_enabled": true
}
```

---

## 주의사항

- **Windows 전용** (트레이 앱 및 이벤트 로그 수집)
- SmartScreen 경고 시: **추가 정보 → 실행** 클릭
- 데이터는 `WorkLog.html`과 같은 폴더의 `localStorage`(브라우저)에 저장됩니다
- 브라우저를 바꾸면 기존 데이터가 보이지 않으니 **같은 브라우저**를 사용하세요
