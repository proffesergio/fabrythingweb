# Production check — 2026-11-03 (Asia/Dhaka)

Read-only check before the storefront discovery update. No DNS, deployment, or production data was changed by this check.

| Check | Result |
| --- | --- |
| `https://fabrything.com/` | HTTP 308 to `https://www.fabrything.com/`; destination HTTP 200 over HTTPS. |
| `https://www.fabrything.com/`, `/shop`, `/food` | HTTP 200. |
| Direct `https://fabrythingapi.vercel.app/api/health/` and proxied `https://www.fabrything.com/api/health/` | Both HTTP 200 with `status: ok`, `database: reachable`, and `pending_migrations: []`. |
| `https://www.fabrything.com/api/store/products/` | HTTP 200; public feed reports 499 products. The separate admin `/api/products/` endpoint returns the expected HTTP 401 without credentials. |
| `https://www.fabrything.com/sitemap.xml` | HTTP 200, XML; 521 URLs with `www.fabrything.com` canonical locations. |
| Sample product image from the public feed | GET returned HTTP 200, `image/jpeg`, 18,394 bytes from the API media route. |
| DNS | Apex and `www` resolve to Cloudflare proxy addresses `104.21.46.202` and `172.67.141.174`; authoritative nameservers are `lily.ns.cloudflare.com` and `wesley.ns.cloudflare.com`. |
| Vercel | Frontend production deployment `dpl_8apcqQxB3ssDqn2NsPpmqbx71Sf5` and API production deployment `dpl_Cm7Pb7p2mm2JTyjeHdcwVd1Hz3Lz` are Ready. Frontend aliases include apex and `www`; API alias is `fabrythingapi.vercel.app`. |

`vercel domains inspect` displays Vercel's intended nameservers as different from the current Cloudflare nameservers. This reflects the existing Cloudflare-managed DNS setup; the domain routes and Vercel aliases above are functioning. A media HEAD request returns 405 because the route allows GET; the GET check passed.

This initial checkpoint is an HTTP and configuration smoke check. It does not cover browser interaction, customer checkout, or authenticated admin actions.

## After API discovery release

API production deployment `dpl_5Y716VeysyDzkqLLmsXWmYfA33X5` was Ready and aliased to `fabrythingapi.vercel.app` when checked. Direct and `www`-proxied `/api/health/` both returned HTTP 200 with a reachable database and no pending migrations.

The `www`-proxied `/api/store/homepage/` returned HTTP 200 with 12 `new_arrivals` and 16 distinct `discover_products`; their product IDs do not overlap. Every discovery item has `requires_prescription: false`. The detail endpoint for discovery product `mens-premium-sports-active-wear-t-shirt-kick-off` returned HTTP 200 with 8 distinct related products, excluded the current product, and reported `requires_prescription: false` for every related item. Public serializers do not expose an active-status field, so inactive exclusion was checked against the deployed code path's `status='ACTIVE'` queryset filter and the focused backend tests rather than inferred from JSON alone.

The frontend release had not occurred at this checkpoint; the browser and domain checks above still describe the preceding frontend deployment.

## Final check after frontend release

Frontend production deployment `dpl_7xcuNBtuWZVGwyH7L2x4xsAGg5kB` was Ready and carried the `fabrything.com`, `www.fabrything.com`, and `fabrythingweb.vercel.app` aliases. API deployment `dpl_5Y716VeysyDzkqLLmsXWmYfA33X5` remained Ready and aliased to `fabrythingapi.vercel.app`.

The apex returned HTTP 308 to `https://www.fabrything.com/`, which returned HTTP 200. The `www` home page, `/shop`, and the discovery product page `/product/mens-premium-sports-active-wear-t-shirt-kick-off` each returned HTTP 200. Direct API and `www`-proxied `/api/health/` each returned HTTP 200 with `status: ok`, `database: reachable`, and `pending_migrations: []`. The sitemap returned HTTP 200 `application/xml` with 521 URLs, all under the `www` canonical origin, including the checked product. A sample public-feed image GET returned HTTP 200 `image/jpeg` (18,394 bytes).

These are read-only HTTP and Vercel checks. Browser interactions and checkout are outside this document's check scope.
