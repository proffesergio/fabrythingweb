# Food Admin Panel (Production) — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:executing-plans (inline) or subagent-driven-development. Steps use `- [ ]` checkboxes. Strict TDD: failing test → run red → implement → run green.

**Goal:** A production-ready, modern Food admin console inside the existing admin shell — dashboard with KPIs+charts, order management, full restaurant onboarding (create + owner login + hours + zones), an admin menu builder (categories/items/options for any restaurant), and delivery-zone controls.

**Architecture:** New/enhanced admin endpoints under `/api/food/admin/` (all `IsPlatformAdmin`), consumed by React pages under `src/pages/food/` registered as `accounts.Modules` (auto-seeded on deploy via `build.sh → seed_food_modules`). Reuse `renderResponse`, `EnvelopeModelViewSetMixin`, `useApi`, MUI, recharts.

**Tech stack:** Django REST, SimpleJWT, React/MUI, recharts (installed), Redux (existing sidebar/Modules).

## Global constraints
- All `/api/food/admin/*` views carry `authentication_classes=[JWTAuthentication]` + `permission_classes=[IsAuthenticated, IsPlatformAdmin]` (PermissionMiddleware bypasses `/api/food/`).
- Money DecimalField(10,2), BDT ৳. Responses use the `renderResponse` envelope.
- Backend tests: Django `TestCase` + `APIClient`, JWT via `RefreshToken.for_user`. Run: `DJANGO_SETTINGS_MODULE=config.settings.test ./.venv/Scripts/python.exe manage.py test food`.
- Frontend tests: `CI=true npx react-scripts test <path> --watchAll=false`. Mock `useApi` with the **inline factory** shape (external-ref mocks return undefined here). Use minimal `configureStore` when a store is needed.
- New admin pages register in `seed_food_modules` (auto-runs on deploy) + routes in `App.js` + icon cases in `layout.js`.
- No commits by me — human commits/pulls/merges manually.

---

## Task 1: Admin food dashboard endpoint
**Files:** create `food/views_admin_dashboard.py`; wire `food/urls.py`; test `food/tests/test_admin_dashboard.py`.
**Interfaces:** `GET /api/food/admin/dashboard/` → `{ orders:{today,this_month,total}, revenue:{today,this_month}, status_distribution:{...}, restaurants:{active,pending,total}, recent_orders:[FoodOrderSerializer], top_restaurants:[{name,orders,revenue}], revenue_trend:[{date,total}] (last 14 days) }`. Revenue excludes CANCELLED.
- [ ] Test: admin gets 200 with keys; non-admin 403; revenue sums only non-cancelled; counts correct for seeded orders.
- [ ] Implement mirroring `storefront/views.py::AdminDashboardView` (aggregates via `Sum`/`Count`, `timezone.now()` windows, trend via per-day loop).
- [ ] Run green. Commit checkpoint.

## Task 2: Admin menu CRUD (any restaurant)
**Files:** create `food/views_admin_menu.py`, `food/serializers_admin_menu.py` (option group/option write serializers); wire `food/urls.py`; test `food/tests/test_admin_menu.py`.
**Interfaces (all `?restaurant=<id>` scoped, admin picks the restaurant):**
- `GET/POST/PATCH/DELETE /api/food/admin/categories/` (reuse `FoodCategoryWriteSerializer`).
- `.../admin/items/` (reuse `FoodItemWriteSerializer`; auto-slug like `views_vendor._unique_item_slug`).
- `.../admin/option-groups/` + `.../admin/options/` (new write serializers for `FoodItemOptionGroup`/`FoodItemOption`).
- Each viewset: `get_queryset` filters by `restaurant` (from `?restaurant=` on list, or the object's restaurant); `perform_create` binds `restaurant`/parent from the request; reject cross-restaurant parents (400).
- [ ] Tests: create category/item/option-group/option under a chosen restaurant; item slug auto-generated; option-group must belong to the item; admin-only (customer 403).
- [ ] Implement (mirror `views_vendor` viewsets but restaurant comes from request, permission is `IsPlatformAdmin`). Reuse `EnvelopeModelViewSetMixin`.
- [ ] Run green. Commit checkpoint.

## Task 3: Admin restaurant onboarding (create + owner + hours + zones)
**Files:** modify `food/serializers_admin.py`, `food/views_admin.py`; create `food/tests/test_admin_onboarding.py`.
**Interfaces:**
- `RestaurantAdminSerializer` gains nested read of `hours` and assigned `zones`; keeps `fields="__all__"` + `hours`, `zone_ids`.
- `AdminRestaurantViewSet.create` accepts optional `owner: {username,email,phone,password}` → `Users.objects.create_user(role="Restaurant", ...)` linked as `owner`; auto-slug from name; create `RestaurantHours` from `hours` list; assign zones via `RestaurantZone` from `zone_ids`. Returns the created restaurant.
- `POST /api/food/admin/restaurants/<id>/zones/` body `{zone_id, delivery_fee?}` → upsert `RestaurantZone`; `DELETE` with `{zone_id}` removes it.
- `PUT /api/food/admin/restaurants/<id>/hours/` replaces the week's `RestaurantHours`.
**Interfaces produced:** `create_restaurant_with_owner(...)` helper in `food/services_admin.py` (testable unit).
- [ ] Tests: create restaurant with owner creates a `Users(role=Restaurant)` linked as owner; duplicate email/username → 400; zone assign/remove; hours replace; owner can then log into `/api/food/vendor/restaurant/`.
- [ ] Implement. Run green. Commit checkpoint.

## Task 4: Admin order detail (+ allowed transitions)
**Files:** modify `food/views_orders.py` (add `AdminFoodOrderDetailView`); wire `food/urls.py`; test `food/tests/test_admin_order_detail.py`.
**Interfaces:** `GET /api/food/admin/orders/<id>/` → `FoodOrderSerializer` data + `allowed_transitions: [...]` from `FoodOrder.ALLOWED_TRANSITIONS`. (List + status PATCH already exist from the customer-COD plan.)
- [ ] Test: admin gets detail + allowed_transitions; 404 for missing; non-admin 403.
- [ ] Implement. Run green. Commit checkpoint.

## Task 5: Register modules + routes + icons
**Files:** modify `food/management/commands/seed_food_modules.py`, `src/App.js`, `src/layout/layout.js`; test `food/tests/test_seed_modules.py` (extend existing).
- [ ] Add modules under "Food": **Food Dashboard** (`/manage/food/dashboard`, icon `Dashboard`, order 0), **Food Orders** (`/manage/food/orders`, icon `ReceiptLong`, order 3), **Menu Management** (`/manage/food/menu`, icon `Category`, order 4). Keep Restaurants (1), Delivery Zones (2).
- [ ] `App.js`: import + routes for `FoodDashboard`, `ManageFoodOrders`, `FoodMenuManager`, and `RestaurantDetail` admin page under `/admin`.
- [ ] `layout.js` `getIcon`: add cases `Restaurant`, `Storefront`, `Map`, `ReceiptLong`, `TwoWheeler` → matching MUI icons (import them).
- [ ] Extend `test_seed_modules` to assert the three new modules register under Food. Run green. Commit checkpoint.

## Task 6: Food Dashboard page (KPIs + charts)
**Files:** create `src/pages/food/FoodDashboard.js` + `.test.js`; small `src/pages/food/_StatTile.js` helper.
**Interfaces:** consumes `GET food/admin/dashboard/`. KPI tiles; revenue-trend `AreaChart` + status `PieChart` (recharts); recent-orders table; pending-approvals count with link.
- [ ] Test (inline `useApi` mock returning dashboard payload): renders a KPI value and a recent order. Run red→green.
- [ ] Implement modern layout (MUI Grid of cards, recharts). Commit checkpoint.

## Task 7: Food Orders management page
**Files:** create `src/pages/food/ManageFoodOrders.js` + `.test.js`.
**Interfaces:** `GET food/admin/orders/?status=`, `GET food/admin/orders/<id>/`, `PATCH food/admin/orders/<id>/status/`. Status filter tabs; table (code, restaurant, customer, total, status, time); detail drawer with items + status stepper + advance/cancel buttons (next legal statuses from `allowed_transitions`).
- [ ] Test: lists an order; clicking advances status (closure-flag inline mock like `VendorOrders.test`). Red→green.
- [ ] Implement. Commit checkpoint.

## Task 8: Restaurants page — onboarding + detail
**Files:** modify `src/pages/food/ManageRestaurants.js`; create `src/pages/food/RestaurantDetailAdmin.js` + a test for the create form.
**Interfaces:** `POST food/admin/restaurants/` (with `owner`), `GET/PATCH food/admin/restaurants/<id>/`, zones/hours endpoints (Task 3), `food/zones/` for the zone picker.
- [ ] "Add restaurant" modal: profile fields + "create owner login" (username/email/phone/password) + commission/fee/min-order. Posts and refreshes.
- [ ] Detail page: edit profile, weekly hours editor, zone assignment (checkbox list + per-zone fee), link to Menu Management for this restaurant.
- [ ] Test: create form posts owner payload (inline mock asserts body). Red→green. Commit checkpoint.

## Task 9: Admin Menu Manager page
**Files:** create `src/pages/food/FoodMenuManager.js` + `.test.js`; reuse an item/option editor component.
**Interfaces:** `food/admin/restaurants/` (restaurant selector), `food/admin/categories|items|option-groups|options/?restaurant=<id>`.
- [ ] Restaurant `<Select>` → loads that restaurant's categories/items; add/edit/delete category; add/edit item (name, price, image URL, availability, veg, spice); manage option groups + options per item (dialog).
- [ ] Test: selecting a restaurant lists its items; adding a category posts with `restaurant`. Red→green. Commit checkpoint.

## Task 10: Final verification
- [ ] Backend: `manage.py test food catalog` all green.
- [ ] Frontend: `react-scripts test src/pages/food src/food src/vendor` all green; `react-scripts build` compiles.
- [ ] Manual smoke: log in as admin → Food Dashboard shows KPIs → create a restaurant with owner → build its menu (category→item→option) → it appears in the customer `/food` app → place a COD order → it shows in Food Orders → advance to Delivered.
- [ ] Hand human the commit/pull/merge commands. Do NOT push/merge.

## Spec coverage
Dashboard+charts → T1,T6. Order mgmt → T4,T7. Menu creation (full) → T2,T9. Restaurant onboarding + owner login → T3,T8. Delivery controls (zones+fees+status) → T3,T7,T8 + existing ManageZones. Module registration/deploy → T5 (+build.sh already seeds). Rider ecosystem → separate future roadmap doc.
