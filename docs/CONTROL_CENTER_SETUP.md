# Control center: production setup

This is the operator checklist for the Google providers and sync worker. The [control center operations guide](CONTROL_CENTER.md) describes job behavior; the [sync job reference](../backend/EcommerceInventory/docs/SYNC_JOBS.md) has the full pricing policy schema. Keep provider credentials out of job payloads and this repository; dated exchange rates belong in the job's pricing policy.

## 1. Deploy the worker and database changes

Production uses the Vercel projects **fabrythingapi** (Django API) and **fabrythingweb** (frontend), backed by Neon PostgreSQL. The API deployment installs `backend/EcommerceInventory/requirements.txt` and runs all migrations through its production build command. Catalog migrations through `0019_products_source_currency` were applied successfully on 2026-11-02.

The `render.yaml` web Blueprint is legacy and does not provision a sync worker. Add a separate persistent worker on Render, Railway, or an existing VPS using the same released code, Neon database, Django production settings, and provider environment as the API. The infinite worker loop must run on that worker host, not inside a Vercel HTTP function: [Vercel functions have bounded execution durations](https://vercel.com/docs/functions/runtimes). From `backend/EcommerceInventory`, its command is:

```sh
python manage.py run_sync_jobs --loop --poll-seconds 15
```

For cron, run `python manage.py run_sync_jobs` once per minute instead. The web request only queues a run. Create provider jobs through `/api/products/admin/sync-jobs/` with a platform staff JWT; jobs start paused by default. After configuration, resume or manually run them and inspect `/api/products/admin/sync-runs/` and `/api/products/admin/insights/` for actual results. A submitted Merchant product still requires Google processing and approval.

For a worker host, install with `pip install -r requirements.txt`, use Python 3.12, and set `DJANGO_SETTINGS_MODULE=config.settings.prod`. Copy the existing backend `SECRET_KEY`, database connection variables (`DATABASE_HOST`, `DATABASE_NAME`, `DATABASE_USER`, `DATABASE_PASSWORD`, `DATABASE_PORT`, `DATABASE_SSLMODE=require`), and the provider settings below into its private environment. Do not replace the existing database or rotate secrets as part of this setup. The Vercel API and worker must both receive the Google configuration. See [backend environment settings](../backend/EcommerceInventory/.env.example) for names; placeholder values are not production credentials.

## 2. Create and store the Google service account

In a Google Cloud project, enable **Merchant API**, **Google Analytics Data API**, and **Google Search Console API** for the providers you will use. Create a service account and a JSON key; keep its `client_email` for the access grants below. Google's [Merchant service-account guide](https://developers.google.com/merchant/api/guides/authorization/access-your-account), [Analytics Data API quickstart](https://developers.google.com/analytics/devguides/reporting/data/v1/quickstart), and [Search Console authorization guide](https://developers.google.com/webmaster-tools/v1/how-tos/authorizing) cover the Cloud steps.

Set exactly one credential source **server side** on both the web and worker services:

For the live API, open the Vercel dashboard → **fabrythingapi → Settings → Environment Variables**, select **Production**, and add the values below. Redeploy **fabrythingapi** after saving them. Do not put them in **fabrythingweb**. Copy the same values into the worker host's secret settings.

```dotenv
GOOGLE_SERVICE_ACCOUNT_JSON=<complete JSON key, entered as a secret>
GOOGLE_MERCHANT_ACCOUNT_ID=<numeric account ID>
GOOGLE_MERCHANT_DATA_SOURCE_ID=<numeric primary API source ID>
PUBLIC_STORE_URL=https://www.fabrything.com
STORE_CURRENCY=BDT
GA4_PROPERTY_ID=<numeric GA4 property ID>
SEARCH_CONSOLE_SITE_URL=sc-domain:fabrything.com
```

Use the exact Search Console property you actually verified; the domain example above does not create or verify a property. You may configure one provider at a time. To have the credentials installed by the engineering assistant, save the JSON key in a private local file and provide only its absolute path, plus the non-secret provider IDs and chosen worker host. Do not paste the private key into chat.

| Environment variable | Value |
| --- | --- |
| `GOOGLE_SERVICE_ACCOUNT_JSON` | Complete JSON key content, stored as a secret environment value. This is simplest where the platform has no durable private file mount. |
| `GOOGLE_APPLICATION_CREDENTIALS` | Absolute path to a privately mounted JSON key file readable by the service. This code reads the file at that path; the variable is not the JSON itself. |

If both are set, this adapter uses the file path. Never put the JSON in frontend variables, the database, a sync job, logs, or Git. Grant the same `client_email` access separately to each Google account or property below. Environment presence only marks a provider configured; it does not verify permissions.

## 3. Merchant Center products

1. In Merchant Center, copy the **numeric Merchant Center account ID**. Add the service-account email under **Settings → Access and services → People and access**. Google says service accounts need **Admin** access for account management; complete [Merchant API developer registration](https://developers.google.com/merchant/api/guides/quickstart/direct-api-calls) if the account has not already done so. [Access instructions](https://developers.google.com/merchant/api/guides/authorization/access-your-account).
2. Create or choose a **primary product API data source** for that account. Record its numeric `dataSourceId` from `accounts/{ACCOUNT_ID}/dataSources/{DATASOURCE_ID}`; a file, Sheets, supplemental, or UI-only source is unsuitable. This adapter sends `feedLabel=BD` and `contentLanguage=en`, so a restricted source must accept **BD / en**. [Create an API source](https://developers.google.com/merchant/api/guides/data-sources/api-sources) · [List sources](https://developers.google.com/merchant/api/guides/data-sources/view-sources).
3. Set `GOOGLE_MERCHANT_ACCOUNT_ID`, `GOOGLE_MERCHANT_DATA_SOURCE_ID`, and `PUBLIC_STORE_URL` (public HTTPS storefront origin). Leave `STORE_CURRENCY` unset or set it to `BDT`; other values fail. Products need an active sellable variant, one common variant price, a public HTTPS image, and a reachable product URL. Review feed diagnostics and approval in Merchant Center after a run.

## 4. GA4 reports

1. In GA4 **Admin → Property details**, copy the **numeric property ID**, not the `G-...` measurement ID. Enable the Analytics Data API in the service account's Cloud project. Give its email **Viewer** access to that GA4 property in **Admin → Property access management**. [GA4 user access](https://support.google.com/analytics/answer/9305788) · [Data API setup](https://developers.google.com/analytics/devguides/reporting/data/v1/quickstart).
2. Set `GA4_PROPERTY_ID` to that numeric ID. This worker reads event counts and item metrics through `runReport`; it does not install tracking. Instrument and verify `view_item`, `add_to_cart`, `begin_checkout`, and `purchase` with an `items` array containing stable `item_id` and `item_name` before expecting a meaningful funnel. An empty report cannot recover events never sent. [GA4 ecommerce event guide](https://developers.google.com/analytics/devguides/collection/ga4/ecommerce).

## 5. Search Console queries

1. Verify the storefront in Search Console as either an HTTPS **URL-prefix property** or a **Domain property**. In **Settings → Users and permissions**, add the service-account email with **Full** access. Ownership is not required for this read-only query integration. See [Google's permission guide](https://support.google.com/webmasters/answer/7687615) and [API access overview](https://developers.google.com/webmaster-tools/about). Enable the Search Console API in the Cloud project.
2. Set `SEARCH_CONSOLE_SITE_URL` to the **exact property identifier**: for example `https://example.com/` for a URL prefix (including its trailing slash, path, and HTTPS scheme as registered), or `sc-domain:example.com` for a Domain property. The worker reads search query clicks and impressions with the read-only scope. [Search Analytics API](https://developers.google.com/webmaster-tools/v1/searchanalytics/query).

## 6. Import and price jobs: dated FX policy

For an `IMPORT` or `PRICE` job that converts supplier currency, supply `pricing_policy.source_currency`, `fx_rate_to_bdt`, and an ISO 8601 `fx_rate_observed_at` with timezone. Set `fx_max_age_hours` according to the team's refresh cadence; update the rate and observation time from a trusted source before it expires. The application does not fetch an FX rate. A missing, stale, future-dated, invalid, or non-positive rate fails the affected quote. If using `shipping_per_kg_bdt`, also provide `weight_grams`; review supplier shipping, fees, target margin, final BDT shelf price, and customer delivery charge before resuming a job. See the [policy example and formula](../backend/EcommerceInventory/docs/SYNC_JOBS.md#pricing-policy).
