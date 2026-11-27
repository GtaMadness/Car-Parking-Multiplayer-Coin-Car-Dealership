import pandas as pd,numpy as np
res=pd.read_pickle('enriched.pkl'); names=list(res)
MARGIN=27.0  # $ margin for 0.01 lot gold at 1:200 (HMR worst case) at ~$5,400
def sim(e,start,risk,order=None):
    pnl=e.pnl1.values; sl=e.sl1.values; mae=e.mae1.values
    idx=np.arange(len(e)) if order is None else order
    bal=start; peak=start; maxdd=0; minlot=0
    for i in idx:
        if risk is None: u=1
        else:
            u=int(bal*risk/sl[i])
            if u<1: u=1; minlot+=1
        if bal<MARGIN*u*0.2 or bal<=0: return dict(final=bal,ruined=True,maxdd=1.0,minlot=minlot)
        low=bal-u*mae[i]
        if low<=0: return dict(final=0,ruined=True,maxdd=1.0,minlot=minlot)
        maxdd=max(maxdd,(peak-low)/peak)
        bal+=u*pnl[i]; peak=max(peak,bal); maxdd=max(maxdd,(peak-bal)/peak)
    return dict(final=bal,ruined=False,maxdd=maxdd,minlot=minlot)
rng=np.random.default_rng(7); rows=[]
for k in names:
    e=res[k]; orders=[rng.permutation(len(e)) for _ in range(3000)]
    for start in [100,150,200,300,500,1000,2000]:
        for risk in [None,0.01,0.02,0.03,0.05]:
            a=sim(e,start,risk); mc=[sim(e,start,risk,o) for o in orders]
            ruin=np.mean([x['ruined'] for x in mc]); dd=np.array([x['maxdd'] for x in mc]); fin=np.array([x['final'] for x in mc])
            rows.append(dict(setup='V2' if 'Aggressive' not in k else 'V2 Aggressive',start=start,sizing='Fixed 0.01 lot' if risk is None else f'{int(risk*100)}% risk/trade (compounding)',
              actual_final=round(a['final'],2),actual_return=f"{a['final']/start-1:.0%}",actual_maxdd=f"{a['maxdd']:.0%}",ruined_actual=a['ruined'],
              trades_forced_to_min_lot=a['minlot'],chance_of_blowup=f"{ruin:.1%}",median_maxdd_shuffled=f"{np.median(dd):.0%}",worst5pct_maxdd=f"{np.percentile(dd,95):.0%}",median_final_shuffled=round(np.median(fin),2)))
r=pd.DataFrame(rows); r.to_pickle('sizing.pkl')
pd.set_option('display.width',250); pd.set_option('display.max_columns',20)
print(r.to_string())
