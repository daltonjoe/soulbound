import random,datetime as d,collections as C,csv
import module1_engine.transit_engine as m
orig=m.calculate_planets;cache={}
def cp(jd):
    if jd not in cache: cache[jd]=orig(jd)
    return cache[jd]
m.calculate_planets=cp
random.seed(7)
NC,ND=1000,120
days=[d.date(2026,10,1)+d.timedelta(3*k) for k in range(ND)]
charts=[{i:random.uniform(0,360) for i in range(1,11)} for _ in range(NC)]
scores=[];cnt=C.Counter()
m.MAX_SLOW=3
for N in charts:
    for day in days:
        scores+=[x['score'] for x in m.compute_daily_events(N,day)]
m.MAX_SLOW=99
for N in charts:
    for day in days:
        for x in m.compute_daily_events(N,day,top_n=999):
            cnt[(x['transit_body_id'],x['aspect_type_id'],x['natal_body_id'])]+=1
scores.sort()
q=lambda p: scores[int(p/100*(len(scores)-1))]
print('olay/gun',round(len(scores)/(NC*ND),2))
print({p:round(q(p),3) for p in (30,50,70,90)})
tot=NC*ND
with open('m1_rates.csv','w',newline='') as f:
    w=csv.writer(f); w.writerow(['t','a','n','rate_pct'])
    for k,v in sorted(cnt.items()): w.writerow([*k,round(100*v/tot,4)])
print('anahtar',len(cnt))
