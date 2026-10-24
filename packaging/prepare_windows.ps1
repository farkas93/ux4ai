$ErrorActionPreference = 'Stop'
$url = 'https://github.com/jrsoftware/issrc/releases/download/is-7_1_0/innosetup-7.1.0-x64.exe'
$expected = '0362a383ed217d4c4239b5933866dd96d3eb2102737da92f80f6057a4b40df2f'
$installer = Join-Path $env:RUNNER_TEMP 'innosetup.exe'
$tools = Join-Path $env:RUNNER_TEMP 'InnoSetup'
Invoke-WebRequest $url -OutFile $installer
if ((Get-FileHash $installer -Algorithm SHA256).Hash.ToLower() -ne $expected) {
    throw 'Inno Setup installer checksum does not match the pinned tool.'
}
$process = Start-Process $installer -Wait -PassThru -ArgumentList `
    '/VERYSILENT', '/SUPPRESSMSGBOXES', '/NORESTART', '/CURRENTUSER', "/DIR=`"$tools`""
if ($process.ExitCode -ne 0) { throw 'Inno Setup installation failed.' }
$compiler = Join-Path $tools 'ISCC.exe'
if (-not (Test-Path $compiler)) { throw 'ISCC.exe was not installed.' }
"AIPM_ISCC=$compiler" >> $env:GITHUB_ENV
