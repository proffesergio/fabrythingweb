# Cloudflare DNS for fabrything.com (Vercel)

Status checked 2026-11-02 with the authenticated Cloudflare and Vercel CLIs:

- `fabrything.com` and `www.fabrything.com` both verify as
  `configured_correctly` and serve the Vercel deployment through Cloudflare.
  `https://www.fabrything.com/` returns `200`; the apex returns the expected
  `308` redirect.
- The Django API is live at `https://fabrythingapi.vercel.app` and needs no
  Cloudflare record.
- `https://www.fabrything.com/sitemap.xml` returns the API-generated sitemap
  (521 URLs: products + articles), not the old static file.
- `media.fabrything.com` is an active R2 custom domain on the
  `fabrything-media` bucket (SSL and ownership `active`), and an existing
  object returns `200`.

**No DNS change is required.** The current proxied A records work and both
domains are verified. The steps below are optional, only for switching to
Vercel's recommended DNS-only layout.

## Why the `www` CNAME cannot be added

The zone already has two A records at `www`:

| Type | Name | Content | Proxy |
| --- | --- | --- | --- |
| A | `www` | `64.29.17.65` | Proxied |
| A | `www` | `64.29.17.1` | Proxied |

DNS forbids a CNAME from coexisting with any other record at the same name, so
Cloudflare rejects:

```
CNAME  www  d42d80059ff18bba.vercel-dns-017.com
```

with `A CNAME record with that host already exists` / `Record already exists`.
**Delete both `www` A records first, then add the CNAME.**

Also note: a CNAME with the orange cloud (proxied) resolves to Cloudflare IPs,
not the Vercel target. Vercel's HTTP challenge can still pass, but its dashboard
may show an invalid configuration. Use **DNS only (grey cloud)** for records
that point at Vercel.

## Option A - keep the current working setup (no change)

The proxied A records already work and Vercel verifies both domains. Keep this
if you want Cloudflare's WAF/caching in front of Vercel. Trade-offs: double CDN,
Cloudflare's request/upload limits, and Vercel sees Cloudflare's IPs rather than
the visitor's unless you forward `CF-Connecting-IP`.

## Option B - Vercel-recommended DNS-only records

Do this only if you want Vercel to terminate TLS directly.

- [ ] In Cloudflare > **fabrything.com** > **DNS** > **Records**, delete:
  - `www` A `64.29.17.65`
  - `www` A `64.29.17.1`
- [ ] Add: `CNAME | www | d42d80059ff18bba.vercel-dns-017.com | DNS only`
- [ ] Edit: `A | @ | 216.198.79.1 | DNS only`
- [ ] Edit the `_domainconnect` CNAME to `_domainconnect.vercel-dns.com` to
      **DNS only** (or delete it if you do not use Vercel Domain Connect).
- [ ] Leave all MX, TXT (SPF/DKIM/Google verification), CAA and `media`
      records unchanged. Do not change nameservers.
- [ ] Verify:
      `vercel domains verify fabrything.com`
      `vercel domains verify www.fabrything.com`
      `curl -I https://www.fabrything.com`
- [ ] Wait a few minutes for DNS caches, then confirm the Vercel Domains page
      shows both domains as valid.

## Record audit (from `fabrything.com.txt`)

| Record | Current value | Verdict |
| --- | --- | --- |
| `@` A | `216.198.79.1`, proxied | Vercel anycast IP; works. Set DNS only for Option B. |
| `www` A | `64.29.17.65`, `64.29.17.1`, proxied | Vercel anycast IPs; works. Replace with the CNAME for Option B. |
| `_domainconnect` CNAME | `_domainconnect.vercel-dns.com`, proxied | Harmless unless you use Vercel Domain Connect. Set DNS only or remove if desired. |
| `media` CNAME | `public.r2.dev`, proxied | Works: `media.fabrything.com` is an active R2 custom domain on `fabrything-media`. Keep. |
| CAA | `sectigo.com`, `pki.goog`, `letsencrypt.org` | Covers Vercel (Let's Encrypt) and Cloudflare. No change. |
| MX | Cloudflare Email Routing (`route1-3.mx.cloudflare.net`) | Preserve. |
| TXT | SPF `include:_spf.mx.cloudflare.net`, DKIM, Google verification | Preserve. |
| `_dmarc` TXT | Missing | Optional; add `v=DMARC1; p=none; rua=mailto:...` for reporting. |

## R2 media host

Verified working; no action needed.

- `cf r2 buckets domains custom list --bucket-name fabrything-media` shows
  `media.fabrything.com` attached with SSL and ownership `active`.
- `https://media.fabrything.com/nobleseek-news-media/Screenshot%202026-10-01%20145650.png`
  returns `200`.
- The bucket's managed public hostname is
  `pub-d68774219ecc4ef8801ba16343cf4a76.r2.dev` (from
  `cf r2 buckets domains managed list`). `https://public.r2.dev/` is not that
  hostname, so its `500` response is expected and does not indicate a problem.

Keep the proxied `media` CNAME. If R2 is ever removed, unset the `AWS_S3_*`
environment variables in Vercel so uploads fall back to DB-backed
`/api/media/<sha256>/` URLs.

## Related

- Vercel backend project: `fabrythingapi`, root directory
  `backend`, Git auto-deploy enabled for `main`.
- Frontend project: `fabrythingweb`, root directory
  `frontend`, Git auto-deploy enabled for `main`.
- Pushing to `main` triggers both Vercel projects; no GitHub Actions deploy
  workflow is required.
