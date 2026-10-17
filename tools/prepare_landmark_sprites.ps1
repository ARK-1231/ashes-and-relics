param(
    [string]$SourceDirectory = 'assets/sprites/landmarks/source',
    [string]$OutputDirectory = 'assets/sprites/landmarks'
)

Add-Type -AssemblyName System.Drawing
$outputRoot = Join-Path $PWD $OutputDirectory
[System.IO.Directory]::CreateDirectory($outputRoot) | Out-Null
foreach ($name in @('shrine', 'stairs', 'exit')) {
    $sourcePath = Join-Path (Join-Path $PWD $SourceDirectory) "$name.png"
    $source = [System.Drawing.Bitmap]::FromFile($sourcePath)
    try {
        $left = $source.Width
        $top = $source.Height
        $right = -1
        $bottom = -1
        $transparent = 0
        for ($y = 0; $y -lt $source.Height; $y++) {
            for ($x = 0; $x -lt $source.Width; $x++) {
                $alpha = $source.GetPixel($x, $y).A
                if ($alpha -eq 0) { $transparent++ }
                if ($alpha -gt 0) {
                    $left = [Math]::Min($left, $x)
                    $top = [Math]::Min($top, $y)
                    $right = [Math]::Max($right, $x)
                    $bottom = [Math]::Max($bottom, $y)
                }
            }
        }
        if ($right -lt $left -or $transparent -eq 0) {
            throw "Missing visible object or genuine transparency: $name"
        }
        $cropWidth = $right - $left + 1
        $cropHeight = $bottom - $top + 1
        $scale = [Math]::Min(112.0 / $cropWidth, 112.0 / $cropHeight)
        $width = [Math]::Max(1, [int][Math]::Round($cropWidth * $scale))
        $height = [Math]::Max(1, [int][Math]::Round($cropHeight * $scale))
        $frame = [System.Drawing.Bitmap]::new(128, 128, [System.Drawing.Imaging.PixelFormat]::Format32bppArgb)
        try {
            $graphics = [System.Drawing.Graphics]::FromImage($frame)
            try {
                $graphics.Clear([System.Drawing.Color]::Transparent)
                $graphics.InterpolationMode = [System.Drawing.Drawing2D.InterpolationMode]::HighQualityBicubic
                $graphics.PixelOffsetMode = [System.Drawing.Drawing2D.PixelOffsetMode]::HighQuality
                $destination = [System.Drawing.Rectangle]::new([int]((128 - $width) / 2), 120 - $height, $width, $height)
                $crop = [System.Drawing.Rectangle]::new($left, $top, $cropWidth, $cropHeight)
                $graphics.DrawImage($source, $destination, $crop, [System.Drawing.GraphicsUnit]::Pixel)
            } finally { $graphics.Dispose() }
            $frame.Save((Join-Path $outputRoot "$name.png"), [System.Drawing.Imaging.ImageFormat]::Png)
        } finally { $frame.Dispose() }
        Write-Output "$name : 128x128 RGBA, source transparent pixels=$transparent"
    } finally { $source.Dispose() }
}
