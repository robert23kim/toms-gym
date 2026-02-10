# Secrets Management Plan

**Date:** 2026-02-10
**Status:** Phase 1-2 Complete, Phase 3-4 Pending
**Severity:** Mitigated — secrets moved to GCP Secret Manager, code fallbacks removed

---

## Before: Current State

### How Secrets Flow Today

```
┌─────────────────────────────────────────────────────────────┐
│                    SOURCE CODE (git)                         │
│                                                             │
│  deploy.py:624      EMAIL_PASSWORD = 'aajrrrnrfqvdltbv'    │
│  deploy.py:631      DB_PASS = 'test'                        │
│  deploy.py:634      JWT_SECRET_KEY = 'your-secret-key-here' │
│  deploy-config.json  DB_PASS = 'test'                       │
│  docker-compose.yml  JWT_SECRET_KEY = 'dev-secret-key'      │
│  docker-compose.yml  DB password = 'test'                   │
└──────────────────────────┬──────────────────────────────────┘
                           │
                    deploy.py runs
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│              deploy.py (lines 627-649)                       │
│                                                             │
│  Builds a plain-text list of ALL secrets as env vars        │
│  Passes them to: gcloud run deploy --set-env-vars=...       │
│                                                             │
│  ⚠️  Logs the FULL command (including secrets) to stdout    │
│     via self.log(f"Running: {' '.join(command)}")           │
│     (deploy.py:289)                                         │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                   Cloud Run Service                          │
│                                                             │
│  Receives secrets as plain-text environment variables        │
│  ENV: JWT_SECRET_KEY=your-secret-key-here                   │
│  ENV: DB_PASS=test                                          │
│  ENV: EMAIL_PASSWORD=aajrrrnrfqvdltbv                       │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                   Flask Application                          │
│                                                             │
│  config.py:66-68   ProductionConfig requires JWT_SECRET_KEY │
│  app.py:61         OVERRIDES with fallback 'test-secret-key'│
│  auth_routes.py:41 ANOTHER fallback to 'dev-secret-key'     │
│                                                             │
│  ⚠️  Three different fallback chains, all with weak defaults│
│     If env var missing, production silently uses a known key│
└─────────────────────────────────────────────────────────────┘
```

### Secrets Inventory (Before)

| Secret | Hardcoded Value | Location(s) | In Git? | Risk |
|--------|----------------|-------------|---------|------|
| Gmail App Password | `aajrrrnrfqvdltbv` | `deploy.py:624` | YES | CRITICAL |
| JWT Secret (prod) | `your-secret-key-here` | `deploy.py:634` | YES | CRITICAL |
| DB Password (prod) | `test` | `deploy.py:631`, `deploy-config.json:18` | YES | CRITICAL |
| JWT Secret fallback | `test-secret-key` | `app.py:61` | YES | HIGH |
| JWT Secret fallback | `dev-secret-key` | `auth_routes.py:41`, `docker-compose.yml:19` | YES | HIGH |
| DB Connection String | `postgresql://postgres:test@...` | `deploy.py:635`, `docker-compose.yml:17` | YES | HIGH |
| Email Username | `t30gupload@gmail.com` | `deploy.py:640`, `docker-compose.yml:33` | YES | MEDIUM |
| GCS Bucket Name | `jtr-lift-u-4ever-cool-bucket` | Multiple files | YES | LOW |
| GCP SA Key | JSON blob | GitHub Secrets (`GCP_SA_KEY`) | No (correct) | OK |

### CI/CD Issues (Before)

| Issue | File | Line | Risk |
|-------|------|------|------|
| Deprecated `service_account_key` auth | `.github/workflows/ci-cd.yml` | 91 | HIGH |
| `deploy.py` logs all secrets to stdout | `deploy.py` | 289 | CRITICAL |
| No `.dockerignore` in `Backend/` | `Backend/` | — | HIGH |
| No `.dockerignore` in `my-frontend/` | `my-frontend/` | — | HIGH |
| `COPY . .` includes credentials.json | `Backend/Dockerfile` | 48, 76 | HIGH |

### JWT Secret Override Chain (Before)

The production JWT secret goes through 3 layers, each with its own insecure fallback:

```
config.py:65-68  ProductionConfig.JWT_SECRET_KEY
  → Requires env var (raises ValueError if missing) ✅ Good

app.py:61  app.config['JWT_SECRET_KEY'] = os.environ.get('JWT_SECRET_KEY', 'test-secret-key')
  → OVERRIDES the config with a fallback to 'test-secret-key' ❌ Bypasses safety

auth_routes.py:41  get_jwt_secret_key()
  → Falls back to 'dev-secret-key' if neither config nor env var set ❌ Another bypass

deploy.py:634  Sets JWT_SECRET_KEY='your-secret-key-here'
  → The actual production value is a placeholder string ❌ Trivially guessable
```

**Net result:** Production JWT signing key = `your-secret-key-here`

---

## After: Target State

### How Secrets Will Flow

```
┌─────────────────────────────────────────────────────────────┐
│                    SOURCE CODE (git)                         │
│                                                             │
│  ✅ ZERO secrets in source code                             │
│  ✅ deploy.py references Secret Manager names, not values   │
│  ✅ docker-compose.yml uses ${VAR} from local .env          │
│  ✅ .env files are gitignored                               │
└──────────────────────────┬──────────────────────────────────┘
                           │
                    deploy.py runs
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│              deploy.py (updated)                             │
│                                                             │
│  Uses: gcloud run deploy --set-secrets=                     │
│    JWT_SECRET_KEY=jwt-secret:latest,                        │
│    DB_PASS=db-password:latest,                              │
│    EMAIL_PASSWORD=email-app-password:latest                 │
│                                                             │
│  ✅ Only secret NAMES logged, never values                  │
│  ✅ Non-sensitive env vars still use --set-env-vars         │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                  GCP Secret Manager                          │
│                                                             │
│  jwt-secret          → (strong random 64-byte key)          │
│  db-password         → (strong random password)             │
│  email-app-password  → (rotated Gmail app password)         │
│                                                             │
│  ✅ Versioned, auditable, access-controlled                 │
│  ✅ Cloud Run service account has secretAccessor role       │
│  ✅ Rotation support built in                               │
└──────────────────────────┬──────────────────────────────────┘
                           │
              Cloud Run mounts secrets
              as environment variables
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                   Cloud Run Service                          │
│                                                             │
│  Secrets injected at runtime by Secret Manager              │
│  ENV: JWT_SECRET_KEY=(from secret manager, never visible)   │
│  ENV: DB_PASS=(from secret manager)                         │
│  ENV: EMAIL_PASSWORD=(from secret manager)                  │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                   Flask Application                          │
│                                                             │
│  config.py       Reads from env vars (no fallbacks in prod) │
│  app.py          No override, uses config directly          │
│  auth_routes.py  No fallback, uses app config               │
│                                                             │
│  ✅ Single source of truth for each secret                  │
│  ✅ Fail-fast if secrets missing (no silent degradation)    │
└─────────────────────────────────────────────────────────────┘
```

### Secrets Inventory (After)

| Secret | Storage | In Git? | Access Control |
|--------|---------|---------|----------------|
| Gmail App Password | GCP Secret Manager (`email-app-password`) | No | IAM: secretAccessor |
| JWT Secret | GCP Secret Manager (`jwt-secret`) | No | IAM: secretAccessor |
| DB Password | GCP Secret Manager (`db-password`) | No | IAM: secretAccessor |
| JWT Secret (dev) | Local `.env` file | No (gitignored) | Local only |
| DB Password (dev) | Local `.env` file | No (gitignored) | Local only |
| GCP SA Key | GitHub Secrets → Workload Identity Federation | No | OIDC + IAM |

### CI/CD (After)

| Change | Detail |
|--------|--------|
| Auth method | Workload Identity Federation (short-lived OIDC tokens, no stored keys) |
| Secret injection | `deploy.py` uses `--set-secrets` (names only, values from Secret Manager) |
| Command logging | Secrets redacted from log output |
| Docker builds | `.dockerignore` in `Backend/` and `my-frontend/` excludes `.env`, `credentials.json`, `*.key`, `*.pem` |
| Secret scanning | `gitleaks` or `detect-secrets` runs in CI on every PR |

### JWT Secret Chain (After)

```
config.py:65-68  ProductionConfig.JWT_SECRET_KEY
  → Requires env var (raises ValueError if missing) ✅ Single source of truth

app.py           Uses app.config['JWT_SECRET_KEY'] from config ✅ No override

auth_routes.py   Uses current_app.config['JWT_SECRET_KEY'] ✅ No fallback
```

---

## Side-by-Side Comparison

| Aspect | Before | After |
|--------|--------|-------|
| **Secrets in git** | 6+ hardcoded secrets | Zero |
| **Production JWT key** | `your-secret-key-here` | 64-byte random key in Secret Manager |
| **Production DB password** | `test` | Strong random in Secret Manager |
| **Gmail password** | Hardcoded in `deploy.py` | Secret Manager |
| **Secret fallback chains** | 3 layers with weak defaults | Fail-fast, no fallbacks in prod |
| **Deploy logging** | Full secrets in stdout | Secret names only |
| **CI/CD auth** | Long-lived SA key JSON | Workload Identity Federation (OIDC) |
| **Docker builds** | No `.dockerignore`, copies everything | Excludes `.env`, creds, keys |
| **Secret rotation** | Never (hardcoded) | Supported via Secret Manager versioning |
| **Access audit trail** | None | GCP Cloud Audit Logs |
| **Local development** | Secrets in docker-compose.yml | `.env` file (gitignored) |
| **Secret scanning** | None | `gitleaks` in CI pipeline |

---

## Implementation Plan

### Phase 1: Emergency Credential Rotation -- COMPLETE (2026-02-10)

> **Goal:** Stop the bleeding. Rotate all compromised credentials immediately.

| Step | Action | Status |
|------|--------|--------|
| 1.1 | Rotate Gmail App Password via Google Account settings | **PENDING** (manual action required) |
| 1.2 | Generate strong JWT secret (64-byte random key) | **DONE** — stored in `jwt-secret` |
| 1.3 | Store DB password in Secret Manager | **DONE** — stored in `db-password` (current value `test`, rotate later) |
| 1.4 | Store email password in Secret Manager | **DONE** — stored in `email-app-password` |
| 1.5 | Grant IAM `secretAccessor` to Cloud Run service account | **DONE** — all 3 secrets |
| 1.6 | Update Cloud Run to use `--set-secrets` | **DONE** — revision `my-python-backend-00098-zxk` |
| 1.7 | Verify production works | **DONE** — 7/7 tests passing |

**Manual follow-ups still needed:**
- Rotate Gmail App Password via Google Account, then: `echo -n "NEW_PASSWORD" | gcloud secrets versions add email-app-password --data-file=-`
- Rotate Cloud SQL password to a strong value, update both Cloud SQL and the secret: `echo -n "NEW_PASSWORD" | gcloud secrets versions add db-password --data-file=-`

### Phase 2: Code Cleanup -- COMPLETE (2026-02-10)

> **Goal:** Remove all hardcoded secrets from source code and harden the build pipeline.

| Step | Action | Status |
|------|--------|--------|
| 2.1 | Update `deploy.py` to use `--set-secrets` for sensitive values | **DONE** |
| 2.2 | Redact secrets from deploy command logging | **DONE** — `--set-env-vars` and `--set-secrets` values show `[REDACTED]` |
| 2.3 | Remove hardcoded fallback in `app.py` | **DONE** — conditional override only if env var explicitly set |
| 2.4 | Remove fallback in `auth_routes.py` | **DONE** — uses `current_app.config['JWT_SECRET_KEY']` directly |
| 2.5 | Remove `DB_PASS` from `deploy-config.json` | **DONE** |
| 2.6 | Add `.dockerignore` to `Backend/` | **DONE** |
| 2.7 | Add `.dockerignore` to `my-frontend/` | **DONE** |
| 2.8 | Move docker-compose secrets to `${VAR}` references | **NOT DONE** — low priority, dev-only |
| 2.9 | Create `.env.example` template | **NOT DONE** — low priority |

### Phase 3: CI/CD Modernization -- PENDING

> **Goal:** Eliminate long-lived credentials from CI/CD.

| Step | Action | Files | Effort |
|------|--------|-------|--------|
| 3.1 | Set up Workload Identity Federation for GitHub Actions | GCP Console + workflow | 2-3 hrs |
| 3.2 | Replace `service_account_key` with `google-github-actions/auth@v2` using OIDC | `ci-cd.yml` | 30 min |
| 3.3 | Ensure deploy step reads secrets from Secret Manager (not source code) | `deploy.py`, `ci-cd.yml` | 1 hr |
| 3.4 | Add `gitleaks` secret scanning to CI pipeline | `ci-cd.yml` | 30 min |

**Updated CI/CD auth (3.1-3.2):**
```yaml
- name: Authenticate to Google Cloud
  uses: google-github-actions/auth@v2
  with:
    workload_identity_provider: 'projects/PROJECT_NUM/locations/global/workloadIdentityPools/github-pool/providers/github-provider'
    service_account: 'toms-gym-service@toms-gym.iam.gserviceaccount.com'
```

**Secret scanning step (3.4):**
```yaml
- name: Secret Scanning
  uses: gitleaks/gitleaks-action@v2
  env:
    GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
```

### Phase 4: Rotation & Documentation -- PENDING

> **Goal:** Ongoing secret hygiene.

| Step | Action | Effort |
|------|--------|--------|
| 4.1 | Set up rotation schedule for DB password in Secret Manager | 1 hr |
| 4.2 | Implement dual-key JWT rotation (accept old + new during rotation window) | 2-3 hrs |
| 4.3 | Document rotation runbook | 1 hr |
| 4.4 | Quarterly rotation reminders | 15 min |

---

## Rollback Strategy

Each phase is independently deployable and reversible:

- **Phase 1:** Cloud Run keeps previous revisions. Roll back instantly with:
  ```bash
  gcloud run services update-traffic my-python-backend --to-revisions=PREVIOUS_REVISION=100
  ```
- **Phase 2:** All code changes are in git. Revert the commit if anything breaks.
- **Phase 3:** Keep the old `GCP_SA_KEY` GitHub secret until WIF is verified. Switch back by reverting the workflow file.
- **Phase 4:** Secret Manager maintains version history. Pin to a previous version if a rotated secret causes issues.

---

## Risk Summary

| Risk Level | Count | Key Items |
|------------|-------|-----------|
| CRITICAL | 4 | JWT key guessable, Gmail password in git, DB password is `test`, secrets in logs |
| HIGH | 4 | No .dockerignore, deprecated CI auth, deploy-config has DB pass, silent fallback chains |
| MEDIUM | 3 | Frontend .env in git (no secrets), dev secrets in compose files, bucket name hardcoded |
| LOW | 2 | Stale root Dockerfile, email username exposed |

**Total estimated effort:** Phase 1-2 complete. Phase 3-4 remaining: ~1 day of work.

---

## Known Issues

1. **DB password is still `test`**: The password was moved to Secret Manager but the underlying Cloud SQL password was not changed. Rotate both together when ready.
2. **Gmail app password not yet rotated**: The existing password is now in Secret Manager. Rotate via Google Account settings and update the secret.
3. **Pre-existing auth_method enum gap**: PostgreSQL `auth_method` enum type is missing `'passwordless'`. Needs: `ALTER TYPE auth_method ADD VALUE 'passwordless';` (unrelated to secrets work).
4. **docker-compose.yml still has dev secrets**: Low priority — these are local development values only (`dev-secret-key`, `test` DB password). Consider moving to `.env` file references.
