# EuroSetu Public Trade Evidence Corpus

A reproducible client-like evidence room for demos, ingestion testing and competitive workflow benchmarks.

## One-command use

Offline/repeatable (default; no external dependency):

```bash
python scripts/build_public_evidence_corpus.py --clean
pytest -q tests/test_public_evidence_corpus.py tests/benchmarks/test_steel_100_demo.py
```

Acquire direct official artifacts too:

```bash
python scripts/build_public_evidence_corpus.py --clean --acquire
```

The acquisition mode downloads only registry entries marked as direct files (`zip/xlsx/csv/json/xml`). Landing pages, APIs, academic repositories and competitor pages require dedicated adapters or manual/license review; the builder does **not** scrape them.

## Generated evidence room

`data/public_trade_evidence/evidence_room/` contains 100 deterministic India→EU steel transactions, 50 suppliers and transaction-linked invoice/packing-list/MTC/CBAM/origin/TARIC evidence metadata. Twenty-five transactions carry one of five labelled faults. `fault_truth.json` is the oracle for the demo.

The existing `STEEL-100-DEMO` benchmark validates 75 READY + 25 BLOCKED → remediation → 100 READY with predecessor and provenance retention.

## Provenance

Every acquired original is immutable and addressed by SHA-256. `manifest.json` records source class, URL, license note, acquisition metadata and artifact hashes. Never overwrite an original; new upstream bytes create a new hash-addressed object.

Source classes:
- OFFICIAL / OFFICIAL_STATISTICS
- ACADEMIC_OPEN_DATA
- PUBLIC_COMPANY
- COMPETITOR_CASE
- SYNTHETIC

Competitor case studies are **scenario specifications**, not calculation goldens unless underlying inputs and expected outputs are actually published.

## Four layers

1. **Regulatory goldens (Layer 1):** EC CBAM examples/defaults/benchmarks, operator guidance, TARIC. Only direct authoritative expected outputs qualify as normative calculation oracles. Never redistributed; link + hash only.
2. **Public real-world (Layer 2):** UCI steel telemetry, DocILE/CORD/QUEST, worldsteel LCI, voestalpine EPDs, Eurostat COMEXT, UN Comtrade, Terlouw Steel_CBAM. Real inputs with provenance; landing pages/APIs never scraped. Health: `python scripts/probe_public_sources.py`.
3. **Competitor scenarios (Layer 3):** Steelforce/Spaeter/CBAMReturn workflow shapes re-implemented synthetically (COMPETITIVE-SCENARIO). Never copy vendor files verbatim.
4. **Synthetic corrupted packs (Layer 4):** `EU-STEEL-EXPORT-2026/` evidence room built by `scripts/build_evidence_room_2026.py` — ERP/LOGISTICS/QUALITY/CARBON/REGULATORY/expected layout, 2,000-row energy telemetry, corrupted derivatives with parent hashes, CHAOS-001..015 mapping, expected initial/remediation/final decisions.

## /benchmarks section

The "Real-world evidence corpus" section surfaces CLIENT-DATA-CHAOS (15 messy-supplier ingestion cases, each BLOCKED → remediated → READY) and STEEL-100-DEMO (100-transaction portfolio with provenance) alongside the legal goldens.

## Adding a prospect dataset

1. Copy/export prospect data into a private, gitignored working location.
2. Create an adapter that maps it into the same transaction/supplier/evidence contracts.
3. Never commit customer documents, credentials, personal data or confidential commercial data.
4. Run the same benchmark/decision pipeline and export only sanitized results approved for sharing.

Engineering assurance, not legal certification.
