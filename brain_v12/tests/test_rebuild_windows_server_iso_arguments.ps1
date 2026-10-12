$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$scriptPath = Join-Path $PSScriptRoot "..\tools\rebuild_windows_server_iso.ps1"
$scriptPath = [System.IO.Path]::GetFullPath($scriptPath)
$tokens = $null
$parseErrors = $null
$ast = [System.Management.Automation.Language.Parser]::ParseFile(
    $scriptPath, [ref]$tokens, [ref]$parseErrors
)
if ($parseErrors.Count -gt 0) { throw "Rebuild script contains PowerShell syntax errors." }

$functionAst = $ast.Find({
    param($node)
    $node -is [System.Management.Automation.Language.FunctionDefinitionAst] -and
        $node.Name -eq "ConvertTo-WindowsCommandLineArgument"
}, $true)
if (-not $functionAst) { throw "Command-line quoting helper was not found." }
. ([scriptblock]::Create($functionAst.Extent.Text))

$cases = @(
    @{ Name = "simple switch"; Input = "-m"; Expected = "-m" },
    @{ Name = "path with spaces"; Input = 'C:\Program Files\Windows ADK\oscdimg.exe'; Expected = '"C:\Program Files\Windows ADK\oscdimg.exe"' },
    @{ Name = "nested bootdata quotes"; Input = '-bootdata:2#p0,e,b"C:\media files\boot\etfsboot.com"#pEF,e,b"C:\media files\efi\efisys.bin"'; Expected = '"-bootdata:2#p0,e,b\"C:\media files\boot\etfsboot.com\"#pEF,e,b\"C:\media files\efi\efisys.bin\""' },
    @{ Name = "trailing backslash in quoted path"; Input = 'C:\Program Files\folder\'; Expected = '"C:\Program Files\folder\\"' }
)

foreach ($case in $cases) {
    $actual = ConvertTo-WindowsCommandLineArgument -Argument $case.Input
    if ($actual -cne $case.Expected) {
        throw ("{0}: expected [{1}], got [{2}]" -f $case.Name, $case.Expected, $actual)
    }
    Write-Output ("PASS: " + $case.Name)
}
Write-Output "WINDOWS_COMMAND_LINE_QUOTING_TESTS_PASSED"
