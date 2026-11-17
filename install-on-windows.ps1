$ErrorActionPreference = 'Stop'

$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$Engine = Join-Path $Root 'evan-engine'
$Config = Join-Path $Engine 'local_tools.json'
$ExampleConfig = Join-Path $Engine 'local_tools.windows.example.json'
$McpServer = Join-Path $Engine 'evan_mcp.py'

$Python = Get-Command py.exe -ErrorAction SilentlyContinue
$PythonArgs = @('-3')
if (-not $Python) {
    $Python = Get-Command python.exe -ErrorAction SilentlyContinue
    $PythonArgs = @()
}
if (-not $Python) {
    throw 'Python 3 was not found. Install Python 3, then run this setup again.'
}

$Node = Get-Command node.exe -ErrorAction SilentlyContinue
if (-not $Node) {
    throw 'Node.js was not found. Install Node.js 20.9 or newer, then run this setup again.'
}
$NodeVersionText = & $Node.Source --version
if ($LASTEXITCODE -ne 0) {
    throw 'Node.js was found but could not report its version.'
}
try {
    $NodeVersion = [version]($NodeVersionText.TrimStart('v'))
} catch {
    throw "Could not read the installed Node.js version: $NodeVersionText"
}
if ($NodeVersion -lt [version]'20.9.0') {
    throw "Node.js 20.9 or newer is required; found $NodeVersionText."
}

$Npm = Get-Command npm.cmd -ErrorAction SilentlyContinue
if (-not $Npm) {
    $Npm = Get-Command npm -ErrorAction SilentlyContinue
}
if (-not $Npm) {
    throw 'npm was not found. Repair the Node.js installation and try again.'
}

if (-not (Test-Path -LiteralPath $Config -PathType Leaf)) {
    Copy-Item -LiteralPath $ExampleConfig -Destination $Config
    Write-Host 'Created evan-engine/local_tools.json from the Windows example.'
} else {
    Write-Host 'Kept the existing evan-engine/local_tools.json.'
}

Push-Location $Engine
try {
    Write-Host 'Installing the pinned local Sharp dependency...'
    & $Npm.Source install
    if ($LASTEXITCODE -ne 0) {
        throw "npm install failed with exit code $LASTEXITCODE."
    }
} finally {
    Pop-Location
}

$Codex = Get-Command codex.exe -ErrorAction SilentlyContinue
if (-not $Codex) {
    $Codex = Get-Command codex -ErrorAction SilentlyContinue
}
if ($Codex) {
    & $Codex.Source mcp get rovor-evan-v3 *> $null
    if ($LASTEXITCODE -eq 0) {
        Write-Host 'Kept the existing rovor-evan-v3 MCP registration.'
    } else {
        $McpCommand = @($Python.Source) + $PythonArgs + @($McpServer)
        $McpArgs = @('mcp', 'add', 'rovor-evan-v3', '--') + $McpCommand
        & $Codex.Source @McpArgs
        if ($LASTEXITCODE -ne 0) {
            throw "Could not register the rovor-evan-v3 MCP server (exit code $LASTEXITCODE)."
        }
        Write-Host 'Registered the separate rovor-evan-v3 MCP server.'
    }
} else {
    Write-Host 'Codex CLI was not found; MCP registration was skipped.'
}

Write-Host ''
Write-Host 'Next, edit evan-engine/local_tools.json and set the Whisper, model, and Rhubarb paths.'
Write-Host 'Install FFmpeg and make sure ffmpeg.exe is available on PATH.'
Write-Host 'Then run from evan-engine: py -3 .\launch_evan.py --check'
Write-Host 'You can render without MCP by opening Make Evan Video.cmd or running launch_evan.py.'

