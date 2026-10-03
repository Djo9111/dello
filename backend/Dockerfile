FROM python:3.12-slim AS base

# Pas de fichiers .pyc, sortie non tamponnee pour que les logs
# apparaissent immediatement chez l'hebergeur
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Les dependances d'abord : cette couche ne change que si requirements.txt change
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Utilisateur non privilegie : une faille dans l'application ne donne
# pas les droits d'administration du conteneur
RUN useradd --create-home --uid 1000 dello && chown -R dello:dello /app
USER dello

EXPOSE 8000

# PORT est fourni par l'hebergeur, 8000 sert en local.
# --proxy-headers : sans cela l'API voit l'adresse du proxy, et tous les
# utilisateurs partageraient le meme quota de limitation de debit.
CMD alembic upgrade head && \
    uvicorn app.main:app \
      --host 0.0.0.0 \
      --port ${PORT:-8000} \
      --proxy-headers \
      --forwarded-allow-ips='*' \
      --no-server-header