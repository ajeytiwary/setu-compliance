from app.live_source_probe import SOURCES,sync
import json,sys
r={}
for n in SOURCES:
 try:r[n]={"ok":True,"snapshot":sync(n)}
 except Exception as e:r[n]={"ok":False,"error":str(e)}
print(json.dumps(r,indent=2))
raise SystemExit(0 if all(x["ok"] for x in r.values()) else 1)
