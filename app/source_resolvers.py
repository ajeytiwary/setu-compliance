"""Versioned raw -> normalized source pipeline.

Layout (gitignored except checked-in legal snapshots):
  data/raw/<dataset>/<version>/source.<ext> + .sha256 + fetch.json
  data/normalized/<dataset>/<version>/normalized.json + manifest.json
  data/manifests/<dataset>-latest.json  (pointer to current version)

Manifest fields: dataset_id, provider_id, source_url, retrieved_at,
effective_from, effective_to, sha256, content_type, record_count,
authority, legal_authority, parser_version, normalizer_version.

Engines must consume data/normalized (never raw Excel/XML directly).
Sanctions versions are never overwritten: one folder per publication date,
so a screening can always answer "what list was in force on 29 Sept?".
"""
from __future__ import annotations
import csv
import hashlib
import io
import json
import re
import urllib.request
import zipfile
import xml.etree.ElementTree as ET
from datetime import date, datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
NORMALIZED = ROOT / "data" / "normalized"
MANIFESTS = ROOT / "data" / "manifests"

PARSER_VERSION = "source_resolvers/1.0"
NORMALIZER_VERSION = "source_normalizers/1.0"
UA = "SetuCompliance/0.7 (+weekly regulatory sync)"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def _version(as_of: str | None, raw: bytes) -> str:
    day = as_of or date.today().isoformat()
    return f"{day}-{_sha(raw)[:8]}"


def fetch_url(url: str, timeout: int = 90) -> tuple[bytes, str]:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        body = r.read()
        ctype = (r.headers.get("Content-Type") or "application/octet-stream").split(";")[0].strip()
    if not body:
        raise ValueError(f"Empty response from {url}")
    return body, ctype


def write_raw(dataset: str, filename: str, raw: bytes, source_url: str,
              content_type: str = "application/octet-stream",
              as_of: str | None = None) -> dict:
    version = _version(as_of, raw)
    folder = RAW / dataset / version
    folder.mkdir(parents=True, exist_ok=True)
    (folder / filename).write_bytes(raw)
    (folder / (filename + ".sha256")).write_text(_sha(raw))
    meta = {"dataset": dataset, "version": version, "filename": filename,
            "source_url": source_url, "retrieved_at": _now(),
            "sha256": _sha(raw), "bytes": len(raw), "content_type": content_type}
    (folder / "fetch.json").write_text(json.dumps(meta, indent=2, sort_keys=True))
    return meta


def _strip_ns(tag: str) -> str:
    return tag.rsplit("}", 1)[-1] if "}" in tag else tag


# ---------------------------------------------------------------- TARIC ----
def normalize_taric_csv(text: str, source_url: str = "", as_of: str | None = None) -> dict:
    from .eu_public_data import normalize_taric
    return normalize_taric(list(csv.DictReader(io.StringIO(text))), as_of)


def normalize_taric_xml(raw: bytes) -> list[dict]:
    """Best-effort TARIC goods-nomenclature/measure XML -> flat measure rows.

    Accepts Commission TARIC bulk exports and the taric-opendata mirror shape.
    Unknown shapes yield [] (validation then refuses publication -- never invent).
    """
    try:
        root = ET.fromstring(raw)
    except ET.ParseError:
        return []
    out: list[dict] = []
    for el in root.iter():
        name = _strip_ns(el.tag).lower()
        if name not in ("measure", "goodsnomenclature", "good", "nomenclature", "row", "record"):
            continue
        kids = { _strip_ns(c.tag).lower(): (c.text or "").strip() for c in el }
        cn = re.sub(r"\D", "", kids.get("goodscode") or kids.get("cncode") or kids.get("code") or "")
        if not cn:
            continue
        out.append({
            "cn_code": cn,
            "origin_country": (kids.get("origincountry") or kids.get("country") or "").upper() or None,
            "measure_type": kids.get("measuretype") or kids.get("type"),
            "duty_rate": kids.get("dutyrate") or kids.get("duty"),
            "quota_order_number": kids.get("quotaordernumber") or kids.get("ordernumber"),
            "additional_code": kids.get("additionalcode"),
            "required_document": kids.get("documentcode") or kids.get("certificate"),
            "condition_text": kids.get("condition"),
            "measure_id": kids.get("measureid") or kids.get("id"),
            "valid_from": kids.get("validfrom") or kids.get("startdate"),
            "valid_to": kids.get("validto") or kids.get("enddate"),
        })
    # de-dup identical rows (bulk exports repeat measures per nomenclature level)
    seen, uniq = set(), []
    for r in out:
        k = json.dumps(r, sort_keys=True)
        if k not in seen:
            seen.add(k)
            uniq.append(r)
    return uniq


# ---------------------------------------------------------------- EUCDM ----
def normalize_eucdm_rows(rows: list[dict]) -> list[dict]:
    """Annex-B / code-list workbook rows -> {data_element, code, description}."""
    out: list[dict] = []
    for r in rows:
        low = {str(k).strip().lower(): v for k, v in r.items() if k != "sheet"}
        def pick(*names):
            for n in names:
                for k, v in low.items():
                    if n in k and v not in (None, ""):
                        return str(v).strip()
            return None
        el = pick("data element", "data-element", "element", "d.e.")
        code = pick("code", "value", "codelist")
        desc = pick("description", "meaning", "name", "label")
        if not (el or code or desc):
            continue
        out.append({"data_element": el, "code": code, "description": desc,
                    "source_sheet": r.get("sheet")})
    seen, uniq = set(), []
    for r in out:
        k = json.dumps(r, sort_keys=True)
        if k not in seen:
            seen.add(k)
            uniq.append(r)
    return uniq


# ----------------------------------------------------------------- ECHA ----
def normalize_echa_candidate_csv(text: str) -> list[dict]:
    rows = list(csv.DictReader(io.StringIO(text)))
    out: list[dict] = []
    for r in rows:
        low = {str(k).strip().lower(): (v or "").strip() for k, v in r.items()}
        def pick(*names):
            for n in names:
                for k, v in low.items():
                    if n in k and v:
                        return v
            return None
        name = pick("substance name", "substance", "name")
        if not name:
            continue
        out.append({
            "substance_name": name,
            "ec_number": pick("ec number", "ec no"),
            "cas_number": pick("cas number", "cas no"),
            "date_included": pick("date of inclusion", "date included", "inclusion date"),
            "reason": pick("reason for inclusion", "reason"),
            "decision": pick("decision", "decision number"),
        })
    return out


def normalize_iuclid_zip(raw: bytes) -> dict:
    """IUCLID Candidate-List reference ZIP: inventory + substance metadata."""
    z = zipfile.ZipFile(io.BytesIO(raw))
    files = z.namelist()
    substances: list[dict] = []
    for n in files:
        if n.lower().endswith((".xml", ".i6z", ".csv")) and "substance" in n.lower():
            try:
                txt = z.read(n).decode("utf-8", "ignore")
            except Exception:
                continue
            if n.lower().endswith(".csv"):
                for r in csv.DictReader(io.StringIO(txt)):
                    if any(r.values()):
                        substances.append({"source_file": n, **r})
            else:
                try:
                    root = ET.fromstring(txt.encode("utf-8", "ignore"))
                    kids = {_strip_ns(c.tag): (c.text or "").strip() for c in root.iter()}
                    substances.append({"source_file": n,
                                       "name": kids.get("Name") or kids.get("name"),
                                       "ec": kids.get("ECNumber") or kids.get("ec"),
                                       "cas": kids.get("CASNumber") or kids.get("cas")})
                except ET.ParseError:
                    continue
    return {"files": files, "substances": substances}


# ----------------------------------------------------------------- SCIP ----
def normalize_scip_zip(raw: bytes) -> dict:
    """SCIP 6.10 package: picklists, changelog, validation artefacts inventory."""
    z = zipfile.ZipFile(io.BytesIO(raw))
    files = z.namelist()
    picklists: list[dict] = []
    changelog: list[str] = []
    for n in files:
        low = n.lower()
        if "change" in low and low.endswith((".txt", ".md", ".pdf", ".html")):
            try:
                changelog.append(z.read(n).decode("utf-8", "ignore")[:4000])
            except Exception:
                pass
        if "picklist" in low and low.endswith(".xml"):
            try:
                root = ET.fromstring(z.read(n))
                for item in root.iter():
                    if _strip_ns(item.tag).lower() in ("value", "item", "entry", "picklistvalue"):
                        txt = (item.text or "").strip()
                        if txt:
                            picklists.append({"list": n, "value": txt,
                                              "attrs": dict(item.attrib)})
            except ET.ParseError:
                continue
    return {"files": files, "picklist_values": picklists, "changelog_excerpts": changelog}


# ------------------------------------------------------------- SANCTIONS ----
def normalize_sanctions_xml(raw: bytes) -> list[dict]:
    """EU FSF 1.1 consolidated XML -> flat screening rows (namespace-agnostic)."""
    try:
        root = ET.fromstring(raw)
    except ET.ParseError:
        return []
    out: list[dict] = []
    for ent in root.iter():
        if _strip_ns(ent.tag) != "SanctionEntity":
            continue
        flat = {"logical_key": ent.attrib.get("LogicalKey"),
                "eu_reference": ent.attrib.get("EUReferenceNumber")}
        names: list[str] = []
        for node in ent.iter():
            t = _strip_ns(node.tag)
            if t == "WholeName" and (node.text or "").strip():
                names.append(node.text.strip())
            elif t in ("NameAlias", "Alias") and (node.text or "").strip():
                names.append(node.text.strip())
            elif t in ("BirthDate", "Birthdate", "DateOfBirth") and (node.text or "").strip():
                flat.setdefault("birth_date", node.text.strip())
            elif t in ("Citizenship", "Nationality", "Country") and (node.text or "").strip():
                flat.setdefault("country", node.text.strip().upper())
            elif t == "RegulationSummary" and (node.text or "").strip():
                flat["programme"] = node.text.strip()[:200]
        if not names:
            continue
        flat["names"] = names
        flat["primary_name"] = names[0]
        out.append(flat)
    return out


def normalize_sanctions_csv(text: str) -> list[dict]:
    rows = list(csv.DictReader(io.StringIO(text)))
    out: list[dict] = []
    for r in rows:
        low = {str(k).strip().lower(): (v or "").strip() for k, v in r.items()}
        def pick(*names):
            for n in names:
                for k, v in low.items():
                    if n in k and v:
                        return v
            return None
        name = pick("name", "whole name", "entity")
        if not name:
            continue
        out.append({"primary_name": name,
                    "programme": pick("programme", "regulation", "regime"),
                    "listing_date": pick("listing date", "listed", "date"),
                    "country": pick("country", "citizenship", "nationality"),
                    "eu_reference": pick("eu reference", "reference")})
    return out


# ---------------------------------------------------- STEEL 2026/1457 ----
def normalize_steel_1457(html: str, source_url: str = "") -> list[dict]:
    """Implementing Regulation (EU) 2026/1457 -> per-category normalized rows.

    The annex lists 26 product categories with CN codes, country allocations
    and quota order numbers. We extract the machine-readable skeleton; the
    checked-in legal snapshot (data/eu_steel_measure_2026.json) remains the
    entitlement source until a full per-category table is imported.
    """
    cats = sorted(set(re.findall(r">\s*(\d{1,2}(?:[.\s]?[AB])?)\s*<", html)))
    orders = sorted(set(re.findall(r"09\.\d{4}", html)))
    cns = sorted(set("".join(x.split()) for x in
                     re.findall(r"\b(?:72|73)\d{2}(?:\s*\d{2}){2}\b", html)))
    rows = [{"category": c, "legal_basis": "2026/1457", "source_url": source_url or None}
            for c in cats]
    return [{"categories": cats, "order_numbers": orders, "cn_codes": cns,
             "category_rows": rows}]


# ---------------------------------------------------------------- COMEXT ----
def normalize_comext(obj: dict, reporters: list[str] | None = None,
                     partner: str = "IN", chapters: tuple[str, ...] = ("72", "73"),
                     years: tuple[str, ...] = ("2024", "2025", "2026")) -> list[dict]:
    """Eurostat/Comext dissemination JSON(-stat) -> filtered India->EU rows."""
    obs: list[dict] = []
    if isinstance(obj, dict) and "value" in obj and "dimension" in obj:
        dims = obj.get("dimension", {})
        ids = obj.get("id", [])
        sizes = obj.get("size", [])
        values = obj.get("value", {})
        labels = {k: (v.get("category", {}).get("label", {}) or {}) for k, v in dims.items()}
        import itertools
        idx_ranges = [range(s) for s in sizes]
        for combo in itertools.product(*idx_ranges):
            key = " ".join(str(i) for i in combo)
            if key not in values:
                continue
            row = {}
            for dim_i, dim_name in enumerate(ids):
                cat_idx = dims[dim_name]["category"]["index"]
                code = next((k for k, v in cat_idx.items() if v == combo[dim_i]), str(combo[dim_i]))
                row[dim_name.lower()] = labels.get(dim_name, {}).get(code, code)
            txt = json.dumps(row)
            if partner not in txt and "India" not in txt:
                continue
            if not any(ch in txt for ch in chapters):
                continue
            if not any(y in txt for y in years):
                continue
            row["value"] = values[key]
            obs.append(row)
            if len(obs) >= 20000:
                break
        return obs
    # Fallback: generic record list, filter for India + chapters 72/73.
    recs = obj if isinstance(obj, list) else obj.get("records", obj.get("data", []))
    if isinstance(recs, list):
        for r in recs:
            if not isinstance(r, dict):
                continue
            txt = json.dumps(r)
            if partner in txt and any(ch in txt for ch in chapters):
                obs.append(r)
                if len(obs) >= 20000:
                    break
    return obs


# --------------------------------------------------------------- PUBLISH ----
def publish_normalized(dataset: str, provider_id: str, source_url: str, raw: bytes,
                       records, content_type: str = "application/octet-stream",
                       authority: str = "OFFICIAL", legal_authority: bool = False,
                       as_of: str | None = None, effective_to: str | None = None,
                       min_records: int = 1, filename: str = "source.bin") -> dict:
    from .reference_validation import validate, publishable
    count = len(records) if isinstance(records, list) else 1
    check = validate(dataset, raw, records if isinstance(records, list) else [records],
                     min_records)
    if not publishable(check):
        raise ValueError(f"{dataset} failed validation: {','.join(check['errors'])}")
    raw_meta = write_raw(dataset, filename, raw, source_url, content_type, as_of)
    version = raw_meta["version"]
    folder = NORMALIZED / dataset / version
    folder.mkdir(parents=True, exist_ok=True)
    norm = {"dataset": dataset, "version": version, "as_of": as_of or date.today().isoformat(),
            "source_url": source_url, "sha256": raw_meta["sha256"],
            "record_count": count, "records": records}
    (folder / "normalized.json").write_text(json.dumps(norm, indent=2, default=str))
    manifest = {"dataset_id": dataset, "provider_id": provider_id,
                "version": version, "source_url": source_url, "retrieved_at": raw_meta["retrieved_at"],
                "effective_from": as_of or date.today().isoformat(),
                "effective_to": effective_to,
                "sha256": raw_meta["sha256"], "content_type": content_type,
                "record_count": count, "authority": authority,
                "legal_authority": legal_authority, "parser_version": PARSER_VERSION,
                "normalizer_version": NORMALIZER_VERSION,
                "raw_path": f"data/raw/{dataset}/{version}/{filename}",
                "normalized_path": f"data/normalized/{dataset}/{version}/normalized.json"}
    (folder / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True))
    MANIFESTS.mkdir(parents=True, exist_ok=True)
    (MANIFESTS / f"{dataset}-latest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True))
    return manifest


def latest_manifest(dataset: str) -> dict | None:
    p = MANIFESTS / f"{dataset}-latest.json"
    return json.loads(p.read_text()) if p.exists() else None
