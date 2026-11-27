import pandas as pd,numpy as np
allt=pd.read_pickle('final_trades.pkl'); names=list(allt)
m=pd.read_pickle('m1.pkl'); T=m.t.values; H=m.high.values; L=m.low.values; SP=m.spread.values*0.001
LEV_HMR=200   # Exness caps leverage around news/weekends; use 1:200 as a safe worst case for margin
def enrich(tr):
    out=[]
    for t in tr:
        a=np.searchsorted(T,t['et']); b=np.searchsorted(T,t['xt'])+1
        if t['side']==1: mae=t['entry']-L[a:b].min()
        else: mae=(H[a:b]+SP[a:b]).max()-t['entry']
        out.append(dict(et=pd.Timestamp(t['et']),xt=pd.Timestamp(t['xt']),pnl1=t['pnl'],sl1=t['dist'],mae1=max(mae,0),price=t['entry']))
    return pd.DataFrame(out)
res={}
for k in names[2:]:
    e=enrich(allt[k]); res[k]=e
    # fixed 0.01 lot: lowest equity relative to start including worst floating loss inside each trade
    bal=0; low=0
    for r in e.itertuples(): low=min(low,bal-r.mae1); bal+=r.pnl1; low=min(low,bal)
    print(k,'| fixed 0.01: worst dip below start $%.2f, largest single SL $%.2f, max margin 0.01 lot @1:200 $%.2f'%(low,e.sl1.max(),e.price.max()/LEV_HMR))
pd.to_pickle(res,'enriched.pkl')
