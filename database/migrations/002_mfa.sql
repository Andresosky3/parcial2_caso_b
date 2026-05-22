ALTER TABLE jugadores
ADD COLUMN IF NOT EXISTS mfa_secret_encrypted TEXT;

ALTER TABLE jugadores
ADD COLUMN IF NOT EXISTS mfa_enabled_at TIMESTAMP;

ALTER TABLE jugadores
ADD COLUMN IF NOT EXISTS mfa_last_verified_at TIMESTAMP;