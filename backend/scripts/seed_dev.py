"""Jeu de données de développement pour Dello.

   python -m scripts.seed_dev          # crée les comptes et signalements
   python -m scripts.seed_dev --reset  # supprime uniquement ce qu'il a créé

Refuse de tourner ailleurs qu'en développement : ces comptes ont tous le
même mot de passe, ils n'ont rien à faire sur un environnement exposé.
"""

import argparse
import random
import sys
from datetime import UTC, datetime, timedelta

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import engine
from app.core.security import hash_document_number, hash_password
from app.modules.claims.models import Claim
from app.modules.claims.verification import hash_answer
from app.modules.reports.masking import mask_owner_name
from app.modules.reports.models import (
    DocumentType,
    Report,
    ReportCircumstance,
    ReportDocument,
    ReportKind,
)
from app.modules.users.models import User

SEED_PREFIX = "+22170000"
SEED_PASSWORD = "Tamarin-Soleil-9"

FIRST_NAMES = [
    "Awa", "Moussa", "Fatou", "Ibrahima", "Ndeye", "Cheikh", "Aminata",
    "Ousmane", "Khady", "Modou", "Mariama", "Alioune", "Sokhna", "Babacar",
]
LAST_NAMES = [
    "Diop", "Fall", "Ndiaye", "Sow", "Ba", "Gueye", "Sarr", "Diouf",
    "Gaye", "Cisse", "Faye", "Seck", "Mbaye", "Toure",
]
REGIONS = {
    "Dakar": ["Keur Massar", "Pikine", "Guediawaye", "Rufisque", "Parcelles"],
    "Thies": ["Mbour", "Tivaouane", "Saly"],
    "Saint-Louis": ["Richard-Toll", "Dagana"],
    "Kaolack": ["Nioro", "Guinguineo"],
    "Ziguinchor": ["Bignona", "Oussouye"],
}
PLACES = [
    "pres du marche", "arret de bus", "dans un taxi", "devant la mosquee",
    "au stade", "pres de la plage", "dans une boutique", "a la gare routiere",
]
QUESTIONS = [
    ("Date de naissance sur le document ?", "12 juin 1995"),
    ("Lieu de naissance inscrit ?", "Dakar"),
    ("Annee de delivrance ?", "2021"),
]


def _require_development() -> None:
    if settings.ENVIRONMENT != "development":
        sys.exit("Refusé : ce script ne tourne qu'en développement")
    if settings.POSTGRES_DB.endswith("_test"):
        sys.exit("Refusé : la base de test est reconstruite par pytest")


def _reset(db: Session) -> None:
    users = db.scalars(
        select(User).where(User.phone_number.like(f"{SEED_PREFIX}%"))
    ).all()
    user_ids = [user.id for user in users]

    if not user_ids:
        print("Rien à supprimer.")
        return

    db.execute(delete(Claim).where(Claim.claimant_id.in_(user_ids)))
    db.execute(delete(Report).where(Report.user_id.in_(user_ids)))
    for user in users:
        db.delete(user)
    db.commit()

    print(f"{len(user_ids)} comptes du jeu de données supprimés.")


def _create_users(db: Session, count: int) -> list[User]:
    users = []
    shared_hash = hash_password(SEED_PASSWORD)

    for index in range(count):
        phone = f"{SEED_PREFIX}{index:04d}"
        if db.scalar(select(User.id).where(User.phone_number == phone)) is not None:
            continue

        user = User(
            phone_number=phone,
            full_name=f"{random.choice(FIRST_NAMES)} {random.choice(LAST_NAMES)}",
            hashed_password=shared_hash,
            is_phone_verified=True,
        )
        db.add(user)
        users.append(user)

    db.commit()
    return users


def _create_reports(db: Session, users: list[User], count: int) -> int:
    if not users:
        return 0

    today = datetime.now(UTC).date()
    created = 0

    for _ in range(count):
        user = random.choice(users)
        kind = random.choice([ReportKind.LOST, ReportKind.FOUND])
        document_type = random.choice(list(DocumentType))
        region = random.choice(list(REGIONS))

        owner_name = f"{random.choice(FIRST_NAMES)} {random.choice(LAST_NAMES)}"
        number = f"{random.randint(1000000000000, 1999999999999)}"

        documents = [
            ReportDocument(
                document_type=document_type,
                document_number_hmac=hash_document_number(document_type.value, number),
            )
        ]

        # Un signalement sur trois porte plusieurs documents, comme un sac
        # qui contenait la carte d'identite et le permis.
        if random.random() < 0.33:
            second_type = random.choice(list(DocumentType))
            documents.append(
                ReportDocument(
                    document_type=second_type,
                    document_number_hmac=hash_document_number(
                        second_type.value, f"{random.randint(1000000000000, 1999999999999)}"
                    ),
                )
            )

        report = Report(
            user_id=user.id,
            kind=kind,
            circumstance=(
                random.choice(list(ReportCircumstance))
                if kind is ReportKind.LOST
                else None
            ),
            owner_name_masked=mask_owner_name(owner_name),
            region=region,
            commune=random.choice(REGIONS[region]),
            place_detail=random.choice(PLACES),
            occurred_on=today - timedelta(days=random.randint(0, 120)),
            documents=documents,
        )

        if kind is ReportKind.FOUND:
            report.latitude = round(14.70 + random.uniform(-0.12, 0.12), 6)
            report.longitude = round(-17.44 + random.uniform(-0.12, 0.12), 6)

            if random.random() < 0.6:
                question, answer = random.choice(QUESTIONS)
                report.verification_question = question
                report.verification_answer_hash = hash_answer(answer)

        db.add(report)
        created += 1

    db.commit()
    return created


def _create_matching_pair(db: Session, users: list[User]) -> None:
    """Une perte et une trouvaille portant le même numéro, pour pouvoir
    tester le rapprochement sans chercher une coïncidence."""
    if len(users) < 2:
        return

    number = "1234567890123"
    owner, finder = users[0], users[1]
    today = datetime.now(UTC).date()
    question, answer = QUESTIONS[0]

    db.add(
        Report(
            user_id=owner.id,
            kind=ReportKind.LOST,
            circumstance=ReportCircumstance.STOLEN,
            owner_name_masked=mask_owner_name("Modienne Guisse"),
            region="Dakar",
            commune="Keur Massar",
            place_detail="pres du marche",
            occurred_on=today - timedelta(days=3),
            documents=[
                ReportDocument(
                    document_type=DocumentType.CNI,
                    document_number_hmac=hash_document_number("cni", number),
                ),
                ReportDocument(
                    document_type=DocumentType.PERMIS,
                    document_number_hmac=hash_document_number("permis", "5555555555"),
                ),
            ],
        )
    )
    db.add(
        Report(
            user_id=finder.id,
            kind=ReportKind.FOUND,
            owner_name_masked=mask_owner_name("Modienne Guisse"),
            region="Dakar",
            commune="Pikine",
            place_detail="arret de bus",
            occurred_on=today - timedelta(days=1),
            latitude=14.7548,
            longitude=-17.3924,
            verification_question=question,
            verification_answer_hash=hash_answer(answer),
            documents=[
                ReportDocument(
                    document_type=DocumentType.CNI,
                    document_number_hmac=hash_document_number("cni", number),
                )
            ],
        )
    )
    db.commit()

    print(f"  Paire de test : {owner.phone_number} a perdu, {finder.phone_number} a trouvé")
    print(f"  Question : {question}  Réponse : {answer}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Jeu de données de développement")
    parser.add_argument("--reset", action="store_true", help="supprime le jeu de données")
    parser.add_argument("--users", type=int, default=8)
    parser.add_argument("--reports", type=int, default=60)
    args = parser.parse_args()

    _require_development()
    random.seed(42)

    with Session(engine) as db:
        if args.reset:
            _reset(db)
            return

        _create_users(db, args.users)
        existing = list(
            db.scalars(select(User).where(User.phone_number.like(f"{SEED_PREFIX}%")))
        )

        count = _create_reports(db, existing, args.reports)
        _create_matching_pair(db, existing)

        print(f"{len(existing)} comptes disponibles, {count + 2} signalements ajoutés.")
        print(f"Connexion : {SEED_PREFIX}0000 à {SEED_PREFIX}{args.users - 1:04d}")
        print(f"Mot de passe commun : {SEED_PASSWORD}")


if __name__ == "__main__":
    main()
