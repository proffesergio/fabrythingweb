# Commerce control center operations

The control center reads `/api/products/admin/` with a platform staff JWT. Its sync and analytics data are real database records or authenticated Google API responses. An unconfigured provider is shown as such; it has no sample success state.

## Setup

Apply the catalog migrations through `0019_products_source_currency` in the target environment using the normal release migration step. Do not point local tests or commands at the live database. Install `backend/EcommerceInventory/requirements.txt` so `google-auth` is available for provider jobs.

Start at least one persistent worker alongside the Django web process:

```sh
cd backend/EcommerceInventory
python manage.py run_sync_jobs --loop --poll-seconds 15
```

For a cron deployment, call `python manage.py run_sync_jobs` once per minute. A manual Run button queues a database record; it does not run the job inside the web request. Inspect `/api/products/admin/sync-runs/` for `QUEUED`, `RUNNING`, `COMPLETED`, `PARTIAL`, or `FAILED`, attempt count, counts, and error summary. Jobs start paused by default. `pause` stops new scheduled work while `resume` makes the next run due. Batch size is limited to 12 and the minimum interval is 15 minutes. One active or queued run is allowed per job. Worker claims use PostgreSQL row locks and a one-hour lease. After a crash, the lease may take that long to expire before recovery; retries stop after three attempts.

## Pricing

`IMPORT` and `PRICE` jobs may carry `pricing_policy`, with `source_currency`, a dated `fx_rate_to_bdt`, `fee_percent`, `target_margin_percent`, `shipping_base_bdt`, `shipping_per_kg_bdt`, and `weight_grams`. The full schema and calculation are in [backend/EcommerceInventory/docs/SYNC_JOBS.md](../backend/EcommerceInventory/docs/SYNC_JOBS.md). Staff must provide a current exchange rate and observed timestamp from their chosen trusted source. This service does not fetch one, guess one, or silently reuse a stale value. A quote fails closed when an FX rate or required weight is invalid. Supplier shipping cost is covered in the item price, independent of any customer delivery fee or free-shipping promotion. Catalog and Merchant prices remain BDT; supplier price and currency are retained separately.

## Google provider configuration

Credentials are environment-only. Set either `GOOGLE_APPLICATION_CREDENTIALS` to the path of a service account JSON file, or `GOOGLE_SERVICE_ACCOUNT_JSON` to the JSON content. Grant that service account the appropriate Google property/account access. Never paste credentials into a job or API payload.

| Job mode | Required environment values | API action |
| --- | --- | --- |
| `MERCHANT` | `GOOGLE_MERCHANT_ACCOUNT_ID`, `GOOGLE_MERCHANT_DATA_SOURCE_ID`, `PUBLIC_STORE_URL` (HTTPS); BDT currency | Submits current product inputs to Merchant API v1, then stores returned external names. Submission is not approval. |
| `ANALYTICS` | `GA4_PROPERTY_ID` | Fetches event counts and per-product ecommerce metrics from GA4 Data API v1beta. |
| `SEARCH_CONSOLE` | `SEARCH_CONSOLE_SITE_URL` (HTTPS URL-prefix or `sc-domain:` property) | Fetches search query clicks and impressions. |

`STORE_CURRENCY` may be omitted or set to `BDT`. Any other value stops Merchant export because there is no verified export conversion rate. The provider status in `/api/products/admin/insights/` is `unconfigured` with missing key names, `empty` when configured but never run, or the most recent run status. A failed run retains an error type; no success is synthesized. Merchant submissions require a public HTTPS image and an active product. Product approval and diagnostics still need review in Merchant Center.
The manual Run action returns `409 Provider unconfigured` with missing key names until configuration is present.

Current API references used for the adapters:

- [Merchant API product input insert](https://developers.google.com/merchant/api/reference/rest/products_v1/accounts.productInputs/insert) and [Merchant API authentication](https://developers.google.com/merchant/api/guides/quickstart/authentication).
- [GA4 Data API runReport](https://developers.google.com/analytics/devguides/reporting/data/v1/rest/v1beta/properties/runReport) and [metric schema](https://developers.google.com/analytics/devguides/reporting/data/v1/api-schema).
- [Search Console searchAnalytics.query](https://developers.google.com/webmaster-tools/v1/searchanalytics/query).

## Local metrics and limits

Inventory velocity and sales heatmap come from confirmed, out-for-delivery, and delivered COD order items in the selected 1–90 day window. GA4 product funnels require ecommerce item events to be instrumented in the site; the API cannot recover events never sent to GA4. Search gaps compare Search Console terms with catalog product name tokens and are directional, not a complete keyword audit. Search Console itself returns top rows subject to its own limits. Supplier imports use public HTTPS hosts, pinned resolved IPs with hostname-checked TLS, no redirects, size limits, and one request per second. The supplier host must match its configured source.
