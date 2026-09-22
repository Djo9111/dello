from slowapi import Limiter
from slowapi.util import get_remote_address

# Stockage en mémoire : suffisant pour une seule instance de l'API.
# Avec plusieurs instances, il faudra un stockage partagé (Redis).
limiter = Limiter(key_func=get_remote_address)