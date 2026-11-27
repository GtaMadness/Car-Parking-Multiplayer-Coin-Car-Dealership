import itertools, pandas as pd, numpy as np
from multiprocessing import Pool
from engine2 import BT, stats
CUT=np.datetime64('2026-05-01')
bt=None
def init():
    global bt; bt=BT()
def job(c):
    pct,rr,flt,trend,news,hours,be=c
    tr=bt.run(pct=pct,rr=rr,flt=flt,trend=trend,news=news,hours=hours,be=be)
    a=stats([t for t in tr if t['et']<CUT]); b=stats([t for t in tr if t['et']>=CUT]); f=stats(tr)
    return dict(sl_pct=pct,rr=rr,filter=flt,trend=trend or 'none',news=news,hours='all' if not hours else f'{hours[0]:02d}-{hours[1]:02d}',be='none' if be is None else f'{be}R',
        trades=f['n'],winrate=f['winrate'],net=f['net'],pf=f['pf'],maxdd=f['maxdd'],is_n=a['n'],is_net=a['net'],is_pf=a['pf'],oos_n=b['n'],oos_net=b['net'],oos_pf=b['pf'])
if __name__=='__main__':
    combos=list(itertools.product([0.2,0.3,0.4],[1,1.25,1.5,2],['none','contract'],[None,'sma20','sma50'],['none','skip_day','after'],[None,(8,24),(10,24),(14,24)],[None,1.0]))
    with Pool(initializer=init) as p: rows=p.map(job,combos,chunksize=8)
    pd.DataFrame(rows).to_pickle('grid2.pkl'); print(len(rows))
