from pathlib import Path
from PIL import Image, ImageDraw
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from scipy.optimize import linear_sum_assignment
from scipy.interpolate import CubicSpline
from scipy.ndimage import gaussian_filter1d, label, binary_dilation
import json,shutil,subprocess,zipfile,hashlib

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'build';OUT.mkdir(exist_ok=True)
FRAMES=OUT/'frames_30fps';FRAMES.mkdir(exist_ok=True)
KEYS=OUT/'drawn_keys';KEYS.mkdir(exist_ok=True)
paths=[str(p) for p in sorted((ROOT/'assets/keyframes').glob('*.png'))]

def signedarea(p):
    return .5*np.sum(p[:,0]*np.roll(p[:,1],-1)-p[:,1]*np.roll(p[:,0],-1))

def resample(p,n):
    p=np.asarray(p,dtype=float)
    if np.linalg.norm(p[0]-p[-1])>1e-6:p=np.vstack([p,p[0]])
    # Canonical winding and topmost starting point.
    if signedarea(p)<0:p=p[::-1]
    p=p[:-1];start=np.lexsort((p[:,0],p[:,1]))[0];p=np.roll(p,-start,axis=0)
    p=np.vstack([p,p[0]])
    dist=np.r_[0,np.cumsum(np.linalg.norm(np.diff(p,axis=0),axis=1))]
    t=np.linspace(0,dist[-1],n,endpoint=False)
    return np.c_[np.interp(t,dist,p[:,0]),np.interp(t,dist,p[:,1])]

def getpaths(path):
    im=Image.open(path).convert('L').resize((1254,1254),Image.Resampling.LANCZOS)
    fig,ax=plt.subplots();c=ax.contour((np.asarray(im)>127).astype(float),levels=[.5]);segs=c.allsegs[0];plt.close(fig)
    segs=[s for s in segs if abs(signedarea(s))>70]
    segs.sort(key=lambda s:abs(signedarea(s)),reverse=True)
    assert len(segs)==9,(path,'expected one outline and eight curls',len(segs))
    return segs[0],segs[1:]

def correspond(ref,target,n,coarse,band):
    a=resample(ref,coarse+1);b=resample(target,coarse+1)
    # Open the common seam at the topmost point. DTW keeps the order of all tips and folds.
    a=np.vstack([a,a[0]]);b=np.vstack([b,b[0]])
    m=len(a)
    costs=np.sum((a[:,None,:]-b[None,:,:])**2,axis=2)
    D=np.full((m+1,m+1),np.inf);D[0,0]=0
    parent=np.zeros((m,m),dtype='uint8')
    for i in range(m):
        for j in range(max(0,i-band),min(m,i+band+1)):
            values=(D[i,j],D[i,j+1]+3,D[i+1,j]+3)
            d=int(np.argmin(values));D[i+1,j+1]=costs[i,j]+values[d];parent[i,j]=d
    matches=[[] for _ in range(m)];i=j=m-1
    while i>=0 and j>=0:
        matches[i].append(j)
        if i==0 and j==0:break
        d=parent[i,j]
        if d==0:i-=1;j-=1
        elif d==1:i-=1
        else:j-=1
    mapping=np.array([np.mean(v) if v else np.nan for v in matches])
    valid=np.flatnonzero(np.isfinite(mapping));mapping=np.interp(np.arange(m),valid,mapping[valid])
    mapping[0]=0;mapping[-1]=m-1
    q=np.linspace(0,m-1,n,endpoint=False)
    targetpos=np.interp(q,np.arange(m),mapping)
    result=np.c_[np.interp(targetpos,np.arange(m),b[:,0]),np.interp(targetpos,np.arange(m),b[:,1])]
    return gaussian_filter1d(result,1.1,axis=0,mode='wrap')

baseouter,baseholes=getpaths(paths[0]);basecenters=np.array([h.mean(axis=0) for h in baseholes])
allpaths=[]
for k,path in enumerate(paths):
    outer,holes=getpaths(path)
    centers=np.array([h.mean(axis=0) for h in holes])
    ri,ci=linear_sum_assignment(np.linalg.norm(basecenters[:,None,:]-centers[None,:,:],axis=2))
    holes=[holes[j] for j in ci]
    # Translation registration only, anchored to all eight persistent curl marks.
    shift=np.median(np.array([h.mean(axis=0) for h in holes])-basecenters,axis=0)
    outer=outer-shift;holes=[h-shift for h in holes]
    aligned=[correspond(baseouter,outer,4096,768,72)]
    aligned.extend(correspond(ref,h,768,192,28) for ref,h in zip(baseholes,holes))
    allpaths.append(aligned)
    shutil.copy2(path,KEYS/f'key_{k:02}.png')
    print('matched drawing',k+1,'with 8 persistent spiral paths',flush=True)

times=np.linspace(0,10,9)
curves=[]
for feature in range(9):
    values=np.stack([p[feature] for p in allpaths]);values=np.concatenate([values,values[:1]],axis=0)
    curves.append(CubicSpline(times,values,axis=0,bc_type='periodic'))

# Keep the requested central icon identical throughout the shot.
master=Image.open(ROOT/'assets/character-source.png').convert('L')
ma=np.asarray(master);labs,n=label(ma>100);areas=np.bincount(labs.ravel());areas[0]=0
fid=np.argsort(areas)[::-1][1];mask=binary_dilation(labs==fid,iterations=2)
char=Image.fromarray(np.where(mask,np.clip((ma.astype(float)-30)*255/195,0,255),0).astype('uint8'))
char=char.crop(char.getbbox());char.thumbnail((370,370),Image.Resampling.LANCZOS)
character=Image.new('L',(1024,1024));character.paste(char,((1024-char.width)//2,512-char.height//2));character=np.asarray(character)

neutral=[curve(0) for curve in curves]
def phased_outline(t):
    base=neutral[0]
    tail=np.clip((base[:,1]-820)/330,0,1)
    crown=np.clip((240-base[:,1])/210,0,1)
    side=(base[:,0]-627)/627
    delay=.08*side+.18*tail
    tt=(t-delay)%10
    curve=curves[0]
    seg=np.clip(np.searchsorted(curve.x,tt,side='right')-1,0,7)
    u=tt-curve.x[seg];ids=np.arange(len(base))
    c=curve.c[:,seg,ids,:]
    p=((c[0]*u[:,None]+c[1])*u[:,None]+c[2])*u[:,None]+c[3]
    gain=1.12+.22*tail+.08*crown
    motion=gaussian_filter1d(p-base,4,axis=0,mode='wrap')
    return base+motion*gain[:,None]

def render(t):
    im=Image.new('L',(2048,2048),0);draw=ImageDraw.Draw(im)
    for j,curve in enumerate(curves):
        if j==0:
            p=phased_outline(t)
        else:
            base=neutral[j];center=base.mean(axis=0)
            tail=float(np.clip((center[1]-820)/330,0,1))
            delay=.08*(center[0]-627)/627+.18*tail
            p=base+1.12*(curve((t-delay)%10)-base)
            # Roll each persistent ink curl in place, with staggered timing.
            pivot=p.mean(axis=0)
            angle=np.deg2rad(5.5)*np.sin(4*np.pi*t/10+j*.55)
            rotation=np.array([[np.cos(angle),-np.sin(angle)],[np.sin(angle),np.cos(angle)]])
            p=(p-pivot)@rotation.T+pivot
        pts=(p/1254*900+62)*2
        draw.polygon([tuple(x) for x in pts],fill=255 if j==0 else 0)
    cloud=im.resize((1024,1024),Image.Resampling.LANCZOS)
    # Validate topology before compositing; curls must never disappear or fragment.
    b=np.asarray(cloud)>127
    labs,n=label(b);areas=np.bincount(labs.ravel());white_components=int(np.sum(areas[1:]>25))
    labs,n=label(~b);areas=np.bincount(labs.ravel());black_components=int(np.sum(areas[1:]>25))
    angle=1.7*np.sin(4*np.pi*t/10)
    xshift=3*np.sin(2*np.pi*t/10)
    yshift=-6*np.sin(4*np.pi*t/10)
    icon=Image.fromarray(character).rotate(angle,resample=Image.Resampling.BICUBIC,center=(512,512),fillcolor=0)
    icon=icon.transform((1024,1024),Image.Transform.AFFINE,(1,0,-xshift,0,1,-yshift),resample=Image.Resampling.BICUBIC)
    frame=Image.fromarray(np.maximum(np.asarray(cloud),np.asarray(icon))).convert('RGB')
    return frame,white_components,black_components

frames=[];topologies=[];digests=[];diffs=[];previous=None
for k in range(300):
    t=10*k/299 # identical first/last images; continuous, one-way cyclic key sequence.
    frame,nw,nb=render(t)
    frame.save(FRAMES/f'frame_{k:03}.png',compress_level=4)
    a=np.asarray(frame)
    if previous is not None:diffs.append(float(np.abs(a.astype(float)-previous).mean()))
    previous=a.astype(float)
    topologies.append((nw,nb));digests.append(hashlib.sha256(frame.tobytes()).hexdigest())
    frames.append(frame)
    if k%50==0:print('rendered',k,flush=True)
print('Topology counts:',sorted(set(topologies)),flush=True)
assert len(set(topologies))==1 and topologies[0]==(1,9),('topology changed',set(topologies))
assert digests[0]==digests[-1]
ff=['ffmpeg','-y','-loglevel','error']
subprocess.run(ff+['-framerate','30','-i',str(FRAMES/'frame_%03d.png'),'-c:v','libx264','-threads','2','-crf','16','-preset','medium','-pix_fmt','yuv420p','-movflags','+faststart',str(OUT/'JoyBoy_Lively_30fps.mp4')],check=True)
subprocess.run(ff+['-i',str(OUT/'JoyBoy_Lively_30fps.mp4'),'-vf','scale=900:900,pad=1080:1920:(ow-iw)/2:(oh-ih)/2:black','-c:v','libx264','-threads','2','-crf','17','-pix_fmt','yuv420p','-movflags','+faststart',str(OUT/'JoyBoy_Lively_Phone.mp4')],check=True)
palette=Image.new('P',(1,1));palette.putpalette([c for i in range(256) for c in (i,i,i)])
gif=[im.resize((640,640),Image.Resampling.LANCZOS).quantize(palette=palette,dither=Image.Dither.NONE) for im in frames]
gif[0].save(OUT/'JoyBoy_Lively.gif',save_all=True,append_images=gif[1:],duration=[30,30,40]*100,loop=0,optimize=True,disposal=1)
frames[0].save(OUT/'JoyBoy_Still.png')
sheet=Image.new('RGB',(2048,2048),'black')
for j,k in enumerate(np.linspace(0,299,16,dtype=int)):sheet.paste(frames[k].resize((512,512)),((j%4)*512,(j//4)*512))
sheet.save(OUT/'Animation_Overview.png')
report={'duration_seconds':10,'fps':30,'frames':300,'unique_frames':len(set(digests)),
        'same_first_last_frame':digests[0]==digests[-1],
        'cloud_components_and_black_regions':sorted(set(topologies)),
        'mean_frame_difference':float(np.mean(diffs)),'max_frame_difference':max(diffs),
        'method':'8 image-generated drawn key poses; correspondence of outline and 8 spiral contours; periodic cubic contour inbetweening and supersampled rasterization. Subtle floating/tilting Luffy; stronger cloud follow-through and curl roll. No raster averaging, wave displacement or backwards playback.'}
(OUT/'Validation.json').write_text(json.dumps(report,indent=2))
(OUT/'README.txt').write_text('Joy Boy Steam Scarf — 10-second loop\nVideo: 1024x1024, 30fps, 300 frames, exact duration 10 seconds.\nPhone video: 1080x1920, 30fps, 10 seconds.\nGIF: 640x640, 300 frames, 30/30/40ms cadence because GIF timing uses 10ms units.\n8 high-resolution key poses were drawn with the image-generation tool.\nThe 300 playback images are contour inbetweens rendered from those drawings, not 300 independently image-generated illustrations.\nMatched contours preserve one connected white scarf and all eight black spiral marks. Luffy floats and tilts gently; cloud tips have stronger, staggered motion.\nContinuous forward loop with periodic key paths; first and last PNG match.\nIncludes all 300 PNGs, all 8 original key drawings, still image, videos and GIF.\n',encoding='utf-8')
shutil.copy2(ROOT/'assets/prompts.txt',OUT/'Prompts.txt')
with zipfile.ZipFile(ROOT/'JoyBoy_Lively_Complete.zip','w',zipfile.ZIP_DEFLATED,compresslevel=1) as z:
    for p in OUT.rglob('*'):
        if p.is_file():z.write(p,p.relative_to(ROOT))
print(json.dumps(report),flush=True)
