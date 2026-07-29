# Per-product shipping fee

Products can now carry their own shipping fee, shown to customers and used
to work out what an order is actually charged for delivery. This document
explains the rule the owner chose, how null and 0 differ, how to set fees
one product at a time or in bulk from the admin, and where customers see it.

## The rule: highest fee wins, flat rate is the floor

**Order shipping = the highest per-product shipping fee among the items in
the cart**, because it's one delivery trip and the bulkiest/costliest item to
ship sets the cost. The store's flat rate (`core.models.StoreConfiguration.
fixed_shipping_rate`, default ৳60) is always in that comparison too, as a
floor — an item with no override, or one that ships free, never pulls the
order shipping *below* the store rate on its own.

```
shipping = max(fixed_shipping_rate, every per-product shipping_fee in the cart)
```

Free-shipping-threshold (`free_shipping_threshold`), when the cart subtotal
qualifies, still overrides all of this to ৳0 — that check runs first and wins
over the max() rule, exactly as it did before this feature.

### Worked examples

| Cart | Result | Why |
| --- | --- | --- |
| A ৳60-flat shirt (no fee) + a monitor with a ৳250 fee | **৳250** | max(60, 250) |
| Two products, neither with a fee | **৳60** (the flat rate) | max(60) — unchanged from before this feature |
| One product with a ৳30 fee, flat rate ৳60 | **৳60** | max(60, 30) — the flat rate is always the floor, a lower per-product fee can't undercut it |
| Any cart whose subtotal meets `free_shipping_threshold` | **৳0** | the threshold wins over everything above |

The rule lives in exactly one place: `StoreConfiguration.shipping_for(subtotal,
product_shipping_fees)` in `backend/EcommerceInventory/core/models.py`. The
COD checkout (`orders/services.py::place_cod_order`) is the only caller —
there is no second copy of this logic anywhere in the storefront views.

## `null` vs an explicit `0` — not the same thing

`Products.shipping_fee` is a nullable decimal:

- **`null` (the default)** — "use the store's flat rate." The product has no
  opinion; it doesn't add a candidate to the max() above at all.
- **`0` (explicit)** — "this specific product ships free." It's a real, valid
  candidate in the max() above (it just rarely wins, since the flat rate is
  the floor) — the important difference is what the *customer sees*: a
  product with `shipping_fee: 0` displays "Free delivery"; a product with
  `shipping_fee: null` displays the store's standard rate instead.

Both the admin quick-update endpoint and the bulk endpoint preserve this
distinction — sending `shipping_fee: null` clears a product back to "use the
store rate," sending `shipping_fee: 0` sets it to free, and the two are never
conflated (a naive `if product.shipping_fee:` truthy check would wrongly
treat 0 the same as missing — the code deliberately uses `is not None`
everywhere this field is read).

## Setting fees from the admin

**All Products** (`/admin/products`, `ManageProducts.js`) has a **Shipping**
column, inline-editable exactly like Price/Discount/Stock:

- Type a number and save — sets that product's fee.
- Clear the field back to blank and save — resets it to `null` ("use the
  store rate"); the field's placeholder reads "store rate" when empty.
- Type `0` and save — makes that product free to ship.

This calls `PATCH /api/products/admin/<pk>/quick-update/` with
`{"shipping_fee": ...}`, same authorization (`isPlatformScope` — Super Admin
or a domain-root user) and the same `field_errors` validation shape as the
existing price/stock fields. Negative fees are rejected with a 400.

### Bulk: apply to many products at once

The **Bulk shipping fee** button (next to Sync prices / Add Product) opens a
dialog with two ways to target products, depending on what's active on the
page:

1. **Selected rows** — check the boxes on the current page's rows (a
   header checkbox selects/clears the whole page) and the dialog targets
   exactly those products.
2. **The active category filter** — with nothing checked, but a category
   chosen in the Category dropdown, the dialog targets every product in that
   category **and its whole subtree** (a 3-level category like `fashion >
   Men > T-shirts` selected at the `fashion` level reaches every leaf below
   it, via the same `catalog.category_tree.descendant_category_ids` walk the
   storefront/admin category filters already use — not a second traversal).

Either way, the dialog shows a confirmation count ("Apply to N selected
products" / "N products in `<category>`") before you commit, and reports back
how many rows actually changed. This calls the new
`POST /api/products/admin/shipping-fee/bulk/` endpoint:

```json
{"shipping_fee": 250, "product_ids": [12, 45, 90]}
```
or
```json
{"shipping_fee": null, "category": "fashion"}
```

Same `isPlatformScope` authorization and `field_errors` shape as
quick-update. Negative fees are rejected. Exactly one of `product_ids` /
`category` must be given. The match is capped at 2000 rows per call
(`AdminBulkShippingFeeView.MAX_BATCH`) — a request matching more than that is
rejected with a message asking you to narrow the selection, so a fat-fingered
top-level category can't silently rewrite the entire catalog in one call.

## Where customers see it

- **Product card** (`ProductCard.js`) — a small, quiet caption under the
  price: "+৳250 delivery", or "Free delivery" when the fee is 0. It never
  shows nothing — a product with no fee set shows the store's standard rate
  ("+৳60 delivery") instead, so the customer always knows the delivery cost
  before opening the product. This is deliberately compact so it doesn't
  push the card back to the height the recent mobile-card fix bought back.
- **Product detail page** (`ProductDetail.js`) — a more prominent labeled box
  with a delivery icon, right under the price: "Delivery: ৳250", or a
  highlighted "Free delivery" state when the fee is 0. Same fallback rule —
  never blank.

Both read `effective_shipping_fee` from the storefront product list/detail
serializers (`storefront/serializers.py`) — a resolved number that is always
present: the product's own `shipping_fee` when set, otherwise
`StoreConfiguration.fixed_shipping_rate`. The raw `shipping_fee` field (which
can be `null`) is also exposed on both endpoints, in case a future UI needs
to distinguish "explicitly free" from "no override" itself rather than
relying on the pre-resolved value.
