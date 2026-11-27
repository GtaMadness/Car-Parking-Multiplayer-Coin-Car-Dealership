import pandas as pd,numpy as np
from scipy.stats import mannwhitneyu
pd.set_option('display.width',250)
FE=['dir_prev_candle','prev_body','prev_clv','prev_range_atr','atr_ratio','nr7','inside','rsi14_dir','sma_slope_dir','dist_sma_dir','ret5_dir','with_trend','with_ema50',
    'gap_atr','open_to_level_atr','hour','dow','mins_to_break','day_range_before_atr','opp_side_dist_atr','mom60_atr','mom15_atr','vol15_ratio','m1range15_ratio','spread','gap_fill','sl_atr','news_next_day','prev_day_news']
CUT=pd.Timestamp('2026-05-01')
for name in ['wide','v2']:
    X=pd.read_pickle(f'feat_{name}.pkl'); X['half']=np.where(X.et<CUT,'A','B')
    rows=[]
    for f in FE:
        x=X[f].astype(float); ok=x.notna()
        w=x[ok&(X.win==1)]; l=x[ok&(X.win==0)]
        p=mannwhitneyu(w,l).pvalue if len(w)>3 and len(l)>3 else np.nan
        # tercile win rates
        try: q=pd.qcut(x.rank(method='first'),3,labels=['low','mid','high'])
        except: q=None
        wr=X.groupby(q,observed=True).win.mean() if q is not None else None
        # same-direction effect in both halves?
        da=X[X.half=='A']; db=X[X.half=='B']
        ca=np.corrcoef(da[f].fillna(da[f].median()),da.win)[0,1]; cb=np.corrcoef(db[f].fillna(db[f].median()),db.win)[0,1]
        rows.append(dict(feature=f,win_mean=round(w.mean(),3),loss_mean=round(l.mean(),3),p=round(p,3),wr_low=round(wr['low'],2),wr_mid=round(wr['mid'],2),wr_high=round(wr['high'],2),corr_A=round(ca,2),corr_B=round(cb,2),consistent=np.sign(ca)==np.sign(cb)))
    r=pd.DataFrame(rows).sort_values('p'); print('\n=====',name,len(X),'trades'); print(r.to_string(index=False))
    # MFE / MAE
    L_=X[X.win==0]; W_=X[X.win==1]
    print('Losses reaching +0.25R/+0.5R/+0.75R/+1R first:',[round((L_.mfe_R>=k).mean(),2) for k in (0.25,0.5,0.75,1.0)])
    print('Wins dipping -0.25R/-0.5R/-0.75R first:',[round((W_.mae_R>=k).mean(),2) for k in (0.25,0.5,0.75)])
    print('Loss MFE median',L_.mfe_R.median().round(2),'Win MAE median',W_.mae_R.median().round(2))
