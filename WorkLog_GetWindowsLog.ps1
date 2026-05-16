# WorkLog - Windows 사용 로그 수집 스크립트
# 실행 방법: PowerShell을 관리자 권한으로 열고 아래 명령 실행
# Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
# .\WorkLog_GetWindowsLog.ps1

param(
    [int]$DaysBack = 30,
    [string]$OutputPath = "$PSScriptRoot\worklog_winlog.json"
)

Write-Host "WorkLog - Windows 사용 로그 수집 중..." -ForegroundColor Cyan

$events = @()

# ── 1. 로그인 / 로그아웃 (Security 이벤트 로그) ──────────────────────────────
$eventIds = @(
    4624,  # 로그인 성공
    4634,  # 로그아웃
    4647,  # 사용자 로그오프
    4800,  # 화면 잠금
    4801,  # 화면 잠금 해제
    4802,  # 화면보호기 시작
    4803   # 화면보호기 종료
)

$logonTypes = @{
    2  = "로컬 로그인"
    3  = "네트워크 로그인"
    7  = "잠금 해제"
    10 = "원격 로그인"
    11 = "도메인 캐시 로그인"
}

$eventIdLabels = @{
    4624 = "로그인"
    4634 = "로그아웃"
    4647 = "로그아웃(사용자)"
    4800 = "화면 잠금"
    4801 = "잠금 해제"
    4802 = "화면보호기 시작"
    4803 = "화면보호기 종료"
}

$startTime = (Get-Date).AddDays(-$DaysBack)

try {
    $secEvents = Get-WinEvent -FilterHashtable @{
        LogName   = 'Security'
        Id        = $eventIds
        StartTime = $startTime
    } -ErrorAction SilentlyContinue

    foreach ($e in $secEvents) {
        $detail = $eventIdLabels[$e.Id]
        $user   = ""

        # XML에서 사용자명/LogonType 추출
        try {
            $xml = [xml]$e.ToXml()
            $ns  = New-Object System.Xml.XmlNamespaceManager($xml.NameTable)
            $ns.AddNamespace("ns","http://schemas.microsoft.com/win/2004/08/events/event")
            $userNode = $xml.SelectSingleNode("//ns:Data[@Name='TargetUserName']", $ns)
            if ($userNode) { $user = $userNode.InnerText }
            if ($e.Id -eq 4624) {
                $ltNode = $xml.SelectSingleNode("//ns:Data[@Name='LogonType']", $ns)
                if ($ltNode) {
                    $lt = [int]$ltNode.InnerText
                    if ($logonTypes.ContainsKey($lt)) { $detail += " (" + $logonTypes[$lt] + ")" }
                }
            }
        } catch {}

        # 시스템 계정 제외
        if ($user -match "SYSTEM|LOCAL SERVICE|NETWORK SERVICE|DWM-|UMFD-|\\$") { continue }

        $events += [PSCustomObject]@{
            ts     = $e.TimeCreated.ToString("yyyy-MM-ddTHH:mm:ss")
            type   = "WIN_" + $e.Id
            detail = $detail
            user   = $user
            source = "Windows Security Log"
        }
    }
    Write-Host "  Security 로그: $($secEvents.Count)개 수집" -ForegroundColor Green
} catch {
    Write-Host "  Security 로그 접근 실패 (관리자 권한 필요): $_" -ForegroundColor Yellow
}

# ── 2. 시스템 시작 / 종료 (System 이벤트 로그) ───────────────────────────────
$sysEventIds = @(
    1074,  # 종료/재시작 요청
    6005,  # 이벤트 로그 서비스 시작 = 부팅
    6006,  # 이벤트 로그 서비스 중지 = 종료
    6008,  # 비정상 종료
    41     # 커널 파워 - 비정상 재부팅
)

$sysEventLabels = @{
    1074 = "시스템 종료/재시작"
    6005 = "시스템 시작(부팅)"
    6006 = "시스템 종료"
    6008 = "비정상 종료"
    41   = "비정상 재부팅(전원 오류)"
}

try {
    $sysEvents = Get-WinEvent -FilterHashtable @{
        LogName   = 'System'
        Id        = $sysEventIds
        StartTime = $startTime
    } -ErrorAction SilentlyContinue

    foreach ($e in $sysEvents) {
        $events += [PSCustomObject]@{
            ts     = $e.TimeCreated.ToString("yyyy-MM-ddTHH:mm:ss")
            type   = "WIN_SYS_" + $e.Id
            detail = $sysEventLabels[$e.Id]
            user   = ""
            source = "Windows System Log"
        }
    }
    Write-Host "  System 로그: $($sysEvents.Count)개 수집" -ForegroundColor Green
} catch {
    Write-Host "  System 로그 접근 실패: $_" -ForegroundColor Yellow
}

# ── 3. 절전/복귀 (System - Kernel-Power) ─────────────────────────────────────
try {
    $powerEvents = Get-WinEvent -FilterHashtable @{
        LogName      = 'System'
        ProviderName = 'Microsoft-Windows-Kernel-Power'
        Id           = @(42, 107, 506, 507)
        StartTime    = $startTime
    } -ErrorAction SilentlyContinue

    $powerLabels = @{ 42="절전 모드 진입"; 107="절전 모드 복귀"; 506="절전 준비"; 507="절전 취소" }

    foreach ($e in $powerEvents) {
        $events += [PSCustomObject]@{
            ts     = $e.TimeCreated.ToString("yyyy-MM-ddTHH:mm:ss")
            type   = "WIN_PWR_" + $e.Id
            detail = if ($powerLabels[$e.Id]) { $powerLabels[$e.Id] } else { "전원 이벤트" }
            user   = ""
            source = "Windows Power Log"
        }
    }
    Write-Host "  Power 로그: $($powerEvents.Count)개 수집" -ForegroundColor Green
} catch {
    Write-Host "  Power 로그 접근 실패: $_" -ForegroundColor Yellow
}

# ── 4. 정렬 후 JSON 저장 ──────────────────────────────────────────────────────
$sorted = $events | Sort-Object ts -Descending

$output = @{
    generatedAt = (Get-Date).ToString("yyyy-MM-ddTHH:mm:ss")
    daysBack    = $DaysBack
    totalCount  = $sorted.Count
    logs        = $sorted
}

$json = $output | ConvertTo-Json -Depth 5 -Compress:$false
[System.IO.File]::WriteAllText($OutputPath, $json, [System.Text.Encoding]::UTF8)

Write-Host ""
Write-Host "완료! 총 $($sorted.Count)개 로그 수집" -ForegroundColor Cyan
Write-Host "저장 위치: $OutputPath" -ForegroundColor White
Write-Host ""
Write-Host "WorkLog 앱 > 관리자 모드 > [Windows 로그 불러오기] 버튼으로 가져오세요." -ForegroundColor Yellow
Read-Host "계속하려면 Enter"
