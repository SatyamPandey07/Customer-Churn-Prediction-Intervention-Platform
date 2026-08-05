"""Initial migration

Revision ID: 610a1f2fe5ca
Revises: 
Create Date: 2026-08-02 16:04:11.069712

"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '610a1f2fe5ca'
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # ENUMs are created automatically by sa.Enum during create_table

    # Create tenants table
    op.create_table(
        'tenants',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('subdomain', sa.String(), nullable=False),
        sa.Column('plan_tier', sa.Enum('tier1', 'tier2', 'tier3', name='plantier'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('subdomain')
    )
    
    # Create users table
    op.create_table(
        'users',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('tenant_id', sa.UUID(), nullable=False),
        sa.Column('email', sa.String(), nullable=False),
        sa.Column('hashed_password', sa.String(), nullable=True),
        sa.Column('role', sa.Enum('owner', 'admin', 'analyst', 'viewer', name='user_role'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('tenant_id', 'email', name='uq_tenant_email')
    )

    # Enable RLS on tenants
    op.execute("ALTER TABLE tenants ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE tenants FORCE ROW LEVEL SECURITY")
    op.execute("CREATE POLICY tenant_isolation_policy ON tenants USING (id = current_setting('app.current_tenant')::uuid)")

    # Enable RLS on users
    op.execute("ALTER TABLE users ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE users FORCE ROW LEVEL SECURITY")
    op.execute("CREATE POLICY tenant_isolation_policy ON users USING (tenant_id = current_setting('app.current_tenant')::uuid)")


def downgrade() -> None:
    # Drop policies
    op.execute("DROP POLICY IF EXISTS tenant_isolation_policy ON users")
    op.execute("DROP POLICY IF EXISTS tenant_isolation_policy ON tenants")
    
    # Drop tables
    op.drop_table('users')
    op.drop_table('tenants')
    
    # Drop ENUMs
    op.execute("DROP TYPE IF EXISTS user_role")
    op.execute("DROP TYPE IF EXISTS plantier")
