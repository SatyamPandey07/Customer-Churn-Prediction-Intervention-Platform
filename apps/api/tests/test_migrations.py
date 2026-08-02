import pytest
import psycopg2
import subprocess
import os
from testcontainers.postgres import PostgresContainer

def test_rls_enabled_on_tables():
    with PostgresContainer("postgres:16-alpine") as postgres:
        # Get connection
        conn = psycopg2.connect(
            host=postgres.get_container_host_ip(),
            port=postgres.get_exposed_port(5432),
            user=postgres.username,
            password=postgres.password,
            dbname=postgres.dbname
        )
        conn.autocommit = True
        cur = conn.cursor()
        
        # Run migrations
        env = os.environ.copy()
        env["DATABASE_URL"] = postgres.get_connection_url().replace("postgresql+psycopg2", "postgresql")
        
        subprocess.run(["alembic", "upgrade", "head"], env=env, check=True)
        
        # Check if RLS is enabled on tenants
        cur.execute("SELECT relrowsecurity FROM pg_class WHERE relname = 'tenants'")
        res = cur.fetchone()
        assert res is not None, "tenants table not found"
        assert res[0] is True, "RLS not enabled on tenants table"
        
        # Check if RLS is enabled on users
        cur.execute("SELECT relrowsecurity FROM pg_class WHERE relname = 'users'")
        res = cur.fetchone()
        assert res is not None, "users table not found"
        assert res[0] is True, "RLS not enabled on users table"
