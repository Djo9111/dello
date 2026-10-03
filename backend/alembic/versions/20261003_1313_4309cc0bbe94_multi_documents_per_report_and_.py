"""multi documents per report and circumstance

Revision ID: 4309cc0bbe94
Revises: 2718c3034da2
Create Date: 2026-10-03 13:13:53.827521

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '4309cc0bbe94'
down_revision: Union[str, Sequence[str], None] = '2718c3034da2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Nouvelle table des documents
    op.create_table(
        "report_documents",
        sa.Column("report_id", sa.Uuid(), nullable=False),
        sa.Column("document_type", sa.String(length=30), nullable=False),
        sa.Column("document_number_hmac", sa.String(length=64), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint(
            "document_number_hmac IS NULL OR char_length(document_number_hmac) = 64",
            name=op.f("ck_report_documents_hmac_length"),
        ),
        sa.CheckConstraint(
            "document_type IN ('cni', 'permis', 'passeport', 'carte_etudiant', 'carte_consulaire', 'autre')",
            name=op.f("ck_report_documents_document_type"),
        ),
        sa.ForeignKeyConstraint(
            ["report_id"], ["reports.id"],
            name=op.f("fk_report_documents_report_id_reports"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_report_documents")),
    )
    op.create_index(op.f("ix_report_documents_report_id"), "report_documents", ["report_id"])
    op.create_index("ix_report_documents_type", "report_documents", ["document_type"])
    op.create_index(
        "ix_report_documents_matching",
        "report_documents",
        ["document_number_hmac"],
        postgresql_where=sa.text("document_number_hmac IS NOT NULL"),
    )

    # 2. Reprise des données : chaque signalement existant devient un
    #    signalement portant un seul document.
    op.execute(
        """
        INSERT INTO report_documents (id, report_id, document_type, document_number_hmac, created_at, updated_at)
        SELECT gen_random_uuid(), id, document_type, document_number_hmac, created_at, updated_at
        FROM reports
        """
    )

    # 3. Les colonnes quittent la table des signalements
    op.drop_index("ix_reports_matching", table_name="reports")
    op.drop_index("ix_reports_public_list", table_name="reports")
    op.drop_constraint(op.f("ck_reports_hmac_length"), "reports", type_="check")
    op.drop_constraint(op.f("ck_reports_document_type"), "reports", type_="check")
    op.drop_column("reports", "document_number_hmac")
    op.drop_column("reports", "document_type")

    # 4. Circonstance : perte ou vol
    op.add_column("reports", sa.Column("circumstance", sa.String(length=30), nullable=True))
    op.create_check_constraint(
        op.f("ck_reports_report_circumstance"),
        "reports",
        "circumstance IS NULL OR circumstance IN ('lost', 'stolen')",
    )
    op.create_index("ix_reports_public_list", "reports", ["is_published", "status", "kind"])

    # 5. Contraintes sur les coordonnees : declarees dans le modele mais
    #    jamais creees, car Alembic ne detecte pas les CheckConstraint
    #    ajoutees a une table existante.
    op.create_check_constraint(
        op.f("ck_reports_latitude_range"),
        "reports",
        "latitude IS NULL OR (latitude BETWEEN -90 AND 90)",
    )
    op.create_check_constraint(
        op.f("ck_reports_longitude_range"),
        "reports",
        "longitude IS NULL OR (longitude BETWEEN -180 AND 180)",
    )
    op.create_check_constraint(
        op.f("ck_reports_coordinates_together"),
        "reports",
        "(latitude IS NULL) = (longitude IS NULL)",
    )


def downgrade() -> None:
    op.drop_constraint(op.f("ck_reports_coordinates_together"), "reports", type_="check")
    op.drop_constraint(op.f("ck_reports_longitude_range"), "reports", type_="check")
    op.drop_constraint(op.f("ck_reports_latitude_range"), "reports", type_="check")

    op.drop_index("ix_reports_public_list", table_name="reports")
    op.drop_constraint(op.f("ck_reports_report_circumstance"), "reports", type_="check")
    op.drop_column("reports", "circumstance")

    op.add_column("reports", sa.Column("document_type", sa.String(length=30), nullable=True))
    op.add_column("reports", sa.Column("document_number_hmac", sa.String(length=64), nullable=True))

    # Un signalement ne peut reprendre qu'un seul document : on garde le premier
    op.execute(
        """
        UPDATE reports r
        SET document_type = d.document_type,
            document_number_hmac = d.document_number_hmac
        FROM (
            SELECT DISTINCT ON (report_id) report_id, document_type, document_number_hmac
            FROM report_documents
            ORDER BY report_id, created_at
        ) d
        WHERE d.report_id = r.id
        """
    )
    op.execute("UPDATE reports SET document_type = 'autre' WHERE document_type IS NULL")
    op.alter_column("reports", "document_type", nullable=False)

    op.create_check_constraint(
        op.f("ck_reports_hmac_length"),
        "reports",
        "document_number_hmac IS NULL OR char_length(document_number_hmac) = 64",
    )
    op.create_check_constraint(
        op.f("ck_reports_document_type"),
        "reports",
        "document_type IN ('cni', 'permis', 'passeport', 'carte_etudiant', 'carte_consulaire', 'autre')",
    )
    op.create_index(
        "ix_reports_matching",
        "reports",
        ["kind", "document_number_hmac"],
        postgresql_where=sa.text("document_number_hmac IS NOT NULL"),
    )
    op.create_index("ix_reports_public_list", "reports", ["is_published", "status", "document_type"])

    op.drop_table("report_documents")
