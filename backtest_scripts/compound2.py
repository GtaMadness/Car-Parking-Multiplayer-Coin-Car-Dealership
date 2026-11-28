import pandas as pd,numpy as np,json
t=pd.DataFrame(json.load(open('v2_trades_gap.json')))
P=t.pnl.values; SL=t.sl_pips.values*0.1; MAE=-t.worst_float.values; MARGIN=27.0
def sim(r,brake,p,sl,mae,start):
    bal=start; peak=start; mdd=0
    for i in range(len(p)):
        rr=r*(0.5 if brake and (peak-bal)/peak>0.15 else 1)
        u=1 if r==0 else max(1,int(bal*rr/sl[i]))
        if bal<MARGIN*u*0.2 or bal-u*mae[i]<=0: return 0.0,1.0,True
        mdd=max(mdd,(peak-(bal-u*mae[i]))/peak); bal+=u*p[i]; peak=max(peak,bal); mdd=max(mdd,(peak-bal)/peak)
    return bal,mdd,False
rng=np.random.default_rng(7); N=3000
B=[rng.integers(0,len(t),170) for _ in range(N)]
rs=np.random.default_rng(3); FL=[rs.random(170)<0.125 for _ in range(N)]
rows=[]
for start in [500,1000]:
  for r in [0,0.02,0.03,0.04,0.05,0.06,0.08]:
    for brake in ([False,True] if r else [False]):
      a=sim(r,brake,P,SL,MAE,start)
      res=[];resw=[]
      for ix,fl in zip(B,FL):
          p=P[ix]; sl=SL[ix]; mae=MAE[ix]
          res.append(sim(r,brake,p,sl,mae,start))
          p2=p.copy(); m2=mae.copy(); f=(p2>0)&fl; p2[f]=-sl[f]; m2[f]=sl[f]; resw.append(sim(r,brake,p2,sl,m2,start))
      f=np.array([x[0] for x in res]); d=np.array([x[1] for x in res]); fw=np.array([x[0] for x in resw]); dw=np.array([x[1] for x in resw])
      rows.append(dict(start=start,rule='Fixed 0.01' if r==0 else f"Risk {r*100:g}%"+(' + halve after 15% DD' if brake else ''),
        actual_final=round(a[0]),actual_dd=f"{a[1]:.0%}",median_3y=round(np.median(f)),p5_3y=round(np.percentile(f,5)),dd_med=f"{np.median(d):.0%}",dd_p95=f"{np.percentile(d,95):.0%}",
        weak_ruin=f"{np.mean([x[2] for x in resw]):.1%}",weak_median=round(np.median(fw)),weak_below_start=f"{(fw<start).mean():.0%}",weak_dd_p95=f"{np.percentile(dw,95):.0%}"))
R=pd.DataFrame(rows); R.to_pickle('compound2.pkl')
pd.set_option('display.width',300); pd.set_option('display.max_columns',30); print(R.to_string(index=False))
