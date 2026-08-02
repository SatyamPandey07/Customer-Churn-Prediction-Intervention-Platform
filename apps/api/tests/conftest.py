import pytest
import pytest_asyncio
import asyncio
from httpx import AsyncClient, ASGITransport
import sqlalchemy
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from testcontainers.postgres import PostgresContainer
from testcontainers.redis import RedisContainer

# We need to set env vars before importing app
import os
os.environ["JWT_SECRET_KEY"] = "test-secret"

from apps.api.main import app
from apps.api.core.deps import get_db
from apps.api.models import Base
import apps.api.core.rate_limit as rl_module
import redis.asyncio as redis

@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture(scope="session")
def postgres_container():
    with PostgresContainer("postgres:16-alpine") as postgres:
        yield postgres

@pytest.fixture(scope="session")
def redis_container():
    with RedisContainer("redis:7-alpine") as redis_server:
        yield redis_server

@pytest_asyncio.fixture()
async def db_engine(postgres_container):
    # testcontainers provides sync url by default, we need asyncpg
    url = postgres_container.get_connection_url().replace("psycopg2", "asyncpg")
    engine = create_async_engine(url, echo=False)
    
    # Create all tables (bypass alembic for tests, or use alembic)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        # We also need to execute the RLS enabling manually since we bypassed alembic
        await conn.execute(sqlalchemy.text("ALTER TABLE tenants ENABLE ROW LEVEL SECURITY"))
        await conn.execute(sqlalchemy.text("ALTER TABLE tenants FORCE ROW LEVEL SECURITY"))
        await conn.execute(sqlalchemy.text("CREATE POLICY tenant_isolation_policy ON tenants USING (id = current_setting('app.current_tenant')::uuid)"))
        await conn.execute(sqlalchemy.text("ALTER TABLE users ENABLE ROW LEVEL SECURITY"))
        await conn.execute(sqlalchemy.text("ALTER TABLE users FORCE ROW LEVEL SECURITY"))
        await conn.execute(sqlalchemy.text("CREATE POLICY tenant_isolation_policy ON users USING (tenant_id = current_setting('app.current_tenant')::uuid)"))
        await conn.execute(sqlalchemy.text("ALTER TABLE audit_logs ENABLE ROW LEVEL SECURITY"))
        await conn.execute(sqlalchemy.text("ALTER TABLE audit_logs FORCE ROW LEVEL SECURITY"))
        await conn.execute(sqlalchemy.text("CREATE POLICY tenant_isolation_policy ON audit_logs USING (tenant_id = current_setting('app.current_tenant')::uuid)"))

        await conn.execute(sqlalchemy.text("ALTER TABLE customers ENABLE ROW LEVEL SECURITY"))
        await conn.execute(sqlalchemy.text("ALTER TABLE customers FORCE ROW LEVEL SECURITY"))
        await conn.execute(sqlalchemy.text("CREATE POLICY tenant_isolation_policy ON customers USING (tenant_id = current_setting('app.current_tenant')::uuid)"))

        await conn.execute(sqlalchemy.text("ALTER TABLE customer_events ENABLE ROW LEVEL SECURITY"))
        await conn.execute(sqlalchemy.text("ALTER TABLE customer_events FORCE ROW LEVEL SECURITY"))
        await conn.execute(sqlalchemy.text("CREATE POLICY tenant_isolation_policy ON customer_events USING (tenant_id = current_setting('app.current_tenant')::uuid)"))
        
        await conn.execute(sqlalchemy.text("ALTER TABLE churn_features ENABLE ROW LEVEL SECURITY"))
        await conn.execute(sqlalchemy.text("ALTER TABLE churn_features FORCE ROW LEVEL SECURITY"))
        await conn.execute(sqlalchemy.text("CREATE POLICY tenant_isolation_policy ON churn_features USING (tenant_id = current_setting('app.current_tenant')::uuid)"))
        
    yield engine
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)



@pytest_asyncio.fixture()
async def db_session(db_engine):
    AsyncSessionLocal = async_sessionmaker(bind=db_engine, class_=AsyncSession, expire_on_commit=False)
    async with AsyncSessionLocal() as session:
        yield session

@pytest_asyncio.fixture(autouse=True)
async def setup_redis(redis_container):
    # Point rate limiter to test redis
    url = f"redis://{redis_container.get_container_host_ip()}:{redis_container.get_exposed_port(6379)}/0"
    rl_module.redis_client = redis.from_url(url, decode_responses=True)
    yield
    await rl_module.redis_client.flushdb()

@pytest_asyncio.fixture()
async def client(db_engine):
    # Override get_db dependency
    async def override_get_db():
        AsyncSessionLocal = async_sessionmaker(bind=db_engine, class_=AsyncSession, expire_on_commit=False)
        async with AsyncSessionLocal() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()
