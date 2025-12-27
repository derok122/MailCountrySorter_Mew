<#
PowerShell helper: cria EXE usando PyInstaller dentro do venv, com suporte a ícone e assinatura.

Uso:
.\n+\build_exe.ps1 -IconPath .\app.ico -PfxPath .\cert.pfx -PfxPassword secret -TimestampUrl "http://timestamp.digicert.com"

Se nenhum `IconPath` for informado, o build continuará sem ícone.
Se `PfxPath` for informado, o script tentará assinar o EXE usando `signtool` (deve estar instalado no PATH).
#>

Param(
	[string]$IconPath = $null,
	[string]$PfxPath = $null,
	[string]$PfxPassword = $null,
	[string]$TimestampUrl = "http://timestamp.digicert.com"
)

$projRoot = Split-Path -Path $PSScriptRoot -Parent
Write-Host "Building EXE with PyInstaller..."
Set-Location $projRoot

$iconArg = $null
if ($IconPath) {
	if (-Not (Test-Path $IconPath)) {
		Write-Warning "Icon file not found: $IconPath. Continuing without icon."
	} else {
		$iconArg = "--icon `"$IconPath`""
		Write-Host "Using icon: $IconPath"
	}
}

$addData = "--add-data `"Tld.map;.\`" --add-data `"Setting.ini;.\`" --add-data `"Country.mmdb;.\`""

$pyCmd = ".\venv\Scripts\python -m PyInstaller --onefile --name EMailCountrySorter $addData $iconArg mail_country_sorter.py"
Write-Host "Executando: $pyCmd"
Invoke-Expression $pyCmd

$exePath = Join-Path $projRoot "dist\EMailCountrySorter.exe"
if (-Not (Test-Path $exePath)) {
	Write-Error "Build falhou: EXE não encontrado em $exePath"
	exit 1
}

Write-Host "Build concluído: $exePath"

if ($PfxPath) {
	if (-Not (Test-Path $PfxPath)) {
		Write-Warning "PFX não encontrado: $PfxPath. Pulando assinatura."
	} else {
		# procura signtool
		$signtool = (Get-Command signtool -ErrorAction SilentlyContinue).Source
		if (-Not $signtool) {
			Write-Warning "signtool não encontrado no PATH — não foi possível assinar o EXE. Instale Windows SDK ou disponibilize signtool.exe no PATH."
		} else {
			Write-Host "Assinando EXE com PFX: $PfxPath"
			$passArg = $null
			if ($PfxPassword) { $passArg = "-p `"$PfxPassword`"" }
			$tsArg = "-tr $TimestampUrl -td sha256"
			$signCmd = "& `"$signtool`" sign /f `"$PfxPath`" $passArg /fd SHA256 $tsArg `"$exePath`""
			Write-Host "Executando: $signCmd"
			try {
				Invoke-Expression $signCmd
				Write-Host "Assinatura concluída."
			} catch {
				Write-Warning "Assinatura falhou: $_"
			}
		}
	}
}

Write-Host "Fim. EXE disponível em: $exePath"
