using System;
using System.Collections.Generic;
using System.Drawing;
using System.Drawing.Imaging;
using System.IO;

public static class CleanEnemyFrames
{
    private sealed class Component
    {
        public readonly List<Point> Pixels = new List<Point>();
        public int MinX = 999, MinY = 999, MaxX = -1, MaxY = -1;
        public int CenterDistance = int.MaxValue;
        public void Add(int x, int y)
        {
            Pixels.Add(new Point(x, y));
            MinX = Math.Min(MinX, x); MinY = Math.Min(MinY, y);
            MaxX = Math.Max(MaxX, x); MaxY = Math.Max(MaxY, y);
            int dx = x - 48, dy = y - 48;
            CenterDistance = Math.Min(CenterDistance, dx * dx + dy * dy);
        }
    }

    public static int Run(string inputRoot, string outputRoot)
    {
        int count = 0;
        foreach (string input in Directory.GetFiles(inputRoot, "*.png", SearchOption.AllDirectories))
        {
            string relative = input.Substring(inputRoot.TrimEnd('\\').Length).TrimStart('\\');
            string output = Path.Combine(outputRoot, relative);
            Directory.CreateDirectory(Path.GetDirectoryName(output));
            Clean(input, output);
            count++;
        }
        return count;
    }

    private static void Clean(string input, string output)
    {
        using (var source = new Bitmap(input))
        using (var result = new Bitmap(source.Width, source.Height, PixelFormat.Format32bppArgb))
        {
            int w = source.Width, h = source.Height;
            var seen = new bool[w, h];
            var components = new List<Component>();
            int[] ox = {-1, 0, 1, -1, 1, -1, 0, 1};
            int[] oy = {-1,-1,-1,  0, 0,  1, 1, 1};
            for (int y = 0; y < h; y++) for (int x = 0; x < w; x++)
            {
                if (seen[x,y] || source.GetPixel(x,y).A == 0) continue;
                var component = new Component();
                var queue = new Queue<Point>();
                queue.Enqueue(new Point(x,y)); seen[x,y] = true;
                while (queue.Count > 0)
                {
                    Point p = queue.Dequeue(); component.Add(p.X, p.Y);
                    for (int i = 0; i < 8; i++)
                    {
                        int nx = p.X + ox[i], ny = p.Y + oy[i];
                        if (nx < 0 || nx >= w || ny < 0 || ny >= h || seen[nx,ny]) continue;
                        seen[nx,ny] = true;
                        if (source.GetPixel(nx,ny).A > 0) queue.Enqueue(new Point(nx,ny));
                    }
                }
                components.Add(component);
            }
            if (components.Count == 0) { result.Save(output, ImageFormat.Png); return; }
            Component main = components[0];
            double best = double.MaxValue;
            foreach (Component c in components)
            {
                double score = c.CenterDistance - Math.Min(c.Pixels.Count, 1200) * 0.12;
                if (score < best) { best = score; main = c; }
            }
            foreach (Component c in components)
            {
                bool nearMain = c == main || (c.Pixels.Count >= 3 &&
                    c.MaxX >= main.MinX - 3 && c.MinX <= main.MaxX + 3 &&
                    c.MaxY >= main.MinY - 3 && c.MinY <= main.MaxY + 3);
                if (!nearMain) continue;
                foreach (Point p in c.Pixels) result.SetPixel(p.X, p.Y, source.GetPixel(p.X, p.Y));
            }
            result.Save(output, ImageFormat.Png);
        }
    }
}
