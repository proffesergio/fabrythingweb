# Fabrything — project map

Read this before exploring. It exists so a fresh session does not have to
re-derive the layout with Glob/Grep. If something here contradicts the code,
the code wins — fix this file in the same commit.

## Stack & layout

Django 5 + DRF backend, Create-React-App (React 18 + MUI 5 + Redux Toolkit)
frontend, Postgres (Neon) in prod. Backend deploys to Render
(`https://fabrythingweb.onrender.com`), frontend to Vercel (fabrything.com).

```
backend/EcommerceInventory/     Django project (manage.py lives here)
  config/settings/{base,dev,prod,test}.py   dev is the manage.py default
  accounts/    custom User (roles), auth, dynamic-form controllers
  core/        helpers.py, middleware, S3/local file upload view
  catalog/ inventory/ purchasing/ orders/   original ERP/inventory domain
  storefront/  public e-commerce storefront API
  food/        food-delivery marketplace  ← most active area
frontend/ecommerce_inventory/src/
  pages/       admin panel (Auth.js, DynamicForm.js, food/, products/, users/…)
  food/        customer-facing food ordering (pages/, components/, redux/, context/)
  vendor/      restaurant-owner panel
  rider/       RiderDashboard.js
  storefront/  public shop
  hooks/       APIHandler.js (useApi → callApi), apiCache, useCachedApi
  utils/       config.js (API base), ProtectedRoute, VendorRoute, Helper
  layout/      shell + MUI theme
```

## Conventions that bite

- **Response envelope.** Every endpoint returns `{data, message}` via
  `core.helpers.renderResponse`. The frontend toasts only `message`, so
  DRF field errors sitting in `data` are invisible unless a screen reads them.
  `EnvelopeModelViewSetMixin` (`food/views_vendor.py`) wraps ModelViewSet in it
  and returns the literal message `"Validation error"` on a 400.
- **No default auth class.** `REST_FRAMEWORK` sets no
  `DEFAULT_AUTHENTICATION_CLASSES`; every authenticated view must declare
  `authentication_classes = [JWTAuthentication]` or `request.user` is anonymous
  despite a valid bearer token.
- **Roles** live on `accounts.User.role` (string, not a group): `Super Admin`,
  `Admin`, `Supplier`, `Customer`, `Staff`, `Restaurant`, `Rider`.
  Food permission classes: `IsRestaurantOwner`, `IsRider`, `IsPlatformAdmin`
  (`food/permissions.py`).
- **Login redirect is role-blind.** `pages/Auth.js` sends every successful login
  to `/admin/home`. Non-admin roles land on an empty admin dashboard.
- **Image fields are `URLField`, not `ImageField`** (`FoodItem.image`,
  `Restaurant.logo/cover_image`). Upload goes through
  `POST /api/uploads/` (`core/views.FileUploadViewInS3` — S3 when AWS keys are
  set, otherwise local `MEDIA_ROOT`) which returns a URL you then store.
- **`FoodItem.category_id` is a ForeignKey literally named `category_id`.**
  Not a raw id column. Serializers expose it as a pk int.
- Admin sidebar modules are DB-driven — a new admin page needs a module row
  seeded before it appears live (see `food/management/commands/seed_food_modules.py`).

## API surface

Root mounts (`config/urls.py`): `api/auth/`, `api/getForm/<model>/`,
`api/getMenus/`, `api/products/`, `api/inventory/`, `api/orders/`,
`api/uploads/`, `api/store/`, `api/food/`.

`api/food/` (`food/urls.py`) — public `restaurants/`, `restaurants/<slug>/`,
`zones/`; customer `orders/`, `orders/<order_code>/`; vendor `vendor/restaurant/`,
`vendor/orders/…` + router `vendor/{categories,items,coupons}`; admin
`admin/dashboard/`, `admin/orders/…`, `admin/orders/<pk>/assign/`,
`admin/payments/` + router `admin/{restaurants,zones,categories,items,option-groups,options,coupons,riders}`;
rider `rider/{me,availability,orders,orders/<pk>/status}`; plus
`coupons/validate/`, `notifications/`, `loyalty/`.

## food/ module

19 models in `food/models.py`: `DeliveryZone`, `Village`, `Restaurant`,
`RestaurantHours`, `RestaurantZone`, `FoodCategory`, `FoodItem`,
`FoodItemOptionGroup`, `FoodItemOption`, `Coupon`, `FoodOrder`, `FoodOrderItem`,
`PaymentTransaction`, `Rider`, `RiderEarning`, `Notification`, `LoyaltyAccount`,
`LoyaltyLedger` (all inherit `TimeStamped`).

Views are split by audience, not by model:
`views_public` · `views_vendor` · `views_admin` · `views_admin_menu` ·
`views_admin_dashboard` · `views_orders` · `views_food_ext` (coupons, riders,
dispatch, notifications, loyalty, payments). Serializers mirror the same split
(`serializers_admin_menu.py`, `serializers_orders.py`, `serializers_write.py`, …).
Business logic in `services.py` / `services_admin.py`; geography in `geo.py`.

`FoodOrder` has a forward-only state machine (`ALLOWED_TRANSITIONS`):
PLACED → CONFIRMED → PREPARING → OUT_FOR_DELIVERY → DELIVERED, CANCELLED
reachable from any non-terminal state. Money is snapshotted at creation.

Delivery is scoped to Bancharampur: 13 unions (`DeliveryZone`) + 121 villages,
per-zone fees, Leaflet map picker. Seed with
`manage.py seed_bancharampur` / `seed_food_demo`.

Rider today: `Rider` has **no location fields** and no heartbeat — there is no
basis for live tracking or proximity dispatch until those are added. Orders
reach a rider only when an admin manually assigns them in `ManageFoodOrders`.

## Commands

```bash
# backend (from backend/EcommerceInventory, venv at .venv)
python manage.py test food            # 20 test modules under food/tests/
python manage.py migrate
python manage.py runserver

# frontend (from frontend/ecommerce_inventory)
npm start        # CRA dev server
npm test         # react-scripts test (jest + RTL); tests sit beside sources
npm run build
```

Specs and design docs live in `docs/superpowers/specs/`.

<!-- code-review-graph MCP tools -->
## MCP Tools: code-review-graph

> **Status (2026-07-21): not running on the Windows checkout.** `.mcp.json`
> points at `/home/billsbro/Music/fabrythingweb/...` (a Linux path) while this
> clone lives at `C:\Users\bhnbi\Music\SaaS\fabrythingweb`, and
> `code_review_graph` is not installed in `backend/EcommerceInventory/.venv`.
> `graphify-out/` is empty. Until both are fixed the tools below are
> unavailable — use the project map above first, then Grep/Glob/Read.

**IMPORTANT: This project has a knowledge graph. ALWAYS use the
code-review-graph MCP tools BEFORE using Grep/Glob/Read to explore
the codebase.** The graph is faster, cheaper (fewer tokens), and gives
you structural context (callers, dependents, test coverage) that file
scanning cannot.

### When to use graph tools FIRST

- **Exploring code**: `semantic_search_nodes` or `query_graph` instead of Grep
- **Understanding impact**: `get_impact_radius` instead of manually tracing imports
- **Code review**: `detect_changes` + `get_review_context` instead of reading entire files
- **Finding relationships**: `query_graph` with callers_of/callees_of/imports_of/tests_for
- **Architecture questions**: `get_architecture_overview` + `list_communities`

Fall back to Grep/Glob/Read **only** when the graph doesn't cover what you need.

### Key Tools

| Tool | Use when |
| ------ | ---------- |
| `detect_changes` | Reviewing code changes — gives risk-scored analysis |
| `get_review_context` | Need source snippets for review — token-efficient |
| `get_impact_radius` | Understanding blast radius of a change |
| `get_affected_flows` | Finding which execution paths are impacted |
| `query_graph` | Tracing callers, callees, imports, tests, dependencies |
| `semantic_search_nodes` | Finding functions/classes by name or keyword |
| `get_architecture_overview` | Understanding high-level codebase structure |
| `refactor_tool` | Planning renames, finding dead code |

### Workflow

1. The graph auto-updates on file changes (via hooks).
2. Use `detect_changes` for code review.
3. Use `get_affected_flows` to understand impact.
4. Use `query_graph` pattern="tests_for" to check coverage.
