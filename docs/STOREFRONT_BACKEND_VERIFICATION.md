# Storefront discovery backend verification

Verified locally on 2026-11-03 with `DJANGO_SETTINGS_MODULE=config.settings.test` and an isolated SQLite test database. No production database was used.

## Behavior

- The homepage returns up to 12 active new arrivals and up to 16 distinct discovery cards outside the new-arrivals set. Discovery takes recent items across categories before filling remaining slots by recency.
- When `StoreConfiguration.rx_sales_enabled` is false, all homepage product sections and product-detail recommendations exclude prescription-required products. The products become eligible when the switch is enabled.
- Product-detail recommendations return up to 8 active products, ordered by category match, brand match, then recency. The current product is excluded.
- Discovery card assembly skips a product that is deactivated or removed after its ID is selected.

## Checks

From `backend/EcommerceInventory`, using `/tmp/fabrything-discovery-venv/bin/python`:

| Check | Result |
| --- | --- |
| `manage.py test storefront.test_product_discovery catalog.test_sync_jobs catalog.test_price_sync catalog.test_admin_product_import --verbosity 1` | 48 tests passed |
| `manage.py test storefront.test_product_discovery --verbosity 1` after final card assembly change | 5 tests passed |
| `manage.py makemigrations --check --dry-run` | No changes detected |

The test runner emitted a missing `staticfiles/` directory warning. Django system checks found no issues.

Production behavior and cache freshness must be checked after deployment against the live homepage API; these local tests do not establish deployment status.
