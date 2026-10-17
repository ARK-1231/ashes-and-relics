param(
    [string]$SourceDirectory = 'assets/sprites/boss_projectiles_source',
    [string]$OutputDirectory = 'assets/sprites/boss_projectiles'
)

Add-Type -AssemblyName System.Drawing
$sourceRoot = Join-Path $PWD $SourceDirectory
$outputRoot = Join-Path $PWD $OutputDirectory
$sizes = @{
    fan = @(34, 18)
    ring = @(24, 24)
    lance = @(40, 14)
    spiral = @(24, 24)
    wave = @(36, 26)
}

foreach ($style in $sizes.Keys) {
    $sourcePath = Join-Path $sourceRoot "$style.png"
    $source = [System.Drawing.Bitmap]::FromFile($sourcePath)
    try {
        $left = $source.Width; $top = $source.Height; $right = -1; $bottom = -1
        for ($y = 0; $y -lt $source.Height; $y++) {
            for ($x = 0; $x -lt $source.Width; $x++) {
                if ($source.GetPixel($x, $y).A -gt 8) {
                    $left = [Math]::Min($left, $x); $top = [Math]::Min($top, $y)
                    $right = [Math]::Max($right, $x); $bottom = [Math]::Max($bottom, $y)
                }
            }
        }
        if ($right -lt $left) { throw "No visible projectile in $sourcePath" }

        $base = [System.Drawing.Bitmap]::new(48, 48, [System.Drawing.Imaging.PixelFormat]::Format32bppArgb)
        $graphics = [System.Drawing.Graphics]::FromImage($base)
        try {
            $graphics.InterpolationMode = [System.Drawing.Drawing2D.InterpolationMode]::HighQualityBicubic
            $width, $height = $sizes[$style]
            $destination = [System.Drawing.Rectangle]::new([int]((48-$width)/2), [int]((48-$height)/2), $width, $height)
            $crop = [System.Drawing.Rectangle]::new($left, $top, $right-$left+1, $bottom-$top+1)
            $graphics.DrawImage($source, $destination, $crop, [System.Drawing.GraphicsUnit]::Pixel)
        } finally { $graphics.Dispose() }

        $styleRoot = Join-Path $outputRoot $style
        [System.IO.Directory]::CreateDirectory($styleRoot) | Out-Null
        for ($index = 0; $index -lt 16; $index++) {
            $frame = [System.Drawing.Bitmap]::new(48, 48, [System.Drawing.Imaging.PixelFormat]::Format32bppArgb)
            $graphics = [System.Drawing.Graphics]::FromImage($frame)
            try {
                $graphics.InterpolationMode = [System.Drawing.Drawing2D.InterpolationMode]::HighQualityBicubic
                $graphics.TranslateTransform(24, 24)
                $graphics.RotateTransform($index * 22.5)
                $graphics.TranslateTransform(-24, -24)
                $graphics.DrawImageUnscaled($base, 0, 0)
            } finally { $graphics.Dispose() }
            try {
                $frame.Save((Join-Path $styleRoot ('{0:00}.png' -f $index)), [System.Drawing.Imaging.ImageFormat]::Png)
            } finally { $frame.Dispose() }
        }
        $base.Dispose()
        Write-Output "$style`: generated 16 directional frames"
    } finally { $source.Dispose() }
}
