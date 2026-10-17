param(
    [string]$SourceDirectory = 'assets/sprites/relics_source',
    [string]$OutputDirectory = 'assets/sprites/relics'
)

Add-Type -AssemblyName System.Drawing
$sourceRoot = Join-Path $PWD $SourceDirectory
$outputRoot = Join-Path $PWD $OutputDirectory
[System.IO.Directory]::CreateDirectory($outputRoot) | Out-Null

foreach ($sourcePath in Get-ChildItem -LiteralPath $sourceRoot -Filter '*.png') {
    $source = [System.Drawing.Bitmap]::FromFile($sourcePath.FullName)
    try {
        $left = $source.Width
        $top = $source.Height
        $right = -1
        $bottom = -1
        for ($y = 0; $y -lt $source.Height; $y++) {
            for ($x = 0; $x -lt $source.Width; $x++) {
                if ($source.GetPixel($x, $y).A -gt 8) {
                    $left = [Math]::Min($left, $x)
                    $top = [Math]::Min($top, $y)
                    $right = [Math]::Max($right, $x)
                    $bottom = [Math]::Max($bottom, $y)
                }
            }
        }
        if ($right -lt $left) { throw "No visible relic in $($sourcePath.FullName)" }

        $sourceWidth = $right - $left + 1
        $sourceHeight = $bottom - $top + 1
        $scale = [Math]::Min(80.0 / $sourceWidth, 80.0 / $sourceHeight)
        $width = [Math]::Max(1, [int][Math]::Round($sourceWidth * $scale))
        $height = [Math]::Max(1, [int][Math]::Round($sourceHeight * $scale))

        $frame = [System.Drawing.Bitmap]::new(96, 96, [System.Drawing.Imaging.PixelFormat]::Format32bppArgb)
        $graphics = [System.Drawing.Graphics]::FromImage($frame)
        try {
            $graphics.InterpolationMode = [System.Drawing.Drawing2D.InterpolationMode]::HighQualityBicubic
            $graphics.PixelOffsetMode = [System.Drawing.Drawing2D.PixelOffsetMode]::HighQuality
            $destination = [System.Drawing.Rectangle]::new([int]((96 - $width) / 2), 88 - $height, $width, $height)
            $crop = [System.Drawing.Rectangle]::new($left, $top, $sourceWidth, $sourceHeight)
            $graphics.DrawImage($source, $destination, $crop, [System.Drawing.GraphicsUnit]::Pixel)
        } finally {
            $graphics.Dispose()
        }
        try {
            $outputPath = Join-Path $outputRoot $sourcePath.Name
            $frame.Save($outputPath, [System.Drawing.Imaging.ImageFormat]::Png)
            Write-Output "$($sourcePath.BaseName): 96x96 transparent relic sprite saved"
        } finally {
            $frame.Dispose()
        }
    } finally {
        $source.Dispose()
    }
}
