"""empty message

Revision ID: 11a66ebc4c48
Revises: 18081e8b53eb
Create Date: 2015-09-07 21:31:08.958522

"""

# revision identifiers, used by Alembic.
revision = '11a66ebc4c48'
down_revision = '18081e8b53eb'

from alembic import op
import sqlalchemy as sa


def upgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.create_table('blacklists',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('account_id', sa.Integer(), nullable=False),
    sa.Column('email', sa.String(length=255), nullable=True),
    sa.Column('detail', sa.String(length=255), nullable=True),
    sa.Column('manual', sa.Integer(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
    sa.ForeignKeyConstraint(['account_id'], ['accounts.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_blacklists_email'), 'blacklists', ['email'], unique=False)
    op.create_index(op.f('ix_unsubscribes_email'), 'unsubscribes', ['email'], unique=False)
    ### end Alembic commands ###


def downgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('blacklists')
    ### end Alembic commands ###
