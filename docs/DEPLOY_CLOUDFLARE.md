# Deploy EuroSetu as a public website on Cloudflare (recommended path)

This is the easiest way to put the EuroSetu landing site and demo online.
You keep the app running on **your own machine or server** and Cloudflare
publishes it to the public internet through a secure tunnel. No open ports,
no firewall rules, no static IP.

**What you get:** `https://eurosetu.example.com` (or any domain you own)
serving the landing page (`/`), trust page (`/trust`), case study
(`/case-study`), and the gated demo (`/demo`).

**What you need:**
- A Cloudflare account (free tier is enough) and a domain whose DNS is on Cloudflare.
- Docker on the machine that will run the app (any laptop, VM, or office server).
- About 20 minutes.

---

## 1. Build and start the app locally

```bash
cd /home/plasmion/git/eurosetu-market-access-mvp-production

# Build the image (uses Dockerfile at the repo root)
docker build -t eurosetu:latest .

# Run it with a persistent database volume
docker run -d --name eurosetu \
  --restart unless-stopped \
  -p 127.0.0.1:8000:8000 \
  -v eurosetu-data:/app/data \
  -e EUROSETU_DB_PATH=/app/data/eurosetu.db \
  eurosetu:latest

# Sanity check (should print 200)
curl -o /dev/null -s -w "%{http_code}\n" http://127.0.0.1:8000/
curl -o /dev/null -s -w "%{http_code}\n" http://127.0.0.1:8000/trust
curl -o /dev/null -s -w "%{http_code}\n" http://127.0.0.1:8000/demo
```

The `-v eurosetu-data:/app/data` volume keeps the SQLite database
(`EUROSETU_DB_PATH=/app/data/eurosetu.db`) across container restarts.
Without it, demo leads and contact submissions vanish on every restart.

## 2. Install `cloudflared` on the same machine

```bash
# Debian / Ubuntu
curl -fsSL https://pkg.cloudflare.com/cloudflare-main.gpg | sudo tee /usr/share/keyrings/cloudflare-main.gpg >/dev/null
echo "deb [signed-by=/usr/share/keyrings/cloudflare-main.gpg] https://pkg.cloudflare.com/cloudflared $(lsb_release -cs) main" \
  | sudo tee /etc/apt/sources.list.d/cloudflared.list
sudo apt update && sudo apt install -y cloudflared

# macOS
brew install cloudflared
```

## 3. Create the tunnel

```bash
# Log in to Cloudflare (opens a browser window once)
cloudflared tunnel login

# Create a named tunnel
cloudflared tunnel create eurosetu

# Note the tunnel ID it prints, e.g. 6f9a…-… — you need it below.
```

## 4. Route your domain to the tunnel

Create a DNS record in the Cloudflare dashboard
(**Websites → your domain → DNS → Add record**):

| Type  | Name     | Target                          | Proxy |
|-------|----------|---------------------------------|-------|
| CNAME | eurosetu | `<TUNNEL-ID>.cfargotunnel.com`  | ON (orange cloud) |

Or from the CLI:

```bash
cloudflared tunnel route dns eurosetu eurosetu.example.com
```

## 5. Point the tunnel at the app

Create `/etc/cloudflared/config.yml` (or `~/.cloudflared/config.yml`):

```yaml
tunnel: <TUNNEL-ID>
credentials-file: /root/.cloudflared/<TUNNEL-ID>.json

ingress:
  - hostname: eurosetu.example.com
    service: http://127.0.0.1:8000
    originRequest:
      noTLSVerify: false
  - service: http_status:404
```

Start the tunnel:

```bash
# Foreground (good for a first test)
cloudflared tunnel --config /etc/cloudflared/config.yml run eurosetu

# Background as a service (recommended for production)
sudo cloudflared service install
sudo systemctl enable --now cloudflared
```

Visit `https://eurosetu.example.com` — you should see the landing page.
Click a card: the "Contact now" button appears, opens the contact dialog,
and submits to `POST /api/contact` through the tunnel.

## 6. Harden it (recommended before sharing the link)

1. **HTTPS is automatic.** Cloudflare terminates TLS at the edge; the
   tunnel itself is encrypted end-to-end. Leave "SSL/TLS → Full (strict)".
2. **Lock down the demo gate.** The `/demo` page is behind a lead form
   (`require_lead`), but rotate nothing secret — there are no static
   credentials in this build. If you add any, put them in environment
   variables (`-e NAME=value`), never in the image.
3. **Back up the database volume** on a schedule:
   ```bash
   docker run --rm -v eurosetu-data:/data -v "$PWD":/backup \
     alpine tar czf /backup/eurosetu-data-$(date +%F).tgz -C /data .
   ```
4. **Updates:** rebuild and swap the container; the volume keeps your data:
   ```bash
   docker build -t eurosetu:latest . \
     && docker stop eurosetu && docker rm eurosetu \
     && docker run -d --name eurosetu --restart unless-stopped \
          -p 127.0.0.1:8000:8000 -v eurosetu-data:/app/data \
          -e EUROSETU_DB_PATH=/app/data/eurosetu.db eurosetu:latest
   ```

## Troubleshooting

| Symptom | Fix |
|---|---|
| `502 Bad Gateway` from Cloudflare | App container is down or not on port 8000: `docker logs eurosetu`, `curl http://127.0.0.1:8000/robots.txt`. |
| Tunnel shows "inactive" | `cloudflared tunnel list`; re-run with the right `--config` path and tunnel name. |
| Contact form returns 500 | Check `docker logs eurosetu` — usually the DB volume is unwritable; ensure `/app/data` is owned by uid 10001 (the image handles this by default). |
| CSS/JS not loading | They are served by the app itself (`/public.css`, `/public.js`); if `/` loads, they load. Hard-refresh (`Ctrl+Shift+R`). |

## When to move off this path

Cloudflare Tunnel is ideal for pilots and demos. If you need autoscaling,
zero-downtime deploys, or a managed database, move to
[Google Cloud Run](DEPLOY_GOOGLE_CLOUD.md) or [AWS App Runner / ECS](DEPLOY_AWS.md)
— the same Docker image works on all three without changes.
