# Verso

> [🇬🇧 English](README.md) | [🇷🇺 Русский](README.ru.md) | 🇫🇷 Français | [🇩🇪 Deutsch](README.de.md)

[![CI](https://github.com/DogNellaf/verso-bookshop/actions/workflows/ci.yml/badge.svg)](https://github.com/DogNellaf/verso-bookshop/actions/workflows/ci.yml)
![Python](https://img.shields.io/badge/python-3.12-3776AB)
![Django](https://img.shields.io/badge/django-5-092E20)
![Vue](https://img.shields.io/badge/vue-3-42B883)
![TypeScript](https://img.shields.io/badge/typescript-5-3178C6)
![PostgreSQL](https://img.shields.io/badge/postgresql-16-4169E1)
![License](https://img.shields.io/badge/license-MIT-green)

Une librairie en ligne : une API Django REST Framework avec une interface
d'administration et une vitrine en Vue 3 + TypeScript. Les visiteurs
parcourent et recherchent le catalogue, gardent un panier persistant, passent
commande, puis suivent ou annulent leurs commandes. L'interface est en anglais
par défaut et disponible en russe, en français et en allemand via le sélecteur
de langue de l'en-tête — catalogue de livres compris.

![Catalogue](docs/screenshots/fr/catalog.png)

## Démarrage rapide

```bash
docker compose up --build
```

Ouvrez <http://localhost:8080> et cliquez sur **Compte de démo** sur la page de
connexion (**demo / demopass123**). L'utilisateur de démo a déjà trois
commandes dans différents états et un panier rempli. Au premier démarrage, 18
romans classiques sont chargés dans le catalogue.

- Référence interactive de l'API (Swagger UI) : <http://localhost:8080/api/docs/>
- Administration : <http://localhost:8080/admin/> — définissez
  `DJANGO_SUPERUSER_USERNAME` et `DJANGO_SUPERUSER_PASSWORD` dans `.env` pour
  qu'un compte soit créé au démarrage.

Pour voir la protection du stock en action, mettez les derniers exemplaires
d'un livre dans le panier depuis deux navigateurs et commandez dans les deux :
la seconde commande est refusée avec un message indiquant combien d'exemplaires
il reste.

## Étude de cas

### Problème

Une petite librairie veut vendre en ligne. La boutique doit se comporter comme
une vraie, pas comme une démo CRUD : ne jamais vendre un exemplaire qu'elle
n'a pas, même quand deux personnes commandent au même moment ; l'historique
des commandes ne doit pas changer quand les prix ou le catalogue sont
modifiés ; et la vitrine doit être agréable sur mobile, en plusieurs langues.

### Solution

L'API REST porte toutes les règles métier ; la SPA est un client typé et léger.
Une commande passe par ces états :

| Statut | Défini par | Effet sur le stock |
|---|---|---|
| **En attente** | La validation du panier | Les exemplaires sont retirés du stock, de façon atomique |
| **Payée / Expédiée / Livrée** | L'équipe, dans l'administration | — |
| **Annulée** | Le client (seulement tant qu'elle est en attente) | Les exemplaires reviennent en stock |

La validation du panier est une seule transaction qui verrouille d'abord les
lignes des livres concernés :

```python
with transaction.atomic():
    books = {b.id: b for b in Book.objects.select_for_update().filter(id__in=ids)}
    errors = [stock_message(books[i.book_id]) for i in items
              if i.quantity > books[i.book_id].stock]
    if errors:
        raise ValidationError({"detail": _("Not enough stock."), "items": errors})
    order = Order.objects.create(buyer=user)
    ...  # instantané du titre et du prix, décrément du stock, vidage du panier
```

### Points techniques

- **Pas de survente.** La commande et l'annulation verrouillent les lignes des
  livres avec `SELECT … FOR UPDATE` ; vérification, mouvements de stock et
  commande forment une seule transaction, donc un échec ne laisse aucune trace.
- **L'historique est un instantané.** Chaque ligne de commande conserve le
  titre et le prix unitaire au moment de l'achat, et la clé étrangère vers le
  livre est `SET_NULL` : modifier ou supprimer un livre ne réécrit jamais les
  commandes passées.
- **Nombre de requêtes constant.** Le panier charge articles et livres en un
  seul `JOIN` plus une requête pour les traductions ; un test fige le nombre de
  requêtes SQL, si bien qu'une régression N+1 fait échouer la CI.
- **L'URL est l'état.** Recherche, tri, filtre « en stock » et numéro de page
  sont dans la query string : toute vue du catalogue peut être partagée,
  rechargée ou retrouvée avec le bouton « précédent ».
- **Un seul rafraîchissement de jeton.** Quand le jeton d'accès expire, toutes
  les réponses 401 simultanées attendent un unique rafraîchissement au lieu de
  se concurrencer avec le même jeton de rafraîchissement tournant.
- **Un rendu soigné, même hors ligne.** Les livres sans image reçoivent une
  couverture typographique générée (couleur dérivée du titre), et les fichiers
  de Swagger UI sont servis localement — aucun CDN tiers n'est nécessaire.
- **Une API documentée et validée.** Le schéma OpenAPI 3 est généré depuis le
  code et validé en CI, avertissements traités comme des erreurs.

### Sécurité

- Les jetons d'accès JWT durent 30 minutes ; les jetons de rafraîchissement
  tournent à chaque utilisation. Si la session ne peut pas être rafraîchie,
  l'interface déconnecte l'utilisateur au lieu d'afficher un état périmé.
- Connexion, inscription et rafraîchissement du jeton sont limités en débit
  (`20/min` par défaut) ; le trafic anonyme et authentifié a ses propres limites.
- L'inscription applique les validateurs de mot de passe de Django.
- La redirection `?next=` après connexion n'accepte que des chemins relatifs du
  même site : impossible de l'utiliser comme redirection ouverte.
- Chaque utilisateur ne voit que son panier et ses commandes ; le reste renvoie
  une 404.
- Secrets et hôtes viennent de l'environnement. `HTTPS=True` active les cookies
  sécurisés, HSTS et la redirection HTTPS ; `X-Frame-Options: DENY` et
  `nosniff` sont toujours actifs.

### Localisation

- **Anglais, russe, français et allemand.** L'anglais est la langue par défaut
  pour tous ; la langue du navigateur est volontairement ignorée, et le
  sélecteur EN / RU / FR / DE mémorise le choix dans le navigateur et met à
  jour `<html lang>`.
- **L'interface** est traduite avec vue-i18n, avec de vraies règles de pluriel
  (« 0 livre / 2 livres », « 1 книга / 3 книги / 5 книг »). Un test vérifie que
  chaque langue possède exactement les mêmes clés.
- **Le catalogue** est traduisible lui aussi : `BookTranslation` stocke titre,
  auteur et description par langue, avec repli sur l'original anglais. La
  recherche trouve un livre dans toutes les langues, et le tri par titre ou
  auteur utilise les valeurs traduites.
- **Les messages de l'API** sont traduits avec le gettext de Django. La SPA
  envoie la langue choisie dans `Accept-Language`, donc des erreurs comme « Il
  ne reste que 2 exemplaires » arrivent dans la langue de l'utilisateur, au bon
  pluriel. La CI vérifie que les catalogues `.mo` compilés correspondent aux
  sources `.po`.
- Prix et dates sont formatés avec `Intl` selon la langue active.

### Architecture

```mermaid
flowchart LR
    U[Navigateur<br/>SPA Vue 3] -->|HTTP| N[nginx<br/>SPA statique + reverse proxy]
    N -->|/api, /admin, /static| G[gunicorn<br/>Django + DRF]
    N -->|/media| M[(Volume média<br/>couvertures)]
    G --> P[(PostgreSQL)]
    G --> M
```

La SPA et l'API sont servies depuis la même origine : pas de CORS en
production, et le frontend utilise des URL relatives. En développement, le
serveur Vite relaie les mêmes chemins vers `runserver`.

| Module | Rôle |
|---|---|
| `backend/main/views.py` | Catalogue, authentification, panier, commande, historique, annulation |
| `backend/main/serializers.py` | Formats de l'API ; choisit la traduction du livre selon la langue |
| `backend/main/models.py` | `Book`, `BookTranslation`, `Cart`, `CartItem`, `Order`, `OrderItem` |
| `backend/main/management/commands/seed.py` | Catalogue de démo, traductions, couvertures, utilisateur de démo |
| `frontend/src/services/api.ts` | Client API typé, stockage JWT, rafraîchissement partagé |
| `frontend/src/router.ts` | Routes chargées à la demande, gardes d'authentification, titres |
| `frontend/src/i18n/` | Configuration vue-i18n, règles de pluriel, textes EN/RU/FR/DE |

### Ce que la refonte a changé

Le projet était au départ une boutique Django rendue côté serveur, où une
commande ne contenait qu'un livre, puis il a été séparé en une API REST et un
frontend Vue. Pour le rendre présentable dans un portfolio, il a fallu :

- retirer les restes d'un squelette généré : chaîne Tailwind/PostCSS inutilisée,
  typages React, analytics et images de remplacement ;
- ajouter l'annulation de commande avec remise en stock sous verrou, des
  filtres de catalogue et un panier à nombre de requêtes constant ;
- documenter l'API avec OpenAPI + Swagger UI, ajouter la limitation de débit,
  un health check branché dans docker-compose et le durcissement HTTPS ;
- reconstruire la vitrine : état dans l'URL, gardes avec retour après
  connexion, sélecteurs de quantité selon le stock, squelettes, états vides,
  page 404, mode sombre et affichage mobile ;
- traduire l'interface, les messages de l'API et le catalogue en russe,
  français et allemand ;
- porter la suite de tests à 138 tests et ajouter à la CI le lint, la
  validation du schéma, la vérification des traductions et la couverture.

## Captures d'écran

| Page d'un livre | Panier |
|---|---|
| ![Page d'un livre](docs/screenshots/fr/book-detail.png) | ![Panier](docs/screenshots/fr/cart.png) |

| Mode sombre | Mobile |
|---|---|
| ![Mode sombre](docs/screenshots/fr/catalog-dark.png) | ![Mobile](docs/screenshots/fr/mobile-cart.png) |

| Historique des commandes | Référence de l'API |
|---|---|
| ![Commandes](docs/screenshots/fr/orders.png) | ![Swagger UI](docs/screenshots/api-docs.png) |

## Lancer sans Docker

Il faut Python 3.12+, Node.js 20+ et pnpm. SQLite est utilisé si aucun
paramètre Postgres n'est fourni.

```bash
./scripts/build-dev.sh          # Linux / macOS : installe et lance les deux applications
.\scripts\build-dev.ps1         # Windows (PowerShell)
```

Ou à la main :

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py seed           # catalogue de démo, traductions, couvertures, utilisateur de démo
python manage.py runserver      # http://127.0.0.1:8000

cd ../frontend
pnpm install
pnpm run dev                    # http://127.0.0.1:5173
```

Les couvertures des livres de démo (issues d'Open Library) sont fournies dans
`backend/main/fixtures/covers/`, donc `seed` fonctionne hors ligne. Pour un
livre sans couverture fournie, `seed` la télécharge depuis Open Library ;
`--save-covers` y enregistre les téléchargements, `--no-covers` les désactive,
`--flush` repart de zéro.

## Configuration

Les paramètres viennent des variables d'environnement ; docker-compose les lit
dans `.env`. Voir [`.env.example`](.env.example).

| Variable | Rôle | Par défaut |
|---|---|---|
| `SECRET_KEY` | Clé secrète Django | clé de dev non sûre |
| `DEBUG` | Mode debug | `True` (`False` dans Docker) |
| `ALLOWED_HOSTS` | Hôtes autorisés, séparés par des virgules | hôtes locaux en debug |
| `CORS_ALLOWED_ORIGINS`, `CSRF_TRUSTED_ORIGINS` | Origines du frontend | serveur Vite |
| `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_HOST`, `POSTGRES_PORT` | PostgreSQL si `POSTGRES_DB` est défini | SQLite |
| `SEED_ON_START` | Charger les données de démo au démarrage du conteneur | `1` |
| `DJANGO_SUPERUSER_USERNAME`, `DJANGO_SUPERUSER_PASSWORD`, `DJANGO_SUPERUSER_EMAIL` | Compte administrateur créé au démarrage | — |
| `HTTPS` | Cookies sécurisés, HSTS, redirection HTTPS | `False` |
| `THROTTLE_ANON`, `THROTTLE_USER`, `THROTTLE_AUTH` | Limites de débit | `120/min`, `600/min`, `20/min` |
| `LOG_LEVEL` | Niveau de journalisation | `INFO` |

## Tests

```bash
cd backend
ruff check . && ruff format --check .
coverage run manage.py test && coverage report

cd ../frontend
pnpm run type-check
pnpm run coverage
```

Le backend compte 60 tests (94 % de couverture) : API, modèles, commande
concurrente, annulation, filtres, traductions, nombre de requêtes SQL,
limitation de débit et commande `seed`. Le frontend compte 78 tests (92 % de
couverture) : pages, gardes du routeur, client API, composants et i18n. La CI
vérifie aussi les migrations manquantes, valide le schéma OpenAPI, contrôle les
traductions compilées et construit les images Docker.

Les captures dans toutes les langues sont prises depuis une instance en cours
d'exécution : `cd frontend && BASE_URL=http://localhost:8080 pnpm run screenshots`.

## Limites

Limites connues de l'implémentation actuelle :

- Pas de prestataire de paiement : la commande est créée « en attente », puis
  l'équipe la fait avancer dans l'administration.
- Seuls les livres de démo sont traduits ; un nouveau livre s'affiche en
  anglais tant qu'aucune traduction n'est ajoutée dans l'administration.
- Les prix sont dans une seule devise (USD) pour toutes les langues.
- Les JWT sont gardés dans `localStorage`. Une session en cookie httpOnly
  résisterait mieux au XSS, au prix d'une gestion du CSRF.
- La recherche utilise `icontains` ; un gros catalogue demanderait la
  recherche plein texte de PostgreSQL.

## Structure du projet

```
├── backend/
│   ├── bookshop/            # Paramètres et URLconf racine
│   ├── locale/              # Messages de l'API en russe, français et allemand (gettext)
│   └── main/
│       ├── fixtures/covers/ # Couvertures de démo (seed hors ligne)
│       ├── management/      # Commande seed et traductions du catalogue
│       ├── filters.py, pagination.py, serializers.py, views.py, admin.py
│       └── tests.py
├── frontend/
│   ├── src/
│   │   ├── i18n/            # Configuration vue-i18n et textes EN/RU/FR/DE
│   │   ├── pages/           # Catalogue, livre, panier, commandes, connexion, inscription, 404
│   │   ├── components/      # BookCover, StockBadge
│   │   ├── services/api.ts  # Client API typé
│   │   └── router.ts
│   ├── scripts/screenshots.mjs
│   └── nginx.conf
├── docs/screenshots/        # en/, ru/, fr/, de/
├── docker-compose.yml
└── .github/workflows/ci.yml
```

## Licence

[MIT](LICENSE)
