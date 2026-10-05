import csv
r = list(csv.DictReader(open('m1_rates.csv')))
v = ",\n".join("('v2',%s,%s,%s,%s)" % (x['t'], x['a'], x['n'], x['rate_pct']) for x in r)
open('m1_rates.sql', 'w').write("insert into ref_event_rates (engine_version,transit_body_id,aspect_type_id,natal_body_id,rate_pct) values\n" + v + ";")
print(len(r))
