import pandas as pd, numpy as np
from engine import *
from openpyxl import load_workbook
from openpyxl.styles import Font, PatternFill, Alignment
from openpyxl.utils import get_column_letter
df,daily=load(); S=pd.Timestamp('2026-05-27'); OOS=np.datetime64('2026-10-01')
PIP=0.1
def trades_df(tr):
    t=pd.DataFrame(tr)
    out=pd.DataFrame({'Previous day':t.ref.dt.date,'Prev high':t.H,'Prev low':t.L,'Prev range (pips)':(t.rng/PIP).round(1),
        'ATR14 at entry (pips)':(t.atr/PIP).round(1),'Range / ATR':(t.rng/t.atr).round(2),'SL dist (pips)':(t.dist/PIP).round(1),
        'Side':np.where(t.side==1,'BUY','SELL'),'Entry time (GMT+2)':pd.to_datetime(t.et),'Entry':t.entry.round(3),'SL':t.sl.round(3),'TP':t.tp.round(3),
        'Exit time (GMT+2)':pd.to_datetime(t.xt),'Result':t.result,'Pips':(t.pnl/PIP).round(1),'P/L $ (0.01 lot)':t.pnl.round(2)})
    out['Cumulative $']=out['P/L $ (0.01 lot)'].cumsum().round(2); return out
cfg_base=dict(pct=0.10,rr=1.0,expiry='keep',flt='none')
cfg_best=dict(pct=0.30,rr=1.5,expiry='day',flt='contract')
cfg_alt=dict(pct=0.30,rr=1.5,expiry='day',flt='none')
named=[('Your original rules',cfg_base),('Recommended: SL 30% of range, TP 1.5x, cancel at day end, only after a quiet day',cfg_best),('Same but no quiet-day filter',cfg_alt)]
summ=[]; tdfs={}
for name,c in named:
    tr=run(df,daily,S,**c); s=stats(tr); t=trades_df(tr); tdfs[name]=t
    a=stats([x for x in tr if x['et']<OOS]); b=stats([x for x in tr if x['et']>=OOS])
    summ.append({'Setup':name,'Trades':s['n'],'Wins':s['wins'],'Losses':s['n']-s['wins'],'Win rate':round(s['winrate'],3),'Net pips':round(s['net']/PIP,1),
        'Net $ (0.01 lot)':round(s['net'],2),'Profit factor':round(s['pf'],2),'Max drawdown $':round(s['maxdd'],2),
        'Jun–Sep net $':round(a['net'],2),'Oct–Nov net $':round(b['net'],2)})
summ=pd.DataFrame(summ)
monthly=pd.concat({k[:40]:v.groupby(v['Entry time (GMT+2)'].dt.to_period('M').astype(str))['P/L $ (0.01 lot)'].agg(['count','sum']).round(2) for k,v in tdfs.items()},axis=1)
monthly.columns=[f"{a} – {'trades' if b=='count' else 'net $'}" for a,b in monthly.columns]; monthly=monthly.reset_index().rename(columns={'Entry time (GMT+2)':'Month'})
d=daily.reset_index()
atr=pd.DataFrame({'Day (GMT+2)':d.day.dt.date,'Open':d.open,'High':d.high,'Low':d.low,'Close':d.close,'Range ($)':d['range'].round(3),'Range (pips)':(d['range']/PIP).round(1),
   'True range (pips)':(d.tr/PIP).round(1),'ATR14 ($)':d.atr14.round(3),'ATR14 (pips)':(d.atr14/PIP).round(1),'Range / ATR':(d['range']/d.atr14).round(2),
   'Quiet day? (range < ATR)':np.where(d.atr14.isna(),'',np.where(d['range']<d.atr14,'Yes','No')),'10% of range (pips)':(d['range']*0.1/PIP).round(1),'30% of range (pips)':(d['range']*0.3/PIP).round(1)})
g=pd.read_pickle('grid.pkl')
grid=g.rename(columns={'direction':'Direction','sl_pct':'SL % of base','sl_basis':'SL base (range/ATR)','rr':'TP multiple of SL','orders':'Unfilled orders (keep/cancel at day end)','filter':'Filter',
  'trades':'Trades','winrate':'Win rate','net':'Net $','pf':'Profit factor','maxdd':'Max DD $','is_trades':'Jun–Sep trades','is_net':'Jun–Sep net $','oos_trades':'Oct–Nov trades','oos_net':'Oct–Nov net $','is_pf':'Jun–Sep PF','oos_pf':'Oct–Nov PF'}).round(3).sort_values('Net $',ascending=False)
grid=grid.replace([np.inf],999)
notes=pd.DataFrame({'Notes':[
 'Period: 27 May – 27 Nov 2026 (6 months), Exness XAUUSDm M1 data, days in GMT+2, 0.01 lot, 1 pip = $0.10, spread from the data included.',
 'ATR14 = simple 14-day average of true range on GMT+2 daily candles (same formula as MT5 ATR). MT5 charts use server time (GMT+0), so its daily ATR will differ slightly.',
 'Jun–Sep was used to find settings, Oct–Nov to check them. A setup that is positive in both halves is more trustworthy.',
 'Filter "contract" (quiet day) = only place orders when the previous day range was smaller than ATR14.',
 'Filter "trend" = only buy if previous close > 20-day average, only sell if below. "expand" = only after a day bigger than ATR14.',
 '"Fade" = trade against the breakout (sell at the high, buy at the low). Tested for comparison only.',
 '640 combinations were tested, so the very top results are partly luck. Prefer settings whose neighbours are also profitable.']})
xl='/home/user/Car-Parking-Multiplayer-Coin-Car-Dealership/XAUUSDm_breakout_backtest.xlsx'
old=pd.read_excel(xl,sheet_name=None)
w=pd.ExcelWriter(xl)
summ.to_excel(w,sheet_name='6M Summary',index=False); notes.to_excel(w,sheet_name='6M Summary',index=False,startrow=len(summ)+3)
monthly.to_excel(w,sheet_name='6M Monthly',index=False)
tdfs[named[0][0]].to_excel(w,sheet_name='6M Trades - original',index=False)
tdfs[named[1][0]].to_excel(w,sheet_name='6M Trades - recommended',index=False)
atr.to_excel(w,sheet_name='Daily ATR',index=False)
grid.to_excel(w,sheet_name='Optimisation grid',index=False)
for k in ['Summary','Trades','Daily ranges']: old[k].to_excel(w,sheet_name='2W '+k,index=False)
w.close()
wb=load_workbook(xl)
for ws in wb:
    for c in ws[1]: c.font=Font(bold=True); c.fill=PatternFill('solid',fgColor='EFE7D2'); c.alignment=Alignment(wrap_text=True,vertical='top')
    ws.freeze_panes='A2'
    for i,col in enumerate(ws.columns,1):
        L=max(len(str(c.value)) if c.value is not None else 0 for c in list(col)[:200]); ws.column_dimensions[get_column_letter(i)].width=min(max(10,L+2),48)
    for row in ws.iter_rows(min_row=2):
        for c in row:
            if hasattr(c.value,'hour'): c.number_format='yyyy-mm-dd hh:mm'
ws=wb['6M Summary']; ws.column_dimensions['A'].width=80
r0=len(summ)+4
for r in range(r0,r0+12): ws.cell(r,1).alignment=Alignment(wrap_text=False)
wb.save(xl)
print(summ.to_string()); print(monthly.to_string()); print(atr.tail(12).to_string())
