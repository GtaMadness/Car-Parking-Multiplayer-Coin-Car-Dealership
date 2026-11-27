import pandas as pd, numpy as np
from news import events, regime
PIP=0.1
class BT:
    def __init__(self):
        df=pd.read_pickle('m1.pkl'); daily=pd.read_pickle('daily.pkl')
        daily['sma20']=daily.close.rolling(20).mean(); daily['sma50']=daily.close.rolling(50).mean()
        self.daily=daily; self.days=list(daily.index); self.dpos={k:i for i,k in enumerate(self.days)}
        self.T=df.t.values; self.DAY=df.day.values; self.O=df.open.values; self.H=df.high.values; self.L=df.low.values; self.C=df.close.values
        self.SP=df.spread.values*0.001; self.HR=df.t.dt.hour.values
        ev=events(); self.ev=ev
        self.newsday={}; [self.newsday.setdefault(np.datetime64(r.day),[]).append((r.event,np.datetime64(r.time_gmt2))) for r in ev.itertuples()]
    def run(self,start='2025-08-01',end=None,pct=0.30,rr=1.5,expiry='day',flt='contract',news='none',hours=None,be=None,eod=False,trend=None,news_wait=15):
        D=self.daily; T,DAY,O,H,L,C,SP,HR=self.T,self.DAY,self.O,self.H,self.L,self.C,self.SP,self.HR
        s=np.searchsorted(DAY,np.datetime64(pd.Timestamp(start))); e=len(DAY) if end is None else np.searchsorted(DAY,np.datetime64(pd.Timestamp(end)),'right')
        trades=[]; pend=None; pos=None; prev=None; active_from=None
        for i in range(s,e):
            dd=DAY[i]
            if dd!=prev:
                if eod and pos is not None and prev is not None:   # close at previous bar close
                    px=C[i-1]+(SP[i-1] if pos['side']==-1 else 0); pnl=(px-pos['entry'])*pos['side']
                    trades.append(dict(pos,xt=T[i-1],exit=px,result='EOD',pnl=pnl)); pos=None
                prev=dd
                if expiry=='day': pend=None
                nd=self.newsday.get(dd,[])
                active_from=None
                if news=='skip_day' and nd: pend=None
                if pend is None and pos is None and self.dpos.get(pd.Timestamp(dd),0)>0:
                    k=self.dpos[pd.Timestamp(dd)]; p=D.iloc[k-1]
                    ok=not np.isnan(p.atr14)
                    if flt in('contract','contract+trend') and not p['range']<p.atr14: ok=False
                    if news=='skip_day' and nd: ok=False
                    if news=='skip_ref' and self.newsday.get(np.datetime64(p.name)): ok=False
                    ab=as_=True
                    tr=trend or ('sma20' if flt=='contract+trend' else None)
                    if tr: ab=p.close>p[tr]; as_=not ab
                    if ok:
                        pend=dict(placed=pd.Timestamp(dd),ref=p.name,H=p.high,L=p.low,rng=p['range'],atr=p.atr14,dist=pct*p['range'],ab=ab,as_=as_,
                                  ref_news=','.join(x[0] for x in self.newsday.get(np.datetime64(p.name),[])),day_news=','.join(x[0] for x in nd))
                        if news=='after' and nd: active_from=max(x[1] for x in nd)+np.timedelta64(news_wait,'m')
            sp=SP[i]
            if pend is not None and pos is None:
                act=True
                if active_from is not None and T[i]<active_from: act=False
                if hours and not(hours[0]<=HR[i]<hours[1]): act=False
                if act:
                    b=pend['ab'] and H[i]+sp>=pend['H']; s_=pend['as_'] and L[i]<=pend['L']
                    if b and s_: b=(pend['H']-(O[i]+sp))<=(O[i]-pend['L']); s_=not b
                    if b or s_:
                        if b: en=max(pend['H'],O[i]+sp); sl=pend['H']-pend['dist']; tp=pend['H']+pend['dist']*rr; sd=1
                        else: en=min(pend['L'],O[i]); sl=pend['L']+pend['dist']; tp=pend['L']-pend['dist']*rr; sd=-1
                        pos=dict(pend,side=sd,entry=en,sl=sl,tp=tp,et=T[i],hour=HR[i],moved=False); pend=None
            if pos is not None:
                if pos['side']==1: htp=H[i]>=pos['tp']; hsl=L[i]<=pos['sl']; fav=H[i]-pos['entry']
                else: htp=L[i]+sp<=pos['tp']; hsl=H[i]+sp>=pos['sl']; fav=pos['entry']-(L[i]+sp)
                if htp or hsl:
                    win=htp and not hsl; px=pos['tp'] if win else pos['sl']; pnl=(px-pos['entry'])*pos['side']
                    trades.append(dict(pos,xt=T[i],exit=px,result='TP' if win else ('BE' if pos['moved'] else 'SL'),pnl=pnl)); pos=None
                elif be and not pos['moved'] and fav>=be*pos['dist']:
                    pos['sl']=pos['entry']; pos['moved']=True
        return trades
def stats(tr):
    if not tr: return dict(n=0,winrate=0,net=0,pf=0,maxdd=0)
    p=np.array([t['pnl'] for t in tr]); eq=np.cumsum(p); dd=(np.maximum.accumulate(np.r_[0,eq])[1:]-eq).max()
    g=p[p>0].sum(); l=-p[p<0].sum()
    return dict(n=len(p),winrate=round((p>0).mean(),3),net=round(p.sum(),2),pf=round(g/l,2) if l else 99,maxdd=round(dd,2))
