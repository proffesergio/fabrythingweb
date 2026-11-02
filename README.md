# Fabrything

Commerce platform for Bangladesh: product storefront, inventory and orders,
food delivery, printing services, and the NobleSeek news desk.

Production: https://www.fabrything.com. React and Django run on Vercel, with
Neon PostgreSQL and Cloudflare R2. Store orders use Cash on Delivery.

## Project structure

```text
backend/       Django entrypoints, settings, domain apps, migrations and tests
frontend/      React app, public assets, browser checks and npm configuration
docs/          Setup, feature guides, production evidence and recovery memory
tools/         Asset-generation utilities
.github/       Repository instructions
```

Backend domain modules are independent Django apps: accounts, catalog, inventory,
purchasing, orders, storefront, food, printing, nobleseek, chat, analytics and core.
Frontend customer, admin, vendor and rider interfaces live under frontend/src/.

## Development

Follow [local setup](docs/SETUP.md) for environment variables, database migrations
and admin creation. After setup, use separate terminals:

```bash
# API, from the repository root
cd backend
source .venv/bin/activate
python manage.py runserver

# React, from the repository root in another terminal
cd frontend
npm ci
npm start
```

API: http://localhost:8000/api/. Frontend: http://localhost:3000/.
Admin sign-in: http://localhost:3000/admin/auth.

## Verification

```bash
# From backend/, with its environment active; isolated SQLite
python manage.py test --settings=config.settings.test --noinput
python manage.py makemigrations --check --dry-run --settings=config.settings.test

# From frontend/; run separately on low-memory machines
CI=true NODE_OPTIONS=--max-old-space-size=1024 npm test -- --watchAll=false --runInBand --silent
NODE_OPTIONS=--max-old-space-size=1536 GENERATE_SOURCEMAP=false REACT_APP_API_URL=/api/ npm run build
```

## Operations

Vercel project roots are `frontend` for `fabrythingweb` and `backend` for
`fabrythingapi`. Each service owns its vercel.json. Preserve the frontend API
rewrites and their trailing-slash behavior.

- [Recovery checkpoint and memory graph](docs/project-memory/CURRENT.md)
- [Production release](docs/PRODUCTION_RELEASE.md)
- [Domain configuration](docs/CLOUDFLARE_DNS_SETUP.md)
- [Control Center worker and provider setup](docs/CONTROL_CENTER_SETUP.md)
- [NobleSeek setup](docs/NOBLESEEK_SETUP.md)

Environment files, credentials, builds and local CLI state are ignored. Commit
migrations and environment examples; keep live data and secrets out of Git.
