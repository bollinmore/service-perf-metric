# Quickstart: Dev/Production Mode Toggle

## Prerequisites
- Python 3.11 with virtual environment set up
- Dependencies installed via `pip install -r requirements.txt`
- `.env` file in repository root

## Local Development
1. Add mode to `.env`:
   ```env
   SPM_MODE=development
   ```
2. Start locally:
   ```bash
   python spm.py serve
   ```
3. Verify active mode via log/output or GET `/mode` if the API endpoint is exposed.

## Switch to Production Locally (for validation only)
1. Update `.env`:
   ```env
   SPM_MODE=production
   ```
2. Restart local serve: `python spm.py serve`.
3. Ensure readiness checklist passes before attempting any deployment.

## Docker Deployment
- Docker images must set `SPM_MODE=production` (or equivalent) at container start; `.env` inside the repo should not override container defaults.
- Build/run example:
  ```bash
  docker compose up --build
  ```

## README Update
- Document `.env` mode usage and Docker default Production behavior in `README.md`.
