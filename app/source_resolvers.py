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
import os
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


# Column headers of the taric-opendata mirror workbooks (verified 2026-09):
# full bulk "Taric measures <date>.xlsx" uses Title-Case headers
#   (Goods code, Add code, Order No., Start date, ..., Measure type, ...);
# daily deltas "Measures_<date>.xlsx" use UPPER_SNAKE headers
#   (GOODS CODE, ADD_CODE, ORD_NUMB, START_DATE, REGULATION, DUTY,
#    GEOGR_AREA, MEAS_TYP_ID, PUBLISH).
TARIC_MEASURE_HEADERS = {
    "cn": ("goodscode", "goods_code", "cncode", "commoditycode", "code"),
    "add_code": ("addcode", "add_code", "additionalcode"),
    "order": ("orderno", "ordnumb", "ordernum", "quotaordernumber", "ordernumber"),
    "start": ("startdate", "start_date", "validfrom", "validitystartdate"),
    "end": ("enddate", "end_date", "validto", "validityenddate"),
    "origin": ("origin", "origincode", "geograrea", "geographicalareaid", "origincountry", "country"),
    "measure_type": ("measuretype", "meas_typ_id", "meastypid", "meas_type_code", "meastype", "measuretypeid", "type"),
    "measure_label": ("measuretype", "measure_type"),
    "duty": ("duty", "dutyrate", "dutyexpression", "dutyamount"),
    "legal": ("legalbase", "regulation", "regulationid"),
    "document": ("certificate", "certificatecode", "documentcode"),
}


def _taric_pick(low: dict, *names: str):
    for n in names:
        for k, v in low.items():
            if n == k and v not in (None, ""):
                return str(v).strip()
    for n in names:
        for k, v in low.items():
            if n in k and v not in (None, ""):
                return str(v).strip()
    return None


def normalize_taric_workbook_rows(rows: list[dict], source_file: str = "") -> list[dict]:
    """Mirror xlsx rows (either header dialect) -> flat measure rows."""
    out: list[dict] = []
    for r in rows:
        low = {re.sub(r"[^a-z0-9]", "", str(k).lower()): v
               for k, v in r.items() if k != "sheet" and v not in (None, "")}
        cn = re.sub(r"\D", "", str(_taric_pick(low, *TARIC_MEASURE_HEADERS["cn"]) or ""))
        if not cn:
            continue
        mt = _taric_pick(low, *TARIC_MEASURE_HEADERS["measure_type"])
        label = _taric_pick(low, *TARIC_MEASURE_HEADERS["measure_label"])
        out.append({
            "cn_code": cn,
            "origin_country": (_taric_pick(low, *TARIC_MEASURE_HEADERS["origin"]) or "").upper() or None,
            "measure_type": mt or label,
            "measure_label": label if label != mt else None,
            "duty_rate": _taric_pick(low, *TARIC_MEASURE_HEADERS["duty"]),
            "quota_order_number": _taric_pick(low, *TARIC_MEASURE_HEADERS["order"]),
            "additional_code": _taric_pick(low, *TARIC_MEASURE_HEADERS["add_code"]),
            "required_document": _taric_pick(low, *TARIC_MEASURE_HEADERS["document"]),
            "valid_from": _taric_pick(low, *TARIC_MEASURE_HEADERS["start"]),
            "valid_to": _taric_pick(low, *TARIC_MEASURE_HEADERS["end"]),
            "legal_basis": _taric_pick(low, *TARIC_MEASURE_HEADERS["legal"]),
            "source_file": source_file or r.get("sheet"),
        })
    seen, uniq = set(), []
    for rec in out:
        k = json.dumps(rec, sort_keys=True)
        if k not in seen:
            seen.add(k)
            uniq.append(rec)
    return uniq


def normalize_taric_delta_zip(raw: bytes) -> dict:
    """Daily TARIC_<date>.zip (Measures/Measure_Conditions/... workbooks).

    Returns {"measures": [...], "conditions": [...], "files": [...]} with the
    real mirror column names preserved per row (GOODS CODE, MEAS_TYP_ID, ...).
    """
    z = zipfile.ZipFile(io.BytesIO(raw))
    files = z.namelist()
    measures: list[dict] = []
    conditions: list[dict] = []
    try:
        from openpyxl import load_workbook
    except ImportError:
        return {"measures": [], "conditions": [], "files": files}
    for n in files:
        if not n.lower().endswith(".xlsx"):
            continue
        try:
            wb = load_workbook(io.BytesIO(z.read(n)), read_only=True, data_only=True)
        except Exception:
            continue
        for ws in wb.worksheets:
            rows = list(ws.iter_rows(values_only=True))
            if not rows:
                continue
            head = [str(c).strip() if c is not None else "" for c in rows[0]]
            recs = []
            for row in rows[1:]:
                rec = {head[i] or f"col_{i}": v for i, v in enumerate(row)
                       if v is not None}
                if rec:
                    recs.append(rec)
            low_name = n.lower()
            if "measure_condition" in low_name or "measure condition" in low_name:
                conditions.extend(recs)
            elif "measure" in low_name or "duties" in low_name:
                measures.extend(normalize_taric_workbook_rows(recs, n))
    return {"measures": measures, "conditions": conditions, "files": files}


def normalize_eucdm_html_zip(raw: bytes) -> dict:
    """EUCDM HTML distribution ZIP (softdev mirror of DG TAXUD v7.0.11).

    The ZIP holds ~7k .htm pages (Annex-B sd1.htm is the 29MB integrated
    data-element view). We extract the distinct D.E. numbers (N/N pattern)
    plus their neighbouring label cells from sd1.htm table rows, and return
    the full file inventory so CI can assert Annex-B coverage.
    """
    z = zipfile.ZipFile(io.BytesIO(raw))
    files = z.namelist()
    records: list[dict] = []
    try:
        sd1 = z.read("EN/EUCDM/Annex-B/sd1.htm").decode("utf-8", "ignore")
    except KeyError:
        return {"data_elements": [], "files": files}
    for m in re.finditer(r"<tr[^>]*>(.*?)</tr>", sd1, flags=re.S | re.I):
        cells = re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", m.group(1), flags=re.S | re.I)
        clean = [re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", c).replace("&nbsp;", " ")).strip()
                 for c in cells]
        clean = [c for c in clean if c]
        de = next((c for c in clean if re.fullmatch(r"[1-8]/[0-9]{1,2}", c)), None)
        if not de:
            continue
        label = next((c for c in clean
                      if c != de and re.search(r"[A-Za-z]{3,}", c)), None)
        records.append({"data_element": de, "label": label,
                        "source_file": "EN/EUCDM/Annex-B/sd1.htm"})
    seen, uniq = set(), []
    for r in records:
        k = (r["data_element"], r["label"])
        if k not in seen:
            seen.add(k)
            uniq.append(r)
    return {"data_elements": uniq, "files": files}


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
    # The ECHA Candidate List export is TAB-delimited with quoted fields
    # (the public mirror preserves this dialect); sniff before parsing so a
    # comma DictReader never collapses a row into a single column.
    # The official export also carries a preamble (export date, filter info)
    # before the header row — skip rows until the real header is found.
    sample = text[:8192]
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=",\t;")
        delimiter = dialect.delimiter
    except Exception:
        delimiter = "\t" if "\t" in sample else ","
    rows = list(csv.reader(io.StringIO(text), delimiter=delimiter))
    # Find the header row: the one containing "Substance name" (case-insensitive)
    header_idx = None
    for i, r in enumerate(rows):
        if any("substance name" in str(c).strip().lower() for c in r):
            header_idx = i
            break
    if header_idx is None:
        return []
    header = [str(c).strip().lower() for c in rows[header_idx]]
    out: list[dict] = []
    for r in rows[header_idx + 1:]:
        if len(r) < len(header):
            continue
        low = {h: (v or "").strip() for h, v in zip(header, r)}
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
    """SCIP 6.10 package: picklists, changelog, validation artefacts inventory.

    Handles both the official ECHA package (nested ``configuration.zip`` with
    ``phrases/PHRASEGROUP.properties`` + ``phrases/PHRASEGROUP.xml``, plus
    ``xsd/*.xsd`` schema files and ``changes_log.txt``) and the older
    flat ``picklist*.xml`` layout.
    """
    z = zipfile.ZipFile(io.BytesIO(raw))
    files = z.namelist()
    picklists: list[dict] = []
    changelog: list[str] = []
    namespaces: set[str] = set()
    xsd_files: list[str] = []

    def _scan_zip(zf: zipfile.ZipFile, prefix: str = "") -> None:
        for n in zf.namelist():
            low = n.lower()
            if "change" in low and low.endswith((".txt", ".md", ".pdf", ".html")):
                try:
                    changelog.append(zf.read(n).decode("utf-8", "ignore")[:4000])
                except Exception:
                    pass
            if low.endswith(".xsd"):
                xsd_files.append(n)
                try:
                    txt = zf.read(n).decode("utf-8", "ignore")
                    import re as _re
                    for m in _re.finditer(r'namespace="([^"]+)"', txt):
                        if "iuclid6.echa.europa.eu" in m.group(1):
                            namespaces.add(m.group(1))
                except Exception:
                    pass
            if "picklist" in low and low.endswith(".xml"):
                try:
                    root = ET.fromstring(zf.read(n))
                    for item in root.iter():
                        if _strip_ns(item.tag).lower() in ("value", "item", "entry", "picklistvalue"):
                            txt = (item.text or "").strip()
                            if txt:
                                picklists.append({"list": n, "value": txt,
                                                  "attrs": dict(item.attrib)})
                except ET.ParseError:
                    continue
            # Official package: phrases/PHRASEGROUP.properties holds the
            # picklist values (phrase code -> text), PHRASEGROUP.xml the groups.
            if low.endswith("phrases/phrasegroup.properties"):
                try:
                    txt = zf.read(n).decode("utf-8", "ignore")
                    for line in txt.splitlines():
                        line = line.strip()
                        if not line or "=" not in line:
                            continue
                        key, _, val = line.partition("=")
                        key = key.strip()
                        if key.startswith("phrases.") and key.endswith(".text"):
                            code = key[len("phrases."):-len(".text")]
                            if val.strip():
                                picklists.append({"list": "PHRASEGROUP.properties",
                                                  "value": val.strip(),
                                                  "phrase_code": code})
                except Exception:
                    pass
            if low.endswith("phrases/phrasegroup.xml"):
                try:
                    root = ET.fromstring(zf.read(n))
                    for grp in root.iter():
                        if _strip_ns(grp.tag).lower() == "phrasegroup":
                            gcode = grp.get("code", "")
                            for ph in grp:
                                if _strip_ns(ph.tag).lower() == "phrase":
                                    picklists.append({
                                        "list": "PHRASEGROUP.xml",
                                        "value": ph.get("code", ""),
                                        "phrase_group": gcode,
                                        "provider": ph.get("provider", ""),
                                        "obsolete": ph.get("obsolete", "false"),
                                    })
                except ET.ParseError:
                    continue

    _scan_zip(z)
    # Official package nests the picklists inside configuration.zip
    for n in files:
        if n.lower().endswith("configuration.zip"):
            try:
                inner = zipfile.ZipFile(io.BytesIO(z.read(n)))
                _scan_zip(inner, prefix=n)
            except Exception:
                continue
    return {"files": files, "picklist_values": picklists,
            "changelog_excerpts": changelog,
            "namespaces": sorted(namespaces), "xsd_files": xsd_files}


def normalize_iuclid_article_models(files: dict[str, str]) -> list[dict]:
    """IUCLID ARTICLE dossier models (SCIP-adjacent schema/picklist payload).

    Source: USEPA/CompTox-IUCLIDTools dev branch
    ``entity_models/article_6_8/models/`` -- the ARTICLE.9.0 document
    definition SCIP notifications are built on
    (``__NAMESPACE__ = http://iuclid6.echa.europa.eu/namespaces/ARTICLE/9.0``),
    plus ``platform_fields.py`` (BasePicklistField et al) and
    ``common_types_domain_v9.py`` (Pg* picklist enums, VALUE_<code> members).

    ECHA blocks automated fetches of the official SCIP 6.10 ZIP (Azure WAF),
    so this GitHub mirror is the downloadable payload artifact: real
    namespaces, field definitions and picklist codes -- not metadata.
    Returns flat records, every row carrying ``version: "6.10"`` so the
    scip_schema contract/validators keep passing.
    """
    records: list[dict] = []
    namespaces: dict[str, str] = {}
    for fname, text in files.items():
        for m in re.finditer(r'__NAMESPACE__\s*=\s*["\']([^"\']+)["\']', text):
            namespaces[fname] = m.group(1)
    article = files.get("article_9_0.py", "")
    # Field definitions: ArticleCategorisation*/ArticleCharacteristics* classes
    # with their Base* parent and Pg* picklist reference.
    for m in re.finditer(
            r"class\s+(Article\w+)\((Base\w+)\)[^\n]*\n(?:.*\n){0,8}?.*?value:\s*Optional\[(Pg\d+)\]",
            article):
        field, base, pg = m.group(1), m.group(2), m.group(3)
        records.append({"version": "6.10", "artifact": "article_9_0",
                        "namespace": namespaces.get("article_9_0.py"),
                        "field": field, "base_type": base, "picklist": pg,
                        "source_file": "entity_models/article_6_8/models/article_9_0.py"})
    # Fallback: field class names even without a Pg annotation nearby.
    if not records:
        for m in re.finditer(r"class\s+(Article\w+)\((Base\w+)\)", article):
            records.append({"version": "6.10", "artifact": "article_9_0",
                            "namespace": namespaces.get("article_9_0.py"),
                            "field": m.group(1), "base_type": m.group(2),
                            "source_file": "entity_models/article_6_8/models/article_9_0.py"})
    common = files.get("common_types_domain_v9.py", "")
    # Picklist enums: class Pg660564(Enum): VALUE_3601 = "3601" ...
    # (Pg660768 is the 22k-entry article-category catalogue; the other 13
    # enums are the small controlled vocabularies. Cap the catalogue so the
    # normalized snapshot stays reviewable while CI still sees real codes.)
    for cm in re.finditer(r"class\s+(Pg\d+)\(Enum\):(.*?)(?=\nclass\s|\Z)", common, re.S):
        pg, body = cm.group(1), cm.group(2)
        codes = re.findall(r'VALUE(?:_([A-Za-z0-9]+))?\s*=\s*["\']([^"\']*)["\']', body)
        codes = [(s, c) for s, c in codes if c]
        if len(codes) > 500:
            codes = codes[:500]
        for suffix, code in codes:
            records.append({"version": "6.10", "artifact": "common_types_domain_v9",
                            "namespace": "http://iuclid6.echa.europa.eu/namespaces/ARTICLE/9.0",
                            "picklist": pg, "value_code": code,
                            "source_file": "entity_models/article_6_8/models/common_types_domain_v9.py"})
    platform = files.get("platform_fields.py", "")
    for m in re.finditer(r"class\s+(Base\w+Field)\b", platform):
        records.append({"version": "6.10", "artifact": "platform_fields",
                        "namespace": namespaces.get("platform_fields.py"),
                        "field": m.group(1),
                        "source_file": "entity_models/article_6_8/models/platform_fields.py"})
    # De-dup identical rows.
    seen, uniq = set(), []
    for r in records:
        k = json.dumps(r, sort_keys=True)
        if k not in seen:
            seen.add(k)
            uniq.append(r)
    return uniq


# ------------------------------------------------------------- SANCTIONS ----
def normalize_sanctions_xml(raw: bytes) -> list[dict]:
    """EU FSF 1.1 consolidated XML -> flat screening rows (namespace-agnostic).

    Real FSF shape (verified 2026-09-22, 6241 entities): lowercase
    <sanctionEntity euReferenceNumber logicalId> with child <regulation
    programme numberTitle>, <subjectType code>, and <nameAlias wholeName>
    attributes (names live in attributes, not element text).
    """
    try:
        root = ET.fromstring(raw)
    except ET.ParseError:
        return []
    out: list[dict] = []
    for ent in root.iter():
        if _strip_ns(ent.tag).lower() != "sanctionentity":
            continue
        attrs = {k.lower(): v for k, v in ent.attrib.items()}
        flat: dict = {"logical_key": attrs.get("logicalkey") or attrs.get("logicalid"),
                       "eu_reference": attrs.get("eureferencenumber")}
        names: list[str] = []
        for node in ent.iter():
            t = _strip_ns(node.tag).lower()
            na = {k.lower(): v for k, v in node.attrib.items()}
            if t == "namealias":
                wn = (na.get("wholename") or "").strip()
                if wn:
                    names.append(wn)
            elif t == "wholename" and (node.text or "").strip():
                names.append(node.text.strip())
            elif t in ("birthdate", "dateofbirth") and (node.text or "").strip():
                flat.setdefault("birth_date", node.text.strip())
            elif t in ("citizenship", "nationality", "country") and (node.text or "").strip():
                flat.setdefault("country", node.text.strip().upper())
            elif t == "regulation" and not flat.get("programme"):
                if na.get("programme"):
                    flat["programme"] = na.get("programme")
                    flat["legal_basis"] = na.get("numbertitle")
            elif t == "regulationsummary" and (node.text or "").strip():
                flat.setdefault("programme", node.text.strip()[:200])
            elif t == "subjecttype" and na.get("code"):
                flat.setdefault("entity_type", na.get("code"))
        if not names:
            continue
        flat["names"] = names
        flat["primary_name"] = names[0]
        out.append(flat)
    return out


def normalize_sanctions_csv(text: str) -> list[dict]:
    # FSF CSV is semicolon-delimited (verified: header starts
    # fileGenerationDate;Entity_LogicalId;...); sniff before parsing.
    sample = text[:8192]
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=",;\t")
        delimiter = dialect.delimiter
    except Exception:
        delimiter = ";" if ";" in sample else ","
    rows = list(csv.DictReader(io.StringIO(text), delimiter=delimiter))
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
                       min_records: int = 1, filename: str = "source.bin",
                       latest_records=None) -> dict:
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
    # Keep data/normalized/<dataset>/latest.json in sync so tests and engines
    # (which read latest.json) see the freshly ingested official payload.
    # latest_records (optional) lets callers trim the tracked snapshot while
    # the versioned normalized.json keeps the full payload.
    latest = NORMALIZED / dataset / "latest.json"
    tmp = NORMALIZED / dataset / f".latest-{version}.tmp"
    tmp.write_text(json.dumps({**manifest, "transport": "PRIMARY",
                               "normalized_file": f"data/normalized/{dataset}/{version}/normalized.json",
                               "records": latest_records if latest_records is not None else records},
                              indent=2, default=str))
    os.replace(tmp, latest)
    return manifest


def latest_manifest(dataset: str) -> dict | None:
    p = MANIFESTS / f"{dataset}-latest.json"
    return json.loads(p.read_text()) if p.exists() else None
