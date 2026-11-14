<# 
.SYNOPSIS
Windows DirectShow でマイク録音を行うスクリプト（M7用）

.DESCRIPTION
ThinkPad内蔵「Microphone Array (AMD Audio Device)」を明示指定して
16kHz mono WAV を書き出す。ffmpeg は PATH から解決。

.PARAMETER Seconds
録音秒数（既定: 20）。最大20秒制限あり。

.PARAMETER OutputPath
出力WAVパス（相対/絶対可）。未指定時は data/mic/mic_<YYYYMMDD_HHMMSS>.wav

.PARAMETER DeviceName
DirectShow デバイス名（既定: "Microphone Array (AMD Audio Device)"）

.EXAMPLE
.\scripts\record_mic.ps1 -Seconds 15 -OutputPath data\mic\test.wav
#>

param(
    [int]$Seconds = 20,
    [string]$OutputPath = "",
    [string]$DeviceName = "Microphone Array (AMD Audio Device)"
)

# 20秒上限チェック
if ($Seconds -gt 20) {
    Write-Error "最大20秒までです（指定: $Seconds 秒）"
    exit 1
}

# ffmpeg.exe を PATH から探す
$ffmpeg = Get-Command ffmpeg.exe -ErrorAction SilentlyContinue
if (-not $ffmpeg) {
    Write-Error "ffmpeg.exe が PATH に見つかりません（WinGet Gyan.FFmpeg 等でインストールしてください）"
    exit 1
}

# 出力パス決定
if (-not $OutputPath) {
    $ts = Get-Date -Format "yyyyMMdd_HHmmss"
    $OutputPath = "data/mic/mic_${ts}.wav"
}

# 絶対パスに正規化（作業ディレクトリ基準）
$absOutput = (Resolve-Path -Path (Split-Path $OutputPath -Parent) -ErrorAction SilentlyContinue).Path + "\" + (Split-Path $OutputPath -Leaf)
if (-not (Test-Path (Split-Path $OutputPath -Parent))) {
    $absOutput = (Get-Location).Path + "\" + $OutputPath
}

Write-Host "=== M7 Mic Record (Windows DirectShow) ==="
Write-Host "Device:  $DeviceName"
Write-Host "Seconds: $Seconds"
Write-Host "Output:  $absOutput"
Write-Host "ffmpeg:  $($ffmpeg.Source)"
Write-Host ""

# 録音実行
& $ffmpeg.Source -y -f dshow -i "audio=$DeviceName" -t $Seconds -ar 16000 -ac 1 -c:a pcm_s16le "$absOutput"

$exitCode = $LASTEXITCODE
if ($exitCode -eq 0 -and (Test-Path $absOutput)) {
    $size = (Get-Item $absOutput).Length
    Write-Host ""
    Write-Host "=== 録音完了 ==="
    Write-Host "File: $absOutput"
    Write-Host "Size: $size bytes"
    exit 0
} else {
    Write-Error "録音に失敗しました (exit code: $exitCode)"
    exit 1
}