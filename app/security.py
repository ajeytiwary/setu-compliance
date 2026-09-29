from __future__ import annotations
from dataclasses import dataclass
from fastapi import Header,HTTPException
@dataclass(frozen=True)
class Principal:
 subject:str
 tenant_id:str
 roles:frozenset[str]
def principal(x_setu_subject:str|None=Header(None),x_setu_tenant:str|None=Header(None),x_setu_roles:str|None=Header(None)):
 if not x_setu_subject or not x_setu_tenant: raise HTTPException(401,"Authenticated subject and tenant required")
 roles=frozenset(x.strip() for x in (x_setu_roles or "").split(",") if x.strip())
 return Principal(x_setu_subject,x_setu_tenant,roles)
def require(p:Principal,*roles):
 if not p.roles.intersection(roles): raise HTTPException(403,"Insufficient role")
 return p
