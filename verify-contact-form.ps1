$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$file = Join-Path $root "contact\index.html"
if (-not (Test-Path $file)) { throw "contact\\index.html がありません。" }
$html = [System.IO.File]::ReadAllText($file)
$checks = @(
  @{ Name = "Apps Script URL設定"; Pass = ($html -match 'action="https://script\.google\.com/macros/s/[A-Za-z0-9_-]+/exec"') },
  @{ Name = "メールアプリ方式の削除"; Pass = (-not $html.Contains('location.href = `mailto:')) },
  @{ Name = "お名前フィールド"; Pass = $html.Contains('id=name name=name') },
  @{ Name = "メールアドレスフィールド"; Pass = $html.Contains('id=email name=email') },
  @{ Name = "お問い合わせ内容フィールド"; Pass = $html.Contains('id=message name=message') },
  @{ Name = "同意チェック必須"; Pass = $html.Contains('name=privacyConsent value=agreed required') }
)
$failed = $false
foreach ($c in $checks) {
  if ($c.Pass) { Write-Host ("OK  " + $c.Name) -ForegroundColor Green }
  else { Write-Host ("NG  " + $c.Name) -ForegroundColor Red; $failed = $true }
}
if ($failed) { exit 1 }
Write-Host "すべての設定チェックに合格しました。" -ForegroundColor Green
