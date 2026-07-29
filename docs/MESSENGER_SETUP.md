# Floating Messenger button — setup instructions

Branch `feat/messenger-button`. Ships **fully built and fully tested but
dormant** — no button appears on the storefront until you paste your Page
ID or username into the admin panel. No redeploy needed to turn it on.

## Why this is a link, not an in-page chat widget

Meta **discontinued the Customer Chat Plugin** (the embeddable in-page
Messenger widget — `fb-customerchat` / `MessengerExtensions`) in 2024. Any
tutorial or old blog post telling you to drop that widget into the site is
out of date and will not work, and this project does not use it.

What's built instead is a **floating button that opens
`https://m.me/<your Page ID or username>` in a new tab** — Facebook's own
supported deep link into your Page's Messenger inbox. It's one tap for a
visitor, and it's the only mechanism Meta still supports for "message this
business" from a website.

## 1. Where to find your Page ID or username

Either of these works in the `m.me/` link — use whichever is easier to find:

- **Page username** (if you set one): your Page's public URL looks like
  `facebook.com/fabrything` — the part after `facebook.com/` is the
  username.
- **Numeric Page ID**: Facebook Page → **About** tab → scroll down to
  **Page ID** (or Meta Business Suite → your Page → Settings →
  **Page transparency** shows it too).

## 2. Where to paste it — admin panel

**Django admin → Core → Store configurations →** the one row →
**`Messenger page id`** field. Paste either value from step 1 and save.

- The button is **not visible anywhere on the storefront while this field
  is blank** — that's the intended default, not a bug, so there is never a
  broken link or an empty floating circle before you're ready.
- As soon as you save a non-blank value, the button appears on every
  storefront page (not on `/admin`, `/food`/vendor, or `/rider` — those are
  separate audiences and were left alone).
- No redeploy required — the storefront reads this from
  `GET /api/store/config/` on load.

## 3. What the button does

- Bottom-right, floating above page content on every storefront page.
- On mobile it sits clear of the bottom navigation bar (offset above it,
  not overlapping).
- Opens `https://m.me/<your value>?ref=website_floating_button` in a new
  tab (`target="_blank"`, `rel="noopener noreferrer"`).
- A real, keyboard-focusable button with an accessible label ("Message us
  on Facebook Messenger"), at least 44px in either dimension.
- Uses the site's own MUI theme colours and a built-in icon — nothing is
  fetched from Facebook's CDN on page load. (That matters: fetching a
  Messenger badge/icon image from Meta's servers on every storefront page
  view would leak every visitor's IP address to Meta before they've clicked
  anything, and CDN-hosted assets like that can also get ad-blocked. The
  icon here is drawn locally.)

## 4. The `ref` parameter — what it does and doesn't get you

The link includes `?ref=website_floating_button`. When a visitor clicks it
and starts (or continues) a conversation, Messenger passes that `ref` value
through to:

- the **conversation view in your Page inbox / Meta Business Suite** (shown
  as the entry point / referral source on the thread), and
- your **webhook payload**, if you ever build a bot or integration that
  reads incoming messages — it arrives as `referral.ref` on the first
  message of the thread.

That's the supported way to tell "this conversation came from the website
button" apart from "this conversation came from a Page post" or an ad.

**Be clear on what this is not.** It is not a website analytics event. A
click on `m.me/...` opens a Facebook-owned page in a new tab — the browser
leaves your site, so **nothing about that click can be reported back into
your own site analytics** (no GA/Meta Pixel event, no admin dashboard
counter). The only place `ref` shows up is inside Meta's own tools, on the
conversation itself, once someone actually messages you.

## 5. What you must configure in Meta Business Suite to see this

For click/referral data to be attributable to your website at all in Meta's
tools, your domain needs to be associated with your Business:

1. **Meta Business Suite → Business Settings → Brand Safety → Domains** —
   add `fabrything.com` (or whatever your storefront's domain is) and
   complete domain verification (Meta gives you a DNS TXT record or an HTML
   file to add — same mechanism as verifying a domain for ads).
2. Once verified, conversations started via the `m.me` link show their
   `ref` value in the conversation's details pane in the Meta Business
   Suite inbox, and (if you build a webhook later) in the `referral` object
   of the first incoming message.
3. No further app review or permissions are needed just to receive these —
   `ref` passthrough on `m.me` links works for any Page. Domain
   verification is what lets Meta attribute the click to *your* verified
   property rather than showing it as an anonymous referral.

Nothing beyond pasting the Page ID/username into the admin panel (step 2) is
required for the button itself to work — domain verification only affects
how well Meta's own tools can label where a conversation came from.

## Files touched

- `backend/EcommerceInventory/core/models.py` —
  `StoreConfiguration.messenger_page_id` (blank by default).
- `backend/EcommerceInventory/core/migrations/0004_storeconfiguration_messenger_page_id.py` — new, single-field migration.
- `backend/EcommerceInventory/core/admin.py` — shows the field on the
  `StoreConfiguration` admin list.
- `backend/EcommerceInventory/storefront/views.py` — `StoreConfigView`
  exposes `messenger_page_id` (empty string when unset).
- `backend/EcommerceInventory/storefront/test_store_config.py` — new,
  covers the default-empty and configured cases.
- `frontend/ecommerce_inventory/src/storefront/components/MessengerButton.js`
  — new, the floating action button. Fetches `store/config/`, renders
  nothing when `messenger_page_id` is empty.
- `frontend/ecommerce_inventory/src/storefront/components/MessengerButton.test.js`
  — new, covers dormant (empty/missing config), configured with a username,
  and configured with a numeric Page ID.
- `frontend/ecommerce_inventory/src/storefront/layout/StorefrontLayout.js`
  — renders `<MessengerButton />` once, alongside the existing mobile
  bottom navigation.

## Note for the next engineer

There is a separate, pre-existing **static** Messenger icon in the site
footer (`StorefrontLayout.js`, next to the Facebook icon) that is hardcoded
to `https://m.me/fabrything` and unconditionally visible — that one predates
this work, is unrelated to `StoreConfiguration`, and was intentionally left
as-is (`StorefrontLayout.social.test.js` pins it). The new floating button
built here is the config-driven, dormant-until-set one described above; the
two are independent and can point at different values if that ever matters.
