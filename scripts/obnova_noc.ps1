# NOČNÍ OBNOVA KATALOGU (Plánovač úloh Windows, rozhodnutí vlastníka 2026-11-14)
# =============================================================================
# Běží na počítači vlastníka, dokud se obnova před spuštěním pro zákazníky
# nepřesune na server (GRANTIO.md §6.4). Pořadí:
#
#   1. .env do prostředí procesu (klíč k modelu, služební klíč databáze);
#      nic se nevypisuje ani neukládá jinam
#   2. refresh_run --tier all: třídy A, B, C (model) i P; časový rozpočet
#      a strop dokumentů na zdroj drží náklad i délku běhu
#   3. jen když obnova i brána prošly: publish_db (zapíše jen export, který
#      prošel bránou; pojistky proti propadu a hromadnému stažení)
#   4. commit a push dat pod identitou regrantio-refresh
#
# Log: data/logs/obnova-RRRR-MM-DD.log (UTF-8, mimo git).
# Ručně:  powershell -ExecutionPolicy Bypass -File scripts\obnova_noc.ps1

$ErrorActionPreference = 'Continue'
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root
$logDir = Join-Path $root 'data\logs'
New-Item -ItemType Directory -Force $logDir | Out-Null
$log = Join-Path $logDir ('obnova-' + (Get-Date -Format 'yyyy-MM-dd') + '.log')

function Write-Log([string]$line) {
	('[' + (Get-Date -Format 'HH:mm:ss') + '] ' + $line) | Out-File -FilePath $log -Append -Encoding utf8
}

foreach ($line in Get-Content (Join-Path $root '.env') -Encoding UTF8) {
	if ($line -match '^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*)$') {
		[Environment]::SetEnvironmentVariable($Matches[1], $Matches[2].Trim().Trim('"').Trim("'"), 'Process')
	}
}
$env:PYTHONIOENCODING = 'utf-8'

Write-Log 'obnova: start'
& python -X utf8 scripts/refresh_run.py --tier all --budget-min 150 --model-limit 15 2>&1 |
	Out-File -FilePath $log -Append -Encoding utf8
$refresh = $LASTEXITCODE
if ($refresh -ne 0) {
	Write-Log "obnova skončila kódem $refresh; do databáze se nezapisuje"
	exit $refresh
}

Write-Log 'zápis do databáze'
& python -X utf8 scripts/publish_db.py 2>&1 | Out-File -FilePath $log -Append -Encoding utf8
$publish = $LASTEXITCODE
if ($publish -ne 0) {
	Write-Log "zápis skončil kódem $publish (pojistka nebo chyba); data se necommitují"
	exit $publish
}

$data = @('data/opportunities.jsonl', 'docs/opportunities.json', 'data/sources.json', 'data/quality.json', 'docs/QUALITY.md')
& git add -- $data 2>&1 | Out-File -FilePath $log -Append -Encoding utf8
& git diff --cached --quiet
if ($LASTEXITCODE -ne 0) {
	& git -c user.name=regrantio-refresh -c user.email=noreply@grantio.cz commit -q -m ('Obnova katalogu ' + (Get-Date -Format 'yyyy-MM-dd')) 2>&1 |
		Out-File -FilePath $log -Append -Encoding utf8
	& git push -q origin main 2>&1 | Out-File -FilePath $log -Append -Encoding utf8
	Write-Log "data commitnutá a pushnutá (git $LASTEXITCODE)"
} else {
	Write-Log 'data beze změny'
}
Write-Log 'obnova: hotovo'
exit 0
