"""Release checks for the Cloudflare Pages artifact, independent of FastAPI."""
from __future__ import annotations

import importlib.util
import json
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("build_public_site", ROOT / "scripts" / "build_public_site.py")
assert spec and spec.loader
builder = importlib.util.module_from_spec(spec)
spec.loader.exec_module(builder)


class Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.urls = []

    def handle_starttag(self, tag, attrs):
        if tag in {"a", "script", "link"}:
            self.urls.extend(value for key, value in attrs if key in {"href", "src"} and value)


def test_public_build_routes_and_isolation(tmp_path):
    out = tmp_path / "site"
    builder.build(out)
    assert (out / "index.html").exists()
    assert (out / "demo" / "index.html").exists()
    assert (out / "guides" / "index.html").exists()
    assert (out / "benchmarks" / "index.html").exists()
    assert (out / "api" / "tools" / "supplier-template.csv").exists()
    forbidden = {"demo.js", "case-study.js", "pilot.js", "app.js", "admin.html", "pilot.html", "real-dossier.html"}
    assert not forbidden.intersection({p.name for p in out.rglob("*")})
    assert not any(p.suffix in {".db", ".pdf", ".env"} for p in out.rglob("*"))
    assert "https://app.eurosetu.trade/demo" in (out / "demo" / "index.html").read_text()
    assert "/api/benchmarks/releases" not in (out / "benchmarks.js").read_text()

    for html in out.rglob("*.html"):
        data = html.read_text()
        assert "hello@eusetu.trade" not in data, html
        assert data.count('rel="canonical"') == 1, html
        parser = Links()
        parser.feed(data)
        for url in parser.urls:
            if not url.startswith("/") or url.startswith("//"):
                continue
            route = url.split("?", 1)[0].split("#", 1)[0]
            if route.startswith("/api/") and route != "/api/tools/supplier-template.csv":
                continue  # Narrow Pages Functions routes.
            dest = out / route.lstrip("/")
            assert dest.is_file() or (dest / "index.html").is_file(), (html, url)

    sitemap = (out / "sitemap.xml").read_text()
    assert "https://eurosetu.trade/benchmarks" in sitemap
    assert "https://eurosetu.trade/pilot" not in sitemap


def test_released_benchmark_cases_are_immutable_files(tmp_path):
    out = tmp_path / "site"
    builder.build(out)
    releases = json.loads((out / "benchmarks" / "releases.json").read_text())
    for release in releases:
        commit = release["commit"]
        summary = json.loads((out / "benchmarks" / commit / "summary.json").read_text())
        results = json.loads((out / "benchmarks" / commit / "results.json").read_text())
        assert summary["code_commit"] == commit
        assert len(results) == summary["total_cases"]
        for result in results:
            case = out / "benchmarks" / commit / "cases" / result["suite_id"] / f'{result["case_id"]}.json'
            assert json.loads(case.read_text()) == result
