-- Migration 014: one-time magic-link sign-in tokens (T15,
-- docs/plans/2026-07-06-ux-roadmap.md).
--
-- Passwordless recovery: email -> signed one-time link -> restores the
-- localStorage userId (and a JWT if the account has auth). Applied at startup
-- via app.run_startup_migrations (startup-migration pattern, like 013).
--
-- Only the SHA-256 hash of the token is stored, so a DB leak never exposes a
-- live sign-in link. Single-use is enforced by an atomic UPDATE that sets
-- used_at only WHERE used_at IS NULL AND expires_at > now(). 15-minute expiry
-- and per-email rate-limiting are driven by expires_at / created_at.

CREATE TABLE IF NOT EXISTS "MagicLinkToken" (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    token_hash TEXT NOT NULL UNIQUE,
    user_id UUID NOT NULL REFERENCES "User"(id) ON DELETE CASCADE,
    email TEXT NOT NULL,
    expires_at TIMESTAMPTZ NOT NULL,
    used_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Consume path looks up by token_hash.
CREATE INDEX IF NOT EXISTS idx_magic_link_token_hash
    ON "MagicLinkToken" (token_hash);

-- Rate-limit path counts recent rows per email.
CREATE INDEX IF NOT EXISTS idx_magic_link_email_created
    ON "MagicLinkToken" (email, created_at DESC);
