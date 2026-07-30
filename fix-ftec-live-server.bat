@echo off
setlocal
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$root = [System.IO.Path]::GetFullPath('%~dp0');" ^
  "$utf8 = New-Object System.Text.UTF8Encoding($false);" ^
  "$count = 0;" ^
  "Get-ChildItem -LiteralPath $root -Filter '*.html' -Recurse | ForEach-Object {" ^
  "  $p = $_.FullName;" ^
  "  $s = [System.IO.File]::ReadAllText($p);" ^
  "  if ($s -notmatch '(?is)</body>\s*</html>\s*$') {" ^
  "    $fixed = $s.TrimEnd() + [Environment]::NewLine + '</body>' + [Environment]::NewLine + '</html>' + [Environment]::NewLine;" ^
  "    [System.IO.File]::WriteAllText($p, $fixed, $utf8);" ^
  "    Write-Host ('Fixed: ' + $p);" ^
  "    $count++;" ^
  "  }" ^
  "};" ^
  "Write-Host ('Completed. Fixed ' + $count + ' HTML file(s).');"
echo.
echo Press any key to close this window.
pause >nul
endlocal
