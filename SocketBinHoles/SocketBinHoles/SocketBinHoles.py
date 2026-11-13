"""Add holes and separate flush label inlays to an existing solid blank. No base generation.

Version is socketbin_core.VERSION (single source of truth).
"""
import os,sys,math,traceback,uuid
import adsk.core,adsk.fusion
HERE=os.path.dirname(os.path.realpath(__file__))
if HERE not in sys.path: sys.path.insert(0,HERE)
# Explicit local imports avoid another installed SocketBin's core taking precedence.
import importlib.util
for _name in ('socketbin_core','holes_layout'):
    _spec=importlib.util.spec_from_file_location(_name,os.path.join(HERE,_name+'.py'))
    _mod=importlib.util.module_from_spec(_spec);sys.modules[_name]=_mod;_spec.loader.exec_module(_mod)
core=sys.modules['socketbin_core'];layout=sys.modules['holes_layout'].layout
VERSION=core.VERSION

def point(x,y,z=0):return adsk.core.Point3D.create(x/10,y/10,z/10)
def val(mm):return adsk.core.ValueInput.createByReal(mm/10)
def collection(items):
    c=adsk.core.ObjectCollection.create()
    for i in items:c.add(i)
    return c

def extrude(comp,profile,depth,op,target=None):
    ei=comp.features.extrudeFeatures.createInput(profile,op)
    ei.setOneSideExtent(adsk.fusion.DistanceExtentDefinition.create(val(depth)),adsk.fusion.ExtentDirections.NegativeExtentDirection)
    if target:ei.participantBodies=[target]
    return comp.features.extrudeFeatures.add(ei)

def text(sk,content,size,x,y):
    texts=sk.sketchTexts
    if hasattr(texts,'createInput3'):
        inp=texts.createInput3("'"+content.replace("'",'’')+"'",val(size))
    else:inp=texts.createInput2(content,size/10)
    inp.fontName='Arial';inp.textStyle=adsk.fusion.TextStyles.TextStyleBold
    half=max(30,len(content)*size)
    inp.setAsMultiLine(point(x-half,y),point(x+half,y+size*3),adsk.core.HorizontalAlignments.CenterHorizontalAlignment,adsk.core.VerticalAlignments.BottomVerticalAlignment,0)
    return texts.add(inp)

def white(design,bodies):
    app=adsk.core.Application.get();ap=design.appearances.itemByName('SocketBinHoles - white')
    if not ap:
        source=None
        for lib in app.materialLibraries:
            for a in lib.appearances:
                if 'Plastic' in a.name:source=a;break
            if source:break
        if not source:raise RuntimeError('No plastic appearance found; assign white manually.')
        ap=design.appearances.addByCopy(source,'SocketBinHoles - white')
        changed=False
        for prop in ap.appearanceProperties:
            cp=adsk.core.ColorProperty.cast(prop)
            if cp:cp.value=adsk.core.Color.create(255,255,255,255);changed=True
        if not changed:raise RuntimeError('Assign white to Labels manually.')
    for b in bodies:b.appearance=ap

def run(context):
    app=adsk.core.Application.get();ui=app.userInterface;made=[];stage='setup'
    floors_created=0;floors_colored=0;floors_expected=0;floor_warnings=[]
    try:
        design=adsk.fusion.Design.cast(app.activeProduct)
        if not design:raise ValueError('Open the existing bin in Fusion first.')
        ui.messageBox('SocketBinHoles %s\n\nSave a copy first. Select the large flat TOP face of a SOLID Gridfinity blank.\nOnly the selected body receives cuts. Feet are never regenerated.\nSupported: body aligned with its component XY plane, top facing +Z. Imported STEP blanks work.'%VERSION,'SocketBinHoles %s'%VERSION)
        sel=ui.selectEntity('Select the large flat top face of the bin','PlanarFaces')
        if not sel:return
        face=sel.entity
        if face.assemblyContext:face=face.nativeObject
        body=face.body;comp=body.parentComponent
        if not body.isSolid:raise ValueError('Select a solid BRep body, not mesh or surface.')
        plane=adsk.core.Plane.cast(face.geometry)
        ok,normal=face.evaluator.getNormalAtPoint(face.pointOnFace)
        if not plane or not ok or normal.z<.999999:raise ValueError('Top must face component +Z. Reorient/activate the bin component and try again.')
        bb=body.boundingBox;z=plane.origin.z*10
        if abs(bb.maxPoint.z*10-z)>.02:raise ValueError('Selected face is not the highest top surface. This version needs a flat solid blank, not a raised stacking lip.')
        dx=(bb.maxPoint.x-bb.minPoint.x)*10;dy=(bb.maxPoint.y-bb.minPoint.y)*10
        H=(bb.maxPoint.z-bb.minPoint.z)*10
        long_y=dy>dx;L,W=(dy,dx) if long_y else (dx,dy)
        answer,cancel=ui.inputBox('Measured %.3f x %.3f x %.3f mm.\nEnter: top inset mm, base-region height mm, minimum floor mm\nDefault 1,5,3 preserves 3 mm ABOVE the 5 mm feet.\nIncrease inset for thick sidewalls; use a SOLID blank, not a hollow bin.'%(L,W,H),'SocketBinHoles %s — safety'%VERSION,'1,5,3')
        if cancel:return
        margin,base,floor=[float(x.strip()) for x in answer.split(',')]
        answer,cancel=ui.inputBox('Pocket floor inlay thickness, mm (same appearance as labels).\n0 = off. Recessed into the existing floor; socket depth stays unchanged.',
                                  'SocketBinHoles %s — pocket floors'%VERSION,'0.6')
        if cancel:return
        floor_inlay=float(answer)
        if not math.isfinite(floor_inlay) or floor_inlay<0:raise ValueError('Floor inlay must be a finite non-negative number.')
        if floor_inlay>0 and floor<floor_inlay+0.8:
            cap=max(0.0,round(floor-0.8,3))
            floor_inlay=cap if cap>=0.2 else 0.0
            floor_warnings.append('Thin-floor safety cap: floor_inlay now %g mm.'%floor_inlay)
        fd=ui.createFileDialog();fd.title='Sockets spreadsheet or CSV (SocketBinHoles %s)'%VERSION;fd.filter='Socket lists (*.xlsx;*.csv)'
        if fd.showOpen()!=adsk.core.DialogResults.DialogOK:return
        try:
            sockets,_=core.read_list(fd.filename);p=layout(sockets,L,W,H,margin,base,floor)
        except core.NoFit as e:
            # Human-readable rail/fit error only; keep traceback out of the main dialog.
            ui.messageBox(e.human_message(),'SocketBinHoles %s — will not fit'%VERSION)
            return
        summary=['SocketBinHoles %s'%VERSION]
        summary.extend(p.get('report') or [])
        if p.get('warnings'):
            summary.append('');summary.extend(p['warnings'])
        msg='%d sockets, %d rows; existing %.3f x %.3f x %.3f mm body.\nDeepest hole %.3f mm; floor above base %.3f mm.\n5 mm bold labels, 1 mm flush inlays.\nNo feet or exterior reconstruction.\n\n%s\n\nProceed?'%(len(sockets),len(p['rows']),L,W,H,max(h['depth'] for h in sockets),H-base-max(h['depth'] for h in sockets),'\n'.join(summary))
        if ui.messageBox(msg,'SocketBinHoles %s — add socket holes'%VERSION,adsk.core.MessageBoxButtonTypes.YesNoButtonType)!=adsk.core.DialogResults.DialogYes:return
        stage='solid blank preflight'
        # Reject hollow bins or holes breaking through walls BEFORE creating any features.
        mgr=adsk.fusion.TemporaryBRepManager.get()
        for h in p['holes']:
            if long_y:cx,cy=bb.minPoint.x*10+W-h['y'],bb.minPoint.y*10+h['x']
            else:cx,cy=bb.minPoint.x*10+h['x'],bb.minPoint.y*10+h['y']
            cylinder=mgr.createCylinderOrCone(point(cx,cy,z-h['depth']-floor_inlay),h['d']/20,point(cx,cy,z),h['d']/20)
            probe=mgr.copy(body)
            expected=cylinder.physicalProperties.volume
            if not mgr.booleanOperation(probe,cylinder,adsk.fusion.BooleanTypes.IntersectionBooleanType):
                raise ValueError('Solid-blank preflight failed for '+h['label'])
            if abs(probe.physicalProperties.volume-expected)>max(1e-6,expected*1e-5):
                raise ValueError('Hole '+h['label']+' intersects a cavity or exterior. Supply a solid blank, increase inset, or revise the layout.')
        stage='construction plane' 
        pi=comp.constructionPlanes.createInput();pi.setByOffset(comp.xYConstructionPlane,val(z))
        top=comp.constructionPlanes.add(pi);top.name='SocketBinHoles - top';made.append(top)
        x0=bb.minPoint.x*10;y0=bb.minPoint.y*10
        def model(x,y):return point(x0+W-y,y0+x,z) if long_y else point(x0+x,y0+y,z)
        CUT=adsk.fusion.FeatureOperations.CutFeatureOperation;NEW=adsk.fusion.FeatureOperations.NewBodyFeatureOperation
        for h in p['holes']:
            stage='hole '+h['label']
            sk=comp.sketches.add(top);made.append(sk);sk.name='Socket hole '+h['label']
            c=sk.modelToSketchSpace(model(h['x'],h['y']))
            sk.sketchCurves.sketchCircles.addByCenterRadius(c,h['d']/20)
            f=extrude(comp,sk.profiles.item(0),h['depth'],CUT,body);made.append(f);f.name='Socket %s D%g depth%g'%(h['label'],h['d'],h['depth']);sk.isVisible=False
        # Each disk is below the ORIGINAL pocket floor. Existing negative-direction helper
        # extrudes from that floor downward; NEW never uses participantBodies.
        floors_expected=len(p['holes']) if floor_inlay>0 else 0
        floor_names=[]
        for index,h in enumerate(p['holes']):
            if floor_inlay<=0:break
            stage='pocket floor '+h['label']
            local=[]
            try:
                pi=comp.constructionPlanes.createInput()
                pi.setByOffset(comp.xYConstructionPlane,val(z-h['depth']))
                fp=comp.constructionPlanes.add(pi);local.append(fp)
                fp.name='Socket floor plane %02d'%(index+1)
                fs=comp.sketches.add(fp);local.append(fs)
                centre=model(h['x'],h['y']);centre.z=(z-h['depth'])/10
                c=fs.modelToSketchSpace(centre);c.z=0.0
                fs.sketchCurves.sketchCircles.addByCenterRadius(c,h['d']/20)
                disk=extrude(comp,fs.profiles.item(0),floor_inlay,NEW)
                local.append(disk)
                if disk.bodies.count!=1:raise RuntimeError('Expected exactly one distinct floor body.')
                disk_body=disk.bodies.item(0)
                # Unique body name permits safe current-timeline lookup after subsequent cuts.
                disk_body.name='Socket floor %02d '%(index+1)+uuid.uuid4().hex[:8]
                disk_name=disk_body.name
                ci=comp.features.combineFeatures.createInput(body,collection([disk_body]))
                ci.operation=CUT;ci.isKeepToolBodies=True
                recess=comp.features.combineFeatures.add(ci);local.append(recess)
                recess.name='Socket floor recess %02d'%(index+1)
                floor_names.append(disk_name);floors_created+=1
                fs.isVisible=False;fp.isLightBulbOn=False
                made.extend(local)
            except Exception as e:
                # Undo this recess and tool if any subsequent floor operation failed.
                rollback=[]
                for obj in reversed(local):
                    try:
                        if obj.isValid:obj.deleteMe()
                    except Exception:rollback.append(type(obj).__name__)
                floor_warnings.append('Floor %02d failed: %s'%(index+1,e))
                if rollback:raise RuntimeError('Floor rollback incomplete: '+', '.join(rollback))
        stage='label calibration' 
        sc=comp.sketches.add(top);made.append(sc)
        tx=text(sc,'0123456789',5,0,0)
        cf=extrude(comp,tx,1,NEW);made.append(cf)
        bounds=[cf.bodies.item(i).boundingBox for i in range(cf.bodies.count)]
        ymin=min(b.minPoint.y for b in bounds)*10;ymax=max(b.maxPoint.y for b in bounds)*10
        factor=5/(ymax-ymin);off=ymin*factor
        cf.deleteMe();sc.deleteMe()
        stage='label geometry'
        sk=comp.sketches.add(top);made.append(sk);sk.name='Socket labels - flush white inlays'
        texts=[]
        for h in p['holes']:
            if h['label']:texts.append(text(sk,h['label'],5*factor,h['x'],h['label_y']-off))
        # Transform all text rectangles from planning coordinates into this body's coordinates.
        # No deprecated SketchText.angle API is used.
        rects=[]
        for t in texts:
            rects.extend(list(t.definition.rectangleLines))
        origin=sk.modelToSketchSpace(model(0,0));ex=sk.modelToSketchSpace(model(1,0));ey=sk.modelToSketchSpace(model(0,1))
        vx=origin.vectorTo(ex);vx.normalize();vy=origin.vectorTo(ey);vy.normalize();vz=vx.crossProduct(vy)
        matrix=adsk.core.Matrix3D.create();matrix.setWithCoordinateSystem(origin,vx,vy,vz)
        if rects:sk.move(collection(rects),matrix)
        labels=[]
        for t in texts:
            f=extrude(comp,t,1,NEW);made.append(f)
            labels.extend(f.bodies.item(i) for i in range(f.bodies.count))
        stage='label pockets'
        # One cut, only against the selected original body. Tools remain for white inlays.
        if labels:
            ci=comp.features.combineFeatures.createInput(body,collection(labels));ci.operation=CUT;ci.isKeepToolBodies=True
            f=comp.features.combineFeatures.add(ci);made.append(f);f.name='Flush label pockets - selected bin only'
        for i,b in enumerate(labels):b.name='Labels' if i==0 else 'Labels %02d'%(i+1)
        # Move first, then re-fetch and apply the SAME label appearance at body level.
        stage='Labels component and appearances'
        label_names=[b.name for b in labels]
        occ=None
        if label_names or floor_names:
            try:
                occ=comp.occurrences.addNewComponent(adsk.core.Matrix3D.create())
                made.append(occ);occ.component.name='Labels'
            except Exception as e:
                # Part Design permits only one component. Grouping is optional; never undo
                # successful geometry just because an assembly-only convenience is unavailable.
                occ=None
                floor_warnings.append('Labels kept as separate bodies in existing component (component grouping unavailable: %s)'%e)
            for name in label_names+floor_names:
                try:
                    current=comp.bRepBodies.itemByName(name)
                    if not current:raise RuntimeError('Body not found at current timeline')
                    if occ is not None:
                        moved=current.moveToComponent(occ)
                        if not moved or not moved.isValid:raise RuntimeError('Move returned no valid body')
                except Exception as e:floor_warnings.append('Move %s: %s'%(name,e))
            for name in label_names+floor_names:
                try:
                    current=(occ.component.bRepBodies.itemByName(name) if occ else None) or comp.bRepBodies.itemByName(name)
                    if not current:raise RuntimeError('Body missing after move')
                    white(design,[current])
                    if not current.appearance:raise RuntimeError('Body appearance override missing')
                    if name in floor_names:floors_colored+=1
                except Exception as e:floor_warnings.append('Appearance %s: %s'%(name,e))
        sk.isVisible=False;top.isLightBulbOn=False
        status='Pocket floors: %d expected / %d created / %d colored.'%(floors_expected,floors_created,floors_colored)
        if floors_created!=floors_expected or floors_colored!=floors_expected:status='WARNING — '+status
        ui.messageBox(status+'\n\nSocketBinHoles %s\nDone: %d holes and %d separate label solids.\nExport bin plus ALL Labels and Socket floor bodies together as one multi-part 3MF; assign Labels and Socket floor parts to the same label filament.\nOriginal feet/exterior retained. Save as a new design.\nNot print-tested.'%(VERSION,len(p['holes']),len(labels))+
                      ('\n\nWARNINGS:\n'+'\n'.join(floor_warnings) if floor_warnings else ''))
    except core.NoFit as e:
        # Setup-stage NoFit should already have returned; this covers any later raise + rollback.
        fail=[]
        for obj in reversed(made):
            try:
                if obj.isValid:obj.deleteMe()
            except Exception:fail.append(type(obj).__name__)
        extra=('\n\nRollback incomplete: '+', '.join(fail)+'. Close WITHOUT saving and reopen your saved copy.') if fail else ''
        ui.messageBox(e.human_message()+extra,'SocketBinHoles %s — will not fit'%VERSION)
    except Exception:
        detail=traceback.format_exc();fail=[]
        for obj in reversed(made):
            try:
                if obj.isValid:obj.deleteMe()
            except Exception:fail.append(type(obj).__name__)
        ui.messageBox('Pocket floors: %d expected / %d created / %d colored (run failed; rollback attempted).\n'%(floors_expected,floors_created,floors_colored)+'SocketBinHoles %s failed at '%VERSION+stage+'\n'+detail+'\nAttempted rollback of this run only.'+('\nRollback incomplete: '+', '.join(fail)+'. Close WITHOUT saving and reopen your saved copy.' if fail else ''),
                      'SocketBinHoles %s — error'%VERSION)
