#!/usr/bin/env python3
"""Client-docs EU-bound demo: redacted extracts -> full pipeline, BLOCKED -> READY.

Reads the redacted derivatives in this folder (no client PDFs copied, no PII),
injects synthetic TARIC snapshots (as_of == import_date, max_age 1 day — the
same pattern as tests/test_active_entitlement.py), and runs the real engines:

  app.evidence_lifecycle (deterministic as_of clock)
  app.decision_engine (DECISION_POLICY_V1, fail-closed, predecessor chain)
  app.market_access_compiler_v2.compile_shipment (PPWR + REACH + sanctions +
      valuation + origin + customs declaration pack)
  app.compliance_entitlement.compile_active_entitlement (TARIC + steel + CBAM)

Phase A (as-extracted): invoice UNVERIFIED, MTC without heat trace, no CBAM
verification pack -> BLOCKED. Phase B (remediated): verified evidence + full
CBAM pack -> READY / READY_FOR_SUBMISSION / ENTITLED for the steel case.
The non-steel contrast case documents an engine boundary: the steel-aware
compiler fail-closes (STEEL_CN_MAPPING) on unmapped CNs by design, while
the entitlement path (base steel measure, applicable=False) ENTITLEs.

Usage: python use_cases/client_docs_eu_bound/run_client_docs_demo.py
"""
from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]

# Synthetic regulatory cache: never touches data/cache/.
_TMP = tempfile.mkdtemp(prefix="eurosetu-client-docs-")
os.environ["EUROSETU_REGULATORY_CACHE"] = _TMP
sys.path.insert(0, str(ROOT))

from app import decision_engine as de  # noqa: E402
from app import eu_public_data as pub  # noqa: E402
from app import evidence_lifecycle as ev  # noqa: E402
from app.compliance_entitlement import compile_active_entitlement  # noqa: E402
from app.market_access_compiler_v2 import compile_shipment  # noqa: E402

# Rebind the regulatory cache: app.eu_public_data binds CACHE at import time,
# so the env var alone is not enough if the app was imported earlier (e.g.
# under pytest). Point it at our synthetic tempdir explicitly.
pub.CACHE = Path(_TMP)

AS_OF = "2026-09-29"
SHIPMENTS = json.loads((HERE / "redacted_shipments.json").read_text())["shipments"]

TARIC_CSV = """cn_code,origin_country,measure_type,duty_rate
72221119,IN,THIRD_COUNTRY_DUTY,0%
40111010,IN,THIRD_COUNTRY_DUTY,0%
"""

# Seed the synthetic snapshot at import time too (not only in main()), so
# test harnesses that call shipment_payload/compile_shipment directly —
# without going through main() — still see a fresh as_of==import_date
# snapshot. store_snapshot is idempotent; main() re-seeds harmlessly.
pub.store_snapshot("taric", pub.parse_csv(TARIC_CSV, "taric", AS_OF),
                   TARIC_CSV.encode())

# Phase A: evidence as extracted — invoice needs validation (UNPARSED),
# MTC without heat trace (UNVERIFIED). Each requirement is evaluated singly
# (one object per requirement): bundling SB+INV+MTC into one set would trip
# the duplicate-hash CONFLICTING rule, which is for same-type duplicates.
def _ev(eid, ref, status, sha):
    return {"evidence_id": eid, "subject_ref": ref,
            "collected_at": AS_OF, "verification_status": status,
            "sha256": sha}

PHASE_A = {
    "CLIENT-AMBICA-01": {
        "INVOICE": [_ev("E-INV-AMBICA", "CLIENT-AMBICA-01", "UNPARSED",
                        "inv-ambica")],
        "MTC_HEAT_TRACE": [_ev("E-MTC-AMBICA", "CLIENT-AMBICA-01",
                               "UNVERIFIED", "mtc-no-heat-trace")],
    },
    "CLIENT-APOLLO-01": {
        "INVOICE": [_ev("E-INV-APOLLO", "CLIENT-APOLLO-01", "UNPARSED",
                        "inv-apollo")],
    },
}

PHASE_B = {
    "CLIENT-AMBICA-01": {
        "INVOICE": [_ev("E-INV-AMBICA", "CLIENT-AMBICA-01", "VERIFIED",
                        "inv-ambica-verified")],
        # Remediated MTC carries a heat trace (shape from mtc_shape.json).
        "MTC_HEAT_TRACE": [_ev("E-MTC-AMBICA", "CLIENT-AMBICA-01",
                               "VERIFIED", "mtc-SYN-HEAT-01-verified")],
    },
    "CLIENT-APOLLO-01": {
        "INVOICE": [_ev("E-INV-APOLLO", "CLIENT-APOLLO-01", "VERIFIED",
                        "inv-apollo-verified")],
    },
}

# Expected phase-B compiler outcome: the steel-aware compiler fail-closes
# (STEEL_CN_MAPPING) on the non-steel tyres CN by design — unmapped CNs
# never assert through the steel path. Entitlement (base steel measure,
# applicable=False for non-steel) still ENTITLEs.
EXPECTED_COMPILER_B = {
    "CLIENT-AMBICA-01": "READY_FOR_SUBMISSION",
    "CLIENT-APOLLO-01": "BLOCKED",
}

FULL_CBAM_PACK = {
    "monitoring_plan": {
        "version": "v1", "effective_from": "2026-01-01",
        "installation_id": "SYN-INSTALLATION-01",
        "production_processes": ["EAF stainless bars"],
        "calculation_methods": ["calculation-based"],
        "system_boundaries": ["installation"], "source_streams": ["fuels"],
        "data_sources": ["meters"], "quality_controls": ["QA plan"],
    },
    "operator_emissions_report": {
        "reporting_period": "2026", "installation_id": "SYN-INSTALLATION-01",
        "goods": [{"cn_code": "72221119", "quantity_t": 24.371}],
        "activity_levels": {"steel_t": 24.371},
        "installation_emissions": {"direct_tco2": 40.0},
        "production_process_emissions": {"eaf_tco2": 40.0},
        "precursors": [{"material": "synthetic ferro-chromium", "quantity_t": 2.0,
                        "specific_embedded_emissions_tco2_per_t": 1.5,
                        "value_type": "ACTUAL"}],
        "heat_waste_gas_electricity_balance": "balanced",
        "data_gaps": "none",
    },
    "verification_report": {
        "installation": {
            "operator_name": "Synthetic Operator",
            "operator_registration_number": "SYN-OP-01",
            "installation_name": "Synthetic Steelworks",
            "installation_address": "Synthetic Address",
            "latitude": "0.0", "longitude": "0.0", "reporting_period": "2026",
        },
        "verifier": {
            "verifier_name": "Synthetic Verifier",
            "verifier_address": "Synthetic Address",
            "lead_auditor": "Synthetic Auditor",
            "accreditation_number": "SYN-ACC-01",
            "national_accreditation_body": "Synthetic NAB",
            "accreditation_country": "DE",
            "accreditation_expiry": "2027-12-31",
            "accreditation_scope": "CBAM",
        },
        "monitoring_plan": {
            "version": "v1", "production_processes": ["EAF stainless bars"],
            "calculation_methods": ["calculation-based"],
        },
        "statement": {
            "reasonable_assurance": True,
            "free_from_material_misstatements": True,
            "free_from_material_nonconformities": True,
        },
        "findings": [],
    },
}


def shipment_payload(s: dict, phase: str) -> dict:
    ref = s["shipment_ref"]
    phase_reqs = (PHASE_B if phase == "B" else PHASE_A)[ref]
    tag = ref.split("-")[1].lower()
    evidence = [{"id": f"E-SB-{tag.upper()}",
                 "evidence_type": "SHIPPING_BILL",
                 "sha256": f"sb-{tag}" + ("-verified" if phase == "B"
                                          else ""),
                 "issuer": "synthetic", "valid_until": "2027-09-29",
                 "document_codes": []}]
    for req_name, objs in phase_reqs.items():
        et = ("COMMERCIAL_INVOICE" if req_name == "INVOICE"
              else "MILL_TEST_CERTIFICATE")
        for e in objs:
            evidence.append(
                {"id": e["evidence_id"], "evidence_type": et,
                 "sha256": e["sha256"], "issuer": "synthetic",
                 "valid_until": "2027-09-29", "document_codes": []})
    return {
        "shipment_ref": ref,
        "cn_code": s["cn_code"],
        "origin_country": s["origin_country"],
        "import_date": AS_OF,
        "customs_value_eur": s["customs_value_eur"],
        "quantity_t": s["pipeline_quantity_t"],
        "gross_mass_kg": s["gross_mass_kg"],
        "net_mass_kg": s["net_mass_kg"],
        "quota_remaining_t": 1000.0,
        "quota_balance_as_of": AS_OF,
        "evidence": evidence,
        "valuation": {"method": 1,
                      "price_paid_or_payable_eur": s["customs_value_eur"]},
        "origin": {"non_preferential": {"country": "IN",
                                        "basis_ref": "SB-" + ref},
                   "preferential": {"claim_preference": False}},
        "ppwr": {"placing_on_market_date": AS_OF,
                 "packaging_components": [{"id": "PKG-1",
                                           "heavy_metals_mg_kg": 10.0}],
                 "conformity_document_ref": "SYN-DOC-01"},
        "reach_scip": {"articles": [
            {"id": "ART-1", "candidate_list_substances": []}]},
        "sanctions": {"parties": [
            {"name": "redacted-counterparty", "screened_at": AS_OF,
             "source_version": "SYN-2026-09-29"}]},
        "cbam_verification_pack": FULL_CBAM_PACK if (
            phase == "B" and s["cbam_scope"]["in_scope"]) else {},
    }


def entitlement_payload(s: dict) -> dict:
    annual = 30.0 + s["pipeline_quantity_t"]  # synthetic YTD + this shipment
    return {
        "shipment_ref": s["shipment_ref"],
        "cn_code": s["cn_code"],
        "origin_country": s["origin_country"],
        "import_date": AS_OF,
        "customs_value_eur": s["customs_value_eur"],
        "quantity_t": s["pipeline_quantity_t"],
        "steel_quota_remaining_t": 1000.0,
        "quota_balance_as_of": AS_OF,
        "importer_cbam_mass_ytd_t": 30.0,
        "authorised_cbam_declarant": True,
        "cbam_emissions_verified": True,
        "_annual_after": annual,
    }


def main() -> int:
    raw = TARIC_CSV.encode()
    pub.store_snapshot("taric", pub.parse_csv(TARIC_CSV, "taric", AS_OF), raw)

    print(f"as_of={AS_OF} policy={de.POLICY_VERSION}")
    print(f"{'shipment':<18} {'phase':<6} {'evidence':<12} "
          f"{'decision':<8} {'compiler':<20} {'entitlement':<10} blockers")
    ok = True
    for s in SHIPMENTS:
        ref = s["shipment_ref"]
        # --- evidence lifecycle + decision engine, A then B with predecessor
        states_a = {k: ev.evaluate_requirement(v, as_of=AS_OF)["state"]
                    for k, v in PHASE_A[ref].items()}
        assert all(x == "UNVERIFIED" for x in states_a.values()), \
            (ref, states_a)
        dec_a = de.build_decision(ref, [
            {"obligation_id": f"EVIDENCE_{k}", "status": st,
             "severity": "BLOCKING", "required_for_release": True}
            for k, st in states_a.items()
        ], as_of=AS_OF)
        states_b = {k: ev.evaluate_requirement(v, as_of=AS_OF)["state"]
                    for k, v in PHASE_B[ref].items()}
        assert all(x == "VALID" for x in states_b.values()), (ref, states_b)
        dec_b = de.build_decision(ref, [
            {"obligation_id": f"EVIDENCE_{k}", "status": "PASS",
             "severity": "BLOCKING", "required_for_release": True}
            for k in states_b
        ], as_of=AS_OF, predecessor_id=dec_a["decision_id"])
        # --- full compilers
        comp_a = compile_shipment(shipment_payload(s, "A"))
        comp_b = compile_shipment(shipment_payload(s, "B"))
        ent = compile_active_entitlement(entitlement_payload(s))
        print(f"{ref:<18} {'A':<6} {','.join(sorted(states_a)):<12} "
              f"{dec_a['status']:<8} {comp_a['decision']:<20} "
              f"{'—':<10} "
              f"{[b.get('code') for b in comp_a['blockers']][:3]}")
        print(f"{ref:<18} {'B':<6} {','.join(sorted(states_b)):<12} "
              f"{dec_b['status']:<8} {comp_b['decision']:<20} "
              f"{ent['decision']:<10} "
              f"{[b.get('code') for b in comp_b['blockers']][:3]}")
        if dec_a["status"] != "BLOCKED":
            print(f"  FAIL: phase A decision must BLOCK for {ref}");
            ok = False
        if dec_b["status"] != "READY":
            print(f"  FAIL: phase B decision must be READY for {ref}");
            ok = False
        if comp_a["decision"] != "BLOCKED":
            print(f"  FAIL: phase A compiler must BLOCK for {ref}");
            ok = False
        if comp_b["decision"] != EXPECTED_COMPILER_B[ref]:
            print(f"  FAIL: phase B compiler for {ref}: "
                  f"{comp_b['decision']} {comp_b['blockers']}");
            ok = False
        if ref == "CLIENT-APOLLO-01" and not any(
                b.get("code") == "STEEL_CN_MAPPING"
                for b in comp_b["blockers"]):
            print("  FAIL: APOLLO phase B must name STEEL_CN_MAPPING");
            ok = False
        if ent["decision"] != "ENTITLED":
            print(f"  FAIL: entitlement must be ENTITLED for {ref}: "
                  f"{ent['blockers']}");
            ok = False
        if dec_b.get("predecessor_id") != dec_a["decision_id"]:
            print(f"  FAIL: predecessor chain broken for {ref}");
            ok = False
    print("GUARDRAIL: READY_FOR_SUBMISSION/ENTITLED means EuroSetu rule/evidence "
          "gates pass. Customs/CBAM/verifier acceptance remains external.")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
