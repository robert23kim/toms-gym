# Database Schema and Migrations

This directory contains the database schema and migration scripts for Tom's Gym application.

## Schema Overview

The database schema is designed to be cloud-agnostic and supports both PostgreSQL and SQLite databases. The schema includes:

1. **User Management**
   - User table with OAuth integration
   - User roles (admin, user, judge)
   - Session management

2. **Competition Management**
   - Competition table with status tracking
   - Attempt submissions with video URLs
   - Scoring system

3. **Security Features**
   - UUID primary keys
   - Automatic timestamp updates
   - Session cleanup

## Files

- `schema.sql`: Complete database schema definition
- `apply_schema.py`: Script to apply schema to different database types
- `add_oauth_tables.sql`: Legacy OAuth table definitions (deprecated)

## Usage

### Local Development (SQLite)

1. Set environment variables:
   ```bash
   export DB_TYPE=sqlite
   export SQLITE_DB_PATH=toms_gym.db
   ```

2. Apply schema:
   ```bash
   python apply_schema.py
   ```

### Production (PostgreSQL)

1. Set environment variables:
   ```bash
   export DB_TYPE=postgres
   export DB_HOST=your-db-host
   export DB_NAME=your-db-name
   export DB_USER=your-db-user
   export DB_PASS=your-db-password
   export DB_PORT=5432
   ```

2. Apply schema:
   ```bash
   python apply_schema.py
   ```

### Cloud SQL (Google Cloud)

1. Set environment variables:
   ```bash
   export DB_TYPE=postgres
   export DB_HOST=/cloudsql/your-instance-connection-name
   export DB_NAME=your-db-name
   export DB_USER=your-db-user
   export DB_PASS=your-db-password
   ```

2. Apply schema:
   ```bash
   python apply_schema.py
   ```

## Schema Features

1. **UUID Primary Keys**
   - All tables use UUIDs for primary keys
   - PostgreSQL: Uses uuid-ossp extension
   - SQLite: Uses custom UUID generation

2. **Timestamps**
   - `created_at`: Record creation time
   - `updated_at`: Automatic update on record modification
   - `last_used_at`: Session tracking

3. **Indexes**
   - Optimized for common queries
   - Supports OAuth lookups
   - Improves competition date filtering

4. **Triggers**
   - Automatic `updated_at` maintenance
   - Session cleanup for expired tokens

## Best Practices

1. **Version Control**
   - Schema changes should be committed to version control
   - Use migration scripts for incremental changes

2. **Backup Strategy**
   - Regular database backups
   - Point-in-time recovery for PostgreSQL
   - SQLite file backups

3. **Security**
   - Use environment variables for credentials
   - Implement proper access controls
   - Regular security audits

4. **Performance**
   - Index optimization
   - Query optimization
   - Regular maintenance

## 008_fairway_schema.sql

Phase B of the Fairway migration. Drops flat `GolfRound`/`GolfHoleScore`/`GolfHandicap` and replaces them with `Course`, `Tee`, `Round`, `HoleScore`, `HandicapSnapshot`. Enables `pg_trgm` extension and adds a GIN trigram index on `Course.name`.

Greenfield — no data preservation. Rollback is `DROP TABLE` on the five new tables plus redeploy of the prior image.

### Caution: `BEGIN;` / `COMMIT;` inside migration SQL

Migration SQL files (including `008_fairway_schema.sql`) wrap the whole script in `BEGIN; ... COMMIT;` so they apply atomically via `psql -f` or `apply_schema.py` in prod — keep that pattern for any new migration. The test harness in `backend/tests/init_db.py` strips those boundaries before executing via SQLAlchemy, because an embedded `COMMIT` terminates SA's implicit transaction and a follow-up `conn.commit()` would then run in an inconsistent state. Do **not** remove `BEGIN;`/`COMMIT;` from the `.sql` files to "fix" a test failure — fix the harness instead.

## Troubleshooting

Common issues and solutions:

1. **Connection Issues**
   - Check environment variables
   - Verify network access
   - Confirm credentials

2. **Schema Application Failures**
   - Check database permissions
   - Verify SQL syntax compatibility
   - Review error logs

3. **Performance Issues**
   - Analyze query performance
   - Check index usage
   - Monitor resource usage 