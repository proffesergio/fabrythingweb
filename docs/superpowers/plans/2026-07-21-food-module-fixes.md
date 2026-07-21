# Food Module Fixes Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix menu-item creation failing with an opaque "Validation Error", give riders a working dashboard with assigned-order detail and live map guidance, and add image upload plus menu copying to admin Menu Management.

**Architecture:** Three independent tracks against the existing Django/DRF + CRA codebase. Track 1 makes the response envelope's hidden field errors reachable in the browser, then fixes the real serializer rejection. Track 2 fixes a role-blind login redirect, adds rider presence via a heartbeat, auto-dispatches to the nearest present rider, and rebuilds the rider screen from four focused components. Track 3 adds a transactional menu-copy endpoint and wires image upload to the existing `/api/uploads/` view.

**Tech Stack:** Django 5, DRF, SimpleJWT, Postgres (Neon) / SQLite for tests; React 18, MUI 5, Redux Toolkit, Leaflet 1.9, axios, jwt-decode; jest + React Testing Library.

## Global Constraints

- Backend commands run from `backend/EcommerceInventory/`. Tests: `python manage.py test food`. Settings default to `config.settings.dev`.
- Frontend commands run from `frontend/ecommerce_inventory/`. Tests: `npm test -- --watchAll=false`.
- **Every authenticated DRF view must declare `authentication_classes = [JWTAuthentication]`.** There is no `DEFAULT_AUTHENTICATION_CLASSES`; omitting it makes `request.user` anonymous despite a valid bearer token.
- **All responses use the envelope** `{"data": ..., "message": ...}` via `core.helpers.renderResponse`.
- Roles are strings on `accounts.User.role`: `Super Admin`, `Admin`, `Supplier`, `Customer`, `Staff`, `Restaurant`, `Rider`. Food permission classes live in `food/permissions.py`.
- `FoodItem.category_id` is a ForeignKey literally named `category_id`. `FoodItem.image` is a `URLField`, not an `ImageField`.
- Bengali (Bangla) labels accompany English on rider-facing and customer-facing UI, matching the existing bilingual pattern.
- Commit after every task. Do not use `--no-verify`.

---

## File Structure

**Track 1 — menu validation**
- Modify `frontend/ecommerce_inventory/src/hooks/APIHandler.js` — opt-in return of the error response.
- Modify `backend/EcommerceInventory/food/serializers_admin_menu.py` — blank-to-null coercion and tag/day validation.
- Modify `frontend/ecommerce_inventory/src/pages/food/FoodMenuManager.js` — inline field errors, send `null` rather than dropping keys.
- Modify `backend/EcommerceInventory/food/tests/test_admin_menu.py`.

**Track 2 — rider**
- Create `frontend/ecommerce_inventory/src/utils/roleHome.js` — single source of truth for post-login landing per role.
- Modify `frontend/ecommerce_inventory/src/pages/Auth.js`, `src/pages/Home.js`.
- Modify `backend/EcommerceInventory/food/models.py` + new migration — rider location/presence fields.
- Create `backend/EcommerceInventory/food/services_dispatch.py` — presence rules and nearest-rider selection.
- Create `backend/EcommerceInventory/food/serializers_rider.py` — rider-facing order payload.
- Modify `backend/EcommerceInventory/food/views_food_ext.py`, `food/urls.py`, `food/views_orders.py`.
- Create `frontend/ecommerce_inventory/src/rider/RiderHeader.js`, `DeliveryCard.js`, `DeliveryMap.js`, `EarningsPanel.js`, `useRiderHeartbeat.js`, `geo.js`.
- Rewrite `frontend/ecommerce_inventory/src/rider/RiderDashboard.js` as composition of the above.
- Create `backend/EcommerceInventory/food/tests/test_rider_dispatch.py`, `test_rider_dashboard_api.py`.

**Track 3 — menu management**
- Create `backend/EcommerceInventory/food/services_menu_copy.py`, `views_menu_copy.py`.
- Create `backend/EcommerceInventory/food/tests/test_menu_copy.py`.
- Create `frontend/ecommerce_inventory/src/pages/food/CopyMenuDialog.js`.
- Modify `frontend/ecommerce_inventory/src/pages/food/FoodMenuManager.js`.

Tracks are independent. Track 1 must precede Track 3's UI work only because both edit `FoodMenuManager.js`.

---

# TRACK 1 — Menu item validation

### Task 1: Let callers read the error body

**Files:**
- Modify: `frontend/ecommerce_inventory/src/hooks/APIHandler.js`
- Test: `frontend/ecommerce_inventory/src/hooks/APIHandler.test.js` (create)

**Interfaces:**
- Consumes: nothing.
- Produces: `callApi({..., rawError: true})` returns the axios *error response object* (`{status, data}`) instead of `null` when the request fails with an HTTP status. Without the flag, behaviour is unchanged (`null`). Later tasks call this to read `res.data.data`.

**Why:** `callApi` currently swallows failures — axios throws, the `catch` toasts `err.response.data.message` (the constant `"Validation error"`), and the function returns `null`. No caller can ever see which field failed. This is the root of the reported symptom.

- [ ] **Step 1: Write the failing test**

Create `frontend/ecommerce_inventory/src/hooks/APIHandler.test.js`:

```javascript
import { renderHook } from "@testing-library/react";
import axios from "axios";
import useApi from "./APIHandler";

jest.mock("axios");
jest.mock("react-toastify", () => ({ toast: { error: jest.fn(), success: jest.fn() } }));

describe("useApi callApi", () => {
    afterEach(() => jest.clearAllMocks());

    it("returns null on an HTTP error by default", async () => {
        axios.request.mockRejectedValue({
            message: "Request failed",
            response: { status: 400, data: { message: "Validation error", data: { price: ["Required."] } } },
        });
        const { result } = renderHook(() => useApi());
        const res = await result.current.callApi({ url: "food/admin/items/", method: "POST" });
        expect(res).toBeNull();
    });

    it("returns the error response when rawError is set", async () => {
        axios.request.mockRejectedValue({
            message: "Request failed",
            response: { status: 400, data: { message: "Validation error", data: { price: ["Required."] } } },
        });
        const { result } = renderHook(() => useApi());
        const res = await result.current.callApi({ url: "food/admin/items/", method: "POST", rawError: true });
        expect(res.status).toBe(400);
        expect(res.data.data).toEqual({ price: ["Required."] });
    });

    it("returns null with rawError when there is no response at all", async () => {
        axios.request.mockRejectedValue({ message: "Network Error" });
        const { result } = renderHook(() => useApi());
        const res = await result.current.callApi({ url: "food/admin/items/", rawError: true });
        expect(res).toBeNull();
    });
});
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd frontend/ecommerce_inventory && npm test -- --watchAll=false APIHandler.test.js
```

Expected: FAIL — the `rawError` test gets `null` instead of the error response.

- [ ] **Step 3: Implement**

In `frontend/ecommerce_inventory/src/hooks/APIHandler.js`, change the signature and the `catch` block:

```javascript
    // Pass silent:true to suppress the error toast (for expected errors the caller
    // handles itself, e.g. a 404 that just means "ask the guest for their phone").
    // Pass rawError:true to receive the error response ({status,data}) instead of
    // null, so the caller can read DRF field errors out of the {data,message}
    // envelope. Default stays null for the ~120 existing call sites.
    const callApi=async ({url,method="GET",body={},header={},params={},silent=false,rawError=false})=>{
```

and at the end of the `catch` block, after `setError(err)`:

```javascript
            setError(err)
            if(rawError && err.response){
                setLoading(false);
                return err.response;
            }
```

- [ ] **Step 4: Run test to verify it passes**

```bash
cd frontend/ecommerce_inventory && npm test -- --watchAll=false APIHandler.test.js
```

Expected: PASS, 3 tests.

- [ ] **Step 5: Commit**

```bash
git add frontend/ecommerce_inventory/src/hooks/APIHandler.js frontend/ecommerce_inventory/src/hooks/APIHandler.test.js
git commit -m "feat(api): opt-in rawError so callers can read DRF field errors"
```

---

### Task 2: Find and fix the real item-validation rejection

**Files:**
- Modify: `backend/EcommerceInventory/food/tests/test_admin_menu.py`
- Modify: `backend/EcommerceInventory/food/serializers_admin_menu.py`

**Interfaces:**
- Consumes: nothing.
- Produces: `POST/PATCH /api/food/admin/items/` accepts `""` and `null` for `discount_price`, `prep_minutes`, `available_from`, `available_to` (both meaning "unset"), validates `tags` against `AdminItemSerializer.ALLOWED_TAGS` and `available_days` against ints 0–6.

- [ ] **Step 1: Write the characterisation tests**

Append to `backend/EcommerceInventory/food/tests/test_admin_menu.py` inside `class AdminMenuTests`:

```python
    def _item_payload(self, **over):
        base = {"restaurant": self.r.id, "category_id": self.cat.id,
                "name": "Beef Tehari", "price": "180.00"}
        base.update(over)
        return base

    def test_create_item_with_tags_schedule_and_spice(self):
        """The full 'additional info' payload the admin UI sends must be accepted."""
        auth(self.client, self.admin)
        res = self.client.post("/api/food/admin/items/", self._item_payload(
            tags=["spicy", "bestseller"], spice_level="Hot",
            available_from="08:00", available_to="11:00", available_days=[0, 1, 2],
            is_featured=True, image="https://cdn.example.com/tehari.jpg",
        ), format="json")
        self.assertEqual(res.status_code, 201, res.content)
        item = FoodItem.objects.get(name="Beef Tehari")
        self.assertEqual(item.tags, ["spicy", "bestseller"])
        self.assertEqual(item.available_days, [0, 1, 2])

    def test_blank_optional_fields_are_treated_as_unset(self):
        """The dialog sends "" for untouched optional fields; that must mean null."""
        auth(self.client, self.admin)
        res = self.client.post("/api/food/admin/items/", self._item_payload(
            discount_price="", prep_minutes="", available_from="", available_to="",
        ), format="json")
        self.assertEqual(res.status_code, 201, res.content)
        item = FoodItem.objects.get(name="Beef Tehari")
        self.assertIsNone(item.discount_price)
        self.assertIsNone(item.prep_minutes)
        self.assertIsNone(item.available_from)

    def test_optional_fields_can_be_cleared_on_edit(self):
        auth(self.client, self.admin)
        item = FoodItem.objects.create(restaurant=self.r, category_id=self.cat, name="X", slug="x",
                                       price=Decimal("100"), discount_price=Decimal("80"))
        res = self.client.patch(f"/api/food/admin/items/{item.id}/",
                                {"discount_price": None}, format="json")
        self.assertEqual(res.status_code, 200, res.content)
        item.refresh_from_db()
        self.assertIsNone(item.discount_price)

    def test_bad_image_reports_the_image_field(self):
        """A non-URL image must fail on 'image' specifically, so the UI can point at it."""
        auth(self.client, self.admin)
        res = self.client.post("/api/food/admin/items/",
                               self._item_payload(image="tehari.jpg"), format="json")
        self.assertEqual(res.status_code, 400)
        self.assertIn("image", res.json()["data"])

    def test_unknown_tag_is_rejected_readably(self):
        auth(self.client, self.admin)
        res = self.client.post("/api/food/admin/items/",
                               self._item_payload(tags=["gluten-free"]), format="json")
        self.assertEqual(res.status_code, 400)
        self.assertIn("tags", res.json()["data"])

    def test_available_day_out_of_range_is_rejected(self):
        auth(self.client, self.admin)
        res = self.client.post("/api/food/admin/items/",
                               self._item_payload(available_days=[9]), format="json")
        self.assertEqual(res.status_code, 400)
        self.assertIn("available_days", res.json()["data"])
```

- [ ] **Step 2: Run the tests to see which actually fail**

```bash
cd backend/EcommerceInventory && python manage.py test food.tests.test_admin_menu -v 2
```

Expected: `test_create_item_with_tags_schedule_and_spice` and `test_bad_image_reports_the_image_field` may already pass; `test_blank_optional_fields_are_treated_as_unset`, `test_optional_fields_can_be_cleared_on_edit`, `test_unknown_tag_is_rejected_readably` and `test_available_day_out_of_range_is_rejected` must FAIL.

**Record the actual failure output in the commit message** — this is the diagnosis the whole track was blocked on. If `test_create_item_with_tags_schedule_and_spice` fails, that failure is the reported bug and its message tells you the offending field.

- [ ] **Step 3: Implement the serializer hardening**

Replace `AdminItemSerializer` in `backend/EcommerceInventory/food/serializers_admin_menu.py`:

```python
class AdminItemSerializer(serializers.ModelSerializer):
    # Slug is auto-generated server-side from name (unique per restaurant).
    slug = serializers.SlugField(read_only=True)

    # Curated tag keys, mirrored by TAG_OPTIONS in FoodMenuManager.js.
    ALLOWED_TAGS = ["spicy", "new", "popular", "bestseller", "veg"]
    # The admin dialog sends "" for optional fields the user never touched.
    # DRF rejects "" for Decimal/Integer/Time, so normalise it to None (unset)
    # before validation. None is also how the UI clears an existing value.
    BLANKABLE = ["discount_price", "prep_minutes", "available_from", "available_to"]

    class Meta:
        model = FoodItem
        fields = ["id", "restaurant", "category_id", "name", "name_bn", "slug", "description",
                  "description_bn", "image", "price", "discount_price", "prep_minutes",
                  "is_available", "is_veg", "is_featured", "tags", "available_from", "available_to",
                  "available_days", "spice_level", "display_order"]

    def to_internal_value(self, data):
        if hasattr(data, "dict"):
            data = data.dict()
        else:
            data = dict(data)
        for field in self.BLANKABLE:
            if data.get(field) == "":
                data[field] = None
        return super().to_internal_value(data)

    def validate_tags(self, value):
        if not isinstance(value, list):
            raise serializers.ValidationError("Tags must be a list.")
        unknown = [t for t in value if t not in self.ALLOWED_TAGS]
        if unknown:
            raise serializers.ValidationError(
                f"Unknown tag(s): {', '.join(map(str, unknown))}. "
                f"Allowed: {', '.join(self.ALLOWED_TAGS)}."
            )
        return value

    def validate_available_days(self, value):
        if not isinstance(value, list):
            raise serializers.ValidationError("Available days must be a list.")
        days = []
        for raw in value:
            try:
                day = int(raw)
            except (TypeError, ValueError):
                raise serializers.ValidationError(f"'{raw}' is not a weekday number.")
            if not 0 <= day <= 6:
                raise serializers.ValidationError("Weekdays must be between 0 (Mon) and 6 (Sun).")
            days.append(day)
        return days
```

Also make the nullable model fields explicitly accept `null` — add to `Meta`:

```python
        extra_kwargs = {
            "discount_price": {"allow_null": True, "required": False},
            "prep_minutes": {"allow_null": True, "required": False},
            "available_from": {"allow_null": True, "required": False},
            "available_to": {"allow_null": True, "required": False},
        }
```

- [ ] **Step 4: Run the tests to verify they pass**

```bash
cd backend/EcommerceInventory && python manage.py test food.tests.test_admin_menu -v 2
```

Expected: PASS, all tests in the module.

- [ ] **Step 5: Run the full food suite for regressions**

```bash
cd backend/EcommerceInventory && python manage.py test food
```

Expected: PASS. `AdminItemSerializer` is also reachable from admin item PATCH used by the quick toggles — confirm `test_admin_api.py` still passes.

- [ ] **Step 6: Commit**

```bash
git add backend/EcommerceInventory/food/serializers_admin_menu.py backend/EcommerceInventory/food/tests/test_admin_menu.py
git commit -m "fix(food): accept blank optionals and validate tags/days on admin item write"
```

---

### Task 3: Show the failing field in the item dialog

**Files:**
- Modify: `frontend/ecommerce_inventory/src/pages/food/FoodMenuManager.js:77-92` (`saveItem`), `:183-235` (item dialog JSX)
- Test: `frontend/ecommerce_inventory/src/pages/food/FoodMenuManager.test.js`

**Interfaces:**
- Consumes: `callApi({rawError: true})` from Task 1; the `{field: [messages]}` shape returned in `data` by Task 2.
- Produces: nothing consumed by later tasks.

- [ ] **Step 1: Make the existing mock controllable per test**

`FoodMenuManager.test.js` currently mocks `useApi` with a hard-coded inline
factory, so no test can vary the response. Tasks 3, 11 and 12 all need to. Replace
the mock block at the top of the file (lines 3–23, from `jest.mock(` through its
closing `}));`) with a `jest.fn()` the tests can reprogram, keeping the existing
default behaviour so the current test still passes:

```javascript
const mockCallApi = jest.fn();
jest.mock('../../hooks/APIHandler', () => () => ({
  loading: false,
  error: '',
  callApi: (...args) => mockCallApi(...args),
}));

const defaultApi = async ({ url, method, body }) => {
  if (method === 'POST' && url.includes('categories')) {
    global.__catPost = body;
    return { status: 201, data: { data: { id: 7, name: body.name, restaurant: body.restaurant } } };
  }
  if (url.startsWith('food/admin/restaurants')) {
    return { status: 200, data: { data: [{ id: 3, name: 'Star Kitchen' }] } };
  }
  if (url.startsWith('food/admin/categories')) {
    return { status: 200, data: { data: [{ id: 1, name: 'Main', restaurant: 3 }] } };
  }
  if (url.startsWith('food/admin/items')) {
    return { status: 200, data: { data: [{ id: 10, name: 'Biriyani', price: '120.00', category_id: 1 }] } };
  }
  return { status: 200, data: { data: [] } };
};

beforeEach(() => mockCallApi.mockImplementation(defaultApi));
afterEach(() => jest.clearAllMocks());
```

Run the file now to confirm the existing test still passes before adding anything:

```bash
cd frontend/ecommerce_inventory && npm test -- --watchAll=false FoodMenuManager.test.js
```

Expected: PASS, 1 test.

- [ ] **Step 2: Write the failing test**

Append to `frontend/ecommerce_inventory/src/pages/food/FoodMenuManager.test.js`:

```javascript
it("shows the failing field inline when the backend rejects the item", async () => {
    // callApi resolves with a 400 envelope carrying per-field errors.
    mockCallApi.mockImplementation(async (args) => {
        if (args.url === "food/admin/items/" && args.method === "POST") {
            return {
                status: 400,
                data: { message: "Validation error", data: { image: ["Enter a valid URL."] } },
            };
        }
        return defaultApi(args);
    });

    render(<FoodMenuManager />);
    // open the add-item dialog, fill the minimum, submit
    fireEvent.click(await screen.findByRole("button", { name: /add item/i }));
    fireEvent.change(screen.getByLabelText(/Name \(English\)/i), { target: { value: "Tehari" } });
    fireEvent.change(screen.getByLabelText(/Price/i), { target: { value: "180" } });
    fireEvent.click(screen.getByRole("button", { name: /^save$/i }));

    // the dialog stays open and names the offending field
    expect(await screen.findByText(/Enter a valid URL/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /^save$/i })).toBeInTheDocument();
});
```

- [ ] **Step 3: Run test to verify it fails**

```bash
cd frontend/ecommerce_inventory && npm test -- --watchAll=false FoodMenuManager.test.js
```

Expected: FAIL — "Enter a valid URL" is never rendered.

- [ ] **Step 4: Implement**

In `FoodMenuManager.js`, add error state next to the other `useState` declarations:

```javascript
    const [itemErrors, setItemErrors] = useState({});
```

Replace `saveItem` (currently lines 77–92) with:

```javascript
    const saveItem = async () => {
        const body = { ...itemDialog, restaurant: Number(restaurant) };
        // Optional numeric/time fields: send null (not "") so the backend treats them
        // as unset — and so clearing a previously-set value actually persists.
        // AdminItemSerializer normalises "" to null too, but being explicit here
        // means an edit that empties a field reaches the server as an intent.
        ["discount_price", "prep_minutes", "available_from", "available_to"].forEach((k) => {
            if (body[k] === "" || body[k] == null) body[k] = null;
        });
        body.available_days = (itemDialog.available_days || []).map(Number);
        const isEdit = !!itemDialog.id;
        setItemErrors({});
        const res = await callApi({
            url: isEdit ? `food/admin/items/${itemDialog.id}/` : "food/admin/items/",
            method: isEdit ? "PATCH" : "POST", body, rawError: true, silent: true,
        });
        if (res?.status === 200 || res?.status === 201) {
            toast.success(isEdit ? "Item saved" : "Item added");
            setItemDialog(null); setItemErrors({}); loadMenu(restaurant);
            return;
        }
        // 400 → the envelope's data is {field: [messages]}. Surface it in place;
        // the generic "Validation error" message alone tells the admin nothing.
        const fields = (res?.status === 400 && res?.data?.data) || {};
        if (fields && typeof fields === "object" && !Array.isArray(fields)) {
            setItemErrors(fields);
            const summary = Object.entries(fields)
                .map(([f, msgs]) => `${f}: ${[].concat(msgs).join(" ")}`).join(" · ");
            toast.error(summary || res?.data?.message || "Could not save item");
        } else {
            toast.error(res?.data?.message || "Could not save item");
        }
    };
```

Add a helper just above the `return (` statement:

```javascript
    // MUI props for a field the backend rejected.
    const errProps = (field, fallbackHelper = "") => {
        const msgs = itemErrors[field];
        return msgs
            ? { error: true, helperText: [].concat(msgs).join(" ") }
            : (fallbackHelper ? { helperText: fallbackHelper } : {});
    };
```

Clear errors when the dialog closes — update both `onClose` and the Cancel button to call `setItemErrors({})` alongside `setItemDialog(null)`:

```javascript
            <Dialog open={!!itemDialog} onClose={() => { setItemDialog(null); setItemErrors({}); }} maxWidth="sm" fullWidth>
```

```javascript
                <DialogActions><Button onClick={() => { setItemDialog(null); setItemErrors({}); }}>Cancel</Button><Button variant="contained" onClick={saveItem}>Save</Button></DialogActions>
```

Spread `errProps` onto each field. The full set of replacements inside the dialog `Grid`:

```javascript
                            <Grid item xs={12} sm={6}><TextField label="Name (English)" fullWidth value={itemDialog.name} onChange={(e) => setItemDialog({ ...itemDialog, name: e.target.value })} {...errProps("name")} /></Grid>
                            <Grid item xs={12} sm={6}><TextField label="নাম (বাংলা)" fullWidth value={itemDialog.name_bn || ""} onChange={(e) => setItemDialog({ ...itemDialog, name_bn: e.target.value })} inputProps={{ lang: "bn" }} {...errProps("name_bn")} /></Grid>
                            <Grid item xs={12} sm={4}><TextField label="Price ৳" type="number" fullWidth value={itemDialog.price} onChange={(e) => setItemDialog({ ...itemDialog, price: e.target.value })} {...errProps("price")} /></Grid>
                            <Grid item xs={12} sm={4}><TextField label="Discount price ৳" type="number" fullWidth value={itemDialog.discount_price || ""} onChange={(e) => setItemDialog({ ...itemDialog, discount_price: e.target.value })} {...errProps("discount_price", "Optional")} /></Grid>
                            <Grid item xs={12} sm={4}><TextField label="Prep minutes" type="number" fullWidth value={itemDialog.prep_minutes || ""} onChange={(e) => setItemDialog({ ...itemDialog, prep_minutes: e.target.value })} {...errProps("prep_minutes")} /></Grid>
```

and for the image, tags and schedule fields:

```javascript
                            <Grid item xs={12}><TextField label="Image URL" fullWidth value={itemDialog.image} onChange={(e) => setItemDialog({ ...itemDialog, image: e.target.value })} {...errProps("image", "Paste a photo URL — dishes with photos look best")} /></Grid>
```

```javascript
                            <Grid item xs={12} sm={6}><TextField label="Available from" type="time" fullWidth InputLabelProps={{ shrink: true }} value={itemDialog.available_from || ""} onChange={(e) => setItemDialog({ ...itemDialog, available_from: e.target.value })} {...errProps("available_from", "Optional schedule")} /></Grid>
                            <Grid item xs={12} sm={6}><TextField label="Available to" type="time" fullWidth InputLabelProps={{ shrink: true }} value={itemDialog.available_to || ""} onChange={(e) => setItemDialog({ ...itemDialog, available_to: e.target.value })} {...errProps("available_to")} /></Grid>
```

For `tags` and `available_days`, which render as Chip rows rather than TextFields, add an error line under each heading. Under the Tags heading:

```javascript
                                {itemErrors.tags && <Typography variant="caption" color="error" display="block">{[].concat(itemErrors.tags).join(" ")}</Typography>}
```

Under the Available-days heading:

```javascript
                                {itemErrors.available_days && <Typography variant="caption" color="error" display="block">{[].concat(itemErrors.available_days).join(" ")}</Typography>}
```

Finally, add a top-of-dialog alert for errors with no matching input. Import `Alert` from `@mui/material` and place this as the first child of the `Grid container`:

```javascript
                            {(itemErrors.non_field_errors || itemErrors.detail) && (
                                <Grid item xs={12}>
                                    <Alert severity="error">{[].concat(itemErrors.non_field_errors || itemErrors.detail).join(" ")}</Alert>
                                </Grid>
                            )}
```

- [ ] **Step 5: Run test to verify it passes**

```bash
cd frontend/ecommerce_inventory && npm test -- --watchAll=false FoodMenuManager.test.js
```

Expected: PASS, including the pre-existing test in that file.

- [ ] **Step 6: Commit**

```bash
git add frontend/ecommerce_inventory/src/pages/food/FoodMenuManager.js frontend/ecommerce_inventory/src/pages/food/FoodMenuManager.test.js
git commit -m "fix(food): surface per-field item errors in Menu Management dialog"
```

---

# TRACK 2 — Rider

### Task 4: Send each role to its own home after login

**Files:**
- Create: `frontend/ecommerce_inventory/src/utils/roleHome.js`
- Create: `frontend/ecommerce_inventory/src/utils/roleHome.test.js`
- Modify: `frontend/ecommerce_inventory/src/pages/Auth.js:68-98`

**Interfaces:**
- Consumes: `getUser()` from `src/utils/Helper.js`, which returns the decoded JWT including the `role` claim (set server-side in `AuthController.LoginAPIView`).
- Produces: `roleHome(role) -> string` — the path a freshly authenticated user of that role should land on. Used by `doLogin` and by the `Home.js` guard, both in this task.

**Why:** `doLogin` navigates every role to `/admin/home`. A `Rider` lands on an admin dashboard that renders nothing for them — the reported "blank dashboard".

- [ ] **Step 1: Write the failing test**

Create `frontend/ecommerce_inventory/src/utils/roleHome.test.js`:

```javascript
import roleHome from "./roleHome";

describe("roleHome", () => {
    it("sends riders to the rider dashboard", () => {
        expect(roleHome("Rider")).toBe("/rider");
    });
    it("sends restaurant owners to the vendor panel", () => {
        expect(roleHome("Restaurant")).toBe("/vendor/orders");
    });
    it("sends admins to the admin home", () => {
        expect(roleHome("Admin")).toBe("/admin/home");
        expect(roleHome("Super Admin")).toBe("/admin/home");
    });
    it("falls back to admin home for unknown or missing roles", () => {
        expect(roleHome(undefined)).toBe("/admin/home");
        expect(roleHome("Wizard")).toBe("/admin/home");
    });
});
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd frontend/ecommerce_inventory && npm test -- --watchAll=false roleHome.test.js
```

Expected: FAIL — `Cannot find module './roleHome'`.

- [ ] **Step 3: Implement**

Create `frontend/ecommerce_inventory/src/utils/roleHome.js`:

```javascript
// Where a freshly authenticated user of each role belongs. Roles are plain
// strings on accounts.User.role and travel in the JWT's `role` claim.
//
// Without this, Auth.js sent every role to /admin/home — which renders no
// modules for a Rider, so riders saw an empty dashboard and never reached
// /rider at all.
const ROLE_HOME = {
    Rider: "/rider",
    Restaurant: "/vendor/orders",
};

const roleHome = (role) => ROLE_HOME[role] || "/admin/home";

export default roleHome;
```

- [ ] **Step 4: Run test to verify it passes**

```bash
cd frontend/ecommerce_inventory && npm test -- --watchAll=false roleHome.test.js
```

Expected: PASS, 4 tests.

- [ ] **Step 5: Wire it into login**

In `frontend/ecommerce_inventory/src/pages/Auth.js`, add imports at the top of the file:

```javascript
import roleHome from "../utils/roleHome";
import { getUser } from "../utils/Helper";
```

In `doLogin`, replace `navigate("/admin/home");` (line 91) with:

```javascript
          // Role lives in the JWT we just stored; send each role to its own home.
          navigate(roleHome(getUser()?.role));
```

Leave `doSignup`'s `/admin/home` unchanged — signup always creates an Admin.

- [ ] **Step 6: Bounce non-admins off the admin home**

A rider with a stale bookmark, or one already logged in when this ships, still
lands on `/admin/home`. `src/pages/Home.js` already imports `getUser` and
`useNavigate`, so add a guard as the first effect in the `Home` component, above
the existing dashboard fetch:

```javascript
    // Riders and vendors have their own home; the admin dashboard renders no
    // modules for them, which is what made the rider screen look blank.
    useEffect(() => {
        const home = roleHome(user?.role);
        if (home !== "/admin/home") navigate(home, { replace: true });
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, []);
```

and add the import:

```javascript
import roleHome from '../utils/roleHome';
```

- [ ] **Step 7: Verify the whole frontend suite still passes**

```bash
cd frontend/ecommerce_inventory && npm test -- --watchAll=false
```

Expected: PASS.

- [ ] **Step 8: Commit**

```bash
git add frontend/ecommerce_inventory/src/utils/roleHome.js frontend/ecommerce_inventory/src/utils/roleHome.test.js frontend/ecommerce_inventory/src/pages/Auth.js frontend/ecommerce_inventory/src/pages/Home.js
git commit -m "fix(auth): route riders and vendors to their own home after login"
```

---

### Task 5: Rider presence — location fields and heartbeat

**Files:**
- Modify: `backend/EcommerceInventory/food/models.py:353-372` (`Rider`)
- Create: `backend/EcommerceInventory/food/migrations/00XX_rider_presence.py` (generated)
- Modify: `backend/EcommerceInventory/food/views_food_ext.py`, `food/urls.py`, `food/serializers_ext.py`
- Create: `backend/EcommerceInventory/food/tests/test_rider_dashboard_api.py`

**Interfaces:**
- Consumes: `IsRider` from `food/permissions.py`.
- Produces:
  - `Rider.current_lat`, `Rider.current_lng` (`DecimalField(max_digits=9, decimal_places=6, null=True)`), `Rider.last_seen_at` (`DateTimeField(null=True)`).
  - `Rider.PRESENCE_WINDOW_MINUTES = 3`.
  - `POST /api/food/rider/heartbeat/` — body `{"lat": float, "lng": float}`, both optional; updates `last_seen_at` always and coordinates when supplied. Returns `{"data": {"last_seen_at": iso8601}, "message": "Heartbeat"}`.
  - `RiderSerializer` gains `current_lat`, `current_lng`, `last_seen_at` (read-only).

- [ ] **Step 1: Write the failing tests**

Create `backend/EcommerceInventory/food/tests/test_rider_dashboard_api.py`:

```python
from django.test import TestCase
from django.utils import timezone
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from food.models import Rider

User = get_user_model()


def auth(c, u):
    c.credentials(HTTP_AUTHORIZATION=f"Bearer {RefreshToken.for_user(u).access_token}")


class RiderHeartbeatTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create(username="rdr", email="rdr@x.com", role="Rider")
        self.rider = Rider.objects.create(user=self.user, name="Rakib")

    def test_heartbeat_records_position_and_time(self):
        auth(self.client, self.user)
        res = self.client.post("/api/food/rider/heartbeat/",
                               {"lat": 23.7104, "lng": 90.9280}, format="json")
        self.assertEqual(res.status_code, 200, res.content)
        self.rider.refresh_from_db()
        self.assertAlmostEqual(float(self.rider.current_lat), 23.7104, places=4)
        self.assertAlmostEqual(float(self.rider.current_lng), 90.9280, places=4)
        self.assertIsNotNone(self.rider.last_seen_at)

    def test_heartbeat_without_coordinates_still_refreshes_presence(self):
        auth(self.client, self.user)
        res = self.client.post("/api/food/rider/heartbeat/", {}, format="json")
        self.assertEqual(res.status_code, 200, res.content)
        self.rider.refresh_from_db()
        self.assertIsNotNone(self.rider.last_seen_at)
        self.assertIsNone(self.rider.current_lat)

    def test_non_rider_is_blocked(self):
        cust = User.objects.create(username="c", email="c@x.com", role="Customer")
        auth(self.client, cust)
        res = self.client.post("/api/food/rider/heartbeat/", {"lat": 1, "lng": 1}, format="json")
        self.assertEqual(res.status_code, 403)

    def test_rider_me_exposes_presence(self):
        self.rider.last_seen_at = timezone.now()
        self.rider.current_lat, self.rider.current_lng = 23.7, 90.9
        self.rider.save()
        auth(self.client, self.user)
        res = self.client.get("/api/food/rider/me/")
        self.assertEqual(res.status_code, 200, res.content)
        self.assertIn("last_seen_at", res.json()["data"])
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd backend/EcommerceInventory && python manage.py test food.tests.test_rider_dashboard_api -v 2
```

Expected: FAIL — 404 on `/api/food/rider/heartbeat/`, and `Rider` has no `current_lat`.

- [ ] **Step 3: Add the model fields**

In `backend/EcommerceInventory/food/models.py`, inside `class Rider`, after `total_deliveries`:

```python
    # Presence. The rider dashboard is a web page, not a native app, so "online"
    # is derived rather than declared: the page posts a heartbeat every ~20s
    # while the rider has the Online switch on. A rider is dispatchable only if
    # is_available AND last_seen_at is inside PRESENCE_WINDOW_MINUTES AND a
    # position is known — closing the tab drops them out with no explicit action.
    PRESENCE_WINDOW_MINUTES = 3

    current_lat = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    current_lng = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    last_seen_at = models.DateTimeField(null=True, blank=True)
```

- [ ] **Step 4: Generate and apply the migration**

```bash
cd backend/EcommerceInventory && python manage.py makemigrations food --name rider_presence && python manage.py migrate
```

Expected: a new migration adding three fields to `rider`.

- [ ] **Step 5: Expose the fields on the serializer**

In `backend/EcommerceInventory/food/serializers_ext.py`, add `"current_lat", "current_lng", "last_seen_at"` to `RiderSerializer.Meta.fields` and add to `Meta`:

```python
        read_only_fields = ["rider_code", "total_deliveries", "current_lat", "current_lng", "last_seen_at"]
```

- [ ] **Step 6: Add the heartbeat view**

In `backend/EcommerceInventory/food/views_food_ext.py`, after `RiderAvailabilityView`:

```python
class RiderHeartbeatView(APIView):
    """Presence + position ping from the rider dashboard (~every 20s while Online).

    Coordinates are optional: a browser that denies geolocation should still be
    able to keep the rider marked present. Only the current position is stored —
    no location history is kept.
    """
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, IsRider]

    def post(self, request):
        rider = request.user.rider
        fields = ["last_seen_at", "updated_at"]
        rider.last_seen_at = timezone.now()
        lat, lng = request.data.get("lat"), request.data.get("lng")
        if lat is not None and lng is not None:
            try:
                rider.current_lat = Decimal(str(lat))
                rider.current_lng = Decimal(str(lng))
            except (InvalidOperation, TypeError):
                return renderResponse(data={"lat": ["Invalid coordinate."]},
                                      message="Validation error", status=400)
            fields += ["current_lat", "current_lng"]
        rider.save(update_fields=fields)
        return renderResponse(data={"last_seen_at": rider.last_seen_at.isoformat()},
                              message="Heartbeat")
```

Ensure these imports exist at the top of the file:

```python
from decimal import Decimal, InvalidOperation
from django.utils import timezone
```

- [ ] **Step 7: Register the route**

In `backend/EcommerceInventory/food/urls.py`, add `RiderHeartbeatView` to the `views_food_ext` import list, and add the path next to the other rider routes:

```python
    path("rider/heartbeat/", RiderHeartbeatView.as_view(), name="food_rider_heartbeat"),
```

- [ ] **Step 8: Run tests to verify they pass**

```bash
cd backend/EcommerceInventory && python manage.py test food.tests.test_rider_dashboard_api -v 2
```

Expected: PASS, 4 tests.

- [ ] **Step 9: Commit**

```bash
git add backend/EcommerceInventory/food/models.py backend/EcommerceInventory/food/migrations backend/EcommerceInventory/food/views_food_ext.py backend/EcommerceInventory/food/urls.py backend/EcommerceInventory/food/serializers_ext.py backend/EcommerceInventory/food/tests/test_rider_dashboard_api.py
git commit -m "feat(food): rider presence via heartbeat with current position"
```

---

### Task 6: Auto-assign the nearest present rider

**Files:**
- Create: `backend/EcommerceInventory/food/services_dispatch.py`
- Modify: `backend/EcommerceInventory/food/views_orders.py:22-25` (`_notify_status`)
- Create: `backend/EcommerceInventory/food/tests/test_rider_dispatch.py`

**Interfaces:**
- Consumes: `Rider.PRESENCE_WINDOW_MINUTES` and location fields from Task 5; `haversine_km(lat1, lng1, lat2, lng2)` from `food/geo.py`; `notify(user, title, body, order_code)` from `food/services.py`.
- Produces:
  - `dispatchable_riders() -> QuerySet[Rider]` — available, seen inside the presence window.
  - `pick_rider_for(order) -> Rider | None` — nearest to the restaurant's pickup point, else least-loaded.
  - `maybe_auto_assign_rider(order) -> Rider | None` — assigns and notifies; no-op if the order already has a rider or is not `CONFIRMED`.

- [ ] **Step 1: Write the failing tests**

Create `backend/EcommerceInventory/food/tests/test_rider_dispatch.py`:

```python
from datetime import timedelta
from decimal import Decimal

from django.test import TestCase
from django.utils import timezone
from django.contrib.auth import get_user_model

from food.models import Restaurant, Rider, FoodOrder
from food.services_dispatch import dispatchable_riders, pick_rider_for, maybe_auto_assign_rider

User = get_user_model()

# Bancharampur upazila centre, near where real orders land.
BANCHARAMPUR = (Decimal("23.7104"), Decimal("90.9280"))


def make_rider(name, *, lat=None, lng=None, seen_minutes_ago=0, available=True):
    user = User.objects.create(username=f"u_{name}", email=f"{name}@x.com", role="Rider")
    return Rider.objects.create(
        user=user, name=name, is_available=available,
        current_lat=lat, current_lng=lng,
        last_seen_at=timezone.now() - timedelta(minutes=seen_minutes_ago),
    )


class DispatchableTests(TestCase):
    def test_excludes_offline_stale_and_locationless_riders(self):
        fresh = make_rider("fresh", lat=BANCHARAMPUR[0], lng=BANCHARAMPUR[1], seen_minutes_ago=1)
        make_rider("stale", lat=BANCHARAMPUR[0], lng=BANCHARAMPUR[1], seen_minutes_ago=10)
        make_rider("offline", lat=BANCHARAMPUR[0], lng=BANCHARAMPUR[1], available=False)
        make_rider("nogps", seen_minutes_ago=1)
        self.assertEqual(list(dispatchable_riders()), [fresh])


class PickRiderTests(TestCase):
    def setUp(self):
        self.restaurant = Restaurant.objects.create(
            name="R", slug="r", status=Restaurant.Status.ACTIVE,
            pickup_lat=BANCHARAMPUR[0], pickup_lng=BANCHARAMPUR[1],
        )
        self.order = FoodOrder.objects.create(
            guest_name="G", guest_phone="017", delivery_address="A",
            restaurant=self.restaurant, subtotal=Decimal("100"), total=Decimal("100"),
            status=FoodOrder.Status.CONFIRMED,
        )

    def test_picks_the_nearest_rider_to_the_restaurant(self):
        far = make_rider("far", lat=Decimal("23.8000"), lng=Decimal("91.0000"), seen_minutes_ago=1)
        near = make_rider("near", lat=Decimal("23.7110"), lng=Decimal("90.9285"), seen_minutes_ago=1)
        self.assertEqual(pick_rider_for(self.order), near)
        self.assertNotEqual(pick_rider_for(self.order), far)

    def test_falls_back_to_least_loaded_when_restaurant_has_no_pickup_point(self):
        self.restaurant.pickup_lat = None
        self.restaurant.pickup_lng = None
        self.restaurant.save()
        busy = make_rider("busy", lat=BANCHARAMPUR[0], lng=BANCHARAMPUR[1], seen_minutes_ago=1)
        idle = make_rider("idle", lat=BANCHARAMPUR[0], lng=BANCHARAMPUR[1], seen_minutes_ago=2)
        FoodOrder.objects.create(
            guest_name="G2", guest_phone="018", delivery_address="B",
            restaurant=self.restaurant, subtotal=Decimal("50"), total=Decimal("50"),
            status=FoodOrder.Status.OUT_FOR_DELIVERY, rider=busy,
        )
        self.assertEqual(pick_rider_for(self.order), idle)

    def test_returns_none_when_nobody_is_dispatchable(self):
        self.assertIsNone(pick_rider_for(self.order))


class AutoAssignTests(TestCase):
    def setUp(self):
        self.restaurant = Restaurant.objects.create(
            name="R", slug="r", status=Restaurant.Status.ACTIVE,
            pickup_lat=BANCHARAMPUR[0], pickup_lng=BANCHARAMPUR[1],
        )

    def _order(self, status=FoodOrder.Status.CONFIRMED, rider=None):
        return FoodOrder.objects.create(
            guest_name="G", guest_phone="017", delivery_address="A",
            restaurant=self.restaurant, subtotal=Decimal("100"), total=Decimal("100"),
            status=status, rider=rider,
        )

    def test_assigns_on_confirmed(self):
        rider = make_rider("r1", lat=BANCHARAMPUR[0], lng=BANCHARAMPUR[1], seen_minutes_ago=1)
        order = self._order()
        self.assertEqual(maybe_auto_assign_rider(order), rider)
        order.refresh_from_db()
        self.assertEqual(order.rider, rider)

    def test_does_not_reassign_an_order_that_already_has_a_rider(self):
        first = make_rider("r1", lat=BANCHARAMPUR[0], lng=BANCHARAMPUR[1], seen_minutes_ago=1)
        make_rider("r2", lat=BANCHARAMPUR[0], lng=BANCHARAMPUR[1], seen_minutes_ago=1)
        order = self._order(rider=first)
        self.assertIsNone(maybe_auto_assign_rider(order))
        order.refresh_from_db()
        self.assertEqual(order.rider, first)

    def test_ignores_orders_not_in_confirmed(self):
        make_rider("r1", lat=BANCHARAMPUR[0], lng=BANCHARAMPUR[1], seen_minutes_ago=1)
        order = self._order(status=FoodOrder.Status.PLACED)
        self.assertIsNone(maybe_auto_assign_rider(order))
        order.refresh_from_db()
        self.assertIsNone(order.rider)

    def test_notifies_the_assigned_rider(self):
        rider = make_rider("r1", lat=BANCHARAMPUR[0], lng=BANCHARAMPUR[1], seen_minutes_ago=1)
        order = self._order()
        maybe_auto_assign_rider(order)
        self.assertTrue(rider.user.food_notifications.filter(order_code=order.order_code).exists())
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd backend/EcommerceInventory && python manage.py test food.tests.test_rider_dispatch -v 2
```

Expected: FAIL — `ModuleNotFoundError: No module named 'food.services_dispatch'`.

- [ ] **Step 3: Implement the dispatch service**

Create `backend/EcommerceInventory/food/services_dispatch.py`:

```python
"""Choosing which rider gets an order.

Riders use the web dashboard, not a native app, so "who is online right now"
is derived from the heartbeat that page sends (see Rider.PRESENCE_WINDOW_MINUTES
and views_food_ext.RiderHeartbeatView) rather than from a standing flag alone.
"""
from datetime import timedelta

from django.db.models import Count, Q
from django.utils import timezone

from food.geo import haversine_km
from food.models import FoodOrder, Rider
from food.services import notify

ACTIVE_STATUSES = [FoodOrder.Status.CONFIRMED, FoodOrder.Status.PREPARING,
                   FoodOrder.Status.OUT_FOR_DELIVERY]


def dispatchable_riders():
    """Riders who are available, recently seen, and have a known position."""
    cutoff = timezone.now() - timedelta(minutes=Rider.PRESENCE_WINDOW_MINUTES)
    return Rider.objects.filter(
        is_available=True,
        last_seen_at__gte=cutoff,
        current_lat__isnull=False,
        current_lng__isnull=False,
    )


def pick_rider_for(order):
    """Nearest dispatchable rider to the pickup point, else the least loaded.

    Riders have no zone association in the current model, so there is no zone
    filter to fall back on — load then staleness is the tiebreak instead.
    """
    riders = list(dispatchable_riders())
    if not riders:
        return None

    restaurant = order.restaurant
    if restaurant.pickup_lat is not None and restaurant.pickup_lng is not None:
        return min(riders, key=lambda r: haversine_km(
            restaurant.pickup_lat, restaurant.pickup_lng, r.current_lat, r.current_lng))

    ranked = dispatchable_riders().annotate(
        active_orders=Count("orders", filter=Q(orders__status__in=ACTIVE_STATUSES))
    ).order_by("active_orders", "last_seen_at")
    return ranked.first()


def maybe_auto_assign_rider(order):
    """Assign a rider to a freshly confirmed order. Returns the rider or None.

    Idempotent: an order that already has a rider is never reassigned, so an
    admin's manual choice always wins.
    """
    if order.rider_id or order.status != FoodOrder.Status.CONFIRMED:
        return None
    rider = pick_rider_for(order)
    if rider is None:
        return None

    order.rider = rider
    order.save(update_fields=["rider", "updated_at"])
    notify(rider.user, f"New delivery {order.order_code}",
           f"Pick up from {order.restaurant.name} 🛵", order.order_code)
    notify(order.customer, f"Order {order.order_code}",
           f"{rider.name} will deliver your order 🛵", order.order_code)
    return rider
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd backend/EcommerceInventory && python manage.py test food.tests.test_rider_dispatch -v 2
```

Expected: PASS, 9 tests.

- [ ] **Step 5: Hook it into the status-change path**

Both the vendor and admin status views already call `_notify_status(order)` after a successful `transition_to`. Extend that single helper in `backend/EcommerceInventory/food/views_orders.py`:

```python
def _notify_status(order):
    msg = STATUS_MSG.get(order.status)
    if msg:
        notify(order.customer, f"Order {order.order_code}", msg, order.order_code)
    # A confirmed order is ready to be carried — hand it to the nearest present
    # rider. No-op when one is already assigned, so admin assignment still wins.
    maybe_auto_assign_rider(order)
```

Add the import at the top of the file:

```python
from food.services_dispatch import maybe_auto_assign_rider
```

- [ ] **Step 6: Write the integration test**

Append to `backend/EcommerceInventory/food/tests/test_rider_dispatch.py`:

```python
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken


class ConfirmAssignsRiderTests(TestCase):
    def test_admin_confirming_an_order_auto_assigns(self):
        admin = User.objects.create(username="adm", email="adm@x.com", role="Admin")
        restaurant = Restaurant.objects.create(
            name="R", slug="r", status=Restaurant.Status.ACTIVE,
            pickup_lat=BANCHARAMPUR[0], pickup_lng=BANCHARAMPUR[1],
        )
        rider = make_rider("r1", lat=BANCHARAMPUR[0], lng=BANCHARAMPUR[1], seen_minutes_ago=1)
        order = FoodOrder.objects.create(
            guest_name="G", guest_phone="017", delivery_address="A",
            restaurant=restaurant, subtotal=Decimal("100"), total=Decimal("100"),
            status=FoodOrder.Status.PLACED,
        )
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {RefreshToken.for_user(admin).access_token}")
        res = client.patch(f"/api/food/admin/orders/{order.id}/status/",
                           {"status": "CONFIRMED"}, format="json")
        self.assertEqual(res.status_code, 200, res.content)
        order.refresh_from_db()
        self.assertEqual(order.rider, rider)
```

- [ ] **Step 7: Run the full food suite**

```bash
cd backend/EcommerceInventory && python manage.py test food
```

Expected: PASS. Existing order tests now exercise `maybe_auto_assign_rider`, which is a no-op when no rider is dispatchable — confirm `test_orders.py` and `test_fulfillment_api.py` are unaffected.

- [ ] **Step 8: Commit**

```bash
git add backend/EcommerceInventory/food/services_dispatch.py backend/EcommerceInventory/food/views_orders.py backend/EcommerceInventory/food/tests/test_rider_dispatch.py
git commit -m "feat(food): auto-assign nearest present rider when an order is confirmed"
```

---

### Task 7: Rider-facing order payload and earnings

**Files:**
- Create: `backend/EcommerceInventory/food/serializers_rider.py`
- Modify: `backend/EcommerceInventory/food/views_food_ext.py` (`RiderOrdersView`, new `RiderEarningsView`), `food/urls.py`
- Modify: `backend/EcommerceInventory/food/tests/test_rider_dashboard_api.py`

**Interfaces:**
- Consumes: `Rider` presence fields (Task 5).
- Produces:
  - `RiderOrderSerializer` — everything `FoodOrderSerializer` returns plus `pickup_lat`, `pickup_lng`, `restaurant_phone`, `restaurant_address`, `notes`, `cash_to_collect`.
  - `GET /api/food/rider/earnings/` → `{"data": {"today": "120.00", "lifetime": "3400.00", "cash_to_collect": "450.00", "history": [{"order_code", "delivered_at", "base_pay", "tip", "payout"}]}}`.

- [ ] **Step 1: Write the failing tests**

Append to `backend/EcommerceInventory/food/tests/test_rider_dashboard_api.py`:

```python
from decimal import Decimal
from food.models import Restaurant, FoodOrder, FoodOrderItem, RiderEarning


class RiderOrderPayloadTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create(username="rdr", email="rdr@x.com", role="Rider")
        self.rider = Rider.objects.create(user=self.user, name="Rakib")
        self.restaurant = Restaurant.objects.create(
            name="Kacchi Ghor", slug="kacchi-ghor", status=Restaurant.Status.ACTIVE,
            pickup_lat=Decimal("23.710400"), pickup_lng=Decimal("90.928000"),
            phone="01711000000", address="Bancharampur Bazar",
        )
        self.order = FoodOrder.objects.create(
            guest_name="Karim", guest_phone="01811000000", delivery_address="Ujanchar",
            restaurant=self.restaurant, rider=self.rider, subtotal=Decimal("300"),
            total=Decimal("340"), status=FoodOrder.Status.OUT_FOR_DELIVERY,
            payment_method="COD", payment_status="PENDING", notes="Extra salad please",
        )
        FoodOrderItem.objects.create(order=self.order, item_name="Kacchi", unit_price=Decimal("300"),
                                     quantity=1, line_total=Decimal("300"),
                                     selected_options=[{"name": "Extra meat", "price_delta": "40.00"}])

    def test_order_payload_carries_pickup_contact_notes_and_cash(self):
        auth(self.client, self.user)
        res = self.client.get("/api/food/rider/orders/")
        self.assertEqual(res.status_code, 200, res.content)
        order = res.json()["data"][0]
        self.assertEqual(order["pickup_lat"], "23.710400")
        self.assertEqual(order["restaurant_phone"], "01711000000")
        self.assertEqual(order["restaurant_address"], "Bancharampur Bazar")
        self.assertEqual(order["notes"], "Extra salad please")
        self.assertEqual(order["cash_to_collect"], "340.00")
        self.assertEqual(order["items"][0]["selected_options"][0]["name"], "Extra meat")

    def test_cash_to_collect_is_zero_for_a_paid_order(self):
        self.order.payment_method = "BKASH"
        self.order.payment_status = "COLLECTED"
        self.order.save()
        auth(self.client, self.user)
        res = self.client.get("/api/food/rider/orders/")
        self.assertEqual(res.json()["data"][0]["cash_to_collect"], "0.00")


class RiderEarningsTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create(username="rdr", email="rdr@x.com", role="Rider")
        self.rider = Rider.objects.create(user=self.user, name="Rakib")
        self.restaurant = Restaurant.objects.create(name="R", slug="r",
                                                    status=Restaurant.Status.ACTIVE)

    def test_earnings_totals_and_history(self):
        delivered = FoodOrder.objects.create(
            guest_name="G", guest_phone="017", delivery_address="A",
            restaurant=self.restaurant, rider=self.rider, subtotal=Decimal("100"),
            total=Decimal("120"), status=FoodOrder.Status.DELIVERED,
        )
        RiderEarning.objects.create(rider=self.rider, order=delivered,
                                    base_pay=Decimal("40.00"), tip=Decimal("10.00"))
        auth(self.client, self.user)
        res = self.client.get("/api/food/rider/earnings/")
        self.assertEqual(res.status_code, 200, res.content)
        data = res.json()["data"]
        self.assertEqual(data["today"], "50.00")
        self.assertEqual(data["lifetime"], "50.00")
        self.assertEqual(data["history"][0]["order_code"], delivered.order_code)
        self.assertEqual(data["history"][0]["payout"], "50.00")

    def test_cash_to_collect_sums_unpaid_cod_orders(self):
        FoodOrder.objects.create(
            guest_name="G", guest_phone="017", delivery_address="A",
            restaurant=self.restaurant, rider=self.rider, subtotal=Decimal("100"),
            total=Decimal("150"), status=FoodOrder.Status.OUT_FOR_DELIVERY,
            payment_method="COD", payment_status="PENDING",
        )
        auth(self.client, self.user)
        res = self.client.get("/api/food/rider/earnings/")
        self.assertEqual(res.json()["data"]["cash_to_collect"], "150.00")
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd backend/EcommerceInventory && python manage.py test food.tests.test_rider_dashboard_api -v 2
```

Expected: FAIL — `KeyError: 'pickup_lat'` and 404 on `/api/food/rider/earnings/`.

- [ ] **Step 3: Implement the serializer**

Create `backend/EcommerceInventory/food/serializers_rider.py`:

```python
"""Order payload for the rider dashboard.

Extends the shared FoodOrderSerializer with what a rider on a motorbike needs
and nobody else does: where to pick up, who to call at each end, what to check
in the bag, and how much cash to collect at the door.
"""
from decimal import Decimal

from rest_framework import serializers

from food.models import FoodOrder
from food.serializers_orders import FoodOrderSerializer


class RiderOrderSerializer(FoodOrderSerializer):
    pickup_lat = serializers.DecimalField(source="restaurant.pickup_lat", max_digits=9,
                                          decimal_places=6, read_only=True)
    pickup_lng = serializers.DecimalField(source="restaurant.pickup_lng", max_digits=9,
                                          decimal_places=6, read_only=True)
    restaurant_phone = serializers.CharField(source="restaurant.phone", read_only=True)
    restaurant_address = serializers.CharField(source="restaurant.address", read_only=True)
    cash_to_collect = serializers.SerializerMethodField()

    class Meta(FoodOrderSerializer.Meta):
        model = FoodOrder
        fields = FoodOrderSerializer.Meta.fields + [
            "pickup_lat", "pickup_lng", "restaurant_phone", "restaurant_address",
            "notes", "cash_to_collect",
        ]

    def get_cash_to_collect(self, obj):
        unpaid_cod = obj.payment_method == "COD" and obj.payment_status != "COLLECTED"
        return str(obj.total if unpaid_cod else Decimal("0.00"))
```

- [ ] **Step 4: Point the rider orders view at it and add earnings**

In `backend/EcommerceInventory/food/views_food_ext.py`, change `RiderOrdersView.get` to use the new serializer and select the restaurant in one query:

```python
class RiderOrdersView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, IsRider]

    def get(self, request):
        qs = FoodOrder.objects.filter(rider=request.user.rider).exclude(
            status__in=[FoodOrder.Status.DELIVERED, FoodOrder.Status.CANCELLED]
        ).select_related("restaurant").prefetch_related("items")
        return renderResponse(data=RiderOrderSerializer(qs, many=True).data,
                              message="Assigned orders")
```

Add after it:

```python
class RiderEarningsView(APIView):
    """Today's and lifetime payout, completed deliveries, and cash owed to the
    restaurant from COD orders the rider is still carrying."""
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, IsRider]

    def get(self, request):
        rider = request.user.rider
        earnings = rider.earnings.select_related("order").order_by("-created_at")
        today = timezone.localdate()

        lifetime = sum((e.base_pay + e.tip for e in earnings), Decimal("0.00"))
        today_total = sum((e.base_pay + e.tip for e in earnings
                           if timezone.localtime(e.created_at).date() == today), Decimal("0.00"))
        cash = sum((o.total for o in FoodOrder.objects.filter(
            rider=rider, payment_method="COD", payment_status="PENDING"
        ).exclude(status__in=[FoodOrder.Status.DELIVERED, FoodOrder.Status.CANCELLED])),
            Decimal("0.00"))

        history = [{
            "order_code": e.order.order_code if e.order else "",
            "delivered_at": e.created_at.isoformat(),
            "base_pay": str(e.base_pay),
            "tip": str(e.tip),
            "payout": str(e.base_pay + e.tip),
        } for e in earnings[:50]]

        return renderResponse(data={
            "today": str(today_total.quantize(Decimal("0.01"))),
            "lifetime": str(lifetime.quantize(Decimal("0.01"))),
            "cash_to_collect": str(cash.quantize(Decimal("0.01"))),
            "history": history,
        }, message="Rider earnings")
```

Add the import near the other food imports in that file:

```python
from food.serializers_rider import RiderOrderSerializer
```

- [ ] **Step 5: Register the route**

In `backend/EcommerceInventory/food/urls.py`, add `RiderEarningsView` to the import list and add:

```python
    path("rider/earnings/", RiderEarningsView.as_view(), name="food_rider_earnings"),
```

- [ ] **Step 6: Run tests to verify they pass**

```bash
cd backend/EcommerceInventory && python manage.py test food.tests.test_rider_dashboard_api -v 2
```

Expected: PASS, 8 tests.

- [ ] **Step 7: Commit**

```bash
git add backend/EcommerceInventory/food/serializers_rider.py backend/EcommerceInventory/food/views_food_ext.py backend/EcommerceInventory/food/urls.py backend/EcommerceInventory/food/tests/test_rider_dashboard_api.py
git commit -m "feat(food): rider order payload with pickup, contacts, notes and cash; earnings endpoint"
```

---

### Task 8: Rider heartbeat hook and dashboard shell

**Files:**
- Create: `frontend/ecommerce_inventory/src/rider/useRiderHeartbeat.js`, `src/rider/geo.js`, `src/rider/RiderHeader.js`, `src/rider/EarningsPanel.js`
- Create: `frontend/ecommerce_inventory/src/rider/useRiderHeartbeat.test.js`, `src/rider/geo.test.js`
- Modify: `frontend/ecommerce_inventory/src/rider/RiderDashboard.js`

**Interfaces:**
- Consumes: `POST food/rider/heartbeat/`, `GET food/rider/earnings/` (Tasks 5, 7).
- Produces:
  - `geo.js`: `haversineKm(a, b) -> number` and `bearingDeg(from, to) -> number`, where points are `{lat, lng}` numbers.
  - `useRiderHeartbeat(online) -> {position, error}` — `position` is `{lat, lng}` or `null`.
  - `<RiderHeader me online onToggle onLogout />`, `<EarningsPanel earnings />`.

- [ ] **Step 1: Write the failing geo test**

Create `frontend/ecommerce_inventory/src/rider/geo.test.js`:

```javascript
import { haversineKm, bearingDeg } from "./geo";

describe("geo", () => {
    it("measures ~0 km between a point and itself", () => {
        expect(haversineKm({ lat: 23.7104, lng: 90.928 }, { lat: 23.7104, lng: 90.928 })).toBeCloseTo(0, 3);
    });

    it("measures a known short distance", () => {
        // ~1.11 km per 0.01 degree of latitude
        const d = haversineKm({ lat: 23.7104, lng: 90.928 }, { lat: 23.7204, lng: 90.928 });
        expect(d).toBeGreaterThan(1.0);
        expect(d).toBeLessThan(1.2);
    });

    it("reports due north as ~0 degrees and due east as ~90", () => {
        expect(bearingDeg({ lat: 23.71, lng: 90.92 }, { lat: 23.72, lng: 90.92 })).toBeCloseTo(0, 0);
        expect(bearingDeg({ lat: 23.71, lng: 90.92 }, { lat: 23.71, lng: 90.93 })).toBeCloseTo(90, 0);
    });
});
```

- [ ] **Step 2: Run it to verify it fails**

```bash
cd frontend/ecommerce_inventory && npm test -- --watchAll=false rider/geo.test.js
```

Expected: FAIL — `Cannot find module './geo'`.

- [ ] **Step 3: Implement geo.js**

Create `frontend/ecommerce_inventory/src/rider/geo.js`:

```javascript
// Distance and bearing for the rider map. Mirrors food/geo.py::haversine_km on
// the backend so the two never disagree about how far away a drop-off is.
const R_KM = 6371;
const rad = (d) => (d * Math.PI) / 180;
const deg = (r) => (r * 180) / Math.PI;

export const haversineKm = (a, b) => {
    const dPhi = rad(b.lat - a.lat);
    const dLambda = rad(b.lng - a.lng);
    const p1 = rad(a.lat);
    const p2 = rad(b.lat);
    const h = Math.sin(dPhi / 2) ** 2 + Math.cos(p1) * Math.cos(p2) * Math.sin(dLambda / 2) ** 2;
    return 2 * R_KM * Math.asin(Math.sqrt(h));
};

// Compass bearing from → to, 0 = north, clockwise.
export const bearingDeg = (from, to) => {
    const p1 = rad(from.lat);
    const p2 = rad(to.lat);
    const dLambda = rad(to.lng - from.lng);
    const y = Math.sin(dLambda) * Math.cos(p2);
    const x = Math.cos(p1) * Math.sin(p2) - Math.sin(p1) * Math.cos(p2) * Math.cos(dLambda);
    return (deg(Math.atan2(y, x)) + 360) % 360;
};
```

- [ ] **Step 4: Run it to verify it passes**

```bash
cd frontend/ecommerce_inventory && npm test -- --watchAll=false rider/geo.test.js
```

Expected: PASS, 3 tests.

- [ ] **Step 5: Write the failing heartbeat test**

Create `frontend/ecommerce_inventory/src/rider/useRiderHeartbeat.test.js`:

```javascript
import { renderHook, act, waitFor } from "@testing-library/react";
import useRiderHeartbeat from "./useRiderHeartbeat";

const mockCallApi = jest.fn(() => Promise.resolve({ status: 200, data: { data: {} } }));
jest.mock("../hooks/APIHandler", () => () => ({ callApi: mockCallApi }));

describe("useRiderHeartbeat", () => {
    let watchers;
    beforeEach(() => {
        jest.useFakeTimers();
        mockCallApi.mockClear();
        watchers = {};
        global.navigator.geolocation = {
            watchPosition: jest.fn((ok) => {
                watchers.ok = ok;
                return 7;
            }),
            clearWatch: jest.fn(),
        };
    });
    afterEach(() => jest.useRealTimers());

    it("does nothing while offline", () => {
        renderHook(() => useRiderHeartbeat(false));
        expect(navigator.geolocation.watchPosition).not.toHaveBeenCalled();
        expect(mockCallApi).not.toHaveBeenCalled();
    });

    it("watches position and posts a heartbeat once online", async () => {
        const { result } = renderHook(() => useRiderHeartbeat(true));
        expect(navigator.geolocation.watchPosition).toHaveBeenCalled();

        act(() => watchers.ok({ coords: { latitude: 23.71, longitude: 90.93 } }));
        await waitFor(() => expect(result.current.position).toEqual({ lat: 23.71, lng: 90.93 }));

        await waitFor(() => expect(mockCallApi).toHaveBeenCalledWith(
            expect.objectContaining({ url: "food/rider/heartbeat/", method: "POST" })
        ));
    });

    it("stops watching when it goes offline", () => {
        const { rerender } = renderHook(({ online }) => useRiderHeartbeat(online),
            { initialProps: { online: true } });
        rerender({ online: false });
        expect(navigator.geolocation.clearWatch).toHaveBeenCalledWith(7);
    });
});
```

- [ ] **Step 6: Run it to verify it fails**

```bash
cd frontend/ecommerce_inventory && npm test -- --watchAll=false useRiderHeartbeat.test.js
```

Expected: FAIL — module not found.

- [ ] **Step 7: Implement the hook**

Create `frontend/ecommerce_inventory/src/rider/useRiderHeartbeat.js`:

```javascript
import { useEffect, useRef, useState } from "react";
import useApi from "../hooks/APIHandler";

const HEARTBEAT_MS = 20000;

// Keeps the rider marked present while the Online switch is on: watches the
// device position and posts it every 20s. Dispatch treats a rider as reachable
// only inside Rider.PRESENCE_WINDOW_MINUTES of the last beat, so closing this
// tab quietly removes them from the pool with no explicit "go offline" step.
//
// Location is only read while online, and only the latest position is sent —
// no trail is recorded anywhere.
export default function useRiderHeartbeat(online) {
    const { callApi } = useApi();
    const [position, setPosition] = useState(null);
    const [error, setError] = useState(null);
    const latest = useRef(null);

    useEffect(() => {
        if (!online) return undefined;

        let watchId = null;
        if (navigator.geolocation?.watchPosition) {
            watchId = navigator.geolocation.watchPosition(
                ({ coords }) => {
                    const p = { lat: coords.latitude, lng: coords.longitude };
                    latest.current = p;
                    setPosition(p);
                },
                (err) => setError(err?.message || "Location unavailable"),
                { enableHighAccuracy: true, maximumAge: 10000, timeout: 15000 },
            );
        } else {
            setError("This device can't share location");
        }

        // Beat immediately so the rider becomes dispatchable without a 20s wait,
        // then on an interval. Coordinates are omitted until the first fix.
        const beat = () => callApi({
            url: "food/rider/heartbeat/", method: "POST",
            body: latest.current || {}, silent: true,
        });
        beat();
        const timer = setInterval(beat, HEARTBEAT_MS);

        return () => {
            clearInterval(timer);
            if (watchId !== null) navigator.geolocation.clearWatch(watchId);
        };
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [online]);

    return { position, error };
}
```

- [ ] **Step 8: Run it to verify it passes**

```bash
cd frontend/ecommerce_inventory && npm test -- --watchAll=false useRiderHeartbeat.test.js
```

Expected: PASS, 3 tests.

- [ ] **Step 9: Extract the header component**

Create `frontend/ecommerce_inventory/src/rider/RiderHeader.js`:

```javascript
import { Box, Card, Stack, Avatar, Typography, Switch, FormControlLabel } from "@mui/material";

// Profile strip + the Online switch that drives the heartbeat. Bilingual, as
// riders here read Bangla more comfortably than English.
export default function RiderHeader({ me, online, onToggle, locationError }) {
    return (
        <Card sx={{ p: 2.5, mb: 2 }}>
            <Stack direction="row" alignItems="center" spacing={2}>
                <Avatar sx={{ bgcolor: "#E8452B", width: 48, height: 48 }}>{(me.name || "?")[0]}</Avatar>
                <Box sx={{ flexGrow: 1 }}>
                    <Typography fontWeight={800}>{me.name}</Typography>
                    <Typography variant="caption" color="text.secondary">
                        {me.rider_code} · {me.total_deliveries} deliveries · ৳{me.total_earnings} earned
                    </Typography>
                </Box>
                <FormControlLabel
                    labelPlacement="top"
                    control={<Switch checked={online} onChange={(e) => onToggle(e.target.checked)} />}
                    label={<Typography variant="caption">{online ? "Online / অনলাইন" : "Offline / অফলাইন"}</Typography>}
                />
            </Stack>
            <Typography variant="caption" color="text.secondary" display="block" sx={{ mt: 1 }}>
                Location is shared only while you are online · আপনি অনলাইনে থাকলেই কেবল অবস্থান শেয়ার হয়
            </Typography>
            {online && locationError && (
                <Typography variant="caption" color="error" display="block">{locationError}</Typography>
            )}
        </Card>
    );
}
```

- [ ] **Step 10: Extract the earnings panel**

Create `frontend/ecommerce_inventory/src/rider/EarningsPanel.js`:

```javascript
import { Card, Stack, Box, Typography, Divider, List, ListItem, ListItemText } from "@mui/material";

const Stat = ({ label, value, color }) => (
    <Box sx={{ flex: 1, textAlign: "center" }}>
        <Typography variant="h6" fontWeight={800} color={color}>৳{value}</Typography>
        <Typography variant="caption" color="text.secondary">{label}</Typography>
    </Box>
);

export default function EarningsPanel({ earnings }) {
    if (!earnings) return null;
    return (
        <Card sx={{ p: 2, mb: 2 }}>
            <Stack direction="row" divider={<Divider orientation="vertical" flexItem />}>
                <Stat label="Today / আজ" value={earnings.today} />
                <Stat label="Lifetime / মোট" value={earnings.lifetime} />
                <Stat label="Cash to hand in" value={earnings.cash_to_collect} color="warning.main" />
            </Stack>
            {earnings.history?.length > 0 && (
                <>
                    <Divider sx={{ my: 1.5 }} />
                    <Typography variant="caption" color="text.secondary">Completed deliveries</Typography>
                    <List dense>
                        {earnings.history.map((h) => (
                            <ListItem key={`${h.order_code}-${h.delivered_at}`} disableGutters>
                                <ListItemText
                                    primary={h.order_code}
                                    secondary={new Date(h.delivered_at).toLocaleString()}
                                />
                                <Typography fontWeight={700}>৳{h.payout}</Typography>
                            </ListItem>
                        ))}
                    </List>
                </>
            )}
        </Card>
    );
}
```

- [ ] **Step 11: Wire header, heartbeat and earnings into the dashboard**

In `frontend/ecommerce_inventory/src/rider/RiderDashboard.js`, add imports:

```javascript
import RiderHeader from "./RiderHeader";
import EarningsPanel from "./EarningsPanel";
import useRiderHeartbeat from "./useRiderHeartbeat";
```

Add earnings state and the heartbeat next to the existing state:

```javascript
    const [earnings, setEarnings] = useState(null);
    const online = !!me?.is_available;
    const { position, error: locationError } = useRiderHeartbeat(online);
```

Extend `load` to fetch earnings alongside the existing two calls:

```javascript
    const load = useCallback(async () => {
        const [m, o, e] = await Promise.all([
            callApi({ url: "food/rider/me/", method: "GET", silent: true }),
            callApi({ url: "food/rider/orders/", method: "GET", silent: true }),
            callApi({ url: "food/rider/earnings/", method: "GET", silent: true }),
        ]);
        setMe(m?.status === 200 ? m.data.data : null);
        setOrders(o?.data?.data || []);
        setEarnings(e?.status === 200 ? e.data.data : null);
        setLoading(false);
    }, []); // eslint-disable-line react-hooks/exhaustive-deps
```

Replace the inline profile `<Card>` (currently lines 65–75) with:

```javascript
                <RiderHeader me={me} online={online} onToggle={toggle} locationError={locationError} />
                <EarningsPanel earnings={earnings} />
```

- [ ] **Step 12: Run the frontend suite**

```bash
cd frontend/ecommerce_inventory && npm test -- --watchAll=false
```

Expected: PASS.

- [ ] **Step 13: Commit**

```bash
git add frontend/ecommerce_inventory/src/rider
git commit -m "feat(rider): presence heartbeat, bilingual header and earnings panel"
```

---

### Task 9: Delivery card and live map

**Files:**
- Create: `frontend/ecommerce_inventory/src/rider/DeliveryMap.js`, `src/rider/DeliveryCard.js`
- Create: `frontend/ecommerce_inventory/src/rider/DeliveryCard.test.js`, `src/rider/RiderDashboard.test.js`
- Modify: `frontend/ecommerce_inventory/src/rider/RiderDashboard.js`

**Interfaces:**
- Consumes: `haversineKm`, `bearingDeg` from `./geo`; `position` from `useRiderHeartbeat`; the `RiderOrderSerializer` payload from Task 7.
- Produces: `<DeliveryCard order riderPosition onAdvance />`, `<DeliveryMap riderPosition pickup dropoff leg />` where `leg` is `"PICKUP"` or `"DROPOFF"`.

**Note on routing:** the map draws a straight polyline, not a road route. Turn-by-turn is delegated to Google Maps via a link. This is deliberate — no routing service, no API key, nothing to rate-limit in production.

- [ ] **Step 1: Write the failing DeliveryCard test**

Create `frontend/ecommerce_inventory/src/rider/DeliveryCard.test.js`:

```javascript
import { render, screen } from "@testing-library/react";
import DeliveryCard from "./DeliveryCard";

// Leaflet needs a real DOM size; the map is exercised separately.
jest.mock("./DeliveryMap", () => () => <div data-testid="delivery-map" />);

const order = {
    id: 1,
    order_code: "FD12345",
    status: "OUT_FOR_DELIVERY",
    restaurant_name: "Kacchi Ghor",
    restaurant_phone: "01711000000",
    restaurant_address: "Bancharampur Bazar",
    guest_name: "Karim",
    guest_phone: "01811000000",
    delivery_address: "Ujanchar",
    notes: "Extra salad please",
    total: "340.00",
    payment_method: "COD",
    cash_to_collect: "340.00",
    pickup_lat: "23.710400",
    pickup_lng: "90.928000",
    delivery_lat: "23.720000",
    delivery_lng: "90.930000",
    items: [
        { id: 1, item_name: "Kacchi", quantity: 2, line_total: "600.00",
          selected_options: [{ name: "Extra meat", price_delta: "40.00" }] },
    ],
};

describe("DeliveryCard", () => {
    it("lists what to pick up including options and the order note", () => {
        render(<DeliveryCard order={order} riderPosition={null} onAdvance={jest.fn()} />);
        expect(screen.getByText(/Kacchi/)).toBeInTheDocument();
        expect(screen.getByText(/Extra meat/)).toBeInTheDocument();
        expect(screen.getByText(/Extra salad please/)).toBeInTheDocument();
    });

    it("offers one-tap calls to both the customer and the restaurant", () => {
        render(<DeliveryCard order={order} riderPosition={null} onAdvance={jest.fn()} />);
        expect(screen.getByRole("link", { name: /call customer/i }))
            .toHaveAttribute("href", "tel:01811000000");
        expect(screen.getByRole("link", { name: /call restaurant/i }))
            .toHaveAttribute("href", "tel:01711000000");
    });

    it("shows the cash to collect for a COD order", () => {
        render(<DeliveryCard order={order} riderPosition={null} onAdvance={jest.fn()} />);
        expect(screen.getByText(/৳340.00/)).toBeInTheDocument();
    });

    it("shows distance to the drop-off once the rider position is known", () => {
        render(<DeliveryCard order={order} riderPosition={{ lat: 23.71, lng: 90.928 }} onAdvance={jest.fn()} />);
        expect(screen.getByText(/km to drop-off/i)).toBeInTheDocument();
    });

    it("warns when the rider is moving away from the target", () => {
        const { rerender } = render(
            <DeliveryCard order={order} riderPosition={{ lat: 23.7190, lng: 90.9300 }} onAdvance={jest.fn()} />);
        // three consecutive positions, each further from the drop-off
        rerender(<DeliveryCard order={order} riderPosition={{ lat: 23.7150, lng: 90.9300 }} onAdvance={jest.fn()} />);
        rerender(<DeliveryCard order={order} riderPosition={{ lat: 23.7100, lng: 90.9300 }} onAdvance={jest.fn()} />);
        rerender(<DeliveryCard order={order} riderPosition={{ lat: 23.7050, lng: 90.9300 }} onAdvance={jest.fn()} />);
        expect(screen.getByText(/moving away/i)).toBeInTheDocument();
    });

    it("links out to Google Maps for turn-by-turn", () => {
        render(<DeliveryCard order={order} riderPosition={null} onAdvance={jest.fn()} />);
        expect(screen.getByRole("link", { name: /open in google maps/i }))
            .toHaveAttribute("href", expect.stringContaining("google.com/maps"));
    });
});
```

- [ ] **Step 2: Run it to verify it fails**

```bash
cd frontend/ecommerce_inventory && npm test -- --watchAll=false DeliveryCard.test.js
```

Expected: FAIL — module not found.

- [ ] **Step 3: Implement DeliveryMap**

Create `frontend/ecommerce_inventory/src/rider/DeliveryMap.js`:

```javascript
import { useEffect, useRef } from "react";
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import { Box } from "@mui/material";

// A deliberately simple map: rider, pickup, drop-off, and a straight dashed line
// for the leg in progress. We do NOT run a routing engine — real turn-by-turn is
// a Google Maps hand-off from DeliveryCard, which keeps this free of API keys,
// rate limits and an extra production dependency.
const icon = (emoji, size = 28) => L.divIcon({
    html: `<div style="font-size:${size}px;line-height:1">${emoji}</div>`,
    className: "", iconSize: [size, size], iconAnchor: [size / 2, size / 2],
});

const num = (v) => (v === null || v === undefined || v === "" ? null : Number(v));

export default function DeliveryMap({ riderPosition, pickup, dropoff, leg }) {
    const el = useRef(null);
    const map = useRef(null);
    const layer = useRef(null);

    useEffect(() => {
        if (!el.current || map.current) return;
        map.current = L.map(el.current, { zoomControl: false, attributionControl: false });
        L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", { maxZoom: 19 })
            .addTo(map.current);
        layer.current = L.layerGroup().addTo(map.current);
        map.current.setView([23.7104, 90.928], 13); // Bancharampur, until we know better
    }, []);

    useEffect(() => {
        if (!map.current || !layer.current) return;
        layer.current.clearLayers();

        const points = [];
        const pick = pickup && num(pickup.lat) !== null ? [num(pickup.lat), num(pickup.lng)] : null;
        const drop = dropoff && num(dropoff.lat) !== null ? [num(dropoff.lat), num(dropoff.lng)] : null;
        const me = riderPosition ? [riderPosition.lat, riderPosition.lng] : null;

        if (pick) { L.marker(pick, { icon: icon("🍳") }).addTo(layer.current); points.push(pick); }
        if (drop) { L.marker(drop, { icon: icon("🏠") }).addTo(layer.current); points.push(drop); }
        if (me) { L.marker(me, { icon: icon("🛵", 32) }).addTo(layer.current); points.push(me); }

        // Dashed line for the leg currently being ridden.
        const target = leg === "PICKUP" ? pick : drop;
        if (me && target) {
            L.polyline([me, target], { color: "#E8452B", weight: 3, dashArray: "8 8" })
                .addTo(layer.current);
        }

        if (points.length > 1) {
            map.current.fitBounds(L.latLngBounds(points).pad(0.25));
        } else if (points.length === 1) {
            map.current.setView(points[0], 15);
        }
    }, [riderPosition, pickup, dropoff, leg]);

    return <Box ref={el} sx={{ height: 220, borderRadius: 2, overflow: "hidden", my: 1.5 }} />;
}
```

- [ ] **Step 4: Implement DeliveryCard**

Create `frontend/ecommerce_inventory/src/rider/DeliveryCard.js`:

```javascript
import { useEffect, useRef, useState } from "react";
import {
    Card, Stack, Box, Typography, Chip, Divider, Button, Alert, List, ListItem, ListItemText,
} from "@mui/material";
import CallIcon from "@mui/icons-material/Call";
import NavigationIcon from "@mui/icons-material/Navigation";
import DeliveryMap from "./DeliveryMap";
import { haversineKm, bearingDeg } from "./geo";

const NEXT = {
    OUT_FOR_DELIVERY: ["DELIVERED", "Mark delivered / ডেলিভারি সম্পন্ন"],
    PREPARING: ["OUT_FOR_DELIVERY", "Picked up / নিয়েছি"],
    CONFIRMED: ["OUT_FOR_DELIVERY", "Picked up / নিয়েছি"],
};

const num = (v) => (v === null || v === undefined || v === "" ? null : Number(v));
const point = (lat, lng) => (num(lat) === null || num(lng) === null ? null : { lat: num(lat), lng: num(lng) });

// Three consecutive growing distances is a real wrong-turn signal; one or two is
// just GPS noise or riding around a building.
const AWAY_STREAK_LIMIT = 3;

export default function DeliveryCard({ order, riderPosition, onAdvance }) {
    const pickup = point(order.pickup_lat, order.pickup_lng);
    const dropoff = point(order.delivery_lat, order.delivery_lng);
    // Before pickup the rider rides to the restaurant; after, to the customer.
    const leg = order.status === "OUT_FOR_DELIVERY" ? "DROPOFF" : "PICKUP";
    const target = leg === "PICKUP" ? pickup : dropoff;

    const distanceKm = riderPosition && target ? haversineKm(riderPosition, target) : null;
    const heading = riderPosition && target ? bearingDeg(riderPosition, target) : null;

    const [movingAway, setMovingAway] = useState(false);
    const lastDistance = useRef(null);
    const awayStreak = useRef(0);

    useEffect(() => {
        if (distanceKm === null) return;
        if (lastDistance.current !== null) {
            if (distanceKm > lastDistance.current) awayStreak.current += 1;
            else awayStreak.current = 0;
            setMovingAway(awayStreak.current >= AWAY_STREAK_LIMIT);
        }
        lastDistance.current = distanceKm;
    }, [distanceKm]);

    const next = NEXT[order.status];
    const cash = Number(order.cash_to_collect || 0);
    const mapsUrl = target
        ? `https://www.google.com/maps/dir/?api=1&destination=${target.lat},${target.lng}&travelmode=driving`
        : "https://www.google.com/maps";

    return (
        <Card sx={{ p: 2, mb: 1.5 }}>
            <Stack direction="row" justifyContent="space-between" alignItems="center">
                <Box>
                    <Typography fontWeight={800}>{order.order_code}</Typography>
                    <Typography variant="body2" color="text.secondary">
                        {order.restaurant_name} → {order.guest_name}
                    </Typography>
                </Box>
                <Chip size="small" label={order.status.replace(/_/g, " ")} />
            </Stack>

            {cash > 0 && (
                <Chip size="small" color="warning" sx={{ mt: 1 }}
                      label={`Collect ৳${order.cash_to_collect} cash`} />
            )}

            <Divider sx={{ my: 1 }} />
            <Typography variant="caption" color="text.secondary">
                {leg === "PICKUP" ? "Pick up from / নিতে হবে" : "Deliver to / পৌঁছে দিন"}
            </Typography>
            <Typography variant="body2">
                {leg === "PICKUP" ? order.restaurant_address : order.delivery_address}
            </Typography>

            <List dense sx={{ py: 0 }}>
                {order.items?.map((it) => (
                    <ListItem key={it.id} disableGutters sx={{ py: 0.25 }}>
                        <ListItemText
                            primary={`${it.quantity} × ${it.item_name}`}
                            secondary={(it.selected_options || []).map((o) => o.name).join(", ") || null}
                        />
                        <Typography variant="body2">৳{it.line_total}</Typography>
                    </ListItem>
                ))}
            </List>

            {order.notes && <Alert severity="info" sx={{ py: 0, mb: 1 }}>{order.notes}</Alert>}

            <DeliveryMap riderPosition={riderPosition} pickup={pickup} dropoff={dropoff} leg={leg} />

            {distanceKm !== null && (
                <Stack direction="row" alignItems="center" spacing={1} sx={{ mb: 1 }}>
                    <NavigationIcon sx={{ transform: `rotate(${heading}deg)`, color: "#E8452B" }} />
                    <Typography variant="body2" fontWeight={700}>
                        {distanceKm.toFixed(2)} km to {leg === "PICKUP" ? "pickup" : "drop-off"}
                    </Typography>
                </Stack>
            )}
            {movingAway && (
                <Alert severity="warning" sx={{ mb: 1 }}>
                    You're moving away from the {leg === "PICKUP" ? "restaurant" : "drop-off"} · আপনি দূরে সরে যাচ্ছেন
                </Alert>
            )}

            <Stack direction="row" spacing={1} sx={{ mb: 1 }}>
                <Button size="small" component="a" href={`tel:${order.guest_phone}`}
                        startIcon={<CallIcon />} variant="outlined" fullWidth>
                    Call customer
                </Button>
                <Button size="small" component="a" href={`tel:${order.restaurant_phone}`}
                        startIcon={<CallIcon />} variant="outlined" fullWidth>
                    Call restaurant
                </Button>
            </Stack>
            <Button size="small" component="a" href={mapsUrl} target="_blank" rel="noreferrer"
                    fullWidth sx={{ mb: 1 }}>
                Open in Google Maps
            </Button>

            {next && (
                <Button fullWidth variant="contained" onClick={() => onAdvance(order.id, next[0])}>
                    {next[1]}
                </Button>
            )}
        </Card>
    );
}
```

- [ ] **Step 5: Run the DeliveryCard test to verify it passes**

```bash
cd frontend/ecommerce_inventory && npm test -- --watchAll=false DeliveryCard.test.js
```

Expected: PASS, 6 tests.

- [ ] **Step 6: Use DeliveryCard in the dashboard**

In `frontend/ecommerce_inventory/src/rider/RiderDashboard.js`, add the import:

```javascript
import DeliveryCard from "./DeliveryCard";
```

and replace the whole `{orders.map((o) => { ... })}` block (the inline card, and the now-unused `NEXT` constant at the top of the file) with:

```javascript
                {orders.map((o) => (
                    <DeliveryCard key={o.id} order={o} riderPosition={position} onAdvance={advance} />
                ))}
```

Delete the `NEXT` constant and the now-unused `Divider` / `Chip` imports if ESLint flags them.

- [ ] **Step 7: Write the dashboard test**

Create `frontend/ecommerce_inventory/src/rider/RiderDashboard.test.js`:

```javascript
import { render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import RiderDashboard from "./RiderDashboard";

jest.mock("./DeliveryMap", () => () => <div data-testid="delivery-map" />);
jest.mock("react-toastify", () => ({ toast: { success: jest.fn(), error: jest.fn() } }));

const mockCallApi = jest.fn();
jest.mock("../hooks/APIHandler", () => () => ({ callApi: mockCallApi }));

const me = { name: "Rakib", rider_code: "RD01", total_deliveries: 5, total_earnings: "250.00", is_available: false };
const orders = [{
    id: 1, order_code: "FD1", status: "OUT_FOR_DELIVERY", restaurant_name: "Kacchi Ghor",
    guest_name: "Karim", guest_phone: "018", restaurant_phone: "017",
    delivery_address: "Ujanchar", restaurant_address: "Bazar", total: "340.00",
    payment_method: "COD", cash_to_collect: "340.00", items: [], notes: "",
}];
const earnings = { today: "50.00", lifetime: "250.00", cash_to_collect: "340.00", history: [] };

beforeEach(() => {
    mockCallApi.mockImplementation(({ url }) => {
        if (url === "food/rider/me/") return Promise.resolve({ status: 200, data: { data: me } });
        if (url === "food/rider/orders/") return Promise.resolve({ status: 200, data: { data: orders } });
        if (url === "food/rider/earnings/") return Promise.resolve({ status: 200, data: { data: earnings } });
        return Promise.resolve({ status: 200, data: { data: {} } });
    });
});
afterEach(() => jest.clearAllMocks());

const renderDash = () => render(<MemoryRouter><RiderDashboard /></MemoryRouter>);

describe("RiderDashboard", () => {
    it("shows the rider profile and their assigned delivery", async () => {
        renderDash();
        expect(await screen.findByText("Rakib")).toBeInTheDocument();
        expect(await screen.findByText("FD1")).toBeInTheDocument();
    });

    it("shows earnings totals", async () => {
        renderDash();
        await waitFor(() => expect(screen.getByText("৳250.00")).toBeInTheDocument());
    });

    it("does not heartbeat while the rider is offline", async () => {
        renderDash();
        await screen.findByText("Rakib");
        expect(mockCallApi).not.toHaveBeenCalledWith(
            expect.objectContaining({ url: "food/rider/heartbeat/" }));
    });
});
```

- [ ] **Step 8: Run the full frontend suite**

```bash
cd frontend/ecommerce_inventory && npm test -- --watchAll=false
```

Expected: PASS.

- [ ] **Step 9: Commit**

```bash
git add frontend/ecommerce_inventory/src/rider
git commit -m "feat(rider): delivery card with items, calls, live map and heading check"
```

---

# TRACK 3 — Menu Management

### Task 10: Menu copy endpoint

**Files:**
- Create: `backend/EcommerceInventory/food/services_menu_copy.py`, `food/views_menu_copy.py`
- Modify: `backend/EcommerceInventory/food/urls.py`
- Create: `backend/EcommerceInventory/food/tests/test_menu_copy.py`

**Interfaces:**
- Consumes: `_unique_item_slug(restaurant, name)` from `food/views_vendor.py`.
- Produces:
  - `copy_menu(source, target, item_ids=None, target_category=None, dry_run=False) -> dict` with keys `categories_created`, `categories_merged`, `items_copied`, `items_skipped`, `options_copied`.
  - `POST /api/food/admin/menu/copy/` — body `{source_restaurant, target_restaurant, item_ids?, target_category?}`, query `?dry_run=true`.

- [ ] **Step 1: Write the failing tests**

Create `backend/EcommerceInventory/food/tests/test_menu_copy.py`:

```python
from decimal import Decimal

from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from food.models import (
    Restaurant, FoodCategory, FoodItem, FoodItemOptionGroup, FoodItemOption,
)
from food.services_menu_copy import copy_menu

User = get_user_model()


def auth(c, u):
    c.credentials(HTTP_AUTHORIZATION=f"Bearer {RefreshToken.for_user(u).access_token}")


class MenuCopyServiceTests(TestCase):
    def setUp(self):
        self.src = Restaurant.objects.create(name="Source", slug="source",
                                             status=Restaurant.Status.ACTIVE)
        self.dst = Restaurant.objects.create(name="Target", slug="target",
                                             status=Restaurant.Status.ACTIVE)
        self.cat = FoodCategory.objects.create(restaurant=self.src, name="Rice")
        self.item = FoodItem.objects.create(restaurant=self.src, category_id=self.cat,
                                            name="Kacchi", slug="kacchi", price=Decimal("300"),
                                            tags=["bestseller"], spice_level="Hot",
                                            image="https://cdn.example.com/k.jpg")
        group = FoodItemOptionGroup.objects.create(item=self.item, name="Size", max_select=1)
        FoodItemOption.objects.create(group=group, name="Full", price_delta=Decimal("50"))

    def test_full_copy_reproduces_categories_items_and_options(self):
        result = copy_menu(self.src, self.dst)
        self.assertEqual(result["categories_created"], 1)
        self.assertEqual(result["items_copied"], 1)
        self.assertEqual(result["options_copied"], 1)

        copied = FoodItem.objects.get(restaurant=self.dst, name="Kacchi")
        self.assertEqual(copied.price, Decimal("300"))
        self.assertEqual(copied.tags, ["bestseller"])
        self.assertEqual(copied.image, "https://cdn.example.com/k.jpg")
        self.assertEqual(copied.category_id.name, "Rice")
        self.assertEqual(copied.option_groups.first().options.first().name, "Full")

    def test_rerunning_a_copy_skips_everything(self):
        copy_menu(self.src, self.dst)
        second = copy_menu(self.src, self.dst)
        self.assertEqual(second["items_copied"], 0)
        self.assertEqual(second["items_skipped"], 1)
        self.assertEqual(second["categories_merged"], 1)
        self.assertEqual(FoodItem.objects.filter(restaurant=self.dst, name="Kacchi").count(), 1)

    def test_same_named_category_is_merged_not_duplicated(self):
        FoodCategory.objects.create(restaurant=self.dst, name="Rice")
        result = copy_menu(self.src, self.dst)
        self.assertEqual(result["categories_created"], 0)
        self.assertEqual(result["categories_merged"], 1)
        self.assertEqual(FoodCategory.objects.filter(restaurant=self.dst, name="Rice").count(), 1)

    def test_slug_collision_in_target_is_resolved(self):
        other_cat = FoodCategory.objects.create(restaurant=self.dst, name="Other")
        FoodItem.objects.create(restaurant=self.dst, category_id=other_cat, name="Different",
                                slug="kacchi", price=Decimal("100"))
        copy_menu(self.src, self.dst)
        copied = FoodItem.objects.get(restaurant=self.dst, name="Kacchi")
        self.assertEqual(copied.slug, "kacchi-2")

    def test_dry_run_writes_nothing(self):
        result = copy_menu(self.src, self.dst, dry_run=True)
        self.assertEqual(result["items_copied"], 1)
        self.assertFalse(FoodItem.objects.filter(restaurant=self.dst).exists())
        self.assertFalse(FoodCategory.objects.filter(restaurant=self.dst).exists())

    def test_selective_copy_into_a_chosen_category(self):
        FoodItem.objects.create(restaurant=self.src, category_id=self.cat, name="Biriyani",
                                slug="biriyani", price=Decimal("250"))
        target_cat = FoodCategory.objects.create(restaurant=self.dst, name="Specials")
        result = copy_menu(self.src, self.dst, item_ids=[self.item.id], target_category=target_cat)
        self.assertEqual(result["items_copied"], 1)
        self.assertEqual(FoodItem.objects.get(restaurant=self.dst).category_id, target_cat)
        self.assertFalse(FoodItem.objects.filter(restaurant=self.dst, name="Biriyani").exists())


class MenuCopyAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.admin = User.objects.create(username="adm", email="adm@x.com", role="Admin")
        self.src = Restaurant.objects.create(name="S", slug="s", status=Restaurant.Status.ACTIVE)
        self.dst = Restaurant.objects.create(name="D", slug="d", status=Restaurant.Status.ACTIVE)
        cat = FoodCategory.objects.create(restaurant=self.src, name="Rice")
        FoodItem.objects.create(restaurant=self.src, category_id=cat, name="Kacchi",
                                slug="kacchi", price=Decimal("300"))

    def test_admin_copies_a_whole_menu(self):
        auth(self.client, self.admin)
        res = self.client.post("/api/food/admin/menu/copy/",
                               {"source_restaurant": self.src.id, "target_restaurant": self.dst.id},
                               format="json")
        self.assertEqual(res.status_code, 200, res.content)
        self.assertEqual(res.json()["data"]["items_copied"], 1)
        self.assertTrue(FoodItem.objects.filter(restaurant=self.dst, name="Kacchi").exists())

    def test_dry_run_previews_without_writing(self):
        auth(self.client, self.admin)
        res = self.client.post("/api/food/admin/menu/copy/?dry_run=true",
                               {"source_restaurant": self.src.id, "target_restaurant": self.dst.id},
                               format="json")
        self.assertEqual(res.status_code, 200, res.content)
        self.assertEqual(res.json()["data"]["items_copied"], 1)
        self.assertFalse(FoodItem.objects.filter(restaurant=self.dst).exists())

    def test_copying_a_restaurant_onto_itself_is_rejected(self):
        auth(self.client, self.admin)
        res = self.client.post("/api/food/admin/menu/copy/",
                               {"source_restaurant": self.src.id, "target_restaurant": self.src.id},
                               format="json")
        self.assertEqual(res.status_code, 400)

    def test_unknown_restaurant_is_rejected(self):
        auth(self.client, self.admin)
        res = self.client.post("/api/food/admin/menu/copy/",
                               {"source_restaurant": self.src.id, "target_restaurant": 99999},
                               format="json")
        self.assertEqual(res.status_code, 400)

    def test_non_admin_is_blocked(self):
        cust = User.objects.create(username="c", email="c@x.com", role="Customer")
        auth(self.client, cust)
        res = self.client.post("/api/food/admin/menu/copy/",
                               {"source_restaurant": self.src.id, "target_restaurant": self.dst.id},
                               format="json")
        self.assertEqual(res.status_code, 403)
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd backend/EcommerceInventory && python manage.py test food.tests.test_menu_copy -v 2
```

Expected: FAIL — `ModuleNotFoundError: No module named 'food.services_menu_copy'`.

- [ ] **Step 3: Implement the service**

Create `backend/EcommerceInventory/food/services_menu_copy.py`:

```python
"""Copying a menu from one restaurant to another.

Onboarding a new restaurant usually means retyping a menu that already exists
somewhere in the platform. This copies it instead.

Matching is by name: a category whose name already exists in the target is
merged into, and an item whose name already exists in that target category is
skipped. That makes a re-run a no-op rather than a duplicate, so an admin can
copy again after adding a few dishes to the source.
"""
from django.db import transaction

from food.models import FoodCategory, FoodItem, FoodItemOptionGroup, FoodItemOption
from food.views_vendor import _unique_item_slug

ITEM_FIELDS = [
    "name", "name_bn", "description", "description_bn", "image", "price", "discount_price",
    "prep_minutes", "is_available", "is_veg", "is_featured", "tags", "available_from",
    "available_to", "available_days", "spice_level", "display_order",
]


def _copy_options(source_item, new_item, counters, dry_run):
    for group in source_item.option_groups.all():
        options = list(group.options.all())
        counters["options_copied"] += len(options)
        if dry_run:
            continue
        new_group = FoodItemOptionGroup.objects.create(
            item=new_item, name=group.name, name_bn=group.name_bn,
            min_select=group.min_select, max_select=group.max_select,
            is_required=group.is_required,
        )
        for option in options:
            FoodItemOption.objects.create(
                group=new_group, name=option.name, name_bn=option.name_bn,
                price_delta=option.price_delta, is_default=option.is_default,
                display_order=option.display_order,
            )


def copy_menu(source, target, item_ids=None, target_category=None, dry_run=False):
    """Copy source's menu into target. Returns counts; writes nothing if dry_run.

    item_ids   — copy only these items (a selective copy); None copies everything.
    target_category — force every copied item into this category; None mirrors
                      the source's own category structure.
    """
    counters = {"categories_created": 0, "categories_merged": 0,
                "items_copied": 0, "items_skipped": 0, "options_copied": 0}

    items = FoodItem.objects.filter(restaurant=source).select_related("category_id")
    if item_ids is not None:
        items = items.filter(id__in=item_ids)

    with transaction.atomic():
        # Category name → target category. Built lazily so a dry run can still
        # count creations without writing them.
        resolved = {}

        for item in items:
            if target_category is not None:
                destination = target_category
            else:
                source_name = item.category_id.name
                if source_name not in resolved:
                    existing = FoodCategory.objects.filter(restaurant=target, name=source_name).first()
                    if existing:
                        counters["categories_merged"] += 1
                        resolved[source_name] = existing
                    else:
                        counters["categories_created"] += 1
                        resolved[source_name] = None if dry_run else FoodCategory.objects.create(
                            restaurant=target, name=source_name,
                            name_bn=item.category_id.name_bn,
                            display_order=item.category_id.display_order,
                        )
                destination = resolved[source_name]

            # Same dish already on the target's menu → leave it alone.
            duplicate = FoodItem.objects.filter(restaurant=target, name=item.name)
            if destination is not None:
                duplicate = duplicate.filter(category_id=destination)
            if duplicate.exists():
                counters["items_skipped"] += 1
                continue

            counters["items_copied"] += 1
            if dry_run or destination is None:
                continue

            values = {f: getattr(item, f) for f in ITEM_FIELDS}
            new_item = FoodItem.objects.create(
                restaurant=target, category_id=destination,
                slug=_unique_item_slug(target, item.name), **values,
            )
            _copy_options(item, new_item, counters, dry_run)

        if dry_run:
            transaction.set_rollback(True)

    return counters
```

- [ ] **Step 4: Run the service tests**

```bash
cd backend/EcommerceInventory && python manage.py test food.tests.test_menu_copy.MenuCopyServiceTests -v 2
```

Expected: PASS, 6 tests.

- [ ] **Step 5: Implement the view**

Create `backend/EcommerceInventory/food/views_menu_copy.py`:

```python
"""Admin endpoint for copying one restaurant's menu onto another."""
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.authentication import JWTAuthentication

from core.helpers import renderResponse
from food.models import FoodCategory, Restaurant
from food.permissions import IsPlatformAdmin
from food.services_menu_copy import copy_menu


class AdminMenuCopyView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, IsPlatformAdmin]

    def post(self, request):
        source_id = request.data.get("source_restaurant")
        target_id = request.data.get("target_restaurant")

        source = Restaurant.objects.filter(pk=source_id).first()
        target = Restaurant.objects.filter(pk=target_id).first()
        if not source or not target:
            return renderResponse(
                data={"restaurant": ["Choose an existing source and target restaurant."]},
                message="Validation error", status=400)
        if source.id == target.id:
            return renderResponse(
                data={"target_restaurant": ["Pick a different restaurant to copy into."]},
                message="Validation error", status=400)

        target_category = None
        category_id = request.data.get("target_category")
        if category_id:
            target_category = FoodCategory.objects.filter(pk=category_id, restaurant=target).first()
            if not target_category:
                return renderResponse(
                    data={"target_category": ["That category is not on the target restaurant."]},
                    message="Validation error", status=400)

        item_ids = request.data.get("item_ids")
        if item_ids is not None and not isinstance(item_ids, list):
            return renderResponse(data={"item_ids": ["Expected a list of item ids."]},
                                  message="Validation error", status=400)

        dry_run = request.GET.get("dry_run") == "true"
        result = copy_menu(source, target, item_ids=item_ids,
                           target_category=target_category, dry_run=dry_run)
        message = "Copy preview" if dry_run else "Menu copied"
        return renderResponse(data=result, message=message)
```

- [ ] **Step 6: Register the route**

In `backend/EcommerceInventory/food/urls.py`, add the import:

```python
from food.views_menu_copy import AdminMenuCopyView
```

and the path alongside the other admin paths:

```python
    path("admin/menu/copy/", AdminMenuCopyView.as_view(), name="food_admin_menu_copy"),
```

- [ ] **Step 7: Run the whole module and then the full suite**

```bash
cd backend/EcommerceInventory && python manage.py test food.tests.test_menu_copy -v 2 && python manage.py test food
```

Expected: PASS, 11 tests in the module; full suite green.

- [ ] **Step 8: Commit**

```bash
git add backend/EcommerceInventory/food/services_menu_copy.py backend/EcommerceInventory/food/views_menu_copy.py backend/EcommerceInventory/food/urls.py backend/EcommerceInventory/food/tests/test_menu_copy.py
git commit -m "feat(food): transactional menu copy between restaurants with dry-run preview"
```

---

### Task 11: Item images — upload and thumbnails

**Files:**
- Modify: `frontend/ecommerce_inventory/src/pages/food/FoodMenuManager.js`
- Modify: `frontend/ecommerce_inventory/src/pages/food/FoodMenuManager.test.js`

**Interfaces:**
- Consumes: `POST /api/uploads/` (`core.views.FileUploadViewInS3`) — multipart; it iterates `request.FILES` so any field name works. **It does not use the project envelope**: it responds `{"message": "File uploaded successfully", "urls": ["<url>", ...]}`, so the URL is at `res.data.urls[0]`. `config.API_URL` already ends in `/api/`, so the `callApi` url is `"uploads/"`. `FoodItem.image` stays a `URLField`.
- Produces: nothing consumed by later tasks.

- [ ] **Step 1: Write the failing test**

Append to `frontend/ecommerce_inventory/src/pages/food/FoodMenuManager.test.js`:

```javascript
it("renders a thumbnail for an item that has an image", async () => {
    mockCallApi.mockImplementation(({ url }) => {
        if (url === "food/admin/restaurants/") {
            return Promise.resolve({ status: 200, data: { data: [{ id: 1, name: "R" }] } });
        }
        if (url === "food/admin/categories/") {
            return Promise.resolve({ status: 200, data: { data: [{ id: 5, name: "Rice" }] } });
        }
        if (url === "food/admin/items/") {
            return Promise.resolve({ status: 200, data: { data: [
                { id: 9, name: "Kacchi", category_id: 5, price: "300.00",
                  image: "https://cdn.example.com/k.jpg", tags: [], available_days: [] },
            ] } });
        }
        return Promise.resolve({ status: 200, data: { data: [] } });
    });

    render(<FoodMenuManager />);
    const thumb = await screen.findByAltText("Kacchi");
    expect(thumb).toHaveAttribute("src", "https://cdn.example.com/k.jpg");
});
```

- [ ] **Step 2: Run it to verify it fails**

```bash
cd frontend/ecommerce_inventory && npm test -- --watchAll=false FoodMenuManager.test.js
```

Expected: FAIL — no element with alt text "Kacchi".

- [ ] **Step 3: Implement upload + preview in the dialog**

In `FoodMenuManager.js`, add state near the others:

```javascript
    const [uploading, setUploading] = useState(false);
```

Add the upload handler next to `saveItem`:

```javascript
    // Uploads through the shared /api/uploads/ endpoint (S3 when AWS keys are
    // configured, local media otherwise) and stores the URL it returns — the
    // model field is a URLField, so the file never touches FoodItem directly.
    const uploadImage = async (file) => {
        if (!file) return;
        setUploading(true);
        const form = new FormData();
        form.append("image", file);
        const res = await callApi({
            url: "uploads/", method: "POST", body: form,
            header: { "Content-Type": "multipart/form-data" }, rawError: true, silent: true,
        });
        setUploading(false);
        // This endpoint predates the {data,message} envelope — it answers {message, urls}.
        const url = res?.data?.urls?.[0];
        if (url) setItemDialog((d) => ({ ...d, image: url }));
        else toast.error("Upload failed — paste an image URL instead");
    };
```

Replace the Image URL grid row with an upload row plus preview:

```javascript
                            <Grid item xs={12}>
                                <Stack direction="row" spacing={1} alignItems="flex-start">
                                    {itemDialog.image && (
                                        <Box component="img" src={itemDialog.image} alt="preview"
                                             sx={{ width: 64, height: 64, borderRadius: 1, objectFit: "cover" }} />
                                    )}
                                    <TextField label="Image URL" fullWidth value={itemDialog.image}
                                               onChange={(e) => setItemDialog({ ...itemDialog, image: e.target.value })}
                                               {...errProps("image", "Upload a photo or paste a URL")} />
                                    <Button component="label" variant="outlined" disabled={uploading} sx={{ minWidth: 110 }}>
                                        {uploading ? "Uploading…" : "Upload"}
                                        <input hidden type="file" accept="image/*"
                                               onChange={(e) => uploadImage(e.target.files?.[0])} />
                                    </Button>
                                </Stack>
                            </Grid>
```

- [ ] **Step 4: Add thumbnails to the item rows**

In the items `<Table>`, add a leading cell to each item row rendering the thumbnail (place it as the first `<TableCell>` in the row that currently starts with the item name):

```javascript
                                        <TableCell sx={{ width: 56 }}>
                                            {it.image
                                                ? <Box component="img" src={it.image} alt={it.name}
                                                       sx={{ width: 44, height: 44, borderRadius: 1, objectFit: "cover" }} />
                                                : <Box sx={{ width: 44, height: 44, borderRadius: 1, bgcolor: "grey.200",
                                                             display: "grid", placeItems: "center", fontSize: 18 }}>🍽️</Box>}
                                        </TableCell>
```

Add a matching empty `<TableCell />` to the header row so the columns line up.

- [ ] **Step 5: Run the test to verify it passes**

```bash
cd frontend/ecommerce_inventory && npm test -- --watchAll=false FoodMenuManager.test.js
```

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add frontend/ecommerce_inventory/src/pages/food/FoodMenuManager.js frontend/ecommerce_inventory/src/pages/food/FoodMenuManager.test.js
git commit -m "feat(food): upload item photos and show thumbnails in Menu Management"
```

---

### Task 12: Copy-menu UI

**Files:**
- Create: `frontend/ecommerce_inventory/src/pages/food/CopyMenuDialog.js`
- Create: `frontend/ecommerce_inventory/src/pages/food/CopyMenuDialog.test.js`
- Modify: `frontend/ecommerce_inventory/src/pages/food/FoodMenuManager.js`

**Interfaces:**
- Consumes: `POST food/admin/menu/copy/` and `?dry_run=true` (Task 10); `callApi({rawError:true})` (Task 1).
- Produces: `<CopyMenuDialog open restaurants targetRestaurant selectedItemIds onClose onCopied />`.

- [ ] **Step 1: Write the failing test**

Create `frontend/ecommerce_inventory/src/pages/food/CopyMenuDialog.test.js`:

```javascript
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import CopyMenuDialog from "./CopyMenuDialog";

jest.mock("react-toastify", () => ({ toast: { success: jest.fn(), error: jest.fn() } }));

const mockCallApi = jest.fn();
jest.mock("../../hooks/APIHandler", () => () => ({ callApi: mockCallApi }));

const restaurants = [{ id: 1, name: "Source" }, { id: 2, name: "Target" }];
const preview = { categories_created: 2, categories_merged: 1, items_copied: 12, items_skipped: 3, options_copied: 4 };

beforeEach(() => {
    mockCallApi.mockImplementation(({ params }) =>
        Promise.resolve({ status: 200, data: { data: preview, message: params?.dry_run ? "Copy preview" : "Menu copied" } }));
});
afterEach(() => jest.clearAllMocks());

describe("CopyMenuDialog", () => {
    it("previews the copy before writing anything", async () => {
        render(<CopyMenuDialog open restaurants={restaurants} targetRestaurant={2}
                               selectedItemIds={[]} onClose={jest.fn()} onCopied={jest.fn()} />);
        fireEvent.mouseDown(screen.getByLabelText(/copy menu from/i));
        fireEvent.click(await screen.findByText("Source"));

        await waitFor(() => expect(screen.getByText(/12 items will be copied/i)).toBeInTheDocument());
        expect(screen.getByText(/3 skipped/i)).toBeInTheDocument();
        expect(mockCallApi).toHaveBeenCalledWith(expect.objectContaining({
            url: "food/admin/menu/copy/", params: { dry_run: "true" },
        }));
    });

    it("performs the copy and reports the result", async () => {
        const onCopied = jest.fn();
        render(<CopyMenuDialog open restaurants={restaurants} targetRestaurant={2}
                               selectedItemIds={[]} onClose={jest.fn()} onCopied={onCopied} />);
        fireEvent.mouseDown(screen.getByLabelText(/copy menu from/i));
        fireEvent.click(await screen.findByText("Source"));
        await screen.findByText(/12 items will be copied/i);

        fireEvent.click(screen.getByRole("button", { name: /copy menu/i }));
        await waitFor(() => expect(onCopied).toHaveBeenCalled());
    });
});
```

- [ ] **Step 2: Run it to verify it fails**

```bash
cd frontend/ecommerce_inventory && npm test -- --watchAll=false CopyMenuDialog.test.js
```

Expected: FAIL — module not found.

- [ ] **Step 3: Implement the dialog**

Create `frontend/ecommerce_inventory/src/pages/food/CopyMenuDialog.js`:

```javascript
import { useCallback, useEffect, useState } from "react";
import {
    Dialog, DialogTitle, DialogContent, DialogActions, Button, TextField, MenuItem,
    Alert, Stack, Typography, CircularProgress,
} from "@mui/material";
import { toast } from "react-toastify";
import useApi from "../../hooks/APIHandler";

// Copies another restaurant's menu into the one being edited. Always previews
// first (server-side dry run) so the admin sees how much will be created and how
// much is already there before anything is written.
export default function CopyMenuDialog({ open, restaurants, targetRestaurant, selectedItemIds, onClose, onCopied }) {
    const { callApi } = useApi();
    const [source, setSource] = useState("");
    const [preview, setPreview] = useState(null);
    const [busy, setBusy] = useState(false);

    const selective = selectedItemIds?.length > 0;

    const body = useCallback(() => ({
        source_restaurant: Number(source),
        target_restaurant: Number(targetRestaurant),
        ...(selective ? { item_ids: selectedItemIds } : {}),
    }), [source, targetRestaurant, selective, selectedItemIds]);

    useEffect(() => {
        if (!open || !source) { setPreview(null); return; }
        let cancelled = false;
        (async () => {
            setBusy(true);
            const res = await callApi({
                url: "food/admin/menu/copy/", method: "POST",
                params: { dry_run: "true" }, body: body(), rawError: true, silent: true,
            });
            setBusy(false);
            if (cancelled) return;
            if (res?.status === 200) setPreview(res.data.data);
            else toast.error(res?.data?.message || "Could not preview the copy");
        })();
        return () => { cancelled = true; };
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [open, source]);

    const doCopy = async () => {
        setBusy(true);
        const res = await callApi({
            url: "food/admin/menu/copy/", method: "POST", body: body(), rawError: true, silent: true,
        });
        setBusy(false);
        if (res?.status === 200) {
            const d = res.data.data;
            toast.success(`Copied ${d.items_copied} items (${d.items_skipped} already there)`);
            setSource(""); setPreview(null);
            onCopied();
        } else {
            toast.error(res?.data?.message || "Copy failed");
        }
    };

    return (
        <Dialog open={open} onClose={onClose} maxWidth="xs" fullWidth>
            <DialogTitle>{selective ? `Copy ${selectedItemIds.length} items from…` : "Copy a whole menu"}</DialogTitle>
            <DialogContent>
                <Stack spacing={2} sx={{ mt: 1 }}>
                    <TextField select fullWidth label="Copy menu from" value={source}
                               onChange={(e) => setSource(e.target.value)}>
                        {restaurants.filter((r) => r.id !== Number(targetRestaurant))
                            .map((r) => <MenuItem key={r.id} value={r.id}>{r.name}</MenuItem>)}
                    </TextField>

                    {busy && <CircularProgress size={22} />}

                    {preview && !busy && (
                        <Alert severity="info">
                            <Typography variant="body2">
                                {preview.items_copied} items will be copied, {preview.items_skipped} skipped
                                as duplicates.
                            </Typography>
                            <Typography variant="caption" color="text.secondary">
                                {preview.categories_created} new categories, {preview.categories_merged} merged
                                into existing ones · {preview.options_copied} add-ons.
                            </Typography>
                        </Alert>
                    )}
                </Stack>
            </DialogContent>
            <DialogActions>
                <Button onClick={onClose}>Cancel</Button>
                <Button variant="contained" disabled={!source || busy || !preview} onClick={doCopy}>
                    Copy menu
                </Button>
            </DialogActions>
        </Dialog>
    );
}
```

- [ ] **Step 4: Run the test to verify it passes**

```bash
cd frontend/ecommerce_inventory && npm test -- --watchAll=false CopyMenuDialog.test.js
```

Expected: PASS, 2 tests.

- [ ] **Step 5: Wire it into Menu Management**

In `FoodMenuManager.js`, add the import and state:

```javascript
import CopyMenuDialog from "./CopyMenuDialog";
```

```javascript
    const [copyOpen, setCopyOpen] = useState(false);
    const [selectedItemIds, setSelectedItemIds] = useState([]);
```

Add the trigger button next to the restaurant picker at the top of the page:

```javascript
                <Button variant="outlined" disabled={!restaurant} onClick={() => setCopyOpen(true)}>
                    {selectedItemIds.length > 0 ? `Copy ${selectedItemIds.length} items to…` : "Copy menu from…"}
                </Button>
```

Add a selection checkbox as the first cell of each item row (before the thumbnail cell added in Task 11), importing `Checkbox` from `@mui/material`:

```javascript
                                        <TableCell padding="checkbox">
                                            <Checkbox
                                                checked={selectedItemIds.includes(it.id)}
                                                onChange={(e) => setSelectedItemIds((ids) =>
                                                    e.target.checked ? [...ids, it.id] : ids.filter((x) => x !== it.id))}
                                            />
                                        </TableCell>
```

Add a matching empty header cell, and render the dialog just before the closing `</Box>`:

```javascript
            <CopyMenuDialog
                open={copyOpen}
                restaurants={restaurants}
                targetRestaurant={restaurant}
                selectedItemIds={selectedItemIds}
                onClose={() => setCopyOpen(false)}
                onCopied={() => { setCopyOpen(false); setSelectedItemIds([]); loadMenu(restaurant); }}
            />
```

- [ ] **Step 6: Run the full frontend suite**

```bash
cd frontend/ecommerce_inventory && npm test -- --watchAll=false
```

Expected: PASS.

- [ ] **Step 7: Run the full backend suite one final time**

```bash
cd backend/EcommerceInventory && python manage.py test food
```

Expected: PASS.

- [ ] **Step 8: Commit**

```bash
git add frontend/ecommerce_inventory/src/pages/food
git commit -m "feat(food): copy a whole menu or selected items into another restaurant"
```

---

## Deferred to a later plan

Explicitly out of scope, per the spec:

- Real road routing / turn-by-turn inside the app.
- Customer-visible live rider tracking (the `Rider` location fields make it possible; no public endpoint exposes them here).
- Rider location history or trails.
- Installable PWA packaging for the rider dashboard.
- Vendor-side menu management (`VendorMenu.js`) — unchanged.
