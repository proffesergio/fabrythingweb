# NobleSeek by Fabrything — Setup & Ops

Trends-driven Bangla news desk: `/nobleseek` listing + `/nobleseek/:slug` max-ad detail + `/admin/manage/nobleseek` easy panel.

## 1. Backend

```bash
cd backend/EcommerceInventory
pip install -r requirements.txt   # includes pytrends
python manage.py migrate          # creates nobleseek_* tables
python manage.py seed_admin_modules  # adds "NobleSeek News" sidebar entry
python manage.py seed_nobleseek   # 5 demo published articles
python manage.py fetch_trends --limit 20  # manual trends pull (BD+US)
```

Cron 2x daily (Render cron or Celery beat):
```
0 6,18 * * * python manage.py fetch_trends --limit 20
```

Optional AI scaffolds (human must still review):
```
OPENAI_API_KEY=sk-...        # or AI_API_KEY + AI_BASE_URL + AI_MODEL
AI_BASE_URL=https://api.openai.com/v1
AI_MODEL=gpt-4o-mini
```

APIs:
- Public: `GET /api/store/nobleseek/articles/`, `.../articles/:slug/`, `.../categories/`, `.../latest/`, `.../ad-config/`
- Admin (JWT + platform staff): `/api/store/nobleseek/admin/articles/`, `/admin/trends/`, `/admin/trends/fetch/`, `/admin/trends/:id/create-draft/`, `/admin/ad-config/`, `/admin/stats/`

## 2. Frontend env (Vercel)

```
REACT_APP_API_URL=https://your-backend/api/
REACT_APP_ADSENSE_CLIENT=ca-pub-XXXXXXXXXXXXXXXX
REACT_APP_GA4_MEASUREMENT_ID=G-XXXX
```

`public/ads.txt` — replace pub-0000 with your real ID (AdSense > Account > ads.txt).

## 3. AdSense wiring (hybrid)

1. AdSense Dashboard > Ads > Get ads > Auto ads: set to LOW site-wide.
2. AdSense > Ads > By site > New ad unit x5: create Display top, In-article 1, In-article 2, Sidebar, Multiplex. Copy numeric slot IDs.
3. Admin panel > NobleSeek News > Ad slots tab: paste client + 5 slot IDs, keep `Shop ads OFF`, `News max ON`.
4. Exclusions (optional but recommended): AdSense > Blocking > URL exclusions for `/cart*`, `/checkout*`, `/account*` — double-guarantees minimal shop ads alongside code guard in `adsConfig.js:shouldSuppressAds`.
5. Anchor/Vignette: AdSense > Auto ads > enable Anchor + Vignette, then in code they only load on `/nobleseek/*` (detail mounts them; shop routes suppress via `shouldSuppressAds`).

Detail density map (`NobleSeekDetailPage.js`):
top leaderboard → hero → in-article every ~300 words (InArticleBody) → multiplex → sticky sidebar 300x600 → related + shop funnel.

## 4. Facebook traffic loop

- FB page (NobleSeek) post format: Bangla hook + `fabrything.com/nobleseek/:slug?utm_source=facebook&utm_medium=social&utm_campaign=nobleseek-fb`
- Detail page has ShareBar (FB/X/WhatsApp/copy) + FB comments + Follow box linking back to FB page.
- Homepage `NobleSeekStrip` shows latest 4 on shop home for reverse flow.

## 5. AdSense policy checklist

- [x] `/nobleseek/about`, `/contact`, `/privacy`, `/disclaimer`, `/ethics` live (dedicated footer)
- [x] Author byline on every detail ("By NobleSeek Desk • Dhaka")
- [x] Image credit + source fields mandatory in editor
- [x] Human review gate: AI = scaffold only, status DRAFT → REVIEW → PUBLISHED
- [x] No ads on transactional pages (cart/checkout/account)
- [x] `ads.txt` published at root
- [ ] Replace demo images with owned/licensed photos before applying for extra placements

## 6. Performance

- News routes code-split (`App.js` lazy), layout has no cart/Redux/chat weight.
- Images `loading=lazy` (list) / `eager+fetchpriority=high` (detail hero only).
- `<AdSlot/>` IntersectionObserver 400px prefetch, pushes once.
- `?amp=1` lite view for FB mobile slow networks.
