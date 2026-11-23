[CmdletBinding()]
param(
    [string]$Server = 'henk@10.50.50.1',
    [string]$RemoteDirectory = '/home/henk/container-backups',
    [string]$Destination = 'C:\productie\backups\container-runtime'
)

$ErrorActionPreference = 'Stop'

New-Item -ItemType Directory -Path $Destination -Force | Out-Null

$remoteArchive = (& ssh -o BatchMode=yes -o ConnectTimeout=12 $Server `
    "ls -1t '$RemoteDirectory'/container-state-*-utc.tar.gz 2>/dev/null | head -1").Trim()
if (-not $remoteArchive) {
    throw "No container-state archive found in $RemoteDirectory"
}

$remoteChecksum = "$remoteArchive.sha256"
$archiveName = Split-Path -Leaf $remoteArchive
$checksumName = Split-Path -Leaf $remoteChecksum
$localArchive = Join-Path $Destination $archiveName
$localChecksum = Join-Path $Destination $checksumName

& scp -q -o BatchMode=yes -o ConnectTimeout=12 `
    "${Server}:$remoteArchive" $localArchive
if ($LASTEXITCODE -ne 0) {
    throw 'Archive transfer failed.'
}

& scp -q -o BatchMode=yes -o ConnectTimeout=12 `
    "${Server}:$remoteChecksum" $localChecksum
if ($LASTEXITCODE -ne 0) {
    throw 'Checksum transfer failed.'
}

$expected = ((Get-Content -Raw -LiteralPath $localChecksum).Trim() -split '\s+')[0]
$actual = (Get-FileHash -Algorithm SHA256 -LiteralPath $localArchive).Hash.ToLowerInvariant()
if ($actual -ne $expected.ToLowerInvariant()) {
    throw "Checksum mismatch for $archiveName"
}

Write-Output "Verified off-host backup: $localArchive"
Write-Warning 'This archive contains sensitive WireGuard configuration and application data. Never add it to Git.'
