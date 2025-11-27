# Research: Dev/Production Mode Toggle

## Decisions

- **Decision**: Introduce `.env` variable `SPM_MODE` with allowed values `development` (default for local) and `production`.
  - **Rationale**: Clear, self-describing flag aligns with spec requirement to toggle modes via `.env` while keeping Production explicit.
  - **Alternatives considered**: Boolean flag (e.g., `IS_PRODUCTION`) rejected because it is less descriptive and harder to extend; command-line-only toggle rejected because spec requires `.env`.

- **Decision**: Local `python spm.py serve` reads `SPM_MODE`; invalid or missing values fall back to `development` and emit a warning.
  - **Rationale**: Keeps local experience safe-by-default and prevents accidental Production behavior when misconfigured.
  - **Alternatives considered**: Failing hard on invalid values rejected to avoid blocking local usage; silent fallback rejected to ensure users notice misconfiguration.

- **Decision**: Docker runtime forces Production mode regardless of `.env`, using container-level environment override.
  - **Rationale**: Aligns with user request and ensures deployments are always Production-grade.
  - **Alternatives considered**: Allowing `.env` inside Docker rejected due to risk of non-production deployments; detecting container context dynamically rejected as unnecessary when Docker entrypoint can set mode.

- **Decision**: Document mode behavior and examples in README (local `.env` setup, Docker default Production, how to verify active mode).
  - **Rationale**: Reduces confusion and sets expectations for contributors.
  - **Alternatives considered**: Inline code comments only rejected because user explicitly requested README update.

## Clarifications Resolved

No open NEEDS CLARIFICATION items remain; defaults chosen above satisfy spec scope.
