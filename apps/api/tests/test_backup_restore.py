import pytest
import os
import subprocess
import uuid
from sqlalchemy.sql import text

@pytest.mark.asyncio
async def test_backup_and_restore(db_engine):
    # This test assumes it runs in an environment where pg_dump and pg_restore are available.
    # It creates a tenant, takes a backup, deletes the tenant, restores, and validates it exists.

    # Extract sync URL from async engine string
    # E.g. postgresql+asyncpg://user:pass@host:port/db -> postgresql://user:pass@host:port/db
    db_url = str(db_engine.url).replace("+asyncpg", "")
    backup_file = "/tmp/test_backup.dump"
    
    tenant_id = uuid.uuid4()
    
    # 1. Insert data
    async with db_engine.begin() as conn:
        await conn.execute(text(
            "INSERT INTO tenants (id, name, subdomain, plan_tier) VALUES (:id, 'BackupTest', 'backup', 'tier1')"
        ), {"id": tenant_id})
        
    # 2. Run backup
    script_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../scripts/db_backup.sh"))
    result = subprocess.run([script_path, db_url, backup_file], capture_output=True, text=True)
    assert result.returncode == 0, f"Backup failed: {result.stderr}"
    assert os.path.exists(backup_file)
    
    # 3. Delete data
    async with db_engine.begin() as conn:
        await conn.execute(text("DELETE FROM tenants WHERE id = :id"), {"id": tenant_id})
        
    # Verify it's gone
    async with db_engine.begin() as conn:
        res = await conn.execute(text("SELECT count(*) FROM tenants WHERE id = :id"), {"id": tenant_id})
        assert res.scalar() == 0
        
    # 4. Run restore
    restore_script = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../scripts/db_restore.sh"))
    result = subprocess.run([restore_script, db_url, backup_file], capture_output=True, text=True)
    # pg_restore with -c might exit with non-zero if some tables don't exist yet, but our script says || true
    
    # 5. Validate restored
    async with db_engine.begin() as conn:
        res = await conn.execute(text("SELECT count(*) FROM tenants WHERE id = :id"), {"id": tenant_id})
        assert res.scalar() == 1
        
    # Cleanup
    if os.path.exists(backup_file):
        os.remove(backup_file)
