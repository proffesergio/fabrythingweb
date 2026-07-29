# Live chat

A live chat feature built in-house, on top of Django + DRF, that customers can use for
general questions, order questions, fast "emergency delivery" requests, and — once it
exists — the revision conversation on a custom print-on-demand order.

## Why polling, not websockets

Deliberate choice, not a shortcut:

- **Render's free tier does not support websockets.** Django Channels would need a
  paid plan (or a separate always-on process) just to hold connections open.
- **The chat has to attach to our own data** — a store order, a food order, and soon a
  print job — which a third-party chat widget (Intercom, Tawk.to, WhatsApp Business
  widget, etc.) cannot do. It only ever sees "a visitor is chatting," never "this is
  order #4821."

So it's plain Django models, plain DRF endpoints, and the client polls for new
messages every few seconds. No Django Channels, no Redis, no websockets.

## What customers can do

- Open a new conversation, choosing a kind: **General**, **Store Order**, **Food
  Order**, or **Emergency delivery request** (the fast-delivery channel the owner
  asked for). A conversation always starts with the first message — there is no
  "empty" thread state.
- See a list of their own conversations, each with an unread badge.
- Read and reply in a conversation. Once staff closes it, the customer can still read
  the history but cannot post further (staff can reopen it).
- See a small red badge (unread count) even when the chat panel is closed.

A customer can only ever see or post to **their own** threads — every read and write
endpoint filters by the authenticated customer and returns a plain 404 for anyone
else's thread id. This was tested explicitly for both read and write, because this
project has shipped a cross-tenant bug once before.

## How the admin inbox works

Staff (Admin / Super Admin / Staff role, platform-scoped — see "Authorization" below)
get an inbox listing every customer's threads, sorted by most-recently-active first,
filterable by status (Open/Closed) and kind. Opening a thread shows the full
conversation with a reply box; staff can mark a thread read (clears their own unread
badge) and close or reopen it.

## The polling endpoints, and the intervals chosen

Two shapes, on purpose:

1. **Full poll** (`GET .../messages/?after=<cursor>`) — returns only the messages
   newer than `after`, which is either a message id or an ISO timestamp, never the
   whole thread history. Backed by an index on `(thread, id)` so this stays cheap
   regardless of how long the conversation has gotten.
2. **Badge poll** (`GET .../threads/updates/`) — a lightweight "anything new?" shape:
   total unread count plus a short list of threads that have unread messages, with
   *no message bodies* and a `select_related`/`.only()`-bounded query. Cheap enough to
   poll far more often than the full conversation view.

Frontend intervals (see `src/storefront/` chat widget):

- **~3–5 seconds** while the chat panel is open and the browser tab is visible (the
  full poll).
- **~30–60 seconds** for the background badge poll when the panel is closed, and it
  pauses entirely when `document.visibilityState !== 'visible'` (tab hidden/minimised).
- Every interval is cleared on unmount — a leaked poll timer on a chat widget is a
  real battery/bandwidth bug, not just an annoyance.

This is not real-time chat; it is "checks in every few seconds." That trade-off is
what makes it possible to run on Render's free tier at all.

## The Render free-tier wake-up caveat (read this before promising "emergency" speed)

**Render's free tier sleeps the backend after a period of inactivity.** The first
request after that — whoever sends it, customer or poll — can take **roughly 30
seconds** to get a response while the instance spins back up. For a general chat
question that's mildly annoying. For the **Emergency delivery request** channel it is
a real limitation: a customer who needs an urgent delivery at 3am when the site has
been idle may wait up to 30 seconds just for their first message to land, and staff
polling won't see it any faster than that either. This is an honest trade-off of the
free tier, not a bug in the chat code, and it should be communicated to customers (or
the owner should upgrade the Render plan) before "emergency" is marketed as instant.

## Authorization

- Every authenticated view declares `authentication_classes = [JWTAuthentication]`
  explicitly — this project sets no DRF default, so a missing declaration silently
  makes `request.user` anonymous.
- Staff endpoints are gated by `chat.permissions.IsChatStaff`: role must be
  `Admin`/`Super Admin`/`Staff` **and** `core.helpers.isPlatformScope(user)` must be
  true. `isPlatformScope` alone is not enough — it is true for *any* domain-root user,
  including an ordinary self-signed-up Customer, so the role check narrows it back
  down; `isPlatformScope` on top of the role check excludes a Staff/Admin account that
  is itself a sub-account under someone else's domain.
- `/api/chat/` is listed in `core.middleware.PUBLIC_API_PREFIXES` (same treatment as
  `/api/food/`): it mixes customer- and staff-authenticated endpoints under one
  prefix, so the middleware's per-user `ModuleUrls` permission gate is bypassed for
  it and each view enforces its own authentication/permission classes instead. This
  means a customer chat endpoint works the moment a Customer account exists — no
  admin has to seed a module-permission row before anyone can open a thread.
- Posting is rate-limited (`ScopedRateThrottle`, scope `chat.message`, default
  30/minute, env-tunable via `THROTTLE_CHAT_MESSAGE`) — applied only to the write
  path, never to the polling reads, so throttling can't break a legitimate poll
  cadence.
- Message length is capped at 4000 characters, validated both in the DRF serializer
  and as a model-level `MaxLengthValidator`.

## Message rendering: plain text, never HTML

`ChatMessage.body` is stored as plain text. **The frontend must render it as text**
(e.g. React's default `{message.body}` interpolation), **never** via
`dangerouslySetInnerHTML` or any HTML-injection path. Nothing in the backend escapes
or sanitises HTML, because nothing here is ever supposed to be interpreted as markup.

## Data model

- `ChatThread`: `customer`, `kind` (GENERAL / ORDER / FOOD_ORDER / EMERGENCY /
  PRINT_JOB), `status` (OPEN / CLOSED), `related_kind` + `related_id` (see below),
  `last_message_at` (denormalised, indexed — the admin inbox sorts on it directly
  instead of computing it per row on every poll), `customer_unread_count` /
  `staff_unread_count` (denormalised per-side unread counters — the badges read these
  directly rather than scanning `ChatMessage` on every poll).
- `ChatMessage`: `thread`, `sender` (nullable — a SYSTEM message has none),
  `sender_role` (CUSTOMER / STAFF / SYSTEM), `body`, `created_at`. Indexed on
  `(thread, id)` for the `?after=` polling query.

### Why `related_kind` + `related_id` instead of `contenttypes`

`ChatThread` links to "the thing the conversation is about" (a store order, a food
order, eventually a print job) with a plain `related_kind` string (e.g.
`"food.FoodOrder"`) + `related_id` integer pair, **not**
`django.contrib.contenttypes`. Contenttypes buys polymorphic FK integrity and a
`GenericForeignKey` descriptor, at the cost of a `ContentType` lookup/join, for a
field this code reads at most once per thread-open (to build a "Re: order #123" link)
and never queries *by* in bulk. A plain pair is enough for that and keeps `chat/` from
importing every app it might ever reference — including, eventually, print-on-demand.

## How print-on-demand will attach here (not built yet)

`ChatThread.Kind.PRINT_JOB` already exists in the enum — nothing creates threads of
that kind yet, but the column, the admin inbox filter, and the polling machinery are
ready for it. When the print-on-demand feature (SP6) is built, its checkout/order flow
should:

1. Create a `ChatThread(kind=ChatThread.Kind.PRINT_JOB, related_kind="printing.PrintJob",
   related_id=<job.id>)` when the job is placed (or lazily, the first time either side
   opens the revision conversation).
2. Post proof images / revision requests as ordinary `ChatMessage` rows. **Attachments
   are out of scope for this task** (see below) — the print-on-demand feature will need
   to add an `attachment_url` (or similar) to `ChatMessage`, or a small side table, to
   carry proof images; nothing here blocks that, it's just not built.
3. Reuse the same customer/staff endpoints and polling cadence — no new chat
   infrastructure needed, just the one thread-creation call at the point the print job
   is placed.

## Deliberately out of scope for this task

- **Attachments** (images/files in a message). `ChatMessage` has no attachment field;
  print-on-demand proofs will need one added later (see above).
- **Typing indicators.** Would need either a much higher polling rate or a websocket —
  contrary to the "polling, no websockets" design.
- **Read receipts** (message-level "seen at X"). Only thread-level unread *counts*
  exist; there's no per-message read state.
- **A second notification system.** Customer messages nudge the admin over WhatsApp by
  reusing the existing `core.whatsapp` provider (the same one order/rider alerts use),
  guarded so a WhatsApp failure or an unconfigured provider can never fail the message
  post itself. It only fires when staff hasn't replied in the last 15 minutes, so an
  active back-and-forth doesn't page the admin's phone on every message. Like every
  other WhatsApp alert in this project, it stays completely dormant (no network calls)
  until `WHATSAPP_ACCESS_TOKEN`/`WHATSAPP_PHONE_NUMBER_ID` are set **and** a
  `chat_new_customer_message` template is created and approved in Meta Business
  Manager — see `docs/WHATSAPP_SETUP.md` for that process.
