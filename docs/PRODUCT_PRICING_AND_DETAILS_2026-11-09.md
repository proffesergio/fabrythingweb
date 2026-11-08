# Product pricing, importing, and details

Deployed to production on 2026-11-09. API deployment `dpl_D6pCgFTQvB7JHKhHEGenzusneB6L`; frontend deployment `dpl_3RrkzdJsyVbgvePqFcH9F8kpbZek`. Both health endpoints report a reachable database and no pending migrations. Live delivery configuration confirms BDT70/BDT120.

## Pricing

Computed BDT prices now retain the configured cash markup floor after attractive-price rounding. Cosmetic rounding is capped at the computed markup target, preventing excessive rounding increases. With the default BDT50 floor, a BDT1290 source price becomes BDT1340 rather than BDT1299. Delivery is charged separately and does not count toward product profit. Manual prices and historical orders are unchanged.

For existing imports, first review the dry run:

```sh
python manage.py repair_import_price_floor
python manage.py repair_import_price_floor --apply
```

The command repairs eligible supplier-linked products from their stored source cost and updates matching active variant prices. Custom variant prices are preserved. Discounted products are skipped because their original discounted supplier cost is not stored; refresh them through source price sync. Repeated repairs do not stack markup. The production dry run found zero eligible price increases; no catalog repair was necessary.

## Delivery

The `core.0013_regional_shipping_rates` migration is applied in production. It sets the inside Dhaka rate to BDT70 and adds an outside Dhaka rate of BDT120. Checkout requires a delivery zone, validates inside Dhaka addresses, and calculates the charge on the server. Existing product-specific higher charges and free-delivery promotions still apply.

Paid delivery text is removed from product cards. Product details declare both regional rates. A product with a zero shipping override alone does not imply free delivery; the explicit free-delivery promotion controls that label.

## Import controls

Admins can fetch 6, 12, or 18 detailed candidates per batch and import up to 18 at a time. Cursor pagination preserves items between batches. Source categories, search, source-supported newest sorting, offer filtering, and new-to-store filtering are available. Offer/new-to-store filters apply to the fetched batch; the UI declares that limitation. OpenCart adapters support newest sorting; other suppliers retain their native listing order. Mapped source categories suggest a destination category while preserving manual selection.

## Product details

The Superdesign-assisted layout follows the supplied reference: a large image gallery beside a compact purchase panel, prominent sizes and stock-aware quantity controls, regional delivery information, size-chart units, specifications, reviews, and related products. Loading failures offer retry. Successful additions link directly to the cart. Existing prescription restrictions remain enforced.

Browser checks cover desktop/mobile galleries, quantities, size-chart conversion, add-to-cart totals, delivery declarations, and horizontal overflow. Screenshots: [desktop](screenshots/product-detail-1440.png), [mobile](screenshots/product-detail-390.png). The browser script uses mocked API fixtures, not production transactions.

Superdesign draft: https://p.superdesign.dev/draft/21431b4d-d7af-45fb-9aa5-344601570b8a

The auxiliary 12ui tool failed in its local conversion engine and lacked its bundled browser for alignment checks. Validation used the working browser harness instead. No performance benchmark was taken.

Final verification: 120 catalog backend tests, 53 checkout/shipping backend tests, and 34 frontend tests passed. The frontend production build succeeded, migration drift check reported no changes, and `git diff --check` passed. Desktop (1440px) and mobile (390px) checks also passed against the production build.
