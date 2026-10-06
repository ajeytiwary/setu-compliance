"""Build the allowlisted, database-free Cloudflare Pages website.

Usage: python scripts/build_public_site.py [output-directory]
The output directory is disposable; no application data directory is traversed.
"""
from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from app import content_pages as pages  # noqa: E402
from app.content_hub import GUIDE_INDEX, shell  # noqa: E402

PUBLIC_HOST = "https://eurosetu.trade"
APP_HOST = "https://app.eurosetu.trade"
STATIC = ROOT / "app" / "static"
BENCHMARKS = ROOT / "web" / "benchmarks"

GENERATED = {
    "product": pages.product_page,
    "workflow": pages.workflow_page,
    "pricing": pages.pricing_page,
    "brokers": pages.brokers_page,
    "liability-preview": pages.liability_page,
    "threshold-checker": pages.threshold_page,
    "carbon-price-relief": pages.relief_page,
    "cbam-rate": pages.rate_page,
    "guides": pages.guides_index_page,
    "worked-example": pages.worked_example_page,
    "supplier-data-template": pages.supplier_template_page,
    "security": pages.security_page,
    "faq": pages.faq_page,
    "sectors": pages.sectors_page,
    "account": pages.account_page,
    "changelog": pages.changelog_page,
}
STATIC_PAGES = ("index", "trust", "case-study", "benchmarks")
STATIC_ASSETS = ("favicon.svg", "public.css", "public.js", "benchmarks.js")


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _html(value: str, route: str) -> str:
    # Source content remains host-agnostic for local FastAPI; the public artifact
    # alone gets absolute canonicals and corrected contact address.
    value = value.replace("hello@eusetu.trade", "hello@eurosetu.trade")
    value = value.replace('href="/pilot"', f'href="{APP_HOST}/pilot"')
    value = value.replace('href="/workflow-run"', f'href="{APP_HOST}/workflow-run"')
    canonical = f'{PUBLIC_HOST}{route}'
    if 'rel="canonical"' in value:
        return value
    return value.replace("</head>", f'<link rel="canonical" href="{canonical}"></head>', 1)


def _page(out: Path, route: str, html: str) -> None:
    path = out / "index.html" if route == "/" else out / route.lstrip("/") / "index.html"
    _write(path, _html(html, route))


def build(out: Path) -> None:
    out = out.resolve()
    if out == ROOT or out in ROOT.parents or (ROOT in out.parents and ROOT / "dist" not in (out, *out.parents)):
        raise ValueError("output cannot replace source or application data")
    marker = out / ".eurosetu-public-build"
    if out.exists():
        if not marker.is_file():
            raise ValueError("refusing to replace an unmarked directory")
        shutil.rmtree(out)
    out.mkdir(parents=True)
    marker.write_text("generated public files only\n", encoding="utf-8")

    routes = ["/"]
    for name in STATIC_PAGES:
        route = "/" if name == "index" else f"/{name}"
        _page(out, route, (STATIC / f"{name}.html").read_text(encoding="utf-8"))
        if route != "/":
            routes.append(route)
    _page(out, "/demo", (STATIC / "demo-landing.html").read_text(encoding="utf-8"))
    routes.append("/demo")
    for name, fn in GENERATED.items():
        _page(out, f"/{name}", shell(*fn()))
        routes.append(f"/{name}")
    for slug in sorted(GUIDE_INDEX):
        result = pages.guide_page(slug)
        if result is None:
            raise ValueError(f"missing guide {slug}")
        _page(out, f"/guides/{slug}", shell(*result))
        routes.append(f"/guides/{slug}")
    for kind in ("privacy", "terms", "dpa"):
        _page(out, f"/{kind}", shell(*pages.legal_page(kind)))
        routes.append(f"/{kind}")

    for name in STATIC_ASSETS:
        data = (STATIC / name).read_text(encoding="utf-8") if name.endswith(".js") else None
        if name == "benchmarks.js":
            data = data.replace("Source: /api/benchmarks/releases → /api/benchmarks/releases/{commit}.", "Source: /benchmarks/releases.json → /benchmarks/{commit}/summary.json.")
            data = data.replace('"/api/benchmarks/releases"', '"/benchmarks/releases.json"')
            data = data.replace('"/api/benchmarks/releases/" + latest', '"/benchmarks/" + latest + "/summary.json"', 1)
            data = data.replace('"/api/benchmarks/releases/" + latest + "/results"', '"/benchmarks/" + latest + "/results.json"')
            data = data.replace('"/api/benchmarks/releases/" + summary.code_commit +\n            "/cases/"', '"/benchmarks/" + summary.code_commit +\n            "/cases/"')
            data = data.replace('encodeURIComponent(r.case_id);', 'encodeURIComponent(r.case_id) + ".json";')
        if data is not None:
            _write(out / name, data)
        else:
            shutil.copyfile(STATIC / name, out / name)

    releases = json.loads((BENCHMARKS / "releases.json").read_text(encoding="utf-8"))
    shutil.copyfile(BENCHMARKS / "releases.json", out / "benchmarks" / "releases.json")
    for release in releases:
        commit = release["commit"]
        if not isinstance(commit, str) or not commit.isalnum():
            raise ValueError("invalid benchmark release commit")
        source = BENCHMARKS / commit
        summary = json.loads((source / "summary.json").read_text(encoding="utf-8"))
        results = json.loads((source / "results.json").read_text(encoding="utf-8"))
        if summary["code_commit"] != commit:
            raise ValueError(f"benchmark commit mismatch: {commit}")
        dest = out / "benchmarks" / commit
        dest.mkdir(parents=True)
        for filename in ("summary.json", "results.json"):
            shutil.copyfile(source / filename, dest / filename)
        for result in results:
            suite = result["suite_id"]
            case = result["case_id"]
            if any("/" in item or item in {".", ".."} for item in (suite, case)):
                raise ValueError("invalid benchmark case path")
            _write(dest / "cases" / suite / f"{case}.json", json.dumps(result, ensure_ascii=False, indent=2) + "\n")

    _write(out / "api" / "tools" / "supplier-template.csv", pages.SUPPLIER_CSV)
    _write(out / "robots.txt", "User-agent: *\nAllow: /\nSitemap: https://eurosetu.trade/sitemap.xml\n")
    _write(out / "sitemap.xml", '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' + "".join(f"<url><loc>{PUBLIC_HOST}{route}</loc></url>\n" for route in sorted(routes)) + "</urlset>\n")
    _write(out / "_headers", "/api/*\n  Cache-Control: no-store\n/benchmarks/*\n  Cache-Control: public, max-age=3600\n/benchmarks/*/cases/*\n  Cache-Control: public, max-age=31536000, immutable\n")
    _write(out / "_redirects", "/pilot https://app.eurosetu.trade/pilot 302\n/admin https://app.eurosetu.trade/admin 302\n/workflow-run https://app.eurosetu.trade/workflow-run 302\n/real-dossier https://app.eurosetu.trade/real-dossier 302\n/dossier-demo https://app.eurosetu.trade/dossier-demo 302\n")


if __name__ == "__main__":
    build(Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "dist" / "public")
