Add-Type -AssemblyName System.Drawing
Add-Type -ReferencedAssemblies System.Drawing -TypeDefinition @"
using System;
using System.Drawing;
using System.Drawing.Imaging;
using System.Drawing.Drawing2D;
public static class BossFrames {
 public static void Run(string source,string directory) {
  using(var sheet=new Bitmap(source)) {
   int w=sheet.Width,h=sheet.Height,n=w*h;bool[] seen=new bool[n];int[] q=new int[n];
   var layers=new Bitmap[6]; for(int i=0;i<6;i++)layers[i]=new Bitmap(w,h);
   for(int seed=0;seed<n;seed++) {
    if(seen[seed])continue;seen[seed]=true;
    if(sheet.GetPixel(seed%w,seed/w).A==0)continue;
    int head=0,tail=1;long sumX=0,sumY=0;q[0]=seed;
    while(head<tail) {
     int p=q[head++],x=p%w,y=p/w;sumX+=x;sumY+=y;
     int[] ns={x>0?p-1:-1,x<w-1?p+1:-1,y>0?p-w:-1,y<h-1?p+w:-1};
     foreach(int k in ns)if(k>=0&&!seen[k]){seen[k]=true;if(sheet.GetPixel(k%w,k/w).A>0)q[tail++]=k;}
    }
    if(tail<3)continue;
    int col=Math.Min(2,(int)(sumX/tail)*3/w),row=Math.Min(1,(int)(sumY/tail)*2/h),index=row*3+col;
    for(int j=0;j<tail;j++){int p=q[j];layers[index].SetPixel(p%w,p/w,sheet.GetPixel(p%w,p/w));}
   }
   string[] names={"melee","boss_fan","boss_ring","boss_lance","boss_spiral","boss_wave"};
   for(int i=0;i<6;i++)using(var layer=layers[i]) {
    int left=w,top=h,right=0,bottom=0;
    for(int y=0;y<h;y++)for(int x=0;x<w;x++)if(layer.GetPixel(x,y).A>0){left=Math.Min(left,x);right=Math.Max(right,x);top=Math.Min(top,y);bottom=Math.Max(bottom,y);}
    float scale=Math.Min(170f/(right-left+1),170f/(bottom-top+1));
    int dw=(int)((right-left+1)*scale),dh=(int)((bottom-top+1)*scale);
    using(var frame=new Bitmap(180,180)) {
     using(var g=Graphics.FromImage(frame)){g.InterpolationMode=InterpolationMode.HighQualityBicubic;g.DrawImage(layer,new Rectangle((180-dw)/2,176-dh,dw,dh),new Rectangle(left,top,right-left+1,bottom-top+1),GraphicsUnit.Pixel);}
     frame.Save(System.IO.Path.Combine(directory,names[i]+".png"),ImageFormat.Png);
    }
    Console.WriteLine(names[i]);
   }
  }
 }
}
"@
[BossFrames]::Run((Join-Path $PWD 'assets/sprites/boss/attacks_transparent.png'),(Join-Path $PWD 'assets/sprites/boss/attacks'))
