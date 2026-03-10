# Reputation V2 Migration Plan

## Overview

This document describes the migration path from the V1 reputation model (single `score` integer in `agent_scores`) to the V2 model (`reputation_profiles` table with dimensional scoring, confidence, and event tracking).

## Schema comparison

### V1: `agent_scores`

| Column | Type | Description |
|--------|------|-------------|
| actor_id | TEXT PK | DID identifier (did:8004:0x...) |
| score | INTEGER | Single composite score, starts at 100 |
| updated_at | INTEGER | Unix epoch of last update |

### V2: `reputation_profiles`

| Column | Type | Description |
|--------|------|-------------|
| actor_id | TEXT PK | DID identifier (did:8004:0x...) |
| model_version | TEXT | Schema version ("2.0.0-draft") |
| service_score | INTEGER | Points from service quality (completions, SLA adherence) |
| court_score | INTEGER | Points from dispute outcomes (wins/losses) |
| reliability_score | INTEGER | Points from overall reliability (completions + filing accuracy) |
| event_count | INTEGER | Total reputation events processed |
| successful_event_count | INTEGER | Events with positive outcomes |
| dispute_event_count | INTEGER | Events from dispute resolutions |
| confidence | REAL | Statistical confidence 0.1–1.0, based on event count |
| updated_at | INTEGER | Unix epoch of last update |

### Supporting table: `score_events`

Already present in both V1 and V2. Contains full event history needed for replay-based migration.

| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER PK | Auto-increment |
| actor_id | TEXT | DID identifier |
| delta | INTEGER | Score change |
| reason | TEXT | Event type (completed_without_dispute, won_dispute, lost_dispute, lost_as_filer) |
| event_key | TEXT UNIQUE | Idempotency key |
| payload_json | TEXT | Event metadata |
| created_at | INTEGER | Unix epoch |

## Migration strategy

### Approach: Replay from event log

The V2 profile can be reconstructed entirely from `score_events`. This is the safest approach because:

1. `score_events` is append-only with unique `event_key` — no data loss risk
2. The `component_deltas()` function deterministically maps `(reason, delta)` → dimensional scores
3. `confidence_for_event_count()` is a pure function of total event count
4. No external data sources needed

### When migration runs

Migration is **not needed for fresh deployments** — `_init_db()` creates all tables with `CREATE TABLE IF NOT EXISTS`, so new databases start with both V1 and V2 tables.

Migration is only needed when:
- An existing `verdict_reputation.db` has `agent_scores` + `score_events` data but no `reputation_profiles` rows
- This happens when upgrading from a pre-V2 deployment

### Detection

```python
# Check if migration is needed
profile_count = conn.execute("SELECT COUNT(*) FROM reputation_profiles").fetchone()[0]
event_count = conn.execute("SELECT COUNT(*) FROM score_events").fetchone()[0]
needs_migration = event_count > 0 and profile_count == 0
```

## Migration script

```sql
-- Step 1: Ensure the V2 table exists (idempotent)
CREATE TABLE IF NOT EXISTS reputation_profiles (
  actor_id TEXT PRIMARY KEY,
  model_version TEXT NOT NULL,
  service_score INTEGER NOT NULL DEFAULT 0,
  court_score INTEGER NOT NULL DEFAULT 0,
  reliability_score INTEGER NOT NULL DEFAULT 0,
  event_count INTEGER NOT NULL DEFAULT 0,
  successful_event_count INTEGER NOT NULL DEFAULT 0,
  dispute_event_count INTEGER NOT NULL DEFAULT 0,
  confidence REAL NOT NULL DEFAULT 0.1,
  updated_at INTEGER NOT NULL DEFAULT (unixepoch())
);

-- Step 2: Seed a profile row for every known actor
INSERT OR IGNORE INTO reputation_profiles (actor_id, model_version)
SELECT DISTINCT actor_id, '2.0.0-draft'
FROM score_events;

-- Step 3: Rebuild dimensional scores from event history
-- This must be done in application code because component_deltas()
-- contains business logic that maps reason → dimensional scores.
```

```python
"""Replay-based migration from V1 to V2 reputation profiles."""
from reputation_service.scorer import (
    MODEL_VERSION,
    component_deltas,
    confidence_for_event_count,
)

def migrate_v1_to_v2(conn):
    """Rebuild reputation_profiles from score_events history."""
    # Get all actors with events
    actors = conn.execute(
        "SELECT DISTINCT actor_id FROM score_events"
    ).fetchall()

    for (actor_id,) in actors:
        # Ensure profile row exists
        conn.execute(
            "INSERT OR IGNORE INTO reputation_profiles (actor_id, model_version) VALUES (?, ?)",
            (actor_id, MODEL_VERSION),
        )

        # Replay all events in order
        events = conn.execute(
            "SELECT delta, reason FROM score_events WHERE actor_id = ? ORDER BY id ASC",
            (actor_id,),
        ).fetchall()

        totals = {"service": 0, "court": 0, "reliability": 0,
                  "successful_events": 0, "dispute_events": 0}
        for delta, reason in events:
            deltas = component_deltas(reason, delta)
            for k, v in deltas.items():
                totals[k] += v

        event_count = len(events)
        confidence = confidence_for_event_count(event_count)

        conn.execute(
            """
            UPDATE reputation_profiles
            SET model_version = ?,
                service_score = ?,
                court_score = ?,
                reliability_score = ?,
                event_count = ?,
                successful_event_count = ?,
                dispute_event_count = ?,
                confidence = ?,
                updated_at = unixepoch()
            WHERE actor_id = ?
            """,
            (MODEL_VERSION, totals["service"], totals["court"],
             totals["reliability"], event_count,
             totals["successful_events"], totals["dispute_events"],
             confidence, actor_id),
        )

    conn.commit()
```

## Rollback

Rolling back from V2 to V1 is safe because:

1. The `agent_scores` table is never modified by the migration
2. The `score_events` table is never modified by the migration
3. V1 consumers only read `agent_scores.score` — this value remains correct
4. Dropping `reputation_profiles` restores V1 state: `DROP TABLE IF EXISTS reputation_profiles;`

## PostgreSQL migration path

When the project moves from SQLite to PostgreSQL (Phase 2 target), the V2 schema translates directly:

```sql
CREATE TABLE reputation_profiles (
  actor_id TEXT PRIMARY KEY,
  model_version TEXT NOT NULL,
  service_score INTEGER NOT NULL DEFAULT 0,
  court_score INTEGER NOT NULL DEFAULT 0,
  reliability_score INTEGER NOT NULL DEFAULT 0,
  event_count INTEGER NOT NULL DEFAULT 0,
  successful_event_count INTEGER NOT NULL DEFAULT 0,
  dispute_event_count INTEGER NOT NULL DEFAULT 0,
  confidence DOUBLE PRECISION NOT NULL DEFAULT 0.1,
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Index for leaderboard queries
CREATE INDEX idx_reputation_profiles_score
  ON reputation_profiles ((service_score + court_score + reliability_score) DESC);
```

The replay migration script works identically against PostgreSQL — the Python code uses parameterized queries and standard SQL.

## Verification

After migration, verify consistency:

```sql
-- V1 score should equal sum of all deltas + 100 (initial score)
SELECT a.actor_id, a.score,
       100 + COALESCE(SUM(e.delta), 0) AS expected
FROM agent_scores a
LEFT JOIN score_events e ON e.actor_id = a.actor_id
GROUP BY a.actor_id
HAVING a.score != expected;
-- Should return 0 rows

-- V2 component scores should equal replay totals
-- (run the Python migration in dry-run mode and compare)
```

## Timeline

| Milestone | When | Action |
|-----------|------|--------|
| V2 schema deployed | Now (done) | `reputation_profiles` table created alongside V1 |
| Dual-write active | Now (done) | New events populate both `agent_scores` and `reputation_profiles` |
| Migration script tested | Phase 1 exit | Run replay migration against dev copy of production DB |
| V1 read path deprecated | Phase 2 | API consumers switch to V2 profile endpoint |
| V1 table dropped | Phase 3 | `agent_scores` removed after confirming no V1 consumers remain |
