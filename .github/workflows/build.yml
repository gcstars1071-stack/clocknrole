name: Build WorkLog.exe

on:
  push:
    branches: [ main ]
    tags:     [ 'v*' ]
  pull_request:
    branches: [ main ]
  workflow_dispatch:

jobs:
  build:
    runs-on: windows-latest

    steps:
      - name: Checkout repository
        uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements.txt

      - name: Build exe with PyInstaller
        run: |
          pyinstaller WorkLog.spec --clean --noconfirm

      - name: Package release files
        run: |
          New-Item -ItemType Directory -Force -Path release
          Copy-Item dist\WorkLog.exe release\
          Copy-Item WorkLog.html release\
          Copy-Item WorkLog_GetWindowsLog.ps1 release\
          '{}' | Out-File release\worklog_config.json -Encoding utf8
          Compress-Archive -Path release\* -DestinationPath WorkLog_release.zip

      - name: Upload build artifact
        uses: actions/upload-artifact@v4
        with:
          name: WorkLog-Windows
          path: WorkLog_release.zip
          retention-days: 30

      - name: Create GitHub Release
        if: startsWith(github.ref, 'refs/tags/v')
        uses: softprops/action-gh-release@v2
        with:
          files: WorkLog_release.zip
          name: WorkLog ${{ github.ref_name }}
          body: |
            ## WorkLog ${{ github.ref_name }}

            ### 설치 방법
            1. `WorkLog_release.zip` 다운로드 후 압축 해제
            2. 모든 파일을 **같은 폴더**에 위치시키기
            3. `WorkLog.exe` 실행
          draft: false
          prerelease: false
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
