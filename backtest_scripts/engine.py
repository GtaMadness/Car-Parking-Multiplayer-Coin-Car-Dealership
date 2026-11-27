import pandas as pd, numpy as np
F="/root/.claude/uploads/774ef45d-4365-5229-b5a1-a50c4a714ed8/6badc50d-XAUUSDm_M1_202601012305_202611270038.csv"
def load():
    df=pd.read_csv(F,sep='\t'); df.columns=[c.strip('<>').lower() for c in df.columns]
    df['t']=pd.to_datetime(df.date+' '+df.time,format='%Y.%m.%d %H:%M:%S')+pd.Timedelta(hours=2)
    df['day']=df.t.dt.normalize()
    daily=df.groupby('day').agg(open=('open','first'),high=('high','max'),low=('low','min'),close=('close','last'),bars=('open','size'))
    daily=daily[daily.bars>=60]  # drop stub sessions
    pc=daily.close.shift(1)
    daily['tr']=np.maximum(daily.high-daily.low,np.maximum((daily.high-pc).abs(),(daily.low-pc).abs()))
    daily['atr14']=daily.tr.rolling(14).mean()          # MT5 ATR = simple average of TR
    daily['sma20']=daily.close.rolling(20).mean()
    daily['range']=daily.high-daily.low
    return df,daily

def run(df,daily,start,end=None,pct=0.10,rr=1.0,expiry='keep',flt='none',basis='range',buffer=0.0,spread=True,fade=False):
    """Returns list of trades. Levels from previous completed day.
    expiry: 'keep' = orders stay until triggered (user rule); 'day' = cancel at day end, re-place from new prev day.
    flt: none | trend (only trade in direction of prev close vs SMA20) | contract (prev range < ATR14) | expand (prev range > ATR14)
    basis: SL distance = pct*prev range ('range') or pct*ATR14 ('atr')."""
    m=(df.day>=start)&((df.day<=end) if end is not None else True)
    d=df[m]
    T=d.t.values; DAY=d.day.values; O=d.open.values; H=d.high.values; L=d.low.values; C=d.close.values
    SP=d.spread.values*0.001 if spread else np.zeros(len(d))
    days=list(daily.index); dpos={k:i for i,k in enumerate(days)}
    trades=[]; pend=None; pos=None; prevday=None
    for i in range(len(d)):
        dd=DAY[i]
        newday = dd!=prevday; prevday=dd
        if newday:
            if expiry=='day' and pend is not None: pend=None
            if pend is None and pos is None and dd in dpos and dpos[dd]>0:
                p=daily.iloc[dpos[dd]-1]
                if not np.isnan(p.atr14):
                    dist=pct*(p['range'] if basis=='range' else p.atr14)
                    allow_buy=allow_sell=True
                    if flt=='trend': allow_buy=p.close>p.sma20; allow_sell=not allow_buy
                    elif flt=='contract' and not p['range']<p.atr14: allow_buy=allow_sell=False
                    elif flt=='expand' and not p['range']>p.atr14: allow_buy=allow_sell=False
                    if allow_buy or allow_sell:
                        pend=dict(placed=pd.Timestamp(dd),ref=p.name,H=p.high+buffer,L=p.low-buffer,rng=p['range'],atr=p.atr14,dist=dist,ab=allow_buy,as_=allow_sell)
        sp=SP[i]
        if pend is not None and pos is None:
            b= pend['ab'] and H[i]+sp>=pend['H']; s= pend['as_'] and L[i]<=pend['L']
            if b and s: b=(pend['H']-(O[i]+sp))<=(O[i]-pend['L']); s=not b
            if b or s:
                if b: e=max(pend['H'],O[i]+sp); sl=pend['H']-pend['dist']; tp=pend['H']+pend['dist']*rr; side=1
                else: e=min(pend['L'],O[i]); sl=pend['L']+pend['dist']; tp=pend['L']-pend['dist']*rr; side=-1
                if fade:  # trade against the breakout: same distances, reversed direction (sell at the high, buy at the low)
                    side=-side; e=pend['H'] if side==-1 else pend['L']
                    lvl=e; sl=lvl-side*pend['dist']; tp=lvl+side*pend['dist']*rr
                    if side==1: e=e+sp  # buying at the low fills on ask
                pos=dict(pend,side=side,entry=e,sl=sl,tp=tp,et=T[i]); pend=None
        if pos is not None:
            if pos['side']==1: htp=H[i]>=pos['tp']; hsl=L[i]<=pos['sl']
            else: htp=L[i]+sp<=pos['tp']; hsl=H[i]+sp>=pos['sl']
            if htp or hsl:
                win=htp and not hsl; px=pos['tp'] if win else pos['sl']
                pnl=(px-pos['entry'])*pos['side']
                trades.append(dict(pos,xt=T[i],exit=px,result='TP' if win else 'SL',pnl=pnl,amb=htp and hsl)); pos=None
    return trades

def stats(tr):
    if not tr: return dict(n=0,wins=0,winrate=0,net=0,pf=0,maxdd=0,avg=0)
    p=np.array([t['pnl'] for t in tr]); eq=np.cumsum(p); dd=(np.maximum.accumulate(np.r_[0,eq])[1:]-eq).max()
    g=p[p>0].sum(); l=-p[p<0].sum()
    return dict(n=len(p),wins=int((p>0).sum()),winrate=(p>0).mean(),net=p.sum(),pf=g/l if l else np.inf,maxdd=dd,avg=p.mean())
