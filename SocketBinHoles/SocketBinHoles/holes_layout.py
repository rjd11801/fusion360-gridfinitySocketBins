"""Pure-Python measured-footprint adapter; mm throughout. Does not silently shorten holes.

Walls / version policy live in socketbin_core (VERSION, ADAPTIVE_WALLS).
"""
import math
import socketbin_core as core

def layout(sockets, length, width, height, margin=1., base_height=5., floor=3.):
    if min(length,width,height)>0 and 0<=margin<min(length,width)/2 and base_height>=0 and floor>0:
        pass
    else: raise ValueError('Invalid dimensions, margin, base height or floor.')
    limit=height-base_height-floor
    deep=[s for s in sockets if s['depth']>limit+1e-7]
    if deep:
        needed=max(s['depth'] for s in sockets)+base_height+floor
        raise ValueError('Bin too short: maximum safe depth %.3f mm. Required overall height %.3f mm. No depths were shortened.'%(limit,needed))
    # core.pack uses 42*pitch - 0.5: fractional counts here deliberately represent
    # the EXACT usable rectangle, not an invented replacement Gridfinity footprint.
    p=core.plan(sockets,grid_x=(length-2*margin+.5)/42,
                grid_y=(width-2*margin+.5)/42,height_units=math.ceil(height/7))
    for h in p['holes']:
        h['x']+=margin;h['y']+=margin;h['label_y']+=margin;h['cut']=h['depth']
    p.update(L=length,W=width,H=height,top_z=height,hu=None)
    p['report']=['Measured source: %.3f x %.3f x %.3f mm; usable rectangle inset %.3f mm.'%(length,width,height,margin)]
    p['warnings']=[w for w in p['warnings'] if 'limited to' not in w]
    return p
