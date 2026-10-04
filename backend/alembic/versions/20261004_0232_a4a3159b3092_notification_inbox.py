"""notification inbox

Revision ID: a4a3159b3092
Revises: 4309cc0bbe94
Create Date: 2026-10-04 02:32:44.939983

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a4a3159b3092'
down_revision: Union[str, Sequence[str], None] = '4309cc0bbe94'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "notification_log",
        sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
    )

    # Nouveau canal : la notification n'a pas quitte le serveur, elle
    # attend d'etre lue dans l'application.
    op.drop_constraint(
        op.f("ck_notification_log_notification_channel"), "notification_log", type_="check"
    )
    op.create_check_constraint(
        op.f("ck_notification_log_notification_channel"),
        "notification_log",
        "channel IN ('in_app', 'push', 'sms')",
    )

    # Boite de reception : les messages non lus d'un utilisateur, du plus recent
    op.create_index(
        "ix_notification_log_inbox",
        "notification_log",
        ["user_id", "read_at", "created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_notification_log_inbox", table_name="notification_log")

    op.execute("DELETE FROM notification_log WHERE channel = 'in_app'")
    op.drop_constraint(
        op.f("ck_notification_log_notification_channel"), "notification_log", type_="check"
    )
    op.create_check_constraint(
        op.f("ck_notification_log_notification_channel"),
        "notification_log",
        "channel IN ('push', 'sms')",
    )

    op.drop_column("notification_log", "read_at")