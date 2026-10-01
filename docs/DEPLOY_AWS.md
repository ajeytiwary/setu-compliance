# Deploy EuroSetu on AWS (App Runner, with an ECS path)

Two options, same Docker image:

- **App Runner (recommended):** fully managed, fastest to a public URL.
  Push the image to ECR, point App Runner at it, done.
- **ECS Fargate + ALB:** more control (VPC, EFS-backed SQLite persistence,
  scheduled `eurosetu-sync` tasks). Use it when the pilot grows teeth.

**Prerequisites:** an AWS account, AWS CLI v2 configured
(`aws configure`), and a region — `ap-south-1` (Mumbai) or `eu-central-1`
(Frankfurt) for EU data residency.

```bash
export REGION=ap-south-1
export ACCOUNT=$(aws sts get-caller-identity --query Account --output text)
```

---

## Option A — App Runner (15 minutes to public URL)

### 1. Push the image to ECR

```bash
aws ecr create-repository --repository-name eurosetu --region "$REGION" || true
aws ecr get-login-password --region "$REGION" \
  | docker login --username AWS --password-stdin "$ACCOUNT.dkr.ecr.$REGION.amazonaws.com"

docker build -t "$ACCOUNT.dkr.ecr.$REGION.amazonaws.com/eurosetu:latest" .
docker push "$ACCOUNT.dkr.ecr.$REGION.amazonaws.com/eurosetu:latest"
```

### 2. Create the service

Console: **App Runner → Create service → Container registry (ECR)** →
select the image → port **8000** → service name `eurosetu`.

Or via CLI:

```bash
aws apprunner create-service --region "$REGION" \
  --service-name eurosetu \
  --source-configuration "{
    \"AuthenticationConfiguration\": {\"AccessRoleArn\": \"arn:aws:iam::$ACCOUNT:role/AppRunnerECRAccessRole\"},
    \"AutoDeploymentsEnabled\": true,
    \"ImageRepository\": {
      \"ImageIdentifier\": \"$ACCOUNT.dkr.ecr.$REGION.amazonaws.com/eurosetu:latest\",
      \"ImageRepositoryType\": \"ECR\",
      \"ImageConfiguration\": {
        \"Port\": \"8000\",
        \"RuntimeEnvironmentVariables\": {\"EUROSETU_DB_PATH\": \"/tmp/eurosetu.db\"}
      }
    }
  }" \
  --instance-configuration '{"Cpu":"1024","Memory":"2048"}' \
  --health-check-configuration '{"Protocol":"HTTP","Path":"/robots.txt","Interval":10,"Timeout":5,"HealthyThreshold":1,"UnhealthyThreshold":5}'
```

App Runner gives you `https://<id>.<region>.awsapprunner.com`.
Auto-deploy means every `docker push :latest` rolls out automatically.

> **SQLite caveat (same as Cloud Run):** App Runner storage is ephemeral,
> so `/tmp/eurosetu.db` resets on redeploys. Fine for the site + demo;
> for persistent leads/contacts use Option B with EFS, or RDS Postgres
> via `app/production_db.py` + `migrations/001_production_tenancy.sql`.

### 3. Custom domain

App Runner console → **Custom domains** → add `eurosetu.example.com` →
add the DNS validation records it shows → associate. TLS is automatic.

---

## Option B — ECS Fargate + ALB (persistent, VPC-controlled)

### 1. Network and storage

```bash
# Use the default VPC for a pilot, or your own VPC/subnets.
# Create an EFS filesystem for the SQLite database so it survives restarts:
aws efs create-file-system --region "$REGION" \
  --creation-token eurosetu-data --tags Key=Name,Value=eurosetu-data
# Note the FileSystemId, then add mount targets in each subnet/zone you use.
```

### 2. Task definition (key fields)

- Image: `$ACCOUNT.dkr.ecr.$REGION.amazonaws.com/eurosetu:latest`
- Container port: `8000`, protocol TCP.
- Env: `EUROSETU_DB_PATH=/data/eurosetu.db`, `PORT=8000`.
- Mount the EFS access point at `/data`.
- Health check: `CMD-SHELL, curl -f http://127.0.0.1:8000/robots.txt || exit 1`
  (or the image's built-in `HEALTHCHECK`).
- Execution role with ECR pull + CloudWatch Logs; task role minimal.

### 3. Service + load balancer

- ALB listener 443 (ACM certificate for your domain) → target group on
  port 8000, health-check path `/robots.txt`.
- ECS service: 1–2 tasks, `awsvpc` networking, spread across two AZs.
- Security groups: ALB open to 443 from the world; tasks accept 8000
  **only from the ALB security group**.

### 4. Background sync (optional)

The repo ships `deploy/eurosetu-sync.service` + `deploy/eurosetu-sync.timer`
(systemd units). On ECS, translate the timer into an **EventBridge
Scheduler → ECS RunTask** invocation on the same task definition with a
different command override, so EU reference-data refreshes run on a cron
without a second service.

---

## Operations checklist (both options)

- **Logs:** App Runner console logs, or CloudWatch `/aws/apprunner/...`;
  ECS → CloudWatch log group on the task definition.
- **Secrets:** use SSM Parameter Store / Secrets Manager injected as
  environment variables — never bake them into the image (`.dockerignore`
  already excludes `.env` and local `*.db` files).
- **Updates:** `docker build/push` new tag → App Runner auto-deploys, or
  ECS → register new task-definition revision → update service
  (`--force-new-deployment`).
- **Backups:** for EFS, enable AWS Backup on the filesystem; for RDS,
  automated snapshots with a 7-day retention minimum for pilots.
- **Cost:** App Runner charges per vCPU/GB-hour while provisioned
  (pause the service when idle); Fargate + ALB + EFS is roughly
  $40–70/month in `ap-south-1` for a single-task pilot.
