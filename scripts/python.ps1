# Use the project's local Python without changing the machine's PATH.
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$runtimeRoot = Join-Path $projectRoot '.python\runtime'
$pythonExecutable = Join-Path $runtimeRoot 'python.exe'
if (-not (Test-Path -LiteralPath $pythonExecutable)) {
    throw 'Local Python is missing. Place a complete Windows Python installation in .python/runtime (including Tcl/Tk).'
}

$temporaryDirectory = Join-Path $projectRoot '.python\temp'
$pipCache = Join-Path $projectRoot '.python\pip-cache'
$buildCache = Join-Path $projectRoot '.python\pyinstaller-cache'
New-Item -ItemType Directory -Force -Path $temporaryDirectory, $pipCache, $buildCache | Out-Null

# Extended Windows paths avoid Tcl's failing normalization of this Downloads path.
$environmentValues = @{
    TCL_LIBRARY = '\\?\' + (Join-Path $runtimeRoot 'tcl\tcl8.6')
    TK_LIBRARY = '\\?\' + (Join-Path $runtimeRoot 'tcl\tk8.6')
    TEMP = $temporaryDirectory
    TMP = $temporaryDirectory
    PIP_CACHE_DIR = $pipCache
    PYINSTALLER_CONFIG_DIR = $buildCache
    PYTHONNOUSERSITE = '1'
    PYTHONUTF8 = '1'
    PYTHONHOME = $null
    PYTHONPATH = $null
    PATH = "$runtimeRoot;$(Join-Path $runtimeRoot 'Scripts');$env:PATH"
}
$previousValues = @{}
$pythonExitCode = 1
try {
    foreach ($name in $environmentValues.Keys) {
        $previousValues[$name] = [Environment]::GetEnvironmentVariable($name, 'Process')
        [Environment]::SetEnvironmentVariable($name, $environmentValues[$name], 'Process')
    }
    if ($MyInvocation.ExpectingInput) {
        $input | & $pythonExecutable @args
    }
    else {
        & $pythonExecutable @args
    }
    $pythonExitCode = $LASTEXITCODE
}
finally {
    foreach ($name in $previousValues.Keys) {
        [Environment]::SetEnvironmentVariable($name, $previousValues[$name], 'Process')
    }
}
exit $pythonExitCode
