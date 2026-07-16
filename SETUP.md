# Fabrything — Local Setup (PostgreSQL + COD Storefront)

This project was restructured into a clean Django + React Cash-on-Delivery
storefront. Because the database engine moved from MySQL to **PostgreSQL** and
the Django apps were renamed, you generate a **fresh set of migrations** the
first time you set it up.

## 1. Backend

### 1.1 Prerequisites
- Python 3.12+
- PostgreSQL 14+ running locally (or a connection URL)

### 1.2 Create the database
```bash
createdb fabrything            # or: psql -c "CREATE DATABASE fabrything;"
```

### 1.3 Python environment + dependencies
```bash
cd backend/EcommerceInventory
python -m venv .venv
source .venv/bin/activate       # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 1.4 Environment variables
```bash
cp .env.example .env
# then edit .env — set SECRET_KEY and the DATABASE_* values for your Postgres
```

Key vars (see `.env.example` for the full list):
- `DATABASE_NAME/USER/PASSWORD/HOST/PORT` — PostgreSQL connection
- `SECRET_KEY` — required
- `DEBUG=True` for local dev
- `THROTTLE_ORDER_CREATE=10/hour` — anti-spam cap on COD order creation

### 1.5 Generate migrations & create the schema
The old app migrations were removed on purpose (apps were renamed and the DB
engine changed). Generate fresh ones:
```bash
python manage.py makemigrations accounts catalog inventory purchasing orders storefront core
python manage.py migrate
```

Settings modules:
- `manage.py` defaults to `config.settings.dev`
- production uses `config.settings.prod` (wsgi/asgi default to it)

### 1.6 Create an admin + seed demo data
```bash
python manage.py create_admin --username admin --email admin@fabrything.com --password "adminPass23"
python manage.py seed_admin_modules      # admin-panel menu/permission modules
python manage.py seed_demo               # catalog + variants/stock + store config
```

`seed_demo` builds the full demo store: the curated clothing catalog, a sellable
`ProductVariant` (with stock) for every size, and the global `StoreConfiguration`
(flat ৳60 COD shipping). It is idempotent.

### 1.7 Run
```bash
python manage.py runserver
```
API is at `http://localhost:8000/`. Admin at `http://localhost:8000/admin/`.

## 2. Frontend
```bash
cd frontend/ecommerce_inventory
cp .env.example .env             # REACT_APP_API_URL=http://localhost:8000/api/ (note the /api/ suffix)
npm install
npm start
```
Storefront: `http://localhost:3000/` · Admin panel: `http://localhost:3000/admin/auth`

## 3. Verifying the COD flow
1. Browse the shop, open a product, pick a size (a variant), add to cart.
2. As a guest, add items → register/login → cart merges into your account.
3. Checkout is a 2-step COD flow: delivery address + phone, then review & place.
4. Shipping is the flat rate from `StoreConfiguration` (change it in Django admin).
5. In the admin order view, move an order through
   `PENDING_VERIFICATION → CONFIRMED → OUT_FOR_DELIVERY → DELIVERED`.
   Cancelling or returning an order **restocks** its variants automatically.

### Over-sell safety
`orders/services.py::place_cod_order` locks each variant row with
`select_for_update()` inside a single `transaction.atomic` block before checking
and decrementing stock, so concurrent checkouts cannot oversell the last unit.

## 4. Project layout (backend)
```
config/       settings (base/dev/prod), urls, wsgi, asgi
core/         StoreConfiguration, shared helpers, middleware, permissions
accounts/     Users, addresses, auth (was UserServices)
catalog/      Products, Categories, ProductVariant (was ProductServices)
inventory/    warehouse/batch stock — back-office (was InventoryServices)
purchasing/   PurchaseOrder/SalesOrder — back-office (was OrderService)
orders/       COD Order + OrderItem + state machine + checkout service
storefront/   customer API: catalog, cart, COD orders (was StorefrontService)
```
