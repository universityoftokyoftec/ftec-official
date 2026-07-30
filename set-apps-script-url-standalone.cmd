@echo off
setlocal
chcp 65001 >nul

powershell -NoProfile -ExecutionPolicy Bypass -Command "$p=$args[0];$r=[IO.File]::ReadAllText($p,[Text.Encoding]::UTF8);$m=[regex]::Match($r,'(?ms)^:__POWERSHELL__\r?\n(.*)$');if(-not $m.Success){throw 'Embedded PowerShell code was not found.'};&([scriptblock]::Create($m.Groups[1].Value)) -ScriptFile $p" "%~f0"

set "EXITCODE=%ERRORLEVEL%"
echo.
if not "%EXITCODE%"=="0" echo Setup failed. Error code: %EXITCODE%
pause
exit /b %EXITCODE%

:__POWERSHELL__
param([string]$ScriptFile)

$ErrorActionPreference = 'Stop'

function Find-ContactFile {
    param([string]$BaseDirectory)

    $direct = Join-Path $BaseDirectory 'contact\index.html'
    if (Test-Path -LiteralPath $direct -PathType Leaf) {
        return (Resolve-Path -LiteralPath $direct).Path
    }

    $matches = @(
        Get-ChildItem -LiteralPath $BaseDirectory -Filter 'index.html' -File -Recurse -ErrorAction SilentlyContinue |
        Where-Object {
            (Split-Path -Leaf (Split-Path -Parent $_.FullName)) -ieq 'contact'
        }
    )

    if ($matches.Count -eq 1) {
        return $matches[0].FullName
    }

    return $null
}

function Resolve-ContactFile {
    param([string]$ScriptDirectory)

    $found = Find-ContactFile -BaseDirectory $ScriptDirectory
    if ($found) {
        return $found
    }

    Write-Host ''
    Write-Host 'contact\index.html が自動で見つかりませんでした。' -ForegroundColor Yellow
    Write-Host 'GitHub Desktop の Repository → Show in Explorer で開く'
    Write-Host 'ftec-official フォルダのフルパスを貼り付けてください。'
    Write-Host ''

    $inputPath = (Read-Host 'ftec-official フォルダのパス').Trim().Trim('"')
    if (-not $inputPath) {
        throw 'フォルダのパスが入力されていません。'
    }

    if (Test-Path -LiteralPath $inputPath -PathType Leaf) {
        if ((Split-Path -Leaf $inputPath) -ieq 'index.html' -and
            (Split-Path -Leaf (Split-Path -Parent $inputPath)) -ieq 'contact') {
            return (Resolve-Path -LiteralPath $inputPath).Path
        }
        throw '指定したファイルは contact\index.html ではありません。'
    }

    if (-not (Test-Path -LiteralPath $inputPath -PathType Container)) {
        throw '指定したフォルダが見つかりません。'
    }

    $candidate = Join-Path $inputPath 'contact\index.html'
    if (-not (Test-Path -LiteralPath $candidate -PathType Leaf)) {
        throw '指定したフォルダ内に contact\index.html が見つかりません。'
    }

    return (Resolve-Path -LiteralPath $candidate).Path
}

function Normalize-WebAppUrl {
    $raw = (Read-Host 'Apps Script のウェブアプリURL（末尾 /exec）').Trim().Trim('"')
    if (-not $raw) {
        throw 'URLが入力されていません。'
    }

    $raw = $raw.TrimEnd('/')

    $uri = $null
    if (-not [Uri]::TryCreate($raw, [UriKind]::Absolute, [ref]$uri)) {
        throw 'URLとして読み取れませんでした。'
    }

    if ($uri.Scheme -ne 'https' -or $uri.Host -ne 'script.google.com') {
        throw 'https://script.google.com から始まるURLを使用してください。'
    }

    if ($uri.AbsolutePath -notmatch '^/macros/s/[A-Za-z0-9_-]+/exec$') {
        throw 'URLの形式が違います。/dev ではなく、末尾が /exec のウェブアプリURLを使用してください。'
    }

    if ($uri.Query -or $uri.Fragment) {
        throw 'URL末尾の ? 以降や # 以降を削除して、/exec で終わるURLを使用してください。'
    }

    return $raw
}

$scriptDirectory = Split-Path -Parent $ScriptFile
$contactFile = Resolve-ContactFile -ScriptDirectory $scriptDirectory
$url = Normalize-WebAppUrl

Write-Host ''
Write-Host ('対象ファイル: ' + $contactFile)
Write-Host ('設定URL   : ' + $url)
Write-Host ''

$utf8NoBom = New-Object System.Text.UTF8Encoding($false)
$html = [IO.File]::ReadAllText($contactFile, [Text.Encoding]::UTF8)
$original = $html

$backupDirectory = Join-Path $env:TEMP 'ftec-contact-form-backups'
if (-not (Test-Path -LiteralPath $backupDirectory -PathType Container)) {
    New-Item -ItemType Directory -Path $backupDirectory | Out-Null
}
$backupName = 'contact-index-' + (Get-Date -Format 'yyyyMMdd-HHmmss') + '.html'
$backup = Join-Path $backupDirectory $backupName
[IO.File]::WriteAllText($backup, $html, $utf8NoBom)

if ($html.Contains('__APPS_SCRIPT_WEB_APP_URL__')) {
    $html = $html.Replace('__APPS_SCRIPT_WEB_APP_URL__', $url)
}
else {
    $options = [Text.RegularExpressions.RegexOptions]::IgnoreCase
    $formPattern = '<form\b[^>]*\bid\s*=\s*(?:"ftec-contact-form"|''ftec-contact-form''|ftec-contact-form)[^>]*>'
    $formMatch = [regex]::Match($html, $formPattern, $options)

    if (-not $formMatch.Success) {
        throw 'id=ftec-contact-form のフォームが見つかりません。正しい contact\index.html か確認してください。'
    }

    $tag = $formMatch.Value
    $actionPattern = '\saction\s*=\s*(?:"[^"]*"|''[^'']*''|[^\s>]+)'

    if ([regex]::IsMatch($tag, $actionPattern, $options)) {
        $newTag = [regex]::Replace(
            $tag,
            $actionPattern,
            ' action="' + $url + '"',
            $options
        )
    }
    else {
        $newTag = $tag.Substring(0, $tag.Length - 1) + ' action="' + $url + '">'
    }

    $html = $html.Substring(0, $formMatch.Index) +
            $newTag +
            $html.Substring($formMatch.Index + $formMatch.Length)
}

if ($html -eq $original) {
    Write-Host 'URLはすでに同じ値に設定されています。ファイル変更はありません。' -ForegroundColor Yellow
}
else {
    [IO.File]::WriteAllText($contactFile, $html, $utf8NoBom)
}

$verifyPattern = '<form\b[^>]*\bid\s*=\s*(?:"ftec-contact-form"|''ftec-contact-form''|ftec-contact-form)[^>]*\baction\s*=\s*"' +
                 [regex]::Escape($url) +
                 '"[^>]*>'

$written = [IO.File]::ReadAllText($contactFile, [Text.Encoding]::UTF8)

if ($written.Contains('__APPS_SCRIPT_WEB_APP_URL__')) {
    throw 'URLのプレースホルダーが残っています。設定に失敗しました。'
}

if (-not [regex]::IsMatch(
    $written,
    $verifyPattern,
    [Text.RegularExpressions.RegexOptions]::IgnoreCase
)) {
    throw '書き込み後の検証に失敗しました。'
}

Write-Host ''
Write-Host '設定と検証が完了しました。' -ForegroundColor Green
Write-Host '次に Live Server で contact ページからテスト送信してください。'
Write-Host ('バックアップ: ' + $backup)
