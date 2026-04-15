"""Clean up old test data so we can test with fresh state."""
import asyncio
import asyncpg

async def main():
    conn = await asyncpg.connect("postgresql://postgres:louai911@localhost:5432/lira")
    
    # Delete all approvals, node executions, messages, artifacts, workflow runs, research
    await conn.execute("DELETE FROM node_review_actions")
    await conn.execute("DELETE FROM approvals")
    await conn.execute("DELETE FROM node_executions")
    await conn.execute("DELETE FROM research_messages")
    await conn.execute("DELETE FROM artifacts")
    await conn.execute("DELETE FROM workflow_runs")
    await conn.execute("DELETE FROM research_histories")
    
    print("All test data cleaned up!")
    await conn.close()

asyncio.run(main())
