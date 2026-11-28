import pandas as pd,numpy as np,json
t=pd.DataFrame(json.load(open('v2_trades_gap.json')))
P=t.pnl.values; SL=(t.sl_pips.values*0.1); MAE=-t.worst_float.values   # per 0.01 lot, in $
P_loss_cap=np.minimum(P,0)
START=500.0; MARGIN=27.0
print('trades',len(t),'SL $ per 0.01: median',np.median(SL).round(1),'max',SL.max().round(1))
def units(rule,bal,sl):
    kind,x=rule
    if kind=='fixed': return 1
    if kind=='step': return max(1,int(bal//x))
    if kind=='risk': return max(1,int(bal*x/sl))
def sim(rule,p,sl,mae,start=START):
    bal=start; peak=start; mdd=0
    for i in range(len(p)):
        u=units(rule,bal,sl[i])
        if bal<MARGIN*u*0.2: return bal,1.0,True
        low=bal-u*mae[i]
        if low<=0: return 0.0,1.0,True
        mdd=max(mdd,(peak-low)/peak); bal+=u*p[i]; peak=max(peak,bal); mdd=max(mdd,(peak-bal)/peak)
        if bal<=0: return 0.0,1.0,True
    return bal,mdd,False
rules=[('fixed',0)]+[('step',x) for x in [100,150,200,250,300,400,500,750,1000]]+[('risk',x) for x in [0.01,0.015,0.02,0.03,0.05]]
name=lambda r:'Fixed 0.01' if r[0]=='fixed' else (f"+0.01 per ${r[1]}" if r[0]=='step' else f"Risk {r[1]*100:g}% per trade")
rng=np.random.default_rng(42); N=4000
def boots(n):  # bootstrap trade sequences (sampling trades with replacement)
    return [rng.integers(0,len(t),n) for _ in range(N)]
B16=boots(len(t)); B3y=boots(170)
# stressed edge: 1 in 8 wins becomes a full loss (win rate ~60% -> ~52%)
pS=P.copy(); wins=np.where(P>0)[0]; rs=np.random.default_rng(1)
rows=[]
for r in rules:
    a=sim(r,P,SL,MAE)
    def mc(idx,stress=False):
        out=[]
        for ix in idx:
            p=P[ix].copy(); sl=SL[ix]; mae=MAE[ix].copy()
            if stress:
                flip=(p>0)&(rs.random(len(p))<0.125); p[flip]=-sl[flip]; mae[flip]=sl[flip]
            out.append(sim(r,p,sl,mae))
        f=np.array([o[0] for o in out]); d=np.array([o[1] for o in out]); ru=np.array([o[2] for o in out])
        return f,d,ru
    f16,d16,r16=mc(B16); f3,d3,r3=mc(B3y); fs,ds,rs_=mc(B3y,stress=True)
    rows.append(dict(rule=name(r),actual_final=round(a[0],0),actual_maxdd=f"{a[1]:.0%}",
      ruin_16m=f"{r16.mean():.1%}",median_16m=round(np.median(f16)),p5_16m=round(np.percentile(f16,5)),dd_med_16m=f"{np.median(d16):.0%}",dd_p95_16m=f"{np.percentile(d16,95):.0%}",
      ruin_3y=f"{r3.mean():.1%}",median_3y=round(np.median(f3)),p5_3y=round(np.percentile(f3,5)),dd_p95_3y=f"{np.percentile(d3,95):.0%}",
      ruin_3y_weaker=f"{rs_.mean():.1%}",median_3y_weaker=round(np.median(fs)),p5_3y_weaker=round(np.percentile(fs,5)),below_start_weaker=f"{(fs<START).mean():.0%}",dd_p95_weaker=f"{np.percentile(ds,95):.0%}"))
R=pd.DataFrame(rows); R.to_pickle('compound.pkl')
pd.set_option('display.width',300); pd.set_option('display.max_columns',30); print(R.to_string(index=False))
