param([string]$Source = 'assets/sprites/allies/source_v2.png')
Add-Type -AssemblyName System.Drawing
$sheet = [System.Drawing.Bitmap]::new((Join-Path $PWD $Source))
$names = @('mira', 'leon', 'noa')
$keys = @('idle_down','walk_down','walk_down','idle_up','walk_up','walk_up','idle_left','walk_left','walk_left','attack','attack','heal')
$indices = @(0,0,1,0,0,1,0,0,1,0,1,0)
try {
    for ($actor = 0; $actor -lt 3; $actor++) {
        $cells = @()
        $bounds = @()
        $maxWidth = 1
        $maxHeight = 1
        for ($i = 0; $i -lt 12; $i++) {
            $col = $i % 6
            $row = $actor * 2 + [int][Math]::Floor($i / 6)
            $left = [int][Math]::Floor($col * $sheet.Width / 6)
            $top = [int][Math]::Floor($row * $sheet.Height / 6)
            $width = [int][Math]::Floor(($col + 1) * $sheet.Width / 6) - $left
            $height = [int][Math]::Floor(($row + 1) * $sheet.Height / 6) - $top
            $cell = $sheet.Clone([System.Drawing.Rectangle]::new($left,$top,$width,$height), [System.Drawing.Imaging.PixelFormat]::Format32bppArgb)

            # Some poses in the preceding atlas row extend a few pixels beyond
            # their cell. Remove that overflow before measuring and scaling the
            # current actor; the intended artwork has clear padding at the top.
            $cleanup = [System.Drawing.Graphics]::FromImage($cell)
            $cleanup.CompositingMode = [System.Drawing.Drawing2D.CompositingMode]::SourceCopy
            $cleanup.FillRectangle([System.Drawing.Brushes]::Transparent, 0, 0, $width, [Math]::Min(24, $height))
            $cleanup.Dispose()

            $x0 = $width; $y0 = $height; $x1 = 0; $y1 = 0
            for ($y = 0; $y -lt $height; $y++) {
                for ($x = 0; $x -lt $width; $x++) {
                    if ($cell.GetPixel($x,$y).A -gt 16) {
                        $x0 = [Math]::Min($x0,$x); $y0 = [Math]::Min($y0,$y)
                        $x1 = [Math]::Max($x1,$x); $y1 = [Math]::Max($y1,$y)
                    }
                }
            }
            if ($x0 -gt $x1) { throw "Empty cell $actor/$i" }
            $bound = [System.Drawing.Rectangle]::new($x0,$y0,$x1-$x0+1,$y1-$y0+1)
            $cells += $cell; $bounds += $bound
            $maxWidth = [Math]::Max($maxWidth,$bound.Width)
            $maxHeight = [Math]::Max($maxHeight,$bound.Height)
        }
        $scale = [Math]::Min(84.0/$maxWidth,84.0/$maxHeight)
        for ($i = 0; $i -lt 12; $i++) {
            $frame = [System.Drawing.Bitmap]::new(96,96)
            $graphics = [System.Drawing.Graphics]::FromImage($frame)
            $graphics.InterpolationMode = [System.Drawing.Drawing2D.InterpolationMode]::NearestNeighbor
            $w = [int][Math]::Round($bounds[$i].Width*$scale)
            $h = [int][Math]::Round($bounds[$i].Height*$scale)
            $graphics.DrawImage($cells[$i],[System.Drawing.Rectangle]::new([int]((96-$w)/2),92-$h,$w,$h),$bounds[$i],[System.Drawing.GraphicsUnit]::Pixel)
            $graphics.Dispose()
            $dir = Join-Path $PWD "assets/sprites/allies/frames_v2/$($names[$actor])/$($keys[$i])"
            [System.IO.Directory]::CreateDirectory($dir) | Out-Null
            $frame.Save((Join-Path $dir ('{0:00}.png' -f $indices[$i])),[System.Drawing.Imaging.ImageFormat]::Png)
            if ($keys[$i].EndsWith('_left')) {
                $frame.RotateFlip([System.Drawing.RotateFlipType]::RotateNoneFlipX)
                $dir = $dir.Replace('_left','_right')
                [System.IO.Directory]::CreateDirectory($dir) | Out-Null
                $frame.Save((Join-Path $dir ('{0:00}.png' -f $indices[$i])),[System.Drawing.Imaging.ImageFormat]::Png)
            }
            $frame.Dispose(); $cells[$i].Dispose()
        }
    }
} finally { $sheet.Dispose() }
Write-Output 'Saved 45 transparent companion animation frames.'
