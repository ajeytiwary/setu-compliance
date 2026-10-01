-- EuroSetu production tenant isolation (PostgreSQL)
-- Apply through the deployment migration runner before enabling customer traffic.
CREATE TABLE IF NOT EXISTS tenants(id text PRIMARY KEY,name text NOT NULL);
CREATE TABLE IF NOT EXISTS tenant_memberships(
 tenant_id text NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
 subject text NOT NULL,
 roles text[] NOT NULL DEFAULT '{}',
 PRIMARY KEY(tenant_id,subject)
);
ALTER TABLE shipments ADD COLUMN IF NOT EXISTS tenant_id text REFERENCES tenants(id);
ALTER TABLE suppliers ADD COLUMN IF NOT EXISTS tenant_id text REFERENCES tenants(id);
ALTER TABLE evidence_requests ADD COLUMN IF NOT EXISTS tenant_id text REFERENCES tenants(id);
ALTER TABLE supplier_evidence ADD COLUMN IF NOT EXISTS tenant_id text REFERENCES tenants(id);
ALTER TABLE audit_events ADD COLUMN IF NOT EXISTS tenant_id text REFERENCES tenants(id);

ALTER TABLE shipments ENABLE ROW LEVEL SECURITY;
ALTER TABLE suppliers ENABLE ROW LEVEL SECURITY;
ALTER TABLE evidence_requests ENABLE ROW LEVEL SECURITY;
ALTER TABLE supplier_evidence ENABLE ROW LEVEL SECURITY;
ALTER TABLE audit_events ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS tenant_shipments ON shipments;
CREATE POLICY tenant_shipments ON shipments USING (tenant_id=current_setting('app.tenant_id',true)) WITH CHECK (tenant_id=current_setting('app.tenant_id',true));
DROP POLICY IF EXISTS tenant_suppliers ON suppliers;
CREATE POLICY tenant_suppliers ON suppliers USING (tenant_id=current_setting('app.tenant_id',true)) WITH CHECK (tenant_id=current_setting('app.tenant_id',true));
DROP POLICY IF EXISTS tenant_requests ON evidence_requests;
CREATE POLICY tenant_requests ON evidence_requests USING (tenant_id=current_setting('app.tenant_id',true)) WITH CHECK (tenant_id=current_setting('app.tenant_id',true));
DROP POLICY IF EXISTS tenant_supplier_evidence ON supplier_evidence;
CREATE POLICY tenant_supplier_evidence ON supplier_evidence USING (tenant_id=current_setting('app.tenant_id',true)) WITH CHECK (tenant_id=current_setting('app.tenant_id',true));
DROP POLICY IF EXISTS tenant_audit ON audit_events;
CREATE POLICY tenant_audit ON audit_events USING (tenant_id=current_setting('app.tenant_id',true)) WITH CHECK (tenant_id=current_setting('app.tenant_id',true));
