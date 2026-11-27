import pandas as pd,numpy as np
m=pd.read_pickle('m1.pkl'); T=m.t.values; H=m.high.values; L=m.low.values; C=m.close.values; SP=m.spread.values*0.001; DAY=m.day.values
allt=pd.read_pickle('final_trades.pkl'); V=[t for t in allt[[k for k in allt if k.startswith('V2:')][0]]]
CUT=np.datetime64('2026-05-01')
def replay(t,be=None,partial=None,part_frac=0.5,tp_mult=None,trail=None,time_stop=None):
    sd=t['side']; e=t['entry']; R=t['dist']; sl=t['sl']; tp=t['tp'] if tp_mult is None else (t['H'] if sd==1 else t['L'])+sd*R*tp_mult
    i=np.searchsorted(T,t['et']); size=1.0; pnl=0.0; moved=False; took=False; best=0
    for k in range(i,len(T)):
        sp=SP[k]
        hi=H[k] if sd==1 else H[k]+sp; lo=L[k] if sd==1 else L[k]+sp
        fav=(hi-e) if sd==1 else (e-lo)
        adv_hit = lo<=sl if sd==1 else hi>=sl
        tp_hit = hi>=tp if sd==1 else lo<=tp
        part_px = e+sd*partial*R if partial else None
        part_hit = partial and not took and ((hi>=part_px) if sd==1 else (lo<=part_px))
        if adv_hit and not (k==i and False):
            # conservative: stop checked before targets in the same bar
            pnl+=size*(sl-e)*sd; return pnl,('BE' if moved and abs(sl-e)<1e-9 else 'SL')
        if part_hit:
            pnl+=size*part_frac*partial*R; size*=(1-part_frac); took=True; sl=e; moved=True
        if tp_hit:
            pnl+=size*(tp-e)*sd; return pnl,'TP'
        best=max(best,fav)
        if be and not moved and fav>=be*R: sl=e; moved=True
        if trail and best>=trail*R:
            nsl=e+sd*(best-trail*R)
            if (sd==1 and nsl>sl) or (sd==-1 and nsl<sl): sl=nsl; moved=True
        if time_stop and (T[k]-t['et'])>=np.timedelta64(time_stop,'h'):
            px=C[k]+(sp if sd==-1 else 0); pnl+=size*(px-e)*sd; return pnl,'TIME'
    return pnl,'OPEN'
def evalv(**kw):
    out=[(replay(t,**kw),t['et']) for t in V]
    p=np.array([o[0][0] for o in out]); et=np.array([o[1] for o in out])
    eq=np.cumsum(p); dd=(np.maximum.accumulate(np.r_[0,eq])[1:]-eq).max()
    g=p[p>0].sum(); l=-p[p<0].sum()
    return dict(net=round(p.sum(),1),win=round((p>0).mean(),2),pf=round(g/l,2),maxdd=round(dd,1),A=round(p[et<CUT].sum(),1),B=round(p[et>=CUT].sum(),1))
tests={'V2 as is':{},'Breakeven at +0.5R':dict(be=0.5),'Breakeven at +0.75R':dict(be=0.75),'Breakeven at +1R':dict(be=1.0),
 'Close half at +0.5R, rest to TP (SL to entry)':dict(partial=0.5),'Close half at +0.75R':dict(partial=0.75),'Close half at +1R':dict(partial=1.0),
 'Trail 0.75R behind best':dict(trail=0.75),'Trail 1R behind best':dict(trail=1.0),
 'TP 1.0x':dict(tp_mult=1.0),'TP 1.5x':dict(tp_mult=1.5),'TP 2x':dict(tp_mult=2.0),'TP 2x + half off at 1R':dict(tp_mult=2.0,partial=1.0),
 'Time stop 4h':dict(time_stop=4),'Time stop 8h':dict(time_stop=8)}
r=pd.DataFrame({k:evalv(**v) for k,v in tests.items()}).T; print(r.to_string())
