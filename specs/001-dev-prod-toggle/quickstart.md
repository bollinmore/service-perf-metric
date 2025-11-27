# Quickstart: Dev/Production Mode Toggle

## Prerequisites
- Python 3.11 with virtual environment set up
- Dependencies installed via `pip install -r requirements.txt`
- `.env` file in repository root

## Local Development
1. Add mode to `.env` (invalid/missing values default to `development`):
   ```env
   SPM_MODE=development
   ```
2. Start locally:
   ```bash
   python spm.py serve
   ```
3. Verify active mode and readiness:
   - Console output at startup shows active mode and snapshot info.
   - GET `/mode` returns the current status and snapshot.
   - GET `/mode/readiness` returns the readiness checklist.

## Switch to Production Locally (for validation only)
1. Update `.env`:
   ```env
   SPM_MODE=production
   ```
2. Restart local serve: `python spm.py serve`.
3. POST `/mode` with `{"mode": "production"}` if toggling via API; snapshot is preserved automatically.
4. Readiness must be complete for Production; if incomplete, the switch response will include warnings and status `400`.

## Docker Deployment
- Containers force Production mode regardless of `.env`. Defaults are set via `SPM_MODE=production` and `SPM_FORCE_PRODUCTION=1`.
- Build/run example:
  ```bash
  docker compose up --build
  ```
  The `/mode` endpoint will report Production mode and ignore toggle requests inside Docker.

## README Update
- Document `.env` mode usage and Docker default Production behavior in `README.md`.
