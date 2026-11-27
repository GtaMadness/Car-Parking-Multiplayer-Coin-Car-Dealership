import pandas as pd,numpy as np
from news import events
m=pd.read_pickle('m1.pkl').set_index('t'); d=pd.read_pickle('daily.pkl'); ev=events()
def run(slk,rr):
    out=[]
    for e in ev.itertuples():
        prior=d.atr14[d.index<e.day].dropna()
        if prior.empty: continue
        t0=e.time_gmt2; w=m.loc[t0-pd.Timedelta(minutes=1):t0+pd.Timedelta(minutes=15)]
        if len(w)<10: continue
        p0=w.open.iloc[0]; en=w.close.iloc[-1]; sd=np.sign(en-p0)
        if sd==0: continue
        dist=slk*prior.iloc[-1]; sp=w.spread.iloc[-1]*0.001
        if sd>0: en+=sp
        sl=en-sd*dist; tp=en+sd*dist*rr
        f=m.loc[t0+pd.Timedelta(minutes=16):t0+pd.Timedelta(hours=4)]; pnl=None; res='4h'
        for b in f.itertuples():
            s2=b.spread*0.001 if sd<0 else 0
            hsl= b.low<=sl if sd>0 else b.high+s2>=sl; htp= b.high>=tp if sd>0 else b.low+s2<=tp
            if hsl: pnl=-dist; res='SL'; break
            if htp: pnl=dist*rr; res='TP'; break
        if pnl is None: pnl=sd*((f.close.iloc[-1]+(f.spread.iloc[-1]*0.001 if sd<0 else 0))-en)
        out.append(dict(day=e.day.date(),event=e.event,side='BUY' if sd>0 else 'SELL',entry_time=t0+pd.Timedelta(minutes=15),entry=round(en,3),sl=round(sl,3),tp=round(tp,3),result=res,pips=round(pnl/0.1,1),pnl=round(pnl,2)))
    return pd.DataFrame(out)
if __name__=='__main__':
    for slk in [0.15,0.25,0.35]:
      for rr in [1,1.5,2]:
        o=run(slk,rr); a=o[o.day<pd.Timestamp('2026-05-01').date()].pnl.sum(); b=o[o.day>=pd.Timestamp('2026-05-01').date()].pnl.sum()
        print(slk,rr,len(o),f"win {(o.pnl>0).mean():.2f} net {o.pnl.sum():.0f}  IS {a:.0f} OOS {b:.0f}")
