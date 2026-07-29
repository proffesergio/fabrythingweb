# Per-product shipping fee and the free-shipping promo

Products can now carry their own shipping fee, plus a separate `free_shipping`
promo flag, both shown to customers and used to work out what an order is
actually charged for delivery. This document explains the rule the owner
chose, how null and 0 differ, what `free_shipping` adds on top of that
(including mixed carts), how to set both one product at a time or in bulk
from the admin, and where customers see them.

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
over everything below it, including the promo rule in the next section.

### Worked examples

| Cart | Result | Why |
| --- | --- | --- |
| A ৳60-flat shirt (no fee) + a monitor with a ৳250 fee | **৳250** | max(60, 250) |
| Two products, neither with a fee | **৳60** (the flat rate) | max(60) — unchanged from before this feature |
| One product with a ৳30 fee, flat rate ৳60 | **৳60** | max(60, 30) — the flat rate is always the floor, a lower per-product fee can't undercut it |
| Any cart whose subtotal meets `free_shipping_threshold` | **৳0** | the threshold wins over everything above |

The rule lives in exactly one place: `StoreConfiguration.shipping_for(subtotal,
product_shipping_fees, free_shipping_flags)` in
`backend/EcommerceInventory/core/models.py`. The COD checkout
(`orders/services.py::place_cod_order`) is the only caller — there is no
second copy of this logic anywhere in the storefront views.

## The free-shipping promo: a real flag, not an overloaded `0`

The owner's actual need, verbatim: *"sometimes i'd want to apply free
shipping on some special on demand products or any promoted product which I
will get special price from the market, so free shipping as a promo on true
per-product is kind of a good option."*

Setting `shipping_fee: 0` does **not** make an item ship free on its own —
the flat rate is always the floor in the max() above, so a cart containing
only a ৳0-fee product still charges the store's flat rate (see the worked
examples above). `Products.free_shipping` (a plain `BooleanField`, default
`False`) is the explicit way to say "this product's shipping is waived,"
independent of whatever `shipping_fee` holds:

1. **The free-shipping-threshold check still runs first and wins**, exactly
   as above — a qualifying subtotal is ৳0 regardless of any promo flag.
2. **If every item in the cart is a `free_shipping` product, shipping is
   ৳0** — a cart made up entirely of promo items ships free even though the
   flat rate would otherwise apply.
3. **In a mixed cart** (some promo items, some not), the promo items are
   **excluded from the max() entirely** — shipping is
   `max(fixed_shipping_rate, every non-null shipping_fee among the *non-promo*
   items)`. A free-shipping shirt must never make a ৳250 monitor ship for
   free, and it must never drag the charge down below what the non-promo
   items would already cost either way.
4. `shipping_fee == 0` on a product that is **not** `free_shipping` keeps its
   original meaning unchanged — a real candidate in the max() that just
   rarely wins, since the flat rate floors it. `free_shipping` is the only
   field that actually waives shipping.

### Worked examples (the promo flag)

| Cart | Result | Why |
| --- | --- | --- |
| One `free_shipping` product | **৳0** | every item in the cart is promo'd |
| Two `free_shipping` products | **৳0** | same rule, still every item |
| A `free_shipping` shirt + a monitor with a ৳250 fee | **৳250** | the shirt is excluded from the max(); max(60, 250) over the remaining (non-promo) item |
| A `free_shipping` shirt + a normal product with no fee | **৳60** (the flat rate) | the shirt is excluded; nothing else is left but the flat rate floor |
| A cart with no promo items at all | unchanged from the table above | `free_shipping` never applies to a cart that doesn't contain one |
| Any cart (promo or not) whose subtotal meets `free_shipping_threshold` | **৳0** | the threshold still wins over the promo rule too |

`shipping_for`'s `free_shipping_flags` parameter is an optional list parallel
to `product_shipping_fees`, one boolean per cart line — `orders/services.py`
builds both lists from `variant.product.shipping_fee` /
`variant.product.free_shipping` for every line in the order.

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

## Setting fees (and the promo flag) from the admin

**All Products** (`/admin/products`, `ManageProducts.js`) has a **Shipping**
column with two independent controls, inline-editable exactly like
Price/Discount/Stock:

- A **fee** text field — type a number and save to set that product's fee;
  clear it back to blank and save to reset it to `null` ("use the store
  rate"; the placeholder reads "store rate" when empty); type `0` and save
  to make that product's *fee* explicitly zero (still not the same as the
  promo flag below — see the "not the same thing" section above).
- A **Free shipping** checkbox — a toggle, not a number, because this is a
  yes/no promo flag. Checking it sets `Products.free_shipping = true` for
  that product; the fee field is disabled while it's checked (the promo
  flag is what governs shipping now, so there's nothing for a fee to
  override). A row with the flag on shows a green "Free" chip instead of the
  fee in read-only contexts (e.g. the product picker).

This calls `PATCH /api/products/admin/<pk>/quick-update/` with
`{"shipping_fee": ...}` and/or `{"free_shipping": true|false}`, same
authorization (`isPlatformScope` — Super Admin or a domain-root user) and the
same `field_errors` validation shape as the existing price/stock fields.
Negative fees are rejected with a 400; `free_shipping` must be a real
boolean (a 400 if it isn't).

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
how many rows actually changed. The dialog has a **Shipping fee** number
field (as before) plus a **Free shipping promo** selector with three states
— "Don't change" (the default — a bulk selection mixes products with
different current flag values, so there's no single current value to show a
checkbox against), "Mark as free-shipping promo", and "Remove free-shipping
promo". This is how the owner "promotes a whole category" — pick a category,
leave the fee blank, choose "Mark as free-shipping promo". This calls the
`POST /api/products/admin/shipping-fee/bulk/` endpoint:

```json
{"shipping_fee": 250, "product_ids": [12, 45, 90]}
```
or
```json
{"shipping_fee": null, "free_shipping": true, "category": "fashion"}
```

`free_shipping` (bool) can be sent alone, alongside `shipping_fee`, or
omitted entirely (in which case it isn't touched) — at least one of
`shipping_fee` / `free_shipping` must be present in the body. Same
`isPlatformScope` authorization and `field_errors` shape as quick-update.
Negative fees and a non-boolean `free_shipping` are both rejected. Exactly
one of `product_ids` / `category` must be given. The match is capped at 2000
rows per call (`AdminBulkShippingFeeView.MAX_BATCH`) — a request matching
more than that is rejected with a message asking you to narrow the
selection, so a fat-fingered top-level category can't silently rewrite the
entire catalog in one call.

## Where customers see it

- **Product card** (`ProductCard.js`) — a small caption under the price:
  "+৳250 delivery" normally, or a bold, brand-green **"Free delivery"** when
  the product is a `free_shipping` promo item *or* its fee is explicitly 0.
  The two texts share the same line and are mutually exclusive by
  construction — "Free delivery" always wins and the delivery-fee text is
  never shown alongside it. A product with no fee and no promo flag shows
  the store's standard rate ("+৳60 delivery") instead, so the customer
  always knows the delivery cost before opening the product. This is
  deliberately compact so it doesn't push the card back to the height the
  recent mobile-card fix bought back.
- **Product detail page** (`ProductDetail.js`) — a more prominent labeled box
  with a delivery icon, right under the price: "Delivery: ৳250" normally, or
  a highlighted "Free delivery" state (same box, different content) when
  `free_shipping` is set *or* the fee is explicitly 0. Same fallback rule —
  never blank, and the two states never show together since it's one box.

Both read `effective_shipping_fee` and `free_shipping` from the storefront
product list/detail serializers (`storefront/serializers.py`).
`effective_shipping_fee` is a resolved number that is always present: the
product's own `shipping_fee` when set, otherwise
`StoreConfiguration.fixed_shipping_rate` — it does **not** itself account for
the promo flag, so the frontend combines the two (`free_shipping ||
effective_shipping_fee === 0`) to decide whether to show "Free delivery" vs.
the resolved fee. The raw `shipping_fee` field (which can be `null`) is also
exposed on both endpoints, in case a future UI needs to distinguish
"explicitly free" from "no override" itself rather than relying on the
pre-resolved value.
