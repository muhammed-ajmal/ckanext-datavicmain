"""Add new table for datastore refresh config

Revision ID: 0eaa360150e3
Revises: 
Create Date: 2021-09-06 18:10:28.634873

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '0eaa360150e3'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
     op.create_table(
        'refresh_dataset_datastore',
        sa.Column('id',
            sa.UnicodeText,
            primary_key=True,
            default=make_uuid()),
        sa.Column('dataset_id',
            sa.UnicodeText,
            nullable=False,
            index=True),
        sa.Column('frequency',
            sa.UnicodeText,
            nullable=False),
        sa.Column('created_user_id',
            sa.UnicodeText,
            nullable=False),
        sa.Column('created_at',
            sa.DateTime,
            nullable=False,
            default=datetime.datetime.utcnow),
        sa.Column('datastore_last_refreshed',
            sa.DateTime,
            nullable=True)
    )       


def downgrade():
    op.drop_table('refresh_dataset_datastore')
