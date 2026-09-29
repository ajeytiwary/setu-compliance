CREATE EXTENSION IF NOT EXISTS pgcrypto;
CREATE TABLE IF NOT EXISTS tenants(id uuid PRIMARY KEY DEFAULT gen_random_uuid(),slug text UNIQUE NOT NULL,name text NOT NULL,created_at timestamptz NOT NULL DEFAULT now());
CREATE TABLE IF NOT EXISTS app_users(id uuid PRIMARY KEY DEFAULT gen_random_uuid(),tenant_id uuid NOT NULL REFERENCES tenants(id),subject text NOT NULL,roles text[] NOT NULL DEFAULT '{}',UNIQUE(tenant_id,subject));
CREATE TABLE IF NOT EXISTS evidence_objects(id uuid PRIMARY KEY DEFAULT gen_random_uuid(),tenant_id uuid NOT NULL REFERENCES tenants(id),shipment_ref text NOT NULL,sha256 text NOT NULL,object_uri text NOT NULL,media_type text,issuer text,valid_until date,created_at timestamptz NOT NULL DEFAULT now(),UNIQUE(tenant_id,sha256));
CREATE TABLE IF NOT EXISTS regulatory_snapshots(id uuid PRIMARY KEY DEFAULT gen_random_uuid(),dataset text NOT NULL,version text NOT NULL,source_url text NOT NULL,sha256 text NOT NULL,record_count bigint NOT NULL,validation_status text NOT NULL,published_at timestamptz NOT NULL DEFAULT now());
ALTER TABLE app_users ENABLE ROW LEVEL SECURITY;
ALTER TABLE evidence_objects ENABLE ROW LEVEL SECURITY;
CREATE POLICY tenant_users ON app_users USING (tenant_id::text=current_setting('app.tenant_id',true)) WITH CHECK (tenant_id::text=current_setting('app.tenant_id',true));
CREATE POLICY tenant_evidence ON evidence_objects USING (tenant_id::text=current_setting('app.tenant_id',true)) WITH CHECK (tenant_id::text=current_setting('app.tenant_id',true));
