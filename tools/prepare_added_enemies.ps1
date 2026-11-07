param([string]$SourceRoot = (Join-Path $PSScriptRoot '../assets/sprites/enemies/source_added_v1'))
$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Drawing
$targetRoot = Join-Path $PSScriptRoot '../assets/sprites/enemies/frames_added_v1'
$directions = @('down', 'up', 'left', 'right')
$animations = @{idle = @(0,0,0,0); walk = @(1,0,2,0); attack = @(0,3,3,0)}
foreach ($id in @('ash_charger', 'ash_healer', 'shield_knight')) {
    $source = [System.Drawing.Bitmap]::new((Join-Path $SourceRoot "$id.png"))
    try {
        $bounds = @{}
        $maxWidth = 1
        $maxHeight = 1
        for ($row = 0; $row -lt 4; $row++) {
            for ($col = 0; $col -lt 4; $col++) {
                $x0 = [int][math]::Floor($source.Width*$col/4)
                $y0 = [int][math]::Floor($source.Height*$row/4)
                $x1 = [int][math]::Floor($source.Width*($col+1)/4)
                $y1 = [int][math]::Floor($source.Height*($row+1)/4)
                $left=$x1; $top=$y1; $right=-1; $bottom=-1
                for ($y=$y0; $y -lt $y1; $y++) {
                    for ($x=$x0; $x -lt $x1; $x++) {
                        if ($source.GetPixel($x,$y).A -gt 12) {
                            $left=[math]::Min($left,$x); $top=[math]::Min($top,$y)
                            $right=[math]::Max($right,$x); $bottom=[math]::Max($bottom,$y)
                        }
                    }
                }
                if ($right -lt 0) { throw "Empty source cell: $id $row $col" }
                $rect=[System.Drawing.Rectangle]::new($left,$top,$right-$left+1,$bottom-$top+1)
                $bounds["$row,$col"]=$rect
                $maxWidth=[math]::Max($maxWidth,$rect.Width)
                $maxHeight=[math]::Max($maxHeight,$rect.Height)
            }
        }
        $scale=[math]::Min(72.0/$maxWidth,64.0/$maxHeight)
        for ($row=0; $row -lt 4; $row++) {
            foreach ($animation in $animations.Keys) {
                $folder=Join-Path $targetRoot "$id/$($directions[$row])/$animation"
                New-Item -ItemType Directory -Path $folder -Force | Out-Null
                for ($frame=0; $frame -lt 4; $frame++) {
                    $rect=$bounds["$row,$($animations[$animation][$frame])"]
                    $w=[int][math]::Round($rect.Width*$scale)
                    $h=[int][math]::Round($rect.Height*$scale)
                    $image=[System.Drawing.Bitmap]::new(96,96,[System.Drawing.Imaging.PixelFormat]::Format32bppArgb)
                    $graphics=[System.Drawing.Graphics]::FromImage($image)
                    try {
                        $graphics.Clear([System.Drawing.Color]::Transparent)
                        $graphics.InterpolationMode=[System.Drawing.Drawing2D.InterpolationMode]::HighQualityBicubic
                        $dest=[System.Drawing.Rectangle]::new([int][math]::Floor((96-$w)/2),84-$h,$w,$h)
                        $graphics.DrawImage($source,$dest,$rect,[System.Drawing.GraphicsUnit]::Pixel)
                        $image.Save((Join-Path $folder ('{0:00}.png' -f ($frame+1))),[System.Drawing.Imaging.ImageFormat]::Png)
                    } finally { $graphics.Dispose(); $image.Dispose() }
                }
            }
        }
        Write-Output "Prepared $id : 48 frames, 96x96, contact y=84"
    } finally { $source.Dispose() }
}
