import sqlite3
import json
import os
from contextlib import contextmanager
from typing import Generator
from backend.app.config import settings

def get_db_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(settings.DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

@contextmanager
def db_session() -> Generator[sqlite3.Connection, None, None]:
    conn = get_db_connection()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

def init_db():
    with db_session() as conn:
        cursor = conn.cursor()
        
        # 1. Goals Table (The persistent North Star representation layer)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS goals (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            intent TEXT NOT NULL,
            invariant_constraints TEXT NOT NULL, -- JSON array of strings
            acceptance_criteria TEXT NOT NULL,   -- JSON array of strings
            anti_goals TEXT NOT NULL,             -- JSON array of forbidden actions/patterns
            current_version INTEGER DEFAULT 1,
            status TEXT DEFAULT 'active',        -- active, completed, paused
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """)

        # 2. Milestones Table (Structured DAG of milestones with dependencies)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS milestones (
            id TEXT PRIMARY KEY,
            goal_id TEXT NOT NULL,
            order_index INTEGER NOT NULL,
            title TEXT NOT NULL,
            description TEXT NOT NULL,
            status TEXT DEFAULT 'pending',       -- pending, in_progress, completed, skipped
            progress REAL DEFAULT 0.0,
            dependencies TEXT DEFAULT '[]',      -- JSON array of milestone IDs
            FOREIGN KEY (goal_id) REFERENCES goals (id) ON DELETE CASCADE
        );
        """)

        # 3. Goal Evolution History (Tracks legitimate evolution vs drift)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS goal_versions (
            id TEXT PRIMARY KEY,
            goal_id TEXT NOT NULL,
            version_num INTEGER NOT NULL,
            reason TEXT NOT NULL,
            diff_summary TEXT NOT NULL,
            approved_by TEXT DEFAULT 'HUMAN_SUPERVISOR',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (goal_id) REFERENCES goals (id) ON DELETE CASCADE
        );
        """)

        # 4. Agent Sessions Table (Multi-session / multi-day tracking)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS sessions (
            id TEXT PRIMARY KEY,
            goal_id TEXT NOT NULL,
            session_name TEXT NOT NULL,
            session_number INTEGER DEFAULT 1,
            status TEXT DEFAULT 'active',        -- active, completed, abandoned
            started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_active_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            summary TEXT DEFAULT '',
            FOREIGN KEY (goal_id) REFERENCES goals (id) ON DELETE CASCADE
        );
        """)

        # 5. Agent Steps Table (Action, reasoning, drift scores, intervention)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS steps (
            id TEXT PRIMARY KEY,
            session_id TEXT NOT NULL,
            step_number INTEGER NOT NULL,
            proposed_action TEXT NOT NULL,
            action_type TEXT NOT NULL,           -- code_edit, terminal_cmd, search, plan, message
            reasoning TEXT NOT NULL,
            context_snapshot TEXT DEFAULT '',
            drift_score REAL NOT NULL,
            drift_tier TEXT NOT NULL,            -- NORMAL, WARNING, INTERVENE, CRITICAL
            intervention_triggered INTEGER DEFAULT 0, -- boolean 0 or 1
            intervention_details TEXT DEFAULT '',
            execution_result TEXT DEFAULT '',
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (session_id) REFERENCES sessions (id) ON DELETE CASCADE
        );
        """)

        # 6. Drift Audits Table (Detailed metrics breakdown per step)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS drift_audits (
            id TEXT PRIMARY KEY,
            session_id TEXT NOT NULL,
            step_id TEXT NOT NULL,
            semantic_score REAL NOT NULL,
            constraint_score REAL NOT NULL,
            horizon_score REAL NOT NULL,
            aggregate_drift REAL NOT NULL,
            status TEXT NOT NULL,
            feedback_prompt TEXT DEFAULT '',
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (session_id) REFERENCES sessions (id) ON DELETE CASCADE,
            FOREIGN KEY (step_id) REFERENCES steps (id) ON DELETE CASCADE
        );
        """)

        # 7. Evolution RFC Proposals Table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS evolution_proposals (
            id TEXT PRIMARY KEY,
            goal_id TEXT NOT NULL,
            session_id TEXT,
            rfc_title TEXT NOT NULL,
            justification TEXT NOT NULL,
            proposed_changes TEXT NOT NULL,      -- JSON representation of updated constraints/criteria
            classification TEXT NOT NULL,        -- EVOLUTION vs DRIFT
            confidence REAL NOT NULL,
            status TEXT DEFAULT 'pending',       -- pending, approved, rejected
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (goal_id) REFERENCES goals (id) ON DELETE CASCADE
        );
        """)

        # Seed default project if empty
        cursor.execute("SELECT COUNT(*) FROM goals")
        count = cursor.fetchone()[0]
        if count == 0:
            seed_initial_data(cursor)

def seed_initial_data(cursor):
    import uuid
    goal_id = "goal_ecommerce_migration"
    
    # Root North Star Goal
    cursor.execute("""
    INSERT INTO goals (id, title, intent, invariant_constraints, acceptance_criteria, anti_goals, current_version, status)
    VALUES (?, ?, ?, ?, ?, ?, 1, 'active')
    """, (
        goal_id,
        "Enterprise E-Commerce Microservice Cloud Migration",
        "Migrate legacy monolithic e-commerce catalog and payment processing service to a high-availability containerized microservice architecture on AWS without downtime.",
        json.dumps([
            "Must maintain 100% backward compatibility with existing mobile clients",
            "Zero credit card plaintext persistence (PCI-DSS compliance invariant)",
            "All endpoints must respond under 200ms latency at p99",
            "Do not introduce unvetted external dependencies or build custom gaming/physics engines"
        ]),
        json.dumps([
            "PostgreSQL schema migrated and verified with 0 data loss",
            "Catalog Service & Cart Service containerized with Dockerfiles",
            "Payment webhook integration verified with mock Stripe test suite",
            "End-to-end integration tests passing with 95%+ coverage"
        ]),
        json.dumps([
            "Building custom GUI games or unrelated utilities",
            "Spending more than 2 sub-sessions refactoring CSS styling or fonts",
            "Re-architecting database engines away from PostgreSQL without an approved RFC",
            "Bypassing PCI-DSS tokenization checks"
        ])
    ))

    # Milestones
    milestones = [
        ("ms_1", goal_id, 1, "Database Schema Extraction & PostgreSQL Migration", "Extract monolith tables, normalize catalog schema, and write idempotent SQL migration scripts.", "completed", 1.0, "[]"),
        ("ms_2", goal_id, 2, "Containerize Core Catalog Microservice", "Develop Dockerfile, configure FastAPI catalog API, and implement Redis cache tier.", "in_progress", 0.65, '["ms_1"]'),
        ("ms_3", goal_id, 3, "Payment & Checkout Service Isolation", "Decouple payment tokenization, implement Stripe webhook listeners, and guarantee idempotent transactions.", "pending", 0.0, '["ms_2"]'),
        ("ms_4", goal_id, 4, "High-Availability Deployment & Smoke Tests", "Setup Kubernetes manifests, configure canary deployment strategy, and pass end-to-end load tests.", "pending", 0.0, '["ms_3"]')
    ]
    cursor.executemany("""
    INSERT INTO milestones (id, goal_id, order_index, title, description, status, progress, dependencies)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, milestones)

    # Initial Version History
    cursor.execute("""
    INSERT INTO goal_versions (id, goal_id, version_num, reason, diff_summary, approved_by)
    VALUES (?, ?, 1, 'Initial North Star baseline definition established', 'Created initial goal invariants, acceptance criteria, and anti-goals.', 'SYSTEM')
    """, (str(uuid.uuid4()), goal_id))

    # Seed an active Session
    session_id = "session_day2_catalog"
    cursor.execute("""
    INSERT INTO sessions (id, goal_id, session_name, session_number, status, summary)
    VALUES (?, ?, 'Day 2 - Catalog Service Containerization & Redis Cache', 2, 'active', 'Working on Docker multi-stage build and Redis caching tier.')
    """, (session_id, goal_id))

    # Seed steps showing drift detection and intervention
    seed_steps = [
        (str(uuid.uuid4()), session_id, 1, "Write multi-stage Dockerfile for catalog service", "code_edit", "Containerizing catalog service to satisfy Milestone 2 requirements.", 0.08, "NORMAL", 0, "", "Dockerfile created and syntax verified."),
        (str(uuid.uuid4()), session_id, 2, "Configure Redis connection pool with retry backoff", "code_edit", "Adding cache layer to meet the p99 < 200ms latency invariant constraint.", 0.12, "NORMAL", 0, "", "Redis cache client implemented."),
        (str(uuid.uuid4()), session_id, 3, "Start coding an arcade mini-game for user loading screens", "code_edit", "Thought users might enjoy an interactive space shooter while waiting for checkout.", 0.68, "INTERVENE", 1, "NORTHSTAR CIRCUIT BREAKER: Action classified as severe tangent drift (Anti-Goal: Building custom GUI games). Re-grounding to Milestone 2: Finish Redis catalog caching.", "Action intercepted and canceled. Agent steered back to caching tests."),
        (str(uuid.uuid4()), session_id, 4, "Write unit tests for Redis cache invalidation logic", "code_edit", "Re-grounded following Northstar directive. Validating cache expiry on product update.", 0.09, "NORMAL", 0, "", "All 14 cache unit tests passing.")
    ]
    cursor.executemany("""
    INSERT INTO steps (id, session_id, step_number, proposed_action, action_type, reasoning, drift_score, drift_tier, intervention_triggered, intervention_details, execution_result)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, seed_steps)
