import pandas as pd
# US release dates (8:30 ET) and FOMC decision days (2:00 pm ET). Sources: BLS schedules / Fed statements via search.
NFP=['2025-08-01','2025-09-05','2025-11-20','2025-12-16','2026-01-09','2026-02-11','2026-03-06','2026-04-03','2026-05-08','2026-06-05','2026-07-02','2026-08-07','2026-09-04','2026-10-02','2026-11-06']
CPI=['2025-08-12','2025-09-11','2025-10-24','2025-12-18','2026-01-13','2026-02-13','2026-03-11','2026-04-10','2026-05-12','2026-06-10','2026-07-14','2026-08-12','2026-09-11','2026-10-14','2026-11-10']
FOMC={'2025-09-17':'cut 25bp','2025-10-29':'cut 25bp','2025-12-10':'cut 25bp','2026-01-28':'hold','2026-03-18':'hold','2026-04-29':'hold',
      '2026-06-17':'hold','2026-07-29':'hold (3 dissents for hike)','2026-09-16':'hike 25bp','2026-10-28':'hold (2 dissents for hike)'}
def us_dst(d):  # US daylight time: 2nd Sun Mar -> 1st Sun Nov
    y=d.year; m=pd.Timestamp(y,3,1); s=m+pd.Timedelta(days=(6-m.weekday())%7+7); n=pd.Timestamp(y,11,1); e=n+pd.Timedelta(days=(6-n.weekday())%7)
    return s<=d<e
def release_time(day,et_hour,et_min=0):  # returns GMT+2 timestamp
    d=pd.Timestamp(day); off=4 if us_dst(d) else 5
    return d+pd.Timedelta(hours=et_hour+off+2,minutes=et_min)
def events():
    rows=[(pd.Timestamp(d),'NFP',release_time(d,8,30)) for d in NFP]+[(pd.Timestamp(d),'CPI',release_time(d,8,30)) for d in CPI]+[(pd.Timestamp(d),'FOMC '+v,release_time(d,14)) for d,v in FOMC.items()]
    return pd.DataFrame(rows,columns=['day','event','time_gmt2']).sort_values('time_gmt2').reset_index(drop=True)
def regime(day):
    d=pd.Timestamp(day)
    if d<pd.Timestamp('2025-09-18'): return '1 Pre-cut (cut expected)'
    if d<pd.Timestamp('2025-12-11'): return '2 Cutting cycle'
    if d<pd.Timestamp('2026-07-30'): return '3 On hold'
    return '4 Hawkish / hike'
