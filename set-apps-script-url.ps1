$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$contactFile = Join-Path $root "contact\index.html"

if (-not (Test-Path $contactFile)) {
  Write-Host "ERROR: contact\\index.html が見つかりません。" -ForegroundColor Red
  Write-Host "このファイル一式を ftec-official フォルダの直下に置いてください。"
  Read-Host "Enterキーで終了"
  exit 1
}

$url = Read-Host "Apps Script のウェブアプリURL（末尾が /exec）を貼り付けてください"
$url = $url.Trim()
if ($url -notmatch '^https://script\.google\.com/macros/s/[A-Za-z0-9_-]+/exec$') {
  Write-Host "ERROR: URLの形式が正しくありません。/dev ではなく /exec のURLを使用してください。" -ForegroundColor Red
  Read-Host "Enterキーで終了"
  exit 1
}

$utf8NoBom = New-Object System.Text.UTF8Encoding($false)
$html = [System.IO.File]::ReadAllText($contactFile, [System.Text.Encoding]::UTF8)
$backup = "$contactFile.before-gas.bak"
if (-not (Test-Path $backup)) {
  [System.IO.File]::WriteAllText($backup, $html, $utf8NoBom)
}

if ($html.Contains('__APPS_SCRIPT_WEB_APP_URL__')) {
  $html = $html.Replace('__APPS_SCRIPT_WEB_APP_URL__', $url)
} elseif ($html -match '(<form class=contact-form[^>]*action=")[^"]+("[^>]*>)') {
  $html = [regex]::Replace($html, '(<form class=contact-form[^>]*action=")[^"]+("[^>]*>)', ('$1' + $url + '$2'), 1)
} else {
  Write-Host "ERROR: フォームのURL設定箇所が見つかりません。" -ForegroundColor Red
  Read-Host "Enterキーで終了"
  exit 1
}

[System.IO.File]::WriteAllText($contactFile, $html, $utf8NoBom)
Write-Host ""
Write-Host "設定完了: contact\\index.html にウェブアプリURLを反映しました。" -ForegroundColor Green
Write-Host "次に Live Server でテスト送信し、F-tec Gmailの受信を確認してください。"
Read-Host "Enterキーで終了"
