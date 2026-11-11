param(
    [Parameter(Mandatory = $true)]
    [ValidateSet('0', '0.8')]
    [string] $Rate
)

$projectRoot = Split-Path -Parent $PSScriptRoot
$valuesPath = Join-Path $projectRoot 'charts\trackhub\values-minikube.yaml'
$content = [System.IO.File]::ReadAllText($valuesPath)
$pattern = '(?m)^  failRate: (0|0\.8)(?=\r?$)'
$matches = [regex]::Matches($content, $pattern)
if ($matches.Count -ne 1) {
    throw "Expected exactly one failRate line; found $($matches.Count). No file was changed."
}

$current = $matches[0].Groups[1].Value
if ($current -eq $Rate) {
    Write-Output "failRate is already $Rate. No file was changed."
    exit 0
}

$replacement = '  failRate: ' + $Rate
$updated = [regex]::Replace($content, $pattern, $replacement)
$utf8 = New-Object System.Text.UTF8Encoding($false)
[System.IO.File]::WriteAllText($valuesPath, $updated, $utf8)
Write-Output "Changed failRate from $current to $Rate in $valuesPath"
