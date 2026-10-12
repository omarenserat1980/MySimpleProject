# Rebuild a separate bootable ISO from official Windows installation media.
# Requires Windows PowerShell 5.1+ and oscdimg.exe from the Windows ADK.
# Does not service or remove components from WIM images.
[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)][string]$SourceIso,
    [Parameter(Mandatory = $true)][string]$OutputIso,
    [Parameter(Mandatory = $true)][string]$Workspace,
    [Parameter(Mandatory = $true)][string]$OscdimgPath
)
$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

function ConvertTo-WindowsCommandLineArgument {
    param([Parameter(Mandatory = $true)][AllowEmptyString()][string]$Argument)
    if ($Argument.Length -gt 0 -and $Argument -notmatch '[\s"]') { return $Argument }
    $builder = New-Object System.Text.StringBuilder
    [void]$builder.Append('"')
    $backslashes = 0
    foreach ($character in $Argument.ToCharArray()) {
        if ($character -eq '\') {
            $backslashes++
            continue
        }
        if ($character -eq '"') {
            if ($backslashes -gt 0) {
                [void]$builder.Append(('\' * (($backslashes * 2) + 1)))
            } else {
                [void]$builder.Append('\')
            }
            [void]$builder.Append('"')
            $backslashes = 0
            continue
        }
        if ($backslashes -gt 0) {
            [void]$builder.Append(('\' * $backslashes))
            $backslashes = 0
        }
        [void]$builder.Append($character)
    }
    if ($backslashes -gt 0) {
        [void]$builder.Append(('\' * ($backslashes * 2)))
    }
    [void]$builder.Append('"')
    return $builder.ToString()
}
$source = (Resolve-Path -LiteralPath $SourceIso).Path
$output = [System.IO.Path]::GetFullPath($OutputIso)
$work = [System.IO.Path]::GetFullPath($Workspace)
$oscdimg = (Resolve-Path -LiteralPath $OscdimgPath).Path
if (-not (Test-Path -LiteralPath $source -PathType Leaf)) { throw "Source ISO not found." }
if ([System.IO.Path]::GetExtension($source) -ine ".iso") { throw "Source must be an ISO file." }
if ([string]::Equals($source, $output, [StringComparison]::OrdinalIgnoreCase)) { throw "Output must not overwrite the source ISO." }
if (Test-Path -LiteralPath $output) { throw "Output already exists; choose a new output path." }
if (-not (Test-Path -LiteralPath $oscdimg -PathType Leaf)) { throw "oscdimg.exe not found." }
if (Test-Path -LiteralPath $work) { throw "Workspace already exists; choose a fresh workspace to preserve evidence." }
New-Item -ItemType Directory -Path (Split-Path -Parent $output) -Force | Out-Null
New-Item -ItemType Directory -Path $work | Out-Null
$manifestPath = Join-Path $work "iso-rebuild-manifest.json"
$sourceHash = (Get-FileHash -LiteralPath $source -Algorithm SHA256).Hash.ToLowerInvariant()
$mounted = $null
$outputMounted = $null
$log = Join-Path $work "oscdimg.log"
try {
    $mounted = Mount-DiskImage -ImagePath $source -StorageType ISO -Access ReadOnly -PassThru
    $volume = $mounted | Get-Volume | Where-Object DriveLetter | Select-Object -First 1
    if (-not $volume) { throw "Mounted ISO has no accessible drive letter." }
    $driveRoot = "$($volume.DriveLetter):\"
    $files = Join-Path $work "media"
    New-Item -ItemType Directory -Path $files | Out-Null
    & robocopy.exe $driveRoot $files /E /COPY:DAT /DCOPY:DAT /R:1 /W:1 /NFL /NDL /NP
    $copyExit = $LASTEXITCODE
    if ($copyExit -ge 8) { throw "Media copy failed with robocopy exit code $copyExit." }
    foreach ($relative in @("efi\boot\bootx64.efi", "sources\boot.wim")) {
        if (-not (Test-Path -LiteralPath (Join-Path $files $relative) -PathType Leaf)) {
            throw "Required file missing from source media: $relative"
        }
    }
    if (-not ((Test-Path (Join-Path $files "sources\install.wim")) -or (Test-Path (Join-Path $files "sources\install.esd")))) {
        throw "Neither sources\install.wim nor sources\install.esd exists."
    }
    $biosBoot = Join-Path $files "boot\etfsboot.com"
    $uefiBoot = Join-Path $files "efi\microsoft\boot\efisys.bin"
    if (-not (Test-Path -LiteralPath $biosBoot -PathType Leaf)) { throw "BIOS boot image missing; refusing to guess boot flags." }
    if (-not (Test-Path -LiteralPath $uefiBoot -PathType Leaf)) { throw "UEFI boot image missing; refusing to guess boot flags." }
    $bootData = '-bootdata:2#p0,e,b"' + $biosBoot + '"#pEF,e,b"' + $uefiBoot + '"'
    # Start-Process joins ArgumentList into one Windows command line. Quote each
    # argument using Windows CRT rules so spaces and the nested quotes required by
    # oscdimg's -bootdata value survive intact under Windows PowerShell 5.1.
    $arguments = @("-m", "-o", "-u2", "-udfver102", $bootData, $files, $output)
    $argumentLine = (($arguments | ForEach-Object {
        ConvertTo-WindowsCommandLineArgument -Argument ([string]$_)
    }) -join " ")
    $started = Get-Date
    $process = Start-Process -FilePath $oscdimg -ArgumentList $argumentLine -Wait -PassThru -NoNewWindow -RedirectStandardOutput $log -RedirectStandardError ($log + ".err")
    if ($process.ExitCode -ne 0) { throw "oscdimg failed with exit code $($process.ExitCode)." }
    if (-not (Test-Path -LiteralPath $output -PathType Leaf)) { throw "oscdimg returned success but output ISO is missing." }

    # Independently mount the newly generated image and inspect its contents.
    # This proves only that the output ISO is structurally readable, not that it boots.
    $outputMounted = Mount-DiskImage -ImagePath $output -StorageType ISO -Access ReadOnly -PassThru
    $outputVolume = $outputMounted | Get-Volume | Where-Object DriveLetter | Select-Object -First 1
    if (-not $outputVolume) { throw "Rebuilt ISO has no accessible drive letter." }
    $outputRoot = "$($outputVolume.DriveLetter):\"
    foreach ($relative in @("efi\\boot\\bootx64.efi", "sources\\boot.wim", "boot\\etfsboot.com", "efi\\microsoft\\boot\\efisys.bin")) {
        if (-not (Test-Path -LiteralPath (Join-Path $outputRoot $relative) -PathType Leaf)) {
            throw "Rebuilt ISO is missing required boot/setup file: $relative"
        }
    }
    if (-not ((Test-Path -LiteralPath (Join-Path $outputRoot "sources\\install.wim") -PathType Leaf) -or (Test-Path -LiteralPath (Join-Path $outputRoot "sources\\install.esd") -PathType Leaf))) {
        throw "Rebuilt ISO is missing sources\\install.wim and sources\\install.esd."
    }
    Dismount-DiskImage -ImagePath $output -ErrorAction Stop | Out-Null
    $outputMounted = $null

    $manifest = [ordered]@{
        schema = "brain.windows-server-iso-rebuild.v1"
        status = "REBUILT_STRUCTURE_VALIDATED_NOT_BOOT_TESTED"
        boot_status = "NOT_TESTED"
        source_name = [System.IO.Path]::GetFileName($source)
        source_sha256 = $sourceHash
        source_size_bytes = (Get-Item -LiteralPath $source).Length
        output_name = [System.IO.Path]::GetFileName($output)
        output_sha256 = (Get-FileHash -LiteralPath $output -Algorithm SHA256).Hash.ToLowerInvariant()
        output_size_bytes = (Get-Item -LiteralPath $output).Length
        oscdimg_path = $oscdimg
        oscdimg_file_version = (Get-Item -LiteralPath $oscdimg).VersionInfo.FileVersion
        elapsed_seconds = [math]::Round(((Get-Date) - $started).TotalSeconds, 2)
        log_file = [System.IO.Path]::GetFileName($log)
        modifications = @("Copied original media without WIM servicing or component removal", "Rebuilt ISO with explicit BIOS and UEFI boot entries")
        limitations = @("Rebuild success is not firmware boot evidence", "Windows Setup and OS first boot remain NOT_TESTED")
    }
    $manifest | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath $manifestPath -Encoding UTF8
    Write-Output ("ISO_REBUILT_NOT_BOOT_TESTED sha256=" + $manifest.output_sha256)
    Write-Output ("Manifest: " + $manifestPath)
}
finally {
    if ($outputMounted) { Dismount-DiskImage -ImagePath $output -ErrorAction SilentlyContinue | Out-Null }
    if ($mounted) { Dismount-DiskImage -ImagePath $source -ErrorAction SilentlyContinue | Out-Null }
}
