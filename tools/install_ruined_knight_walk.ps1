param(
    [string]$Sheet = 'assets/sprites/enemies/source_v2/ruined_knight_walk_sheet.png',
    [string]$FrameRoot = 'assets/sprites/enemies/frames_v6/ruined_knight'
)

Add-Type -AssemblyName System.Drawing

$sheetPath = Join-Path $PWD $Sheet
$frameRootPath = Join-Path $PWD $FrameRoot
$directions = @('down', 'up', 'left', 'right')
$source = [System.Drawing.Bitmap]::new($sheetPath)

try {
    $cellWidth = [math]::Floor($source.Width / 4)
    $cellHeight = [math]::Floor($source.Height / 4)
    for ($row = 0; $row -lt 4; $row++) {
        for ($column = 0; $column -lt 4; $column++) {
            $cellX = $column * $cellWidth
            $cellY = $row * $cellHeight
            $minX = $cellWidth
            $minY = $cellHeight
            $maxX = -1
            $maxY = -1
            for ($y = 0; $y -lt $cellHeight; $y++) {
                for ($x = 0; $x -lt $cellWidth; $x++) {
                    if ($source.GetPixel($cellX + $x, $cellY + $y).A -gt 8) {
                        $minX = [math]::Min($minX, $x)
                        $minY = [math]::Min($minY, $y)
                        $maxX = [math]::Max($maxX, $x)
                        $maxY = [math]::Max($maxY, $y)
                    }
                }
            }
            if ($maxX -lt 0) {
                throw "Empty sprite cell at row $row column $column"
            }

            $sourceWidth = $maxX - $minX + 1
            $sourceHeight = $maxY - $minY + 1
            $scale = [math]::Min(82.0 / $sourceWidth, 66.0 / $sourceHeight)
            $drawWidth = [math]::Max(1, [math]::Round($sourceWidth * $scale))
            $drawHeight = [math]::Max(1, [math]::Round($sourceHeight * $scale))
            $drawX = [math]::Round((96 - $drawWidth) / 2)
            $drawY = 85 - $drawHeight

            $frame = [System.Drawing.Bitmap]::new(
                96, 96, [System.Drawing.Imaging.PixelFormat]::Format32bppArgb
            )
            try {
                $graphics = [System.Drawing.Graphics]::FromImage($frame)
                try {
                    $graphics.Clear([System.Drawing.Color]::Transparent)
                    $graphics.InterpolationMode = [System.Drawing.Drawing2D.InterpolationMode]::NearestNeighbor
                    $graphics.PixelOffsetMode = [System.Drawing.Drawing2D.PixelOffsetMode]::Half
                    $destination = [System.Drawing.Rectangle]::new($drawX, $drawY, $drawWidth, $drawHeight)
                    $crop = [System.Drawing.Rectangle]::new(
                        $cellX + $minX, $cellY + $minY, $sourceWidth, $sourceHeight
                    )
                    $graphics.DrawImage($source, $destination, $crop, [System.Drawing.GraphicsUnit]::Pixel)
                }
                finally {
                    $graphics.Dispose()
                }
                $outputDirectory = Join-Path $frameRootPath "$($directions[$row])/walk"
                $outputPath = Join-Path $outputDirectory ('{0:D2}.png' -f ($column + 1))
                $frame.Save($outputPath, [System.Drawing.Imaging.ImageFormat]::Png)
            }
            finally {
                $frame.Dispose()
            }
        }
    }
}
finally {
    $source.Dispose()
}

Write-Output 'Installed 16 complete ruined-knight walking frames.'
