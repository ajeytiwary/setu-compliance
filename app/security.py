from __future__ import annotations
import base64,hashlib,hmac,json,os,time
from dataclasses import dataclass
from fastapi import Header,HTTPException,Request

@dataclass(frozen=True)
class Principal:
    subject:str
    tenant_id:str
    roles:frozenset[str]

def _b64decode(value:str)->bytes:
    return base64.urlsafe_b64decode(value+"="*(-len(value)%4))

def _jwt(token:str)->dict:
    jwks=os.getenv("EUROSETU_OIDC_JWKS_URL")
    if jwks:
        try:
            import jwt
            key=jwt.PyJWKClient(jwks).get_signing_key_from_jwt(token).key
            opts={"require":["exp","sub"]}
            return jwt.decode(token,key,algorithms=["RS256","ES256"],issuer=os.getenv("EUROSETU_JWT_ISSUER") or None,audience=os.getenv("EUROSETU_JWT_AUDIENCE") or None,options=opts)
        except Exception:
            raise HTTPException(401,"Invalid or expired OIDC bearer token")
    secret=os.getenv("EUROSETU_JWT_SECRET")
    if not secret:
        raise HTTPException(503,"Production authentication is not configured")
    try:
        h,p,s=token.split(".")
        header=json.loads(_b64decode(h))
        claims=json.loads(_b64decode(p))
        expected=base64.urlsafe_b64encode(hmac.new(secret.encode(),f"{h}.{p}".encode(),hashlib.sha256).digest()).rstrip(b"=").decode()
        if header.get("alg")!="HS256" or not hmac.compare_digest(expected,s):
            raise ValueError("signature")
        if claims.get("exp") is not None and int(claims["exp"])<=int(time.time()):
            raise ValueError("expired")
        issuer=os.getenv("EUROSETU_JWT_ISSUER")
        audience=os.getenv("EUROSETU_JWT_AUDIENCE")
        if issuer and claims.get("iss")!=issuer: raise ValueError("issuer")
        aud=claims.get("aud")
        if audience and not (audience==aud or isinstance(aud,list) and audience in aud): raise ValueError("audience")
        if not claims.get("sub"): raise ValueError("subject")
        return claims
    except HTTPException: raise
    except Exception:
        raise HTTPException(401,"Invalid or expired bearer token")

def principal(request:Request)->Principal:
    auth=request.headers.get("authorization","")
    if not auth.lower().startswith("bearer "):
        raise HTTPException(401,"Bearer token required")
    parts=auth.split(None,1)
    if len(parts)<2 or not parts[1].strip():
        raise HTTPException(401,"Bearer token required")
    claims=_jwt(parts[1].strip())
    subject=str(claims["sub"])
    requested_tenant=request.headers.get("x-eurosetu-tenant")
    memberships=claims.get("tenants") or {}
    if not isinstance(memberships,dict):
        raise HTTPException(403,"Token has no server-verified tenant memberships")
    tenant=requested_tenant or claims.get("tenant_id")
    if not tenant or tenant not in memberships:
        raise HTTPException(403,"No membership in requested tenant")
    roles=memberships.get(tenant) or []
    if isinstance(roles,str): roles=[roles]
    return Principal(subject,tenant,frozenset(str(x) for x in roles))

def require(p:Principal,*roles):
    if roles and not p.roles.intersection(roles):
        raise HTTPException(403,"Insufficient role")
    return p

def require_request(request:Request,*roles)->Principal:
    return require(principal(request),*roles)
