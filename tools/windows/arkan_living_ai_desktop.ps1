[CmdletBinding()]
param(
    [string]$BrainBaseUrl = $(if ($env:V12_BRAIN_URL) { $env:V12_BRAIN_URL } else { "http://127.0.0.1:8012" }),
    [switch]$StartHidden
)
$ErrorActionPreference = "Stop"
Add-Type -AssemblyName PresentationFramework, PresentationCore, WindowsBase, System.Xaml

function New-TextBlock([string]$Text, [double]$Size = 14, [string]$Color = "#D9F7FF", [bool]$Bold = $false) {
    $t = New-Object System.Windows.Controls.TextBlock
    $t.Text = $Text; $t.FontSize = $Size
    $t.Foreground = [System.Windows.Media.BrushConverter]::new().ConvertFromString($Color)
    $t.Margin = "4"
    if ($Bold) { $t.FontWeight = "SemiBold" }
    return $t
}
function New-Button([string]$Text) {
    $b = New-Object System.Windows.Controls.Button
    $b.Content = $Text; $b.Margin = "5"; $b.Padding = "12,7"
    $b.Foreground = [System.Windows.Media.Brushes]::White
    $b.Background = [System.Windows.Media.BrushConverter]::new().ConvertFromString("#203B5B")
    $b.BorderBrush = [System.Windows.Media.BrushConverter]::new().ConvertFromString("#347D9A")
    $b.Cursor = [System.Windows.Input.Cursors]::Hand
    return $b
}
function Get-BrainSnapshot {
    $s = [ordered]@{ Reachable = $false; State = "OFFLINE"; Detail = "No successful response from Brain API"; CheckedAt = (Get-Date).ToString("HH:mm:ss") }
    try {
        $r = Invoke-RestMethod -Uri "$BrainBaseUrl/api/system/readiness" -Method Get -TimeoutSec 2
        $s.Reachable = $true
        if ($r.status) { $s.State = ([string]$r.status).ToUpperInvariant() } else { $s.State = "CONNECTED" }
        $s.Detail = "Readiness endpoint responded; individual checks are not inferred."
        if ($r.checks -and $r.checks -is [System.Management.Automation.PSCustomObject]) {
            $parts = @()
            foreach ($p in $r.checks.PSObject.Properties) {
                if ($p.Value -is [string]) { $parts += "$($p.Name): $($p.Value)" }
                elseif ($p.Value.status) { $parts += "$($p.Name): $($p.Value.status)" }
            }
            if ($parts.Count) { $s.Detail = $parts -join " | " }
        }
    } catch { $s.Detail = "API unavailable: $($_.Exception.Message)" }
    return [pscustomobject]$s
}

$window = New-Object System.Windows.Window
$window.Title = "Electronic Brain — Arkan AI Desktop"
$window.Width = 920; $window.Height = 590; $window.MinWidth = 760; $window.MinHeight = 480
$window.WindowStartupLocation = "CenterScreen"; $window.WindowStyle = "None"
$window.ResizeMode = "CanResizeWithGrip"; $window.AllowsTransparency = $true
$window.Background = [System.Windows.Media.Brushes]::Transparent; $window.Topmost = $true
$window.ShowInTaskbar = $true; $window.FontFamily = "Segoe UI"

$outer = New-Object System.Windows.Controls.Border
$outer.CornerRadius = "18"; $outer.BorderThickness = "1"; $outer.Padding = "18"
$outer.BorderBrush = [System.Windows.Media.BrushConverter]::new().ConvertFromString("#4D9BC2")
$outer.Background = [System.Windows.Media.BrushConverter]::new().ConvertFromString("#F2081422")
$window.Content = $outer
$root = New-Object System.Windows.Controls.DockPanel
$outer.Child = $root

$header = New-Object System.Windows.Controls.Grid
$header.Margin = "0,0,0,10"
[void]$header.ColumnDefinitions.Add((New-Object System.Windows.Controls.ColumnDefinition -Property @{ Width = "*" }))
[void]$header.ColumnDefinitions.Add((New-Object System.Windows.Controls.ColumnDefinition -Property @{ Width = "Auto" }))
[System.Windows.Controls.DockPanel]::SetDock($header, "Top"); [void]$root.Children.Add($header)
$titleStack = New-Object System.Windows.Controls.StackPanel
[void]$titleStack.Children.Add((New-TextBlock "ELECTRONIC BRAIN" 23 "#7DEBFF" $true))
[void]$titleStack.Children.Add((New-TextBlock "ARKAN // LIVING AI DESKTOP" 11 "#7EADC0"))
[System.Windows.Controls.Grid]::SetColumn($titleStack, 0); [void]$header.Children.Add($titleStack)
$headerButtons = New-Object System.Windows.Controls.StackPanel; $headerButtons.Orientation = "Horizontal"
$minButton = New-Button "—"; $closeButton = New-Button "×"; $minButton.Width = 42; $closeButton.Width = 42
$minButton.Add_Click({ $window.WindowState = "Minimized" }); $closeButton.Add_Click({ $window.Close() })
[void]$headerButtons.Children.Add($minButton); [void]$headerButtons.Children.Add($closeButton)
[System.Windows.Controls.Grid]::SetColumn($headerButtons, 1); [void]$header.Children.Add($headerButtons)

$body = New-Object System.Windows.Controls.Grid
[void]$body.ColumnDefinitions.Add((New-Object System.Windows.Controls.ColumnDefinition -Property @{ Width = "2*" }))
[void]$body.ColumnDefinitions.Add((New-Object System.Windows.Controls.ColumnDefinition -Property @{ Width = "3*" }))
[void]$body.RowDefinitions.Add((New-Object System.Windows.Controls.RowDefinition -Property @{ Height = "*" }))
[void]$body.RowDefinitions.Add((New-Object System.Windows.Controls.RowDefinition -Property @{ Height = "Auto" }))
[void]$root.Children.Add($body)

$left = New-Object System.Windows.Controls.StackPanel; $left.Margin = "4,8,12,8"
[System.Windows.Controls.Grid]::SetColumn($left, 0); [System.Windows.Controls.Grid]::SetRow($left, 0); [void]$body.Children.Add($left)
[void]$left.Children.Add((New-TextBlock "NEURAL CORE" 13 "#71DFFF" $true))
$core = New-Object System.Windows.Controls.TextBlock
$core.Text = "◉"; $core.FontFamily = "Segoe UI Symbol"; $core.FontSize = 108
$core.HorizontalAlignment = "Center"; $core.Foreground = [System.Windows.Media.BrushConverter]::new().ConvertFromString("#4DE4FF")
$core.Margin = "12,18,12,10"; [void]$left.Children.Add($core)
$brainState = New-TextBlock "CONNECTING…" 17 "#FFFFFF" $true; $brainState.HorizontalAlignment = "Center"; [void]$left.Children.Add($brainState)
$brainDetail = New-TextBlock "Checking local Brain API…" 11 "#9EC6D6"; $brainDetail.TextWrapping = "Wrap"; $brainDetail.MaxWidth = 330
[void]$left.Children.Add($brainDetail)
[void]$left.Children.Add((New-TextBlock "LOCAL CONTROL // USER-INITIATED ACTIONS ONLY" 9 "#638A9A"))

$right = New-Object System.Windows.Controls.StackPanel; $right.Margin = "12,8,4,8"
[System.Windows.Controls.Grid]::SetColumn($right, 1); [System.Windows.Controls.Grid]::SetRow($right, 0); [void]$body.Children.Add($right)
[void]$right.Children.Add((New-TextBlock "SYSTEM TELEMETRY" 13 "#71DFFF" $true))
$telemetry = New-Object System.Windows.Controls.Grid
foreach ($i in 0..1) { [void]$telemetry.ColumnDefinitions.Add((New-Object System.Windows.Controls.ColumnDefinition -Property @{ Width = "*" })) }
foreach ($i in 0..2) { [void]$telemetry.RowDefinitions.Add((New-Object System.Windows.Controls.RowDefinition -Property @{ Height = "Auto" })) }
[void]$right.Children.Add($telemetry)
$metrics = @{}; $names = @("CPU", "MEMORY", "OS", "BRAIN API", "DEVICE", "MODE")
for ($i = 0; $i -lt $names.Count; $i++) {
    $card = New-Object System.Windows.Controls.Border
    $card.Margin = "4"; $card.Padding = "10"; $card.CornerRadius = "8"; $card.BorderThickness = "1"
    $card.BorderBrush = [System.Windows.Media.BrushConverter]::new().ConvertFromString("#294E65")
    $card.Background = [System.Windows.Media.BrushConverter]::new().ConvertFromString("#99102030")
    $stack = New-Object System.Windows.Controls.StackPanel
    [void]$stack.Children.Add((New-TextBlock $names[$i] 10 "#7CA9BA" $true))
    $val = New-TextBlock "—" 16 "#E4FAFF" $true; [void]$stack.Children.Add($val); $card.Child = $stack
    [System.Windows.Controls.Grid]::SetColumn($card, ($i % 2)); [System.Windows.Controls.Grid]::SetRow($card, [math]::Floor($i / 2))
    [void]$telemetry.Children.Add($card); $metrics[$names[$i]] = $val
}
$eventsBox = New-Object System.Windows.Controls.Border
$eventsBox.Margin = "0,12,0,0"; $eventsBox.Padding = "10"; $eventsBox.CornerRadius = "8"; $eventsBox.BorderThickness = "1"
$eventsBox.BorderBrush = [System.Windows.Media.BrushConverter]::new().ConvertFromString("#294E65")
$eventsBox.Background = [System.Windows.Media.BrushConverter]::new().ConvertFromString("#B808111D")
[System.Windows.Controls.Grid]::SetColumnSpan($eventsBox, 2); [System.Windows.Controls.Grid]::SetRow($eventsBox, 1); [void]$body.Children.Add($eventsBox)
$eventsStack = New-Object System.Windows.Controls.StackPanel
[void]$eventsStack.Children.Add((New-TextBlock "EVENT STREAM" 11 "#71DFFF" $true))
$eventText = New-TextBlock "Desktop companion started. Brain status not yet verified." 11 "#A7D7E5"; $eventText.TextWrapping = "Wrap"
[void]$eventsStack.Children.Add($eventText); $eventsBox.Child = $eventsStack

$footer = New-Object System.Windows.Controls.StackPanel; $footer.Orientation = "Horizontal"; $footer.Margin = "0,12,0,0"
[System.Windows.Controls.DockPanel]::SetDock($footer, "Bottom"); [void]$root.Children.Add($footer)
$refreshButton = New-Button "REFRESH STATUS"; $openApiButton = New-Button "OPEN BRAIN API"; $ambientButton = New-Button "AMBIENT MODE"
[void]$footer.Children.Add($refreshButton); [void]$footer.Children.Add($openApiButton); [void]$footer.Children.Add($ambientButton)
$script:ambient = $false; $script:tick = 0
$refreshAction = {
    try {
        $os = Get-CimInstance Win32_OperatingSystem
        $computer = Get-CimInstance Win32_ComputerSystem
        $cpu = Get-CimInstance Win32_Processor | Measure-Object -Property LoadPercentage -Average
        $usedGb = [math]::Round(($computer.TotalPhysicalMemory - ($os.FreePhysicalMemory * 1KB)) / 1GB, 1)
        $totalGb = [math]::Round($computer.TotalPhysicalMemory / 1GB, 1)
        $metrics["CPU"].Text = "$([math]::Round($cpu.Average))%"
        $metrics["MEMORY"].Text = "$usedGb / $totalGb GB"
        $metrics["OS"].Text = [string]$os.Caption; $metrics["DEVICE"].Text = $env:COMPUTERNAME
        $metrics["MODE"].Text = $(if ($script:ambient) { "AMBIENT" } else { "ACTIVE" })
        $snap = Get-BrainSnapshot; $metrics["BRAIN API"].Text = $snap.State; $brainState.Text = $snap.State
        $brainDetail.Text = "$($snap.Detail)" + [Environment]::NewLine + "Checked $($snap.CheckedAt)"
        if ($snap.Reachable) {
            $core.Foreground = [System.Windows.Media.BrushConverter]::new().ConvertFromString("#4DE4FF")
            $eventText.Text = "[$($snap.CheckedAt)] Readiness endpoint responded. State=$($snap.State). Model activity is not inferred."
        } else {
            $core.Foreground = [System.Windows.Media.BrushConverter]::new().ConvertFromString("#FFB86B")
            $eventText.Text = "[$($snap.CheckedAt)] Brain API not verified: $($snap.Detail)"
        }
    } catch { $eventText.Text = "[$((Get-Date).ToString('HH:mm:ss'))] Telemetry error: $($_.Exception.Message)" }
}
$refreshButton.Add_Click($refreshAction)
$openApiButton.Add_Click({ try { Start-Process "$BrainBaseUrl/api/system/readiness" } catch { [System.Windows.MessageBox]::Show($_.Exception.Message, "Electronic Brain") | Out-Null } })
$ambientButton.Add_Click({
    $script:ambient = -not $script:ambient
    if ($script:ambient) { $window.Opacity = 0.88; $core.FontSize = 84; $ambientButton.Content = "AI ACTIVE MODE" }
    else { $window.Opacity = 1.0; $core.FontSize = 108; $ambientButton.Content = "AMBIENT MODE" }
    & $refreshAction
})
$window.Add_MouseLeftButtonDown({ if ($_.ButtonState -eq [System.Windows.Input.MouseButtonState]::Pressed) { try { $window.DragMove() } catch {} } })
$timer = New-Object System.Windows.Threading.DispatcherTimer; $timer.Interval = [TimeSpan]::FromSeconds(5)
$timer.Add_Tick({
    $script:tick++
    if (-not $script:ambient) { $core.Opacity = 0.78 + (0.22 * [math]::Abs([math]::Sin($script:tick / 3))) } else { $core.Opacity = 0.82 }
    & $refreshAction
})
$window.Add_Closed({ $timer.Stop() })
if ($StartHidden) { $window.WindowState = "Minimized" }
$timer.Start(); & $refreshAction
[void]$window.ShowDialog()
