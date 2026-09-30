from __future__ import annotations
def submission_readiness(compiled:dict):
 blockers=compiled.get("blockers") or []
 ready=not blockers
 return {"decision":"READY_FOR_SUBMISSION" if ready else "BLOCKED","ready_for_submission":ready,"authority_acceptance":"PENDING" if ready else "NOT_SUBMITTED","blockers":blockers,"notice":"EuroSetu evaluates evidence and regulatory-data readiness. Acceptance remains with customs authorities and, where applicable, the CBAM Registry and accredited verifier."}
