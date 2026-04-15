"""One-shot schema migration for per-node HITL columns."""
import asyncio
import asyncpg

MIGRATIONS = [
    # workflow_runs new columns
    "ALTER TABLE workflow_runs ADD COLUMN IF NOT EXISTS current_node VARCHAR(100)",
    "ALTER TABLE workflow_runs ADD COLUMN IF NOT EXISTS current_node_execution_id UUID",
    # node_executions new columns
    "ALTER TABLE node_executions ADD COLUMN IF NOT EXISTS node_order INTEGER DEFAULT 0",
    "ALTER TABLE node_executions ADD COLUMN IF NOT EXISTS attempt_number INTEGER DEFAULT 1",
    "ALTER TABLE node_executions ADD COLUMN IF NOT EXISTS revision_number INTEGER DEFAULT 0",
    "ALTER TABLE node_executions ADD COLUMN IF NOT EXISTS approved_at TIMESTAMPTZ",
    "ALTER TABLE node_executions ADD COLUMN IF NOT EXISTS feedback_text TEXT",
    "ALTER TABLE node_executions ADD COLUMN IF NOT EXISTS input_summary JSONB",
    # new table
    """CREATE TABLE IF NOT EXISTS node_review_actions (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        node_execution_id UUID NOT NULL REFERENCES node_executions(id) ON DELETE CASCADE,
        research_id UUID NOT NULL REFERENCES research_histories(id) ON DELETE CASCADE,
        action_type VARCHAR(50) NOT NULL,
        feedback_text TEXT,
        created_at TIMESTAMPTZ DEFAULT now()
    )""",
    "CREATE INDEX IF NOT EXISTS ix_node_review_actions_node_execution_id ON node_review_actions(node_execution_id)",
    "CREATE INDEX IF NOT EXISTS ix_node_review_actions_research_id ON node_review_actions(research_id)",
]

async def main():
    conn = await asyncpg.connect("postgresql://postgres:louai911@localhost:5432/lira")
    for sql in MIGRATIONS:
        try:
            await conn.execute(sql)
            print(f"  OK: {sql[:60]}...")
        except Exception as e:
            print(f"  SKIP: {sql[:60]}... ({e})")
    await conn.close()
    print("\nSchema migration complete!")

if __name__ == "__main__":
    asyncio.run(main())
