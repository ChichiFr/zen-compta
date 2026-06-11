# Deploiement prive sur Render

Objectif: mettre Zen Compta en ligne avec un lien prive pour une demo, sans
mettre de secrets dans GitHub.

Architecture:

```text
Utilisateur
  -> Frontend Render
  -> Backend Render
  -> PostgreSQL Render
```

## 1. Creer PostgreSQL

1. Ouvrir le Render Dashboard: https://dashboard.render.com/
2. Cliquer `New +`.
3. Choisir `Postgres`.
4. Renseigner:
   - Name: `zen-compta-db`
   - Region: choisir la meme region pour la base, le backend et le frontend.
   - Plan: choisir le plan le moins cher pour la demo.
5. Cliquer `Create Database`.
6. Quand la base est prete, ouvrir l'onglet `Info`.
7. Copier `Internal Database URL`.

Render donne souvent une URL comme:

```text
postgresql://user:password@host:5432/database
```

Dans le backend, utiliser le format SQLAlchemy avec `psycopg`:

```text
postgresql+psycopg://user:password@host:5432/database
```

## 2. Creer le backend

1. Render Dashboard -> `New +`.
2. Choisir `Web Service`.
3. Connecter le repo GitHub `ChichiFr/zen-compta`.
4. Choisir la branche `main`.
5. Configurer le service:
   - Name: `zen-compta-api`
   - Root Directory: `backend`
   - Runtime: `Python`
   - Build Command:

```bash
pip install -r requirements.txt
```

   - Start Command:

```bash
alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

6. Ajouter les variables d'environnement:

| Key | Value |
| --- | --- |
| `ENVIRONMENT` | `production` |
| `DATABASE_URL` | Render internal database URL, converted to `postgresql+psycopg://...` |
| `INTERNAL_API_TOKEN` | Long random secret |
| `OPENAI_API_KEY` | OpenAI project key |
| `OPENAI_INVOICE_MODEL` | `gpt-5.5` |
| `UPLOAD_STORAGE_DIR` | `private_uploads` |

`INTERNAL_API_TOKEN` doit etre une valeur longue et impossible a deviner. Il
faut reutiliser exactement la meme valeur cote frontend.

Pour generer un secret localement:

```powershell
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

7. Creer le service.
8. Tester le backend:

```text
https://zen-compta-api.onrender.com/api/health
```

Resultat attendu:

```json
{"status":"ok"}
```

## 3. Creer le frontend

1. Render Dashboard -> `New +`.
2. Choisir `Web Service`.
3. Connecter le meme repo GitHub `ChichiFr/zen-compta`.
4. Choisir la branche `main`.
5. Configurer le service:
   - Name: `zen-compta`
   - Root Directory: `frontend`
   - Runtime: `Node`
   - Build Command:

```bash
npm install && npm run build
```

   - Start Command:

```bash
npm run start -- --hostname 0.0.0.0 --port $PORT
```

6. Ajouter les variables d'environnement:

| Key | Value |
| --- | --- |
| `NEXT_PUBLIC_API_URL` | Backend Render URL, for example `https://zen-compta-api.onrender.com` |
| `INTERNAL_API_TOKEN` | Same value as backend |
| `ZEN_COMPTA_APP_PASSWORD` | Private demo password |
| `ZEN_COMPTA_SESSION_SECRET` | Another long random secret |

`ZEN_COMPTA_APP_PASSWORD` est le mot de passe que l'utilisateur saisira sur la
page de login.

7. Creer le service.
8. Ouvrir:

```text
https://zen-compta.onrender.com/login
```

## 4. Test de demo

Tester dans cet ordre:

1. Login.
2. Page `Factures`.
3. Import d'une facture PDF ou image.
4. Revue de la facture importee.
5. Validation.
6. Page `Prevision`.
7. Modifier cash, CA, baisse de CA.
8. Verifier la phrase `combien de mois on tient`.

## 5. Limites connues pour la demo

- Ne pas partager le lien publiquement.
- Utiliser un mot de passe fort.
- Mettre peu de donnees sensibles au debut.
- Les uploads dans `private_uploads` sont acceptables pour une demo courte,
  mais pas pour une vraie production.
- Pour une vraie production, ajouter un stockage fichier durable type S3.
- Si `gpt-5.5` n'est pas disponible sur le compte OpenAI, remplacer
  `OPENAI_INVOICE_MODEL` par un modele disponible.

## 6. Verifications locales avant deploy

Avant de deployer, lancer:

```powershell
.\scripts\check.ps1
```

Ne pas deployer si les tests, le build ou le scan de securite echouent.

## Docs Render utiles

- https://render.com/docs/postgresql-creating-connecting
- https://render.com/docs/deploy-fastapi
- https://render.com/docs/deploy-nextjs-app
- https://render.com/docs/configure-environment-variables
