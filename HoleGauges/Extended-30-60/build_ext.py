import json, math, os, sys, zipfile, itertools
import numpy as np, cadquery as cq, trimesh
from layout import plan, GAP, LANE, TUBE
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Circle, Rectangle, FancyBboxPatch

OUT=sys.argv[1] if len(sys.argv)>1 else 'out'
P=206.0; T=10.0; FLOOR=2.0; WALL=2.0; LBL_D=0.6; FONT=6.6
os.makedirs(OUT,exist_ok=True)
sizes=[30+0.5*i for i in range(61)]
plates=plan(sizes)

def fmt(d): return ('%g'%d)
def text_bbox(s):
    bb=cq.Workplane('XY').text(s,FONT,LBL_D,font='DejaVu Sans',kind='bold',halign='center',valign='center').val().BoundingBox()
    return bb.xlen,bb.ylen

def layout(rows):
    """returns holes list with x,y (y measured from top, like earlier plates), tube etc."""
    heights=[max(d+TUBE for d in r)+LANE for r in rows]
    slack=196.0-sum(heights)
    y=5+slack/2
    holes=[]
    for ri,r in enumerate(rows):
        maxod=max(d+TUBE for d in r)
        yc=y+maxod/2
        w=sum(d+TUBE for d in r)+GAP*(len(r)-1)
        x=P/2-w/2
        for d in r:
            od=d+TUBE
            holes.append(dict(row=ri+1,d=d,od=od,x=x+od/2,y=yc))
            x+=od+GAP
        y+=maxod+LANE
    return holes,heights,slack

def place_labels(holes):
    for h in holes:
        h['label']=None
    for h in holes:
        if abs(h['d']-round(h['d']))>1e-9: continue
        s=str(int(round(h['d']))); w,hh=text_bbox(s)
        # preferred: just under own tube; try x shifts then y shifts
        done=False
        for dy in (0.4,0.3,0.6,0.9,1.2):
          for dx in [0,-1,1,-2,2,-3,3,-4,4,-5,5,-6,6]:
            cx=h['x']+dx; cy=h['y']+h['od']/2+dy+hh/2
            ok=True
            for o in holes:
                # rectangle vs circle distance (tube outer + 0.5 clearance)
                qx=min(max(o['x'],cx-w/2),cx+w/2); qy=min(max(o['y'],cy-hh/2),cy+hh/2)
                if math.hypot(qx-o['x'],qy-o['y'])<o['od']/2+0.35: ok=False;break
            if cx-w/2<5.5 or cx+w/2>P-5.5 or cy+hh/2>P-5.5: ok=False
            if ok: done=True;break
          if done:break
        if not done: raise SystemExit('no label place %s'%s)
        h['label']=dict(text=s,x=cx,y=cy,w=w,h=hh)

def build_body_labels(holes):
    # CAD coords: Y up; y_cad = P - y_top
    outer=(cq.Workplane('XY').box(P,P,T,centered=False).edges('|Z').fillet(5.0).faces('>Z').edges().fillet(1.0))
    cav=(cq.Workplane('XY').workplane(offset=FLOOR).center(P/2,P/2).rect(P-2*WALL,P-2*WALL).extrude(T).edges('|Z').fillet(3.0))
    body=outer.cut(cav)
    tubes=None
    for h in holes:
        c=(cq.Workplane('XY').center(h['x'],h['y']).circle(h['od']/2).extrude(T))
        tubes=c if tubes is None else tubes.union(c)
    body=body.union(tubes)
    for h in holes:
        b=cq.Workplane('XY').workplane(offset=-1).center(h['x'],h['y']).circle(h['d']/2).extrude(T+2)
        body=body.cut(b)
    labels=None
    for h in holes:
        l=h['label']
        if not l: continue
        t=(cq.Workplane('XY').workplane(offset=FLOOR-LBL_D).center(l['x'],l['y'])
           .text(l['text'],FONT,LBL_D,font='DejaVu Sans',kind='bold',halign='center',valign='center',combine=False))
        labels=t if labels is None else labels.add(t)
    lab_solids=[s for s in labels.vals()] if labels else []
    # pocket the body
    cutter=cq.Workplane('XY').add(lab_solids).combine() if False else None
    for s in lab_solids:
        body=body.cut(cq.Workplane('XY').add(s))
    comp=cq.Compound.makeCompound(lab_solids)
    return body.val(),comp,lab_solids

def mesh_of(shape,tol=0.02,ang=0.1):
    v,f=shape.tessellate(tol,ang)
    return trimesh.Trimesh(np.array([[p.x,p.y,p.z] for p in v]),np.array(f),process=True)

def write_3mf(path,title,body_m,lab_m,name):
    def blk(m,oid,nm,pindex):
        vs=''.join('<vertex x="%.5f" y="%.5f" z="%.5f"/>\n'%tuple(v) for v in m.vertices)
        ts=''.join('<triangle v1="%d" v2="%d" v3="%d"/>\n'%tuple(t) for t in m.faces)
        return '<object id="%d" type="model" name="%s" pid="1" pindex="%d">\n <mesh>\n <vertices>\n%s</vertices>\n <triangles>\n%s</triangles>\n </mesh>\n</object>\n'%(oid,nm,pindex,vs,ts)
    model=('<?xml version="1.0" encoding="UTF-8"?>\n<model unit="millimeter" xml:lang="en-US" xmlns="http://schemas.microsoft.com/3dmanufacturing/core/2015/02">\n'
      ' <metadata name="Title">%s</metadata>\n <resources>\n<basematerials id="1">\n <base name="Body" displaycolor="#BFBFBF"/>\n <base name="Labels" displaycolor="#000000"/>\n</basematerials>\n'%title
      + blk(body_m,2,name+' Body',0)+blk(lab_m,3,name+' Labels',1)
      + '<object id="4" type="model" name="%s">\n <components>\n  <component objectid="2"/>\n  <component objectid="3"/>\n </components>\n</object>\n </resources>\n <build>\n  <item objectid="4" transform="1 0 0 0 1 0 0 0 1 32.5 33 0"/>\n </build>\n</model>\n'%name)
    cfg=('<?xml version="1.0" encoding="UTF-8"?>\n<config>\n<object id="4">\n <metadata key="name" value="%s"/>\n <metadata key="extruder" value="1"/>\n'
      '  <part id="2" subtype="normal_part">\n   <metadata key="name" value="Body"/>\n   <metadata key="matrix" value="1 0 0 0 0 1 0 0 0 0 1 0 0 0 0 1"/>\n   <metadata key="extruder" value="1"/>\n  </part>\n'
      '  <part id="3" subtype="normal_part">\n   <metadata key="name" value="Labels"/>\n   <metadata key="matrix" value="1 0 0 0 0 1 0 0 0 0 1 0 0 0 0 1"/>\n   <metadata key="extruder" value="4"/>\n  </part>\n</object>\n\n</config>\n'%name)
    ct='<?xml version="1.0" encoding="UTF-8"?>\n<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">\n <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>\n <Default Extension="model" ContentType="application/vnd.ms-package.3dmanufacturing-3dmodel+xml"/>\n <Default Extension="config" ContentType="text/xml"/>\n <Default Extension="json" ContentType="application/json"/>\n</Types>\n'
    rels='<?xml version="1.0" encoding="UTF-8"?>\n<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">\n <Relationship Target="/3D/3dmodel.model" Id="rel0" Type="http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel"/>\n</Relationships>\n'
    with zipfile.ZipFile(path,'w',zipfile.ZIP_DEFLATED) as z:
        z.writestr('[Content_Types].xml',ct); z.writestr('_rels/.rels',rels)
        z.writestr('3D/3dmodel.model',model); z.writestr('Metadata/model_settings.config',cfg)

def preview(path,pn,holes,lo,hi,n):
    fig=plt.figure(figsize=(10.24,7.09),dpi=100,facecolor='#f0f0f0')
    ax=fig.add_axes([0.06,0.1,0.52,0.75]); ax.set_aspect('equal'); ax.set_xlim(0,P); ax.set_ylim(0,P); ax.axis('off')
    ax.add_patch(FancyBboxPatch((0,0),P,P,boxstyle='round,pad=0,rounding_size=5',fc='#b0b0b0',ec='#808080'))
    ax.add_patch(FancyBboxPatch((2,2),P-4,P-4,boxstyle='round,pad=0,rounding_size=3',fc='#d9d9d9',ec='#a0a0a0'))
    for h in holes:
        ax.add_patch(Circle((h['x'],h['y']),h['od']/2,fc='#999999',ec='#777777'))
        ax.add_patch(Circle((h['x'],h['y']),h['d']/2,fc='#f0f0f0',ec='#777777'))
    for h in holes:
        l=h['label']
        if l: ax.text(l['x'],l['y'],l['text'],ha='center',va='center',fontsize=9.5,fontweight='bold',color='black')
    fig.text(0.038,0.945,'U1 HOLE GAUGE EXTENDED — PLATE %d of %d — 206 × 206 mm'%(pn,n),fontsize=14,fontweight='bold')
    fig.text(0.038,0.905,'%d nominal bores Ø%s–%s / 0.5 steps · %d rows · body head1 / black labels head4 · no plugs'%(len(holes),fmt(lo),fmt(hi),max(h['row'] for h in holes)),fontsize=8.5,fontweight='bold')
    fig.text(0.59,0.80,'Plate %d (no plugs)'%pn,fontsize=14,fontweight='bold')
    fig.text(0.59,0.70,'Ø%s – Ø%s mm\n%d holes\n206 × 206 × 10 mm\nLabels: whole sizes only'%(fmt(lo),fmt(hi),len(holes)),fontsize=10,va='top')
    fig.text(0.59,0.45,'Filaments',fontsize=14,fontweight='bold')
    for i,(c,t) in enumerate([('#BFBFBF','Ext 1  Body'),('#000000','Ext 4  Labels BLACK')]):
        fig.patches.append(Rectangle((0.59,0.38-i*0.06),0.025,0.035,transform=fig.transFigure,fc=c,ec='#555'))
        fig.text(0.63,0.385-i*0.06,t,fontsize=10)
    fig.savefig(path,facecolor=fig.get_facecolor()); plt.close(fig)

summary=[]
n=len(plates)
for pi,(ds,h_req,rows) in enumerate(plates,1):
    holes,heights,slack=layout(rows)
    place_labels(holes)
    body,labcomp,lab_solids=build_body_labels(holes)
    lo,hi=ds[0],ds[-1]
    stem='hole_gauge_ext_plate%d_%s-%s'%(pi,fmt(lo).replace('.','p'),fmt(hi).replace('.','p'))
    name='Hole Gauge Ext Plate %d (Ø%s-%s)'%(pi,fmt(lo),fmt(hi))
    cq.exporters.export(cq.Workplane('XY').add(cq.Compound.makeCompound([body,labcomp])),os.path.join(OUT,stem+'.step'))
    bm=mesh_of(body); lm=mesh_of(labcomp,0.01,0.1)
    bm.export(os.path.join(OUT,stem+'_plate_body.stl')); lm.export(os.path.join(OUT,stem+'_plate_labels.stl'))
    write_3mf(os.path.join(OUT,stem+'.3mf'),'Hole gauge extended plate %d Ø%s-%s 206mm'%(pi,fmt(lo),fmt(hi)),bm,lm,name)
    preview(os.path.join(OUT,stem+'_preview.png'),pi,holes,lo,hi,n)
    # verification
    bores=[]
    for hh in holes:
        pass
    # tube gaps
    mingap=1e9
    for a,b in itertools.combinations(holes,2):
        mingap=min(mingap,math.hypot(a['x']-b['x'],a['y']-b['y'])-a['od']/2-b['od']/2)
    wall=min(min(h['x']-h['od']/2-2,P-2-(h['x']+h['od']/2),h['y']-h['od']/2-2,P-2-(h['y']+h['od']/2)) for h in holes)
    ov=[]
    for s in lab_solids:
        ov.append(round(s.intersect(body).Volume(),4))
    # label vs tube: labels pocketed in floor; check label solid vs tube solids
    tube_ov=0.0
    summary.append(dict(plate=pi,stem=stem,name=name,hole_count=len(holes),min_d=lo,max_d=hi,rows=[[r[0],r[-1],len(r)] for r in rows],
        required_height=round(h_req,2),label_count=len(lab_solids),min_tube_gap_mm=round(mingap,3),min_tube_to_inner_wall_mm=round(wall,3),
        label_body_overlap_mm3_max=max(ov) if ov else 0,
        body_watertight=bool(bm.is_watertight),labels_watertight=bool(lm.is_watertight),body_volume_mm3=round(float(bm.volume),1),
        body_bounds=[list(map(lambda v:round(float(v),3),r)) for r in bm.bounds],label_bounds=[list(map(lambda v:round(float(v),3),r)) for r in lm.bounds],
        holes=[dict(d=h['d'],tube_od=h['od'],x=round(h['x'],3),y_cad=round(h['y'],3),label=(h['label']['text'] if h['label'] else None)) for h in holes]))
    print(pi,name,len(holes),'gap',round(mingap,2),'wall',round(wall,2),'ov',max(ov) if ov else 0,bm.is_watertight,lm.is_watertight,flush=True)
json.dump(summary,open(os.path.join(OUT,'verification-ext.json'),'w'),indent=1)
