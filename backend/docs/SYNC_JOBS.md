# Catalog sync jobs

All control endpoints are under `/api/products/admin/` and require a platform staff JWT.

- `GET/POST sync-jobs/` lists and creates jobs.
- `GET/PATCH sync-jobs/<id>/` reads and updates a job.
- `POST sync-jobs/<id>/run/`, `/pause/`, `/resume/` enqueue or control it.
- `GET sync-runs/` lists the last 100 audited attempts, including partial batches.
- `GET insights/?days=30` returns local order metrics and the last provider results.

Create `IMPORT` jobs with an enabled `source` ID, `category_path`, and `target_category` ID. Create `PRICE` jobs with a partner source whose `sets_source_url` is true. `MERCHANT`, `ANALYTICS`, and `SEARCH_CONSOLE` jobs use no source. Intervals are 15–10080 minutes, batch sizes 1–12. New jobs start paused unless `is_paused=false` is supplied. A manual run queues work, including for a paused job. Pausing stops future scheduling; it does not cancel a queued or running batch.

Run `python manage.py run_sync_jobs --loop` in one or more persistent worker processes. Each process polls every 15 seconds by default. A one-shot invocation is suitable for cron. PostgreSQL row locks and leases prevent two workers claiming the same run. Attempts retry at most three times with bounded backoff. A stopped worker's lease expires after one hour, long enough for a bounded import with image fetches. Import jobs advance a source listing page cursor; price and Merchant jobs advance a product cursor. At the end, each cursor wraps to the first page or product.

## Pricing policy

`pricing_policy` is optional. An empty object preserves the existing `StoreConfiguration` markup. A policy accepts these keys:

```json
{
  "source_currency": "USD",
  "fx_rate_to_bdt": "120.50",
  "fx_rate_observed_at": "2026-11-02T12:00:00+06:00",
  "fx_max_age_hours": 24,
  "fee_percent": "2",
  "target_margin_percent": "12",
  "shipping_base_bdt": "50",
  "shipping_per_kg_bdt": "25",
  "weight_grams": 500
}
```

The operator supplies the observed FX rate and its timestamp; this app does not fetch or guess an exchange rate. A missing, stale, future-dated, non-finite, or non-positive rate fails the affected quote. A per-kg shipping rule requires a weight. Quotes use Decimal arithmetic and choose the higher of the existing platform markup and a floor that covers supplier cost, supplier shipping cost, payment fee, absolute markup, and target margin. Supplier shipping is included in the item price because customer delivery fees can be waived or shared across a cart; the policy does not change `Products.shipping_fee`. Review the resulting shelf price and delivery fee before enabling a policy. Prices remain BDT in the catalog and Merchant export. The `source_price` and `source_currency` fields retain the raw supplier amount and currency.

## Google integrations

Install `requirements.txt`, and set `GOOGLE_APPLICATION_CREDENTIALS` to a service account JSON **file path**, or `GOOGLE_SERVICE_ACCOUNT_JSON` to the JSON content. Grant the service account access to each Google property/account. Credentials are loaded from the environment at call time and are never saved in sync records. Configure only the jobs you need:

- Merchant API: `GOOGLE_MERCHANT_ACCOUNT_ID`, `GOOGLE_MERCHANT_DATA_SOURCE_ID` (an API data source), `PUBLIC_STORE_URL` (HTTPS), and optionally `STORE_CURRENCY=BDT`. Only BDT prices are exported; setting another currency fails rather than relabeling prices. Merchant runs submit product inputs and record accepted requests; Google processing and approval are separate.
- GA4 Data API: `GA4_PROPERTY_ID`. The worker fetches event counts for the past 30 days using `properties.runReport`.
- Search Console API: `SEARCH_CONSOLE_SITE_URL`, an HTTPS URL-prefix or `sc-domain:` property. The worker fetches query clicks and impressions for the past 30 days.

The insights response marks a provider `unconfigured` if any required setting is missing, `empty` when configured but never run, or the status of its last run. It never substitutes sample analytics for live data. Local inventory velocity and sales heatmap use confirmed or later COD order items; a zero-order store reports `inventory_state: empty`.

Supplier pages are fetched only over HTTPS. Hosts are resolved and public addresses are pinned for TLS connections; redirects and oversized responses are rejected. A source URL must match its configured supplier host. Keep source base URLs restricted to approved suppliers.
