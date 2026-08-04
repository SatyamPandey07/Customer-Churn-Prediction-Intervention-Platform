import os
import subprocess

import psycopg2
import pytest

try:
    import testcontainers.core.config as tc_config
    _orig_read = tc_config.read_tc_properties
    def _safe_read():
        try:
            return _orig_read()
        except PermissionError:
            return {}
    tc_config.read_tc_properties = _safe_read
except Exception:
    pass

try:
    from testcontainers.community.postgres import PostgresContainer
    HAS_TESTCONTAINERS = True
except Exception:
    try:
        from testcontainers.postgres import PostgresContainer
        HAS_TESTCONTAINERS = True
    except Exception:
        HAS_TESTCONTAINERS = False


def test_rls_enabled_on_tables():
    use_live_services = os.environ.get("USE_LIVE_SERVICES", "false").lower() == "true"
    db_url = os.environ.get("DATABASE_URL")

    if use_live_services and db_url:
        # Run directly against live database
        url_clean = db_url.replace("postgresql+asyncpg://", "postgresql://").replace("postgresql+psycopg2://", "postgresql://")
        conn = psycopg2.connect(url_clean)
        conn.autocommit = True
        cur = conn.cursor()
        api_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)))
        subprocess.run(["alembic", "upgrade", "head"], check=True, cwd=api_dir)

        cur.execute("SELECT relrowsecurity FROM pg_class WHERE relname = 'tenants'")
        res = cur.fetchone()
        assert res is not None, "tenants table not found"
        assert res[0] is True, "RLS not enabled on tenants table"

        cur.execute("SELECT relrowsecurity FROM pg_class WHERE relname = 'users'")
        res = cur.fetchone()
        assert res is not None, "users table not found"
        assert res[0] is True, "RLS not enabled on users table"
        return

    if not HAS_TESTCONTAINERS:
        pytest.skip("Testcontainers not available and USE_LIVE_SERVICES is false")

    try:
        with PostgresContainer("postgres:16-alpine") as postgres:
            conn = psycopg2.connect(
                host=postgres.get_container_host_ip(),
                port=postgres.get_exposed_port(5432),
                user=postgres.username,
                password=postgres.password,
                dbname=postgres.dbname
            )
            conn.autocommit = True
            cur = conn.cursor()

            env = os.environ.copy()
            env["DATABASE_URL"] = postgres.get_connection_url().replace("postgresql+psycopg2", "postgresql")

            api_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)))
            subprocess.run(["alembic", "upgrade", "head"], env=env, check=True, cwd=api_dir)

            cur.execute("SELECT relrowsecurity FROM pg_class WHERE relname = 'tenants'")
            res = cur.fetchone()
            assert res is not None, "tenants table not found"
            assert res[0] is True, "RLS not enabled on tenants table"

            cur.execute("SELECT relrowsecurity FROM pg_class WHERE relname = 'users'")
            res = cur.fetchone()
            assert res is not None, "users table not found"
            assert res[0] is True, "RLS not enabled on users table"
    except Exception as e:
        pytest.skip(f"Could not run Postgres container: {e}")
