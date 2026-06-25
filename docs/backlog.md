# MVP Backlog

## Phase 1: Foundation

- Wire real config validation and error messages
- Add persistent scan IDs and run metadata
- Add logging and structured error handling

## Phase 2: State ingestion

- Support multiple state blobs per environment
- Add state caching and etag-based revalidation
- Handle Terraform state outputs and module nesting edge cases

## Phase 3: Azure inventory

- Add ARM detail fetchers for storage accounts, NSGs, and VMs
- Batch Resource Graph queries to handle large subscription sets
- Add tenant-wide scan support where access model allows it

## Phase 4: Drift rules

- Add per-resource ignore rules
- Support severity levels by attribute path
- Add configurable treatment for unmanaged resources

## Phase 5: Interfaces

- Expose REST API endpoints for scan submission and history
- Add dashboard summaries and resource drill-down
- Add JSONL export for SIEM ingestion

## Phase 6: Platform hardening

- Add Postgres storage
- Add scheduled scan runner
- Add authn/authz for API consumers
- Add metrics, tracing, and audit logs

