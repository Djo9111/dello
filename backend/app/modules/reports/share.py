"""Page publique d'un signalement.

Un signalement partagé sur les réseaux doit mener quelque part pour
quelqu'un qui n'a pas encore l'application. Cette page montre exactement
ce que voit un utilisateur connecté, sans numéro de téléphone ni lieu
précis : la mise en relation reste dans Dello, après vérification.
"""

from html import escape

from app.core.config import settings
from app.modules.reports.models import Report, ReportKind

_DOCUMENT_LABELS = {
    "cni": "Carte d'identité",
    "permis": "Permis de conduire",
    "passeport": "Passeport",
    "carte_etudiant": "Carte étudiant",
    "carte_consulaire": "Carte consulaire",
    "autre": "Autre document",
}

_CIRCUMSTANCE_LABELS = {"lost": "Égaré", "stolen": "Volé"}


def share_text(report: Report) -> str:
    """Texte proposé au partage. Aucun numéro de téléphone : c'est tout
    l'intérêt par rapport à une publication sur un réseau social."""
    documents = ", ".join(
        _DOCUMENT_LABELS[document.document_type.value] for document in report.documents
    )
    action = "Trouvé" if report.kind is ReportKind.FOUND else "Perdu"

    return (
        f"{action} : {documents} à {report.commune or report.region}. "
        f"Si cela vous concerne, ouvrez le lien pour entrer en contact "
        f"en toute sécurité sur Dello.\n{share_url(report.id)}"
    )


def share_url(report_id) -> str:
    return f"{settings.PUBLIC_BASE_URL.rstrip('/')}/r/{report_id}"


def render_page(report: Report) -> str:
    """Page autonome, sans dépendance externe ni donnée personnelle."""
    # Nos propres libellés sont des constantes : l'apostrophe de
    # "Carte d'identité" n'a pas besoin d'être échappée. Seules les
    # données venant des utilisateurs le sont intégralement.
    documents = "".join(
        f"<li>{escape(_DOCUMENT_LABELS[document.document_type.value], quote=False)}</li>"
        for document in report.documents
    )

    is_found = report.kind is ReportKind.FOUND
    title = "Document trouvé" if is_found else "Document perdu"

    circumstance = ""
    if report.circumstance is not None:
        circumstance = (
            f'<p class="tag">'
            f"{escape(_CIRCUMSTANCE_LABELS[report.circumstance.value], quote=False)}"
            f"</p>"
        )

    place = escape(report.commune or "") or escape(report.region)
    region = escape(report.region)
    owner = escape(report.owner_name_masked or "Non précisé")
    occurred = report.occurred_on.strftime("%d/%m/%Y") if report.occurred_on else "Non précisée"

    return f"""<!doctype html>
<html lang="fr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<!-- Un signalement de piece d'identite n'a rien a faire dans un moteur de recherche -->
<meta name="robots" content="noindex, nofollow, noarchive">
<title>{escape(title, quote=False)} - Dello</title>
<style>
  :root {{ --bleu: #13497B; --ocre: #C2762A; --vert: #1E7A5C; --sable: #FAF7F2; --encre: #1B2733; }}
  * {{ box-sizing: border-box; }}
  body {{ margin: 0; background: var(--sable); color: var(--encre);
         font-family: system-ui, -apple-system, "Segoe UI", Roboto, sans-serif; }}
  .page {{ max-width: 520px; margin: 0 auto; padding: 24px 20px 48px; }}
  header {{ text-align: center; padding: 24px 0 12px; }}
  .logo {{ font-size: 28px; font-weight: 800; color: var(--bleu); letter-spacing: .5px; }}
  .baseline {{ color: #5B6B7B; font-size: 14px; margin-top: 4px; }}
  .card {{ background: #fff; border: 1px solid #E8E2D9; border-radius: 16px;
           padding: 20px; margin-top: 20px; }}
  .badge {{ display: inline-block; padding: 6px 12px; border-radius: 20px;
            font-size: 13px; font-weight: 700;
            color: {'var(--vert)' if is_found else 'var(--ocre)'};
            background: {'rgba(30,122,92,.12)' if is_found else 'rgba(194,118,42,.12)'}; }}
  .tag {{ display: inline-block; margin: 8px 0 0; padding: 4px 10px; font-size: 12px;
          border-radius: 8px; background: #F1EDE6; color: #5B6B7B; }}
  h1 {{ font-size: 22px; margin: 12px 0 4px; }}
  ul {{ margin: 8px 0 0; padding-left: 20px; }}
  li {{ margin-bottom: 4px; }}
  dl {{ margin: 16px 0 0; }}
  dt {{ font-size: 12px; color: #5B6B7B; margin-top: 12px; }}
  dd {{ margin: 2px 0 0; font-weight: 600; }}
  .cta {{ display: block; margin-top: 20px; padding: 16px; text-align: center;
          background: var(--bleu); color: #fff; text-decoration: none;
          border-radius: 12px; font-weight: 600; }}
  .note {{ margin-top: 16px; font-size: 13px; color: #5B6B7B; line-height: 1.5; }}
</style>
</head>
<body>
<div class="page">
  <header>
    <div class="logo">DELLO</div>
    <div class="baseline">Documents perdus et trouvés au Sénégal</div>
  </header>

  <div class="card">
    <span class="badge">{escape(title, quote=False)}</span>
    {circumstance}
    <h1>{escape(place)}</h1>
    <ul>{documents}</ul>
    <dl>
      <dt>Nom sur le document</dt><dd>{owner}</dd>
      <dt>Région</dt><dd>{region}</dd>
      <dt>Date</dt><dd>{escape(occurred)}</dd>
    </dl>
    <a class="cta" href="{escape(settings.PLAY_STORE_URL)}">Ouvrir dans Dello</a>
    <p class="note">
      Les coordonnées ne sont jamais publiées. Pour entrer en contact,
      installez Dello et faites une demande : l'échange se fait seulement
      après vérification.
    </p>
  </div>
</div>
</body>
</html>"""


def render_not_found() -> str:
    return f"""<!doctype html>
<html lang="fr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="robots" content="noindex, nofollow">
<title>Signalement introuvable - Dello</title>
<style>
  body {{ margin: 0; background: #FAF7F2; color: #1B2733;
         font-family: system-ui, -apple-system, "Segoe UI", Roboto, sans-serif; }}
  .page {{ max-width: 520px; margin: 0 auto; padding: 64px 24px; text-align: center; }}
  .logo {{ font-size: 28px; font-weight: 800; color: #13497B; }}
  p {{ color: #5B6B7B; line-height: 1.6; }}
  a {{ display: inline-block; margin-top: 20px; padding: 14px 24px; background: #13497B;
      color: #fff; text-decoration: none; border-radius: 12px; font-weight: 600; }}
</style>
</head>
<body>
<div class="page">
  <div class="logo">DELLO</div>
  <p>Ce signalement n'est plus disponible.<br>
     Le document a peut-être déjà été restitué.</p>
  <a href="{escape(settings.PLAY_STORE_URL)}">Découvrir Dello</a>
</div>
</body>
</html>"""