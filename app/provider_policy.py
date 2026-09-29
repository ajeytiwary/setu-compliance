from __future__ import annotations
RANK={"LEGAL":5,"OFFICIAL":4,"OFFICIAL_STATISTICS":3,"MIRROR":2,"DEMO_ONLY":1}
def may_satisfy(authority_required,provider_authority):
 return (not authority_required) or RANK.get(provider_authority,0)>=RANK["OFFICIAL"]
def choose(dataset_config,available_ids=None):
 available=set(available_ids or [p["id"] for p in dataset_config["providers"]])
 candidates=[p for p in dataset_config["providers"] if p.get("enabled",True) and p["id"] in available]
 candidates.sort(key=lambda p:RANK.get(p["authority"],0),reverse=True)
 for p in candidates:
  if may_satisfy(dataset_config.get("authority_required",False),p["authority"]):return p
 raise RuntimeError("No provider satisfies trust policy")
