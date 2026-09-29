from __future__ import annotations
import hashlib,json
def validate(name,raw,records,min_records=1):
 errors=[]
 if len(records)<min_records: errors.append("RECORD_COUNT_BELOW_MINIMUM")
 seen=set()
 for i,r in enumerate(records):
  key=json.dumps(r,sort_keys=True,default=str)
  if key in seen: errors.append("DUPLICATE_RECORD:"+str(i))
  seen.add(key)
 return {"dataset":name,"valid":not errors,"errors":errors,"record_count":len(records),"sha256":hashlib.sha256(raw).hexdigest()}
def publishable(v): return bool(v.get("valid") and v.get("record_count",0)>0 and v.get("sha256"))
