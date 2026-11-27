import pandas as pd, itertools, numpy as np
from engine import *
df,daily=load()
S=pd.Timestamp('2026-05-27'); IS_END=pd.Timestamp('2026-09-30'); OOS=pd.Timestamp('2026-10-01')
rows=[]
for pct,rr,exp,flt,basis,fade in itertools.product([0.05,0.10,0.15,0.20,0.30],[0.5,1,1.5,2],['keep','day'],['none','trend','contract','expand'],['range','atr'],[False,True]):
    tr=run(df,daily,S,pct=pct,rr=rr,expiry=exp,flt=flt,basis=basis,fade=fade)
    a=stats([t for t in tr if t['et']<=np.datetime64(IS_END+pd.Timedelta(days=1))]); b=stats([t for t in tr if t['et']>=np.datetime64(OOS)]); f=stats(tr)
    rows.append(dict(direction='Fade' if fade else 'Breakout',sl_pct=pct,sl_basis=basis,rr=rr,orders=exp,filter=flt,
        trades=f['n'],winrate=f['winrate'],net=f['net'],pf=f['pf'],maxdd=f['maxdd'],
        is_trades=a['n'],is_net=a['net'],is_pf=a['pf'],oos_trades=b['n'],oos_net=b['net'],oos_pf=b['pf']))
g=pd.DataFrame(rows); g.to_pickle('grid.pkl')
print(len(g))
