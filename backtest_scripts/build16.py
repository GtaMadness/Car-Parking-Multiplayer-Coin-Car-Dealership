import pandas as pd,numpy as np
from engine2 import BT,stats; from news import regime,events
from openpyxl import load_workbook
from openpyxl.styles import Font,PatternFill,Alignment
from openpyxl.utils import get_column_letter
PIP=0.1; CUT=pd.Timestamp('2026-05-01')
bt=BT(); D=bt.daily; allt=pd.read_pickle('final_trades.pkl')
RATE={'1 Pre-cut (cut expected)':'4.25–4.50%','2 Cutting cycle':'4.00% → 3.50–3.75%','3 On hold':'3.50–3.75%','4 Hawkish / hike':'3.50–3.75% → 3.75–4.00%'}
def tdf(tr):
    t=pd.DataFrame(tr)
    o=pd.DataFrame({'Previous day':t.ref.dt.date,'Prev high':t.H,'Prev low':t.L,'Prev range (pips)':(t.rng/PIP).round(1),'ATR14 (pips)':(t.atr/PIP).round(1),
      'Range/ATR':(t.rng/t.atr).round(2),'Prev close vs SMA20':np.where(t.ref.map(D.close)>t.ref.map(D.sma20),'Above','Below'),
      'News on entry day':t.day_news.replace('','–'),'News on previous day':t.ref_news.replace('','–'),'Fed regime':t.ref.map(regime),
      'Side':np.where(t.side==1,'BUY','SELL'),'Entry time (GMT+2)':pd.to_datetime(t.et),'Entry':t.entry.round(3),'SL':t.sl.round(3),'TP':t.tp.round(3),
      'SL (pips)':(t.dist/PIP).round(1),'Exit time (GMT+2)':pd.to_datetime(t.xt),'Result':t.result,'Pips':(t.pnl/PIP).round(1),'P/L $ (0.01 lot)':t.pnl.round(2)})
    o['Cumulative $']=o['P/L $ (0.01 lot)'].cumsum().round(2); return o
names=list(allt)
summ=[]
for k in names:
    tr=allt[k]; f=stats(tr); a=stats([t for t in tr if t['et']<np.datetime64(CUT)]); b=stats([t for t in tr if t['et']>=np.datetime64(CUT)])
    summ.append({'Setup':k,'Trades':f['n'],'Win rate':f['winrate'],'Net pips':round(f['net']/PIP,1),'Net $ (0.01 lot)':f['net'],'Profit factor':f['pf'],'Max drawdown $':f['maxdd'],
                 'Aug25–Apr26 net $ (used to pick settings)':a['net'],'May–Nov26 net $ (unseen check)':b['net'],'Aug25–Apr26 PF':a['pf'],'May–Nov26 PF':b['pf']})
summ=pd.DataFrame(summ)
rules=pd.DataFrame({'V2 rules (recommended)':[
 '1. Each day (GMT+2) take the previous day high and low. Range = high − low.',
 '2. Only trade if the previous day range is smaller than ATR(14) (a quiet day).',
 '3. Trend: if the previous close is above the 20-day SMA, place only the BUY STOP at the previous high. If below, place only the SELL STOP at the previous low.',
 '4. Skip the day completely if NFP, CPI or an FOMC decision is released that day. Check a calendar every morning.',
 '5. SL = 30% of the previous range. TP = 1.25 × SL.',
 '6. Cancel the order at the end of the day if it did not fill. An open trade stays until SL or TP.',
 '',
 'Data: Exness XAUUSDm M1, 1 Aug 2025 – 27 Nov 2026, spread included, 0.01 lot, 1 pip = $0.10.',
 'News dates come from BLS/Fed schedules (via search) and each was checked against a price spike in this data.',
 'Settings were chosen on Aug 2025 – Apr 2026 and checked on May – Nov 2026, which the optimiser never saw.']})
per=[]
for k in names:
    t=pd.DataFrame(allt[k]); t['q']=pd.to_datetime(t.et).dt.to_period('Q').astype(str); t['reg']=t.ref.map(regime)
    per.append(t.groupby('q').pnl.sum().rename(k)); 
quart=pd.concat(per,axis=1).round(2).reset_index().rename(columns={'q':'Quarter'})
regs=[]
for k in names:
    t=pd.DataFrame(allt[k]); t['reg']=t.ref.map(regime); regs.append(t.groupby('reg').pnl.agg(['count','sum']).round(2).rename(columns={'count':k[:30]+' – trades','sum':k[:30]+' – net $'}))
reg=pd.concat(regs,axis=1).reset_index().rename(columns={'reg':'Fed regime'}); reg.insert(1,'Fed funds rate',reg['Fed regime'].map(RATE))
# news calendar
ev=events(); nc=pd.read_pickle('newscheck.pkl'); rx=pd.read_pickle('reactions.pkl')
cal=ev.copy(); cal['Day']=cal.day.dt.date; cal['Release time (GMT+2)']=cal.time_gmt2
cal=cal.merge(nc.rename(columns={'day':'Day','event':'event'}),on=['Day','event'],how='left').merge(rx[['day','event','first15','four_h']].rename(columns={'day':'Day'}),on=['Day','event'],how='left')
cal['Fed regime']=cal.day.map(regime)
cal=cal[['Day','event','Release time (GMT+2)','Fed regime','15min range $','x normal','first15','four_h']].rename(columns={'event':'Event','x normal':'15-min move vs normal (x)','first15':'Gold move first 15 min ($)','four_h':'Gold move first 4 h ($)'})
cal['First 15 min direction held 4h?']=np.where(cal['Gold move first 15 min ($)'].isna(),'',np.where(np.sign(cal['Gold move first 15 min ($)'])==np.sign(cal['Gold move first 4 h ($)']),'Yes','No'))
# patterns from the last-recommendation trades
b=pd.read_pickle('base_trades.pkl'); b['half']=np.where(b.et<CUT,'Aug25–Apr26','May–Nov26')
pats=[]
for col,label in [('trend','Trade vs SMA20'),('day_news','News on entry day'),('wd','Weekday'),('hb','Entry hour (GMT+2)'),('dir','Direction'),('regime','Fed regime'),('ratio','Prev range / ATR')]:
    p=b.pivot_table(index=col,columns='half',values='pnl',aggfunc=['count','sum'],observed=True).round(2)
    p.columns=[f"{'Trades' if a=='count' else 'Net $'} {h}" for a,h in p.columns]; p=p.reset_index().rename(columns={col:'Group'}); p.insert(0,'Pattern',label); p['Group']=p.Group.astype(str); pats.append(p)
pats=pd.concat(pats)
tested=pd.DataFrame({'Idea tested':['Trade only with the 20-day SMA trend','Skip NFP / CPI / FOMC days','Only arm orders 15 min after news','Session filter (London/NY only)','Move SL to breakeven at +1R','Trade the first-15-min news direction','Quiet-day filter (range < ATR)','Wider SL (40%)'],
 'Result':['Strongest edge. With-trend trades made money in both halves; counter-trend trades lost.','Small, consistent improvement. Fewer losing whipsaw days.','Worse than skipping the day.','Hurt results. Asian-session breakouts are fine once the trend filter is on.','No real effect, so left out to keep it simple.','Profitable Aug–Apr, lost May–Nov. Not reliable, rejected.','Halves the drawdown, but cuts trades. Kept in V2, dropped in Aggressive.','More profit, bigger drawdown. Used in Aggressive.'],
 'Kept?':['Yes','Yes','No','No','No','No','V2 only','Aggressive only']})
d=D.reset_index()
atr=pd.DataFrame({'Day (GMT+2)':d.day.dt.date,'Open':d.open,'High':d.high,'Low':d.low,'Close':d.close,'Range (pips)':(d['range']/PIP).round(1),'True range (pips)':(d.tr/PIP).round(1),
  'ATR14 (pips)':(d.atr14/PIP).round(1),'Range/ATR':(d['range']/d.atr14).round(2),'Quiet day?':np.where(d.atr14.isna(),'',np.where(d['range']<d.atr14,'Yes','No')),
  'SMA20':d.sma20.round(2),'Close vs SMA20':np.where(d.sma20.isna(),'',np.where(d.close>d.sma20,'Above','Below')),'30% SL (pips)':(d['range']*0.3/PIP).round(1),
  'News that day':d.day.map(lambda x:', '.join(ev[ev.day==x].event)).fillna(''),'Fed regime':d.day.map(regime)})
g=pd.read_pickle('grid2.pkl').sort_values('net',ascending=False).rename(columns={'is_n':'Aug–Apr trades','is_net':'Aug–Apr net $','is_pf':'Aug–Apr PF','oos_n':'May–Nov trades','oos_net':'May–Nov net $','oos_pf':'May–Nov PF'})
xl='/home/user/Car-Parking-Multiplayer-Coin-Car-Dealership/XAUUSDm_breakout_backtest.xlsx'
old=pd.read_excel(xl,sheet_name=None); old.pop('Daily ATR',None)
w=pd.ExcelWriter(xl)
summ.to_excel(w,sheet_name='16M Summary',index=False); rules.to_excel(w,sheet_name='16M Summary',index=False,startrow=len(summ)+2)
tested.to_excel(w,sheet_name='16M Summary',index=False,startrow=len(summ)+len(rules)+5)
quart.to_excel(w,sheet_name='16M Quarterly & Fed',index=False); reg.to_excel(w,sheet_name='16M Quarterly & Fed',index=False,startrow=len(quart)+3)
tdf(allt[names[2]]).to_excel(w,sheet_name='16M Trades - V2',index=False)
tdf(allt[names[3]]).to_excel(w,sheet_name='16M Trades - V2 Aggressive',index=False)
tdf(allt[names[1]]).to_excel(w,sheet_name='16M Trades - 30% 1.5x',index=False)
tdf(allt[names[0]]).to_excel(w,sheet_name='16M Trades - original',index=False)
pats.to_excel(w,sheet_name='Patterns',index=False)
cal.to_excel(w,sheet_name='News calendar',index=False)
atr.to_excel(w,sheet_name='Daily ATR',index=False)
g.to_excel(w,sheet_name='16M Optimisation grid',index=False)
for k,v in old.items(): v.to_excel(w,sheet_name=k,index=False)
w.close()
wb=load_workbook(xl); hdr=PatternFill('solid',fgColor='EFE7D2')
for ws in wb:
    for c in ws[1]: c.font=Font(bold=True); c.fill=hdr; c.alignment=Alignment(wrap_text=True,vertical='top')
    ws.freeze_panes='A2'
    for i,col in enumerate(ws.columns,1):
        L=max(len(str(c.value)) if c.value is not None else 0 for c in list(col)[:300]); ws.column_dimensions[get_column_letter(i)].width=min(max(10,L+2),50)
    for row in ws.iter_rows(min_row=2):
        for c in row:
            if hasattr(c.value,'hour'): c.number_format='yyyy-mm-dd hh:mm'
ws=wb['16M Summary']
for r in [len(summ)+3,len(summ)+len(rules)+6]:
    for c in ws[r]: 
        if c.value: c.font=Font(bold=True); c.fill=hdr
ws.column_dimensions['A'].width=60; ws.column_dimensions['B'].width=70
wb.save(xl); print(wb.sheetnames); print(summ.to_string())
