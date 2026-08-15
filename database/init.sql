-- SigmaCloud AI - PostgreSQL bootstrap
--
-- Intentionally does NOT create application tables.
--
-- SQLAlchemy owns the schema and creates every table at startup
-- (Base.metadata.create_all), including columns this file used to omit -
-- `users`, and the `user_id` foreign keys that scope data per account.
-- When this script created the tables first, create_all() saw them already
-- present and skipped them, leaving the app running against a schema missing
-- the ownership columns.
--
-- Keep provider-level setup (extensions, roles, grants) here instead.

-- Case-insensitive text and trigram search are useful for dataset name lookups.
CREATE EXTENSION IF NOT EXISTS pg_trgm;
