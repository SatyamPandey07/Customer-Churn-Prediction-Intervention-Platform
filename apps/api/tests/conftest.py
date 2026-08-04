import asyncio
import os

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

# We need to set env vars before importing app
os.environ["JWT_SECRET_KEY"] = "test-secret"
os.environ["TESTING"] = "true"

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

import apps.api.core.rate_limit as rl_module
import redis.asyncio as redis
from apps.api.core.deps import get_db
from apps.api.main import app
from apps.api.models import Base

# Use the live postgres/redis services when running inside Docker,
# or testcontainers when running locally with Docker available.
USE_LIVE_SERVICES = os.environ.get("USE_LIVE_SERVICES", "false").lower() == "true"

@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


# ---------------------------------------------------------------------------
# Fakeredis fallback: use fakeredis if available, otherwise a real container
# ---------------------------------------------------------------------------
try:
    import fakeredis.aioredis as fakeredis_aio
    HAS_FAKEREDIS = True
except ImportError:
    HAS_FAKEREDIS = False


if USE_LIVE_SERVICES:
    # Running against live Docker Compose services
    TEST_DB_URL = os.environ.get(
        "DATABASE_URL",
        "postgresql+asyncpg://postgres:postgres@postgres:5432/churn_platform_test"
    )
    TEST_REDIS_URL = os.environ.get("REDIS_URL", "redis://redis:6379/1")

    @pytest.fixture(scope="session")
    def postgres_container():
        """No-op fixture when using live services."""
        return

    @pytest.fixture(scope="session")
    def redis_container():
        """No-op fixture when using live services."""
        return

    @pytest_asyncio.fixture()
    async def db_engine(postgres_container):
        engine = create_async_engine(TEST_DB_URL, echo=False)
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        import apps.api.core.deps as deps_mod
        import apps.api.worker as worker_mod
        test_session_maker = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
        deps_mod.AsyncSessionLocal = test_session_maker
        worker_mod.AsyncSessionLocal = test_session_maker

        yield engine
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)

    @pytest_asyncio.fixture(autouse=True)
    async def setup_redis(redis_container):
        rl_module.redis_client = redis.from_url(TEST_REDIS_URL, decode_responses=True)
        yield
        try:
            await rl_module.redis_client.flushdb()
        except Exception:
            pass

else:
    # Running locally with Docker available (testcontainers)
    try:
        from testcontainers.community.postgres import PostgresContainer
        from testcontainers.community.redis import RedisContainer
        HAS_TESTCONTAINERS = True
    except Exception:
        try:
            from testcontainers.postgres import PostgresContainer
            from testcontainers.redis import RedisContainer
            HAS_TESTCONTAINERS = True
        except Exception:
            HAS_TESTCONTAINERS = False

    if HAS_TESTCONTAINERS:
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
            url = postgres_container.get_connection_url().replace("psycopg2", "asyncpg")
            engine = create_async_engine(url, echo=False)
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)

            import apps.api.core.deps as deps_mod
            import apps.api.worker as worker_mod
            test_session_maker = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
            deps_mod.AsyncSessionLocal = test_session_maker
            worker_mod.AsyncSessionLocal = test_session_maker

            yield engine
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.drop_all)

        @pytest_asyncio.fixture(autouse=True)
        async def setup_redis(redis_container):
            url = f"redis://{redis_container.get_container_host_ip()}:{redis_container.get_exposed_port(6379)}/0"
            rl_module.redis_client = redis.from_url(url, decode_responses=True)
            # Flush all rate limit keys before each test to prevent cross-test contamination
            try:
                await rl_module.redis_client.flushdb()
            except Exception:
                pass
            yield
            try:
                await rl_module.redis_client.flushdb()
            except Exception:
                pass
    else:
        # No testcontainers, no live services — use fakeredis if available
        @pytest.fixture(scope="session")
        def postgres_container():
            return None

        @pytest.fixture(scope="session")
        def redis_container():
            return None

        @pytest_asyncio.fixture()
        async def db_engine(postgres_container):
            pytest.skip("No database available (testcontainers not installed)")

        @pytest_asyncio.fixture(autouse=True)
        async def setup_redis(redis_container):
            if HAS_FAKEREDIS:
                rl_module.redis_client = fakeredis_aio.FakeRedis(decode_responses=True)
            else:
                rl_module.redis_client = redis.from_url("redis://localhost:6379/15", decode_responses=True)
            yield


@pytest_asyncio.fixture()
async def db_session(db_engine):
    AsyncSessionLocal = async_sessionmaker(bind=db_engine, class_=AsyncSession, expire_on_commit=False)
    async with AsyncSessionLocal() as session:
        yield session


@pytest_asyncio.fixture()
async def client(db_engine, setup_redis):
    async def override_get_db():
        AsyncSessionLocal = async_sessionmaker(bind=db_engine, class_=AsyncSession, expire_on_commit=False)
        async with AsyncSessionLocal() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()
