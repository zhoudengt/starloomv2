-- StarLoom: optional schema alignment for existing MySQL databases.
-- Use database `starloom` (or your DB name) before running:
--   mysql -u root -p starloom < scripts/migrate_starloom_optional.sql
--
-- If a column already exists, MySQL returns Error 1060 — skip that statement.
-- New installs: `create_all` on app startup creates full schema; this file is for upgrades.
-- Since app startup: `ensure_users_birth_place_columns` in `app.database.init_db` also
-- adds these columns idempotently when the API boots (or run `scripts/run_optional_migration.py`).

-- users: birth location (quicktest / profile / reports)
ALTER TABLE users ADD COLUMN birth_place_name VARCHAR(80) NULL;
ALTER TABLE users ADD COLUMN birth_place_lat DOUBLE NULL;
ALTER TABLE users ADD COLUMN birth_place_lon DOUBLE NULL;
ALTER TABLE users ADD COLUMN birth_tz VARCHAR(64) NULL;
