# Data Model: Dev/Production Mode Toggle

## Entities

### Deployment Mode
- **Fields**:
  - `mode` (enum: `development`, `production`; default `development` for local serve)
  - `source` (enum: `env`, `docker-forced`)
  - `validated` (bool; true when readiness checks pass for Production)
  - `last_updated_at` (timestamp; when mode was last set)
  - `set_by` (string; optional identifier for audit logs)
- **Relationships**:
  - References `Version Snapshot` for preserved development state when switching to Production.
- **Validation Rules**:
  - `mode` must be one of the allowed enum values; invalid input triggers fallback to `development` for local serve.
  - When `mode` is `production`, `validated` must be true before allowing deployment readiness.

### Version Snapshot
- **Fields**:
  - `id` (string; development version identifier)
  - `timestamp` (timestamp; when snapshot captured)
  - `notes` (string; optional context for the snapshot)
- **Relationships**:
  - Linked from `Deployment Mode` when preserving development state before switching to Production.
- **Validation Rules**:
  - `id` required when preserving a snapshot.

### Readiness Checklist
- **Fields**:
  - `items` (list of checklist items: name, required bool, status enum `pending`/`complete`, message)
  - `last_reviewed_at` (timestamp)
- **Relationships**:
  - Evaluated when `Deployment Mode` is set to `production` to block/allow deployment readiness.
- **Validation Rules**:
  - All required items must be `complete` to mark Production mode as validated.

## State Transitions
- Development → Production: capture `Version Snapshot`, set `mode=production`, run readiness validation; if invalid, block deployment readiness and report issues.
- Production → Development: restore `Version Snapshot`, set `mode=development`, clear Production-only overrides.
