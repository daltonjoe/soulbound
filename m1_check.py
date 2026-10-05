import random,datetime as d
import module1_engine.transit_engine as m
m.MAX_SLOW=99;random.seed(3);n=0;D=0
for _ in range(200):
    N={i:random.uniform(0,360) for i in range(1,11)}
    for k in range(40):
        n+=len(m.compute_daily_events(N,d.date(2026,10,1)+d.timedelta(9*k),top_n=999));D+=1
print('tavansiz olay/gun',round(n/D,2))
