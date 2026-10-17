param([string]$AssetDirectory = (Join-Path $PSScriptRoot '../assets/sprites/allies'))

Add-Type -AssemblyName System.Drawing
foreach ($name in @('mira', 'leon', 'noa')) {
    $sourcePath = Join-Path $AssetDirectory "source_${name}_v2.png"
    $outputPath = Join-Path $AssetDirectory "${name}_v2.png"
    $source = [System.Drawing.Bitmap]::new($sourcePath)
    $target = [System.Drawing.Bitmap]::new(96, 96)
    $graphics = [System.Drawing.Graphics]::FromImage($target)
    try {
        # Keep the generated alpha, fit the entire character, and align feet.
        $left = $source.Width
        $top = $source.Height
        $right = 0
        $bottom = 0
        for ($y = 0; $y -lt $source.Height; $y += 2) {
            for ($x = 0; $x -lt $source.Width; $x += 2) {
                if ($source.GetPixel($x, $y).A -gt 16) {
                    $left = [Math]::Min($left, $x)
                    $top = [Math]::Min($top, $y)
                    $right = [Math]::Max($right, $x + 1)
                    $bottom = [Math]::Max($bottom, $y + 1)
                }
            }
        }
        if ($left -ge $right) { throw "No visible character in $sourcePath" }
        $left = [Math]::Max(0, $left - 2)
        $top = [Math]::Max(0, $top - 2)
        $right = [Math]::Min($source.Width - 1, $right + 2)
        $bottom = [Math]::Min($source.Height - 1, $bottom + 2)
        $sourceWidth = $right - $left + 1
        $sourceHeight = $bottom - $top + 1
        $scale = [Math]::Min(80.0 / $sourceWidth, 80.0 / $sourceHeight)
        $width = [int][Math]::Round($sourceWidth * $scale)
        $height = [int][Math]::Round($sourceHeight * $scale)
        $destination = [System.Drawing.Rectangle]::new([int]((96 - $width) / 2), 84 - $height, $width, $height)
        $crop = [System.Drawing.Rectangle]::new($left, $top, $sourceWidth, $sourceHeight)
        $graphics.Clear([System.Drawing.Color]::Transparent)
        $graphics.InterpolationMode = [System.Drawing.Drawing2D.InterpolationMode]::HighQualityBicubic
        $graphics.PixelOffsetMode = [System.Drawing.Drawing2D.PixelOffsetMode]::HighQuality
        $graphics.DrawImage($source, $destination, $crop, [System.Drawing.GraphicsUnit]::Pixel)
        $target.Save($outputPath, [System.Drawing.Imaging.ImageFormat]::Png)
        Write-Output "$name`: 96x96 transparent sprite saved"
    } finally {
        $graphics.Dispose()
        $target.Dispose()
        $source.Dispose()
    }
}
