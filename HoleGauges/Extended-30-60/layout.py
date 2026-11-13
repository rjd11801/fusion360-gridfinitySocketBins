import functools
GAP=1.5; LANE=5.8; TUBE=4.0
def row_ok(ds,W):
    return sum(d+TUBE for d in ds)+GAP*(len(ds)-1)<=W+1e-9
def row_h(ds): return max(d+TUBE for d in ds)+LANE
def best_plate(sizes,W=196.0,H=196.0):
    """max holes (prefix of sizes) that fit on a plate, with row partition minimizing height"""
    n=len(sizes)
    best=None
    for k in range(n,0,-1):
        s=sizes[:k]
        # DP min height
        @functools.lru_cache(None)
        def f(i):
            if i==k: return (0.0,())
            r=(1e9,())
            for j in range(i+1,k+1):
                if not row_ok(s[i:j],W): break
                h=row_h(s[i:j]); sub=f(j)
                if h+sub[0]<r[0]: r=(h+sub[0],((i,j),)+sub[1])
            return r
        h,rows=f(0)
        if h<=H+1e-9: return k,h,rows
    return 0,0,()
def plan(sizes,W=196.0,H=196.0):
    out=[];rest=list(sizes)
    while rest:
        k,h,rows=best_plate(rest,W,H)
        if k==0: raise SystemExit('too big %s'%rest[0])
        out.append((rest[:k],h,[rest[i:j] for i,j in rows])); rest=rest[k:]
    return out
if __name__=='__main__':
    import sys
    W=float(sys.argv[1]) if len(sys.argv)>1 else 196
    sizes=[30+0.5*i for i in range(61)]
    for p,h,rows in plan(sizes,W,W):
        print(len(p),p[0],p[-1],round(h,1),[ (r[0],r[-1]) for r in rows])
