# Security Policy

## Scope and safety posture

AlphaOption is paper-only through Phases 0–10. Live order placement must remain disabled, live option selling is out of scope, and no real account connection or credential is required for repository setup. Phase 11 is a separately reviewed decision gate, not automatic authorization. Security issues involving credentials, order routing, risk controls, or data exposure are high priority.

## Credential handling

- Never commit API keys, client codes, passwords, access/refresh/feed tokens, cookies, private keys, database passwords, or account identifiers.
- Never store **TOTP secrets/seeds** in source control, examples, fixtures, notebooks, screenshots, logs, shell history, or datasets.
- Keep local values in ignored `.env` files or an OS secret store. Use placeholder names only in `.env.example`.
- Later AWS deployments must use an encrypted secrets manager, least-privilege IAM, restricted network access, and auditable retrieval.
- Use separate credentials and permissions for development/paper and any future live environment. Grant only required market-data permissions until live use is separately approved.

## Secret rotation

Rotate credentials on a documented schedule, after personnel/device changes, after unusual authentication activity, and immediately after suspected exposure. Revoke old sessions/tokens, verify replacement access, and review recent broker/database/audit activity. Rotation must not require editing tracked files.

## Log redaction

Structured logging must denylist/redact authorization headers, API keys, passwords, tokens, TOTP values, cookies, account/client identifiers, database URLs, and sensitive request/response bodies. Do not log entire environment mappings or authentication payloads. Test redaction and limit log access/retention.

## Repository hygiene

- Use `.gitignore`, pre-commit/CI secret scanning, dependency review, and protected branches.
- Review staged diffs before every commit; never paste real secrets into issues, pull requests, chat, docs, test snapshots, or generated reports.
- Keep downloaded market data, database files, model artifacts, backtest exports, tokens, and logs outside Git.
- Treat forks and Git history as potentially permanent. Deleting a working-tree file does not remove it from history.

## Safe paper/live separation

- Default to `TRADING_MODE=paper` and `ENABLE_LIVE_ORDERS=false`; fail closed on missing or invalid configuration.
- Use separate paper and future live broker adapters. Early SmartAPI integration may call market-data/session APIs but must not expose an order-placement path.
- Any Phase 11 live adapter requires independent isolation plus explicit build, runtime, account, network, and release gates; restricted order permissions; clear UI banners; account-level risk approval; idempotency; reconciliation; audit events; kill switches; and independent review.
- Changing one environment variable, deploying to AWS, completing a profitable paper period, or merely possessing credentials must never activate live trading.
- Never infer live permission from the presence of credentials. Never silently fall back from paper to live.
- Test that live order calls are unreachable/denied in paper, backtest, replay, CI, and developer environments.

## Incident response: committed secret

1. Treat the secret as compromised; do not merely delete the file.
2. Revoke/rotate it immediately at the broker, database, cloud, or identity provider and terminate active sessions.
3. Preserve a private incident timeline and notify the repository/security owner without reposting the value.
4. Inspect access, broker orders, authentication, database, and audit logs for misuse; activate trading kill switches where relevant.
5. Remove the secret from the working tree and, with owner coordination, rewrite Git history if necessary. Coordinate force-pushes and ask collaborators to re-clone.
6. Re-run secret scans, verify replacement credentials, document impact/remediation, and add a preventive control.

Report vulnerabilities privately to the repository owner. Do not open a public issue containing exploit details, credentials, account information, or TOTP material.
