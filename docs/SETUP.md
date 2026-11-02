# Local setup

Use Python 3.12, PostgreSQL, and Node with npm. Run commands from the repository
root unless stated otherwise.

## Backend

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Edit backend/.env: set a unique SECRET_KEY and local DATABASE_NAME, DATABASE_USER,
DATABASE_PASSWORD, DATABASE_HOST and DATABASE_PORT. Create that PostgreSQL
database before continuing. Use local development data or an isolated development
branch. Optional storage credentials can be left unset for database-backed images.

Apply the migrations already in the repository; keep their history intact:

```bash
python manage.py migrate
python manage.py seed_admin_modules
```

Create an admin using your own username, email and password via
`python manage.py create_admin --username <username> --email <email> --password <password>`.
Replace placeholders with your own values. This command sets the platform role
and domain ownership required by the back-office UI. No default admin credentials
are provided. Then start the API:

```bash
python manage.py runserver
```

Seed commands are explicit operator actions. `seed_demo --if-empty` is optional
for a disposable local database; production deploys do not run demo seeds.
API: http://localhost:8000/api/. Django admin: http://localhost:8000/admin/.

## Frontend

In a separate terminal, from the repository root:

```bash
cd frontend
cp .env.example .env
npm ci
npm start
```

Set REACT_APP_API_URL=http://localhost:8000/api/ in frontend/.env, including the
trailing slash. Browse http://localhost:3000/; admin sign-in is /admin/auth.

## Checks and deployment

See the [root README](../README.md) for isolated test and build commands and the
[production guide](PRODUCTION_RELEASE.md) for release details. Django defaults
to config.settings.dev; production uses config.settings.prod. Tests explicitly
use config.settings.test, which isolates them from PostgreSQL.

Vercel service roots are backend/ and frontend/. The API uses config/wsgi.py;
the frontend publishes build/. The former Render bootstrap has been removed.
Maintenance, seeding and persistent sync workers are separate operations; see
[Control Center setup](CONTROL_CENTER_SETUP.md).
