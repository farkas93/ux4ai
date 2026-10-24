param([Parameter(Mandatory=$true)][string]$Target)
$ErrorActionPreference = 'Stop'
if (-not $env:WINDOWS_CERT_FILE -or -not $env:WINDOWS_CERT_PASSWORD) {
    throw 'Windows publisher certificate is required for a production release.'
}
$signtool = Get-Command signtool.exe -ErrorAction SilentlyContinue
if (-not $signtool) {
    $signtool = Get-ChildItem "${env:ProgramFiles(x86)}\Windows Kits\10\bin\*\x64\signtool.exe" |
        Sort-Object FullName -Descending | Select-Object -First 1
}
if (-not $signtool) { throw 'signtool.exe was not found.' }
$toolpath = if ($signtool.Source) { $signtool.Source } else { $signtool.FullName }
& $toolpath sign /fd SHA256 /td SHA256 /tr 'http://timestamp.digicert.com' `
    /f $env:WINDOWS_CERT_FILE /p $env:WINDOWS_CERT_PASSWORD $Target
if ($LASTEXITCODE -ne 0) { throw 'Authenticode signing failed.' }
if ((Get-AuthenticodeSignature $Target).Status -ne 'Valid') { throw 'Authenticode verification failed.' }
