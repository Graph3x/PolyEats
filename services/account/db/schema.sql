CREATE TABLE accounts (
  account_id    TEXT PRIMARY KEY DEFAULT gen_random_uuid()::text,
  email         TEXT NOT NULL UNIQUE,
  password_hash TEXT NOT NULL,
  role          TEXT NOT NULL DEFAULT 'user',
  epoch         BIGINT NOT NULL DEFAULT 1
);
