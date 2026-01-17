# HTTPS Deployment Change Plan (Docker)

## Goal
- Provide browser access via `https://<FQDN>` for the Dockerized service.
- Use HTTPS only in Production; keep HTTP for Development.
- Reuse the existing GoDaddy (company CA) certificate.

## Current State (Assumptions)
- The app runs in a Docker container and listens on `http://0.0.0.0:6231`.
- Access today is via `http://<IP>:6231` on the internal network/VPN.
- A valid certificate and private key are available on the host.

## Target Architecture
- HTTPS terminates at a reverse proxy (Nginx).
- The app container continues to serve HTTP internally.
- Only `443` is exposed to clients (optionally redirect `80` to `443`).

## Option A: Host Nginx (Recommended)
1. Run the app container bound to loopback only:
   - `-p 127.0.0.1:6231:6231`
2. Install and configure Nginx on the host.
3. Configure Nginx to:
   - Listen on `443` with the GoDaddy cert/key.
   - Proxy to `http://127.0.0.1:6231`.
   - Redirect `80` -> `443` (optional but typical).
4. Open firewall for `443` (VPN internal only); keep `6231` closed externally.

## Option B: Reverse Proxy Container
1. Add an Nginx container to `docker-compose`.
2. Place the cert/key on the host and mount into the Nginx container.
3. `proxy_pass` to `http://spm:6231` over the Docker network.
4. Expose only `443` (and optionally `80`) to the internal network.

## Production vs Development
- Production:
  - Set `SPM_MODE=production`.
  - Run app container with the standard HTTP port.
  - Access via `https://<FQDN>`.
- Development:
  - Set `SPM_MODE=development` (or unset).
  - Access via `http://<IP>:6231` or `http://localhost:6231`.

## Required Inputs
- `FQDN` to use for HTTPS.
- Certificate chain file path (full chain).
- Private key file path.
- Decide between Option A (host Nginx) or Option B (proxy container).

## Change Steps (High Level)
1. Confirm FQDN DNS points to the Linux host (VPN-resolvable).
2. Place cert + key on the host with restricted permissions.
3. Implement reverse proxy (Option A or B).
4. Update `docker-compose.yml` if using Option B.
5. Verify:
   - `https://<FQDN>` loads.
   - `http://<IP>:6231` still works for dev.
   - No external access to `6231`.

## Rollback
- Stop the reverse proxy service/container.
- Revert firewall changes if any.
- Access service via `http://<IP>:6231` as before.
