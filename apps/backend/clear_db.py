import asyncio
from sqlalchemy import delete
from apps.backend.app.core.database import AsyncSessionLocal
from apps.backend.app.domain.models.models import Scan, Finding, FixRun

async def clear():
    async with AsyncSessionLocal() as db:
        await db.execute(delete(FixRun))
        await db.execute(delete(Finding))
        await db.execute(delete(Scan))
        await db.commit()
    print("Database cleared of scans, findings, and fix runs.")

if __name__ == "__main__":
    asyncio.run(clear())
