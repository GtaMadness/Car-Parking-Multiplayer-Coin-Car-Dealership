import pandas as pd,numpy as np,warnings; warnings.filterwarnings('ignore')
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.tree import DecisionTreeClassifier, export_text
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import make_pipeline
from sklearn.impute import SimpleImputer
from sklearn.metrics import roc_auc_score
from sklearn.inspection import permutation_importance
FE=['dir_prev_candle','prev_body','prev_clv','prev_range_atr','atr_ratio','nr7','inside','rsi14_dir','sma_slope_dir','dist_sma_dir','ret5_dir','with_trend','with_ema50',
    'gap_atr','open_to_level_atr','hour','dow','mins_to_break','day_range_before_atr','opp_side_dist_atr','mom60_atr','mom15_atr','vol15_ratio','m1range15_ratio','spread','prev_day_news','news_next_day']
NOTREND=[f for f in FE if f not in ('rsi14_dir','sma_slope_dir','dist_sma_dir','ret5_dir','with_trend','with_ema50')]
W=pd.read_pickle('feat_wide.pkl').sort_values('et').reset_index(drop=True); V2=pd.read_pickle('feat_v2.pkl')
models={'Logistic':lambda:make_pipeline(SimpleImputer(strategy='median'),StandardScaler(),LogisticRegression(C=0.3,max_iter=2000)),
        'RandomForest':lambda:make_pipeline(SimpleImputer(strategy='median'),RandomForestClassifier(300,min_samples_leaf=8,random_state=0)),
        'GradBoost':lambda:make_pipeline(SimpleImputer(strategy='median'),GradientBoostingClassifier(n_estimators=150,max_depth=2,learning_rate=0.05,subsample=0.8,random_state=0))}
def walk(X,feats,mk,start=90,step=30):
    pr=pd.Series(np.nan,index=X.index)
    for s in range(start,len(X),step):
        m=mk().fit(X.loc[:s-1,feats],X.loc[:s-1,'win']); e=min(s+step,len(X))
        pr.loc[s:e-1]=m.predict_proba(X.loc[s:e-1,feats])[:,1]
    return pr
res={}
for setname,feats in [('all features',FE),('without trend features',NOTREND)]:
    for k,mk in models.items():
        pr=walk(W,feats,mk); ok=pr.notna(); auc=roc_auc_score(W.win[ok],pr[ok])
        # trade only when model prob > 0.5 on the unseen part
        sel=ok&(pr>0.5); 
        print(f"{setname:24s} {k:12s} AUC on unseen trades {auc:.3f} | unseen trades {ok.sum()}: all net ${W.pnl[ok].sum():.0f} win {W.win[ok].mean():.2f} | model-picked {sel.sum()}: net ${W.pnl[sel].sum():.0f} win {W.win[sel].mean():.2f}")
        res[(setname,k)]=pr
# importance (RF on all data, permutation)
m=models['RandomForest']().fit(W[FE],W.win); pi=permutation_importance(m,W[FE],W.win,n_repeats=30,random_state=0,scoring='roc_auc')
imp=pd.Series(pi.importances_mean,index=FE).sort_values(ascending=False); print('\nPermutation importance (all 245):'); print(imp.head(10).round(3).to_string())
# simple readable tree
tr=make_pipeline(SimpleImputer(strategy='median'),DecisionTreeClassifier(max_depth=3,min_samples_leaf=20,random_state=0)).fit(W[FE],W.win)
print('\n'+export_text(tr[-1],feature_names=FE))
# within V2: can a model trained on wide (no lookahead) separate V2 wins?
pr=walk(W,FE,models['Logistic']); W['p']=pr
# leave-one-out style on V2 itself
from sklearn.model_selection import cross_val_predict, StratifiedKFold
v=V2.sort_values('et').reset_index(drop=True)
pv=walk(v,NOTREND,models['Logistic'],start=40,step=10); ok=pv.notna()
print('\nV2-only walk-forward AUC (logistic, no trend feats):',round(roc_auc_score(v.win[ok],pv[ok]),3),'on',ok.sum(),'trades')
pd.to_pickle(dict(imp=imp),'ml_out.pkl')
