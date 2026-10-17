param(
    [string]$FrameRoot = 'assets/sprites/enemies/frames_v6/ruined_knight'
)

$root = Join-Path $PWD $FrameRoot
$directions = @('down', 'left', 'right', 'up')
$replacementFrames = @('01.png', '02.png', '04.png')

function Copy-CompleteFrame([string]$Direction, [string]$Animation) {
    $animationDirectory = Join-Path $root "$Direction/$Animation"
    $source = Join-Path $animationDirectory '03.png'
    if (-not (Test-Path -LiteralPath $source)) {
        throw "Missing complete reference frame: $source"
    }
    foreach ($filename in $replacementFrames) {
        Copy-Item -LiteralPath $source -Destination (Join-Path $animationDirectory $filename) -Force
    }
}

# The atlas source crosses cell boundaries in these groups. Frame 03 is the
# complete, correctly centered pose; use it instead of retaining clipped limbs.
foreach ($direction in $directions) {
    Copy-CompleteFrame $direction 'walk'
}
foreach ($direction in @('down', 'left', 'right')) {
    Copy-CompleteFrame $direction 'attack'
}

Write-Output 'Repaired 21 clipped ruined-knight frames from complete references.'
