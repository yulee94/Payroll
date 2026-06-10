# Personal AI — development memo

AI assistance is routed outside repo-owned Python. Python compatibility shims were removed in G028; do not add new Python AI clients, local assistants, streaming adapters, or tests.

Future TypeScript/Rust platform chat integration:

1. Call the Rust/Kubernetes AI policy gateway from an approved server endpoint.
2. Stream provider responses through that server endpoint with cancellation and bounded error states.
3. Keep API keys in Kubernetes Secrets, an external secret manager, or service settings approved by the security contract.
4. Enforce tenant scope, audit logging, and sensitive-data redaction before prompts or files leave the trust boundary.

Detailed design backlog: `docs/AI_AGENT.md`.
