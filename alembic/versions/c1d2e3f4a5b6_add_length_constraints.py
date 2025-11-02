"""add_length_constraints

Revision ID: c1d2e3f4a5b6
Revises: ba2444ddeb3e
Create Date: 2025-10-29 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'c1d2e3f4a5b6'
down_revision = 'ba2444ddeb3e'
branch_labels = None
depends_on = None


def upgrade():
    # Add length constraints to string columns for security
    # PostgreSQL allows ALTER TYPE without data loss if new length >= old length
    # Since we're adding constraints that didn't exist before, this should be safe

    # Alter meeting_code to VARCHAR(50)
    with op.batch_alter_table('meetings') as batch_op:
        batch_op.alter_column('meeting_code',
                              existing_type=sa.String(),
                              type_=sa.String(length=50),
                              existing_nullable=False)

    # Alter poll name to VARCHAR(200)
    with op.batch_alter_table('polls') as batch_op:
        batch_op.alter_column('name',
                              existing_type=sa.String(),
                              type_=sa.String(length=200),
                              existing_nullable=False)


def downgrade():
    # Remove length constraints
    with op.batch_alter_table('polls') as batch_op:
        batch_op.alter_column('name',
                              existing_type=sa.String(length=200),
                              type_=sa.String(),
                              existing_nullable=False)

    with op.batch_alter_table('meetings') as batch_op:
        batch_op.alter_column('meeting_code',
                              existing_type=sa.String(length=50),
                              type_=sa.String(),
                              existing_nullable=False)
