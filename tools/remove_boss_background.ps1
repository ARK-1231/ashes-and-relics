param(
    [string]$Source = "assets/sprites/boss/kingdom_guardian_spellblade_preview.png",
    [string]$Destination = "assets/sprites/boss/kingdom_guardian_spellblade.png"
)
Add-Type -AssemblyName System.Drawing
Add-Type -ReferencedAssemblies System.Drawing -TypeDefinition @"
using System;
using System.Drawing;
using System.Drawing.Imaging;
using System.Runtime.InteropServices;
public static class BossCutout {
 public static void Run(string source,string target) {
  using(var input=new Bitmap(source)) using(var bmp=new Bitmap(input.Width,input.Height,PixelFormat.Format32bppArgb)) {
   using(var g=Graphics.FromImage(bmp)) g.DrawImageUnscaled(input,0,0);
   int w=bmp.Width,h=bmp.Height,n=w*h;
   var data=bmp.LockBits(new Rectangle(0,0,w,h),ImageLockMode.ReadWrite,PixelFormat.Format32bppArgb);
   byte[] bytes=new byte[data.Stride*h]; Marshal.Copy(data.Scan0,bytes,0,bytes.Length);
   bool[] visited=new bool[n]; int[] queue=new int[n]; int removed=0;
   for(int seed=0;seed<n;seed++) {
    if(visited[seed]) continue;
    int head=0,tail=0; queue[tail++]=seed; visited[seed]=true;
    int off=(seed/w)*data.Stride+(seed%w)*4;
    if(!White(bytes,off)) continue;
    while(head<tail) {
     int p=queue[head++],x=p%w,y=p/w;
     int[] next={x>0?p-1:-1,x<w-1?p+1:-1,y>0?p-w:-1,y<h-1?p+w:-1};
     foreach(int q in next) if(q>=0&&!visited[q]) {
      visited[q]=true; int k=(q/w)*data.Stride+(q%w)*4;
      if(White(bytes,k)) queue[tail++]=q;
     }
    }
    if(tail<24) continue;
    for(int j=0;j<tail;j++) {int p=queue[j];bytes[(p/w)*data.Stride+(p%w)*4+3]=0;removed++;}
   }
   Marshal.Copy(bytes,0,data.Scan0,bytes.Length);bmp.UnlockBits(data);bmp.Save(target,ImageFormat.Png);
   Console.WriteLine("Removed background pixels: "+removed);
  }
 }
 static bool White(byte[] b,int k) {int lo=Math.Min(b[k],Math.Min(b[k+1],b[k+2]));int hi=Math.Max(b[k],Math.Max(b[k+1],b[k+2]));return lo>=225 && hi-lo<=24;}
}
"@
[BossCutout]::Run((Join-Path $PWD $Source),(Join-Path $PWD $Destination))
