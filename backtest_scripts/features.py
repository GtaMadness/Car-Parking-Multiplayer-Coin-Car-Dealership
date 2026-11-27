import pandas as pd,numpy as np
from engine2 import BT
from news import events
bt=BT(); D=bt.daily.copy()
m=pd.read_pickle('m1.pkl'); T=m.t.values; O=m.open.values; H=m.high.values; L=m.low.values; C=m.close.values; V=m.tickvol.values; SP=m.spread.values*0.001
# daily indicators (all known at previous close)
D['body']=(D.close-D.open)/D['range']; D['clv']=(D.close-D.low)/D['range']
delta=D.close.diff(); up=delta.clip(lower=0).rolling(14).mean(); dn=(-delta.clip(upper=0)).rolling(14).mean(); D['rsi14']=100-100/(1+up/dn)
D['atr50']=D.tr.rolling(50).mean(); D['atr_ratio']=D.atr14/D.atr50
D['sma20_slope']=(D.sma20-D.sma20.shift(5))/D.atr14
D['dist_sma20']=(D.close-D.sma20)/D.atr14
D['nr7']=(D['range']<=D['range'].rolling(7).min()).astype(int)
D['inside']=((D.high<D.high.shift(1))&(D.low>D.low.shift(1))).astype(int)
D['ret5']=(D.close-D.close.shift(5))/D.atr14
D['ema50']=D.close.ewm(span=50).mean(); D['above_ema50']=(D.close>D.ema50).astype(int)
dpos={k:i for i,k in enumerate(D.index)}
evdays=set(pd.Timestamp(x).normalize() for x in events().day)
def feats(t):
    sd=t['side']; ref=t['ref']; day=pd.Timestamp(t['placed']); p=D.loc[ref]
    i=np.searchsorted(T,t['et']); d0=np.searchsorted(T,np.datetime64(day))
    f={}
    f['side']=sd
    f['dir_prev_candle']=np.sign(p.close-p.open)*sd            # +1 = previous candle points the trade's way
    f['prev_body']=p.body*sd; f['prev_clv']=(p.clv if sd==1 else 1-p.clv)   # 1 = closed at the level we break
    f['prev_range_atr']=p['range']/p.atr14; f['atr_ratio']=p.atr_ratio; f['nr7']=p.nr7; f['inside']=p.inside
    f['rsi14_dir']=(p.rsi14-50)*sd; f['sma_slope_dir']=p.sma20_slope*sd; f['dist_sma_dir']=p.dist_sma20*sd; f['ret5_dir']=p.ret5*sd
    f['with_trend']=int((p.close>p.sma20)==(sd==1)); f['with_ema50']=int((p.above_ema50==1)==(sd==1))
    op=O[d0]; f['gap_atr']=(op-p.close)/p.atr14*sd
    lvl=t['H'] if sd==1 else t['L']; f['open_to_level_atr']=abs(lvl-op)/p.atr14
    f['hour']=pd.Timestamp(t['et']).hour; f['dow']=day.dayofweek; f['mins_to_break']=(i-d0)
    hi=H[d0:i+1].max() if i>d0 else H[i]; lo=L[d0:i+1].min() if i>d0 else L[i]
    f['day_range_before_atr']=(hi-lo)/p.atr14
    f['opp_side_dist_atr']=((lvl-lo) if sd==1 else (hi-lvl))/p.atr14     # how far price travelled from the other side today
    a=max(i-60,0); f['mom60_atr']=(C[i]-O[a])/p.atr14*sd if i>a else 0
    a15=max(i-15,0); f['mom15_atr']=(C[i]-O[a15])/p.atr14*sd if i>a15 else 0
    b=max(i-1440,0); vol_base=np.median(V[b:i]) if i-b>60 else np.nan
    f['vol15_ratio']=V[a15:i+1].mean()/vol_base if vol_base else np.nan
    rng_base=np.median((H-L)[b:i]) if i-b>60 else np.nan
    f['m1range15_ratio']=(H[a15:i+1]-L[a15:i+1]).mean()/rng_base if rng_base else np.nan
    f['spread']=SP[i]; f['gap_fill']=int(abs(t['entry']-lvl)>0.5)
    f['sl_atr']=t['dist']/p.atr14
    f['news_next_day']=int((day+pd.Timedelta(days=1)) in evdays or (day+pd.Timedelta(days=3) in evdays and day.dayofweek==4))
    f['prev_day_news']=int(pd.Timestamp(ref) in evdays)
    # outcome-side info (NOT used as predictors): MFE/MAE in R
    j=np.searchsorted(T,t['xt'])+1
    if sd==1: mfe=H[i:j].max()-t['entry']; mae=t['entry']-L[i:j].min()
    else: mfe=t['entry']-(L[i:j]+SP[i:j]).min(); mae=(H[i:j]+SP[i:j]).max()-t['entry']
    f['mfe_R']=mfe/t['dist']; f['mae_R']=mae/t['dist']
    f['win']=int(t['pnl']>0); f['pnl']=t['pnl']; f['R']=t['pnl']/t['dist']; f['et']=pd.Timestamp(t['et'])
    return f
if __name__=='__main__':
    wide=bt.run(pct=0.30,rr=1.25,flt='none',trend=None,news='none')
    v2=bt.run(pct=0.30,rr=1.25,flt='contract',trend='sma20',news='skip_day')
    W=pd.DataFrame([feats(t) for t in wide]); V2=pd.DataFrame([feats(t) for t in v2])
    W.to_pickle('feat_wide.pkl'); V2.to_pickle('feat_v2.pkl')
    print(len(W),W.win.mean().round(3),W.pnl.sum().round(1),'|',len(V2),V2.win.mean().round(3),V2.pnl.sum().round(1))
