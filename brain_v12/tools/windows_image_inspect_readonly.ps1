# Read-only Windows image metadata inspection.
# Does not mount, service, execute, or modify the input image.
[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string] $ImagePath,

    [Parameter(Mandatory = $false)]
    [string] $OutputPath
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$resolved = Resolve-Path -LiteralPath $ImagePath -ErrorAction Stop
$file = Get-Item -LiteralPath $resolved.Path
if (-not $file.PSIsContainer -and $file.Length -le 0) {
    throw 'IMAGE_FILE_EMPTY'
}
if ($file.PSIsContainer) {
    throw 'IMAGE_PATH_MUST_BE_A_FILE'
}

$extension = [System.IO.Path]::GetExtension($file.Name).TrimStart('.').ToLowerInvariant()
$allowed = @('wim', 'vhd', 'vhdx', 'ffu')
if ($extension -notin $allowed) {
    throw ('UNSUPPORTED_READ_ONLY_INSPECTION_FORMAT:' + $extension)
}

$dism = Join-Path $env:SystemRoot 'System32\Dism.exe'
if (-not (Test-Path -LiteralPath $dism -PathType Leaf)) {
    throw 'DISM_NOT_FOUND'
}

$hash = (Get-FileHash -LiteralPath $file.FullName -Algorithm SHA256).Hash.ToLowerInvariant()
$beforeLength = $file.Length
$beforeWriteUtc = $file.LastWriteTimeUtc.ToString('o')

# DISM /Get-ImageInfo is a metadata query; it does not mount or service the image.
$dismOutput = & $dism /English /Get-ImageInfo ("/ImageFile:$($file.FullName)") 2>&1
$exitCode = $LASTEXITCODE
$dismText = ($dismOutput | ForEach-Object { [string]$_ }) -join "`n"

$after = Get-Item -LiteralPath $file.FullName
$afterHash = (Get-FileHash -LiteralPath $file.FullName -Algorithm SHA256).Hash.ToLowerInvariant()
$unchanged = ($hash -eq $afterHash) -and
    ($beforeLength -eq $after.Length) -and
    ($beforeWriteUtc -eq $after.LastWriteTimeUtc.ToString('o'))

$report = [ordered]@{
    schema_version = 1
    inspection_mode = 'READ_ONLY_METADATA_QUERY'
    evidence_type = 'HOST_OBSERVED_TOOL_OUTPUT'
    image_path = $file.FullName
    filename = $file.Name
    format = $extension
    size_bytes = $beforeLength
    sha256_before = $hash
    sha256_after = $afterHash
    file_metadata_unchanged = $unchanged
    dism_executable = $dism
    dism_exit_code = $exitCode
    dism_output = $dismText
    inspected_at_utc = [DateTime]::UtcNow.ToString('o')
    image_mounted = $false
    image_serviced = $false
    guest_boot_verified = $false
}

$json = $report | ConvertTo-Json -Depth 5
if ($OutputPath) {
    $outputFullPath = [System.IO.Path]::GetFullPath($OutputPath)
    if ($outputFullPath -eq $file.FullName) {
        throw 'OUTPUT_PATH_MUST_NOT_OVERWRITE_IMAGE'
    }
    $json | Set-Content -LiteralPath $outputFullPath -Encoding utf8
} else {
    $json
}

if (-not $unchanged) {
    throw 'IMAGE_FILE_CHANGED_DURING_INSPECTION'
}
if ($exitCode -ne 0) {
    throw ('DISM_IMAGE_INFO_FAILED:' + $exitCode)
}
