from pathlib import Path
def test_production_migration_has_tenant_rls():
 s=Path("migrations/001_production_tenancy.sql").read_text()
 assert "ENABLE ROW LEVEL SECURITY" in s
 assert "current_setting('app.tenant_id'" in s
 assert "evidence_objects" in s
