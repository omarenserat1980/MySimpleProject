# Compare an authorized Windows artifact with a SHA-256 obtained independently.
# This script does not download, execute, mount, or modify the artifact.
[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string] $ArtifactPath,

    [Parameter(Mandatory = $true)]
    [ValidatePattern('^[A-Fa-f0-9]{64}$')]
    [string] $ExpectedSha256,

    [Parameter(Mandatory = $true)]
    [ValidatePattern('^https://')]
    [string] $TrustedReferenceUrl,

    [Parameter(Mandatory = $false)]
    [string] $OutputPath
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$resolved = Resolve-Path -LiteralPath $ArtifactPath -ErrorAction Stop
$file = Get-Item -LiteralPath $resolved.Path
if ($file.PSIsContainer) { throw 'ARTIFACT_PATH_MUST_BE_A_FILE' }
if ($file.Length -le 0) { throw 'ARTIFACT_FILE_EMPTY' }

$outputFullPath = $null
if ($OutputPath) {
    $outputFullPath = [System.IO.Path]::GetFullPath($OutputPath)
    if ([string]::Equals($outputFullPath, $file.FullName, [System.StringComparison]::OrdinalIgnoreCase)) {
        throw 'OUTPUT_PATH_MUST_NOT_OVERWRITE_ARTIFACT'
    }
    if (Test-Path -LiteralPath $outputFullPath) { throw 'OUTPUT_PATH_ALREADY_EXISTS' }
    $outputDirectory = [System.IO.Path]::GetDirectoryName($outputFullPath)
    if (-not (Test-Path -LiteralPath $outputDirectory -PathType Container)) {
        throw 'OUTPUT_DIRECTORY_NOT_FOUND'
    }
}

$expected = $ExpectedSha256.ToLowerInvariant()
$before = Get-FileHash -LiteralPath $file.FullName -Algorithm SHA256
$afterItem = Get-Item -LiteralPath $file.FullName
$after = Get-FileHash -LiteralPath $file.FullName -Algorithm SHA256
$unchanged = ($before.Hash -eq $after.Hash) -and
    ($file.Length -eq $afterItem.Length) -and
    ($file.LastWriteTimeUtc.ToString('o') -eq $afterItem.LastWriteTimeUtc.ToString('o'))
$matches = ($after.Hash.ToLowerInvariant() -eq $expected) -and $unchanged

$report = [ordered]@{
    schema_version = 1
    evidence_type = 'HOST_OBSERVED_HASH_COMPARISON'
    status = if ($matches) { 'HASH_MATCH' } else { 'HASH_MISMATCH_OR_CHANGED' }
    artifact_path = $file.FullName
    filename = $file.Name
    size_bytes = $file.Length
    expected_sha256 = $expected
    observed_sha256_before = $before.Hash.ToLowerInvariant()
    observed_sha256_after = $after.Hash.ToLowerInvariant()
    file_metadata_unchanged = $unchanged
    trusted_reference_url = $TrustedReferenceUrl
    reference_independently_reviewed = $false
    publisher_authenticity_verified = $false
    real_guest_boot_verified = $false
    checked_at_utc = [DateTime]::UtcNow.ToString('o')
}
$json = $report | ConvertTo-Json -Depth 4
if ($OutputPath) { $json | Set-Content -LiteralPath $outputFullPath -Encoding utf8 } else { $json }
if (-not $matches) { throw 'ARTIFACT_HASH_VERIFICATION_FAILED' }
