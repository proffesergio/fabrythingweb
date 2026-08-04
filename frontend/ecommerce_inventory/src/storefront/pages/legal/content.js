// Legal page content, kept as data so every policy shares one layout and one
// place to edit. Written against what the platform ACTUALLY does — Cash on
// Delivery only, Bancharampur-scoped food delivery, Rokomari affiliate links,
// prescription medicines gated off, custom-print orders. If a behaviour here
// stops being true, change it here in the same commit as the code.
//
// PLACEHOLDERS the owner must replace before these are relied on:
//   [LEGAL ENTITY NAME], [TRADE LICENCE NO.], [REGISTERED ADDRESS]
// They are deliberately left visible rather than invented — a made-up licence
// number on a published policy is worse than an obvious blank.
//
// These are plain-language drafts describing real practice. They are NOT
// lawyer-reviewed. Have a Bangladeshi lawyer read them before launch,
// especially the medicine, refund and liability sections.

export const SUPPORT = {
  email: "support@fabrything.com",
  whatsapp: "+8801842168117",
  messenger: "https://m.me/fabrything",
  entity: "Fabrything Limited",
  licence: "34823432",
  address: "Bancharampur, Brahmanbaria, Bangladesh",
};

export const LAST_UPDATED = "4 August 2026";

export const PRIVACY = {
  slug: "privacy",
  title: "Privacy Policy",
  intro:
    "This policy explains what we collect when you use Fabrything, why we collect it, and what choices you have. We have written it in plain language rather than legal boilerplate.",
  sections: [
    {
      h: "What we collect",
      body: [
        "Account details: your name, phone number and email address when you register.",
        "Delivery details: the addresses you save, plus the delivery location you pin on the map at checkout. We keep this so repeat orders reach you and so we can price delivery by distance.",
        "Order history: what you bought, when, and the amount — required to handle returns, disputes and accounting.",
        "Custom printing: any brief, reference image or artwork you upload, plus the roster details (player names, numbers, sizes) you enter for team orders.",
        "Messages: anything you send us through the in-app chat.",
        'Rider location (Rider app only): a rider\'s device location is shared while — and only while — the rider turns the "Share my location" switch on. Turning it off stops the sharing.',
        "Technical data: your device type, app version and basic error logs.",
      ],
    },
    {
      h: "What we do NOT collect",
      body: [
        "We do not take or store card, bank or mobile-wallet details. Fabrything is Cash on Delivery only — you pay the rider when your order arrives, so no payment credentials ever reach us.",
      ],
    },
    {
      h: "Why we collect it",
      body: [
        "To take, deliver and support your orders.",
        "To calculate delivery charges by distance from the restaurant or store to your location.",
        "To notify you and our staff about order status, including WhatsApp alerts to our team when an order is placed.",
        "To detect misuse and keep accounts secure.",
      ],
    },
    {
      h: "Who we share it with",
      body: [
        "Delivery riders receive the name, phone number and address needed to complete your delivery — nothing more.",
        "Restaurants and vendors receive the order contents and contact details needed to prepare and hand over your order.",
        "Our hosting and infrastructure providers process data on our behalf so the service can run.",
        "We do not sell your personal information to anyone.",
      ],
    },
    {
      h: "Facebook and Meta tools",
      body: [
        "Our website loads the Meta Pixel, which tells Meta that a visit happened and lets us measure our advertising. If you message us through the Messenger or WhatsApp buttons, that conversation happens on Meta's platforms and is governed by Meta's own privacy policy as well as ours.",
        "You can block this with your browser's tracking protection or an ad blocker; the site still works.",
      ],
    },
    {
      h: "Affiliate links",
      body: [
        'Some products shown on our Deals page and in promotional placements are affiliate links to Rokomari.com, clearly marked "via Rokomari". Clicking one takes you to Rokomari and we may earn a commission if you buy. Your purchase there is with Rokomari under their terms and privacy policy — not with us. We count clicks on our own links to see what is useful; we do not receive your Rokomari account details.',
      ],
    },
    {
      h: "How long we keep it",
      body: [
        "Order and delivery records are kept while your account is active and afterwards for as long as needed for accounting, tax and dispute handling. Chat messages and uploaded artwork are kept while the related request is open and for a reasonable period afterwards.",
      ],
    },
    {
      h: "Your choices",
      body: [
        "You can ask us for a copy of the personal data we hold about you, ask us to correct it, or ask us to delete your account. Contact us using the details below. Some records — for example completed order and payment history — may need to be retained where the law requires it.",
        "Riders can stop location sharing at any time from the switch in the Rider app.",
      ],
    },
    {
      h: "Children",
      body: [
        "Fabrything is not intended for children under 13, and we do not knowingly collect their data.",
      ],
    },
    {
      h: "Changes",
      body: [
        "If we change this policy we will update the date at the top of this page.",
      ],
    },
  ],
};

export const TERMS = {
  slug: "terms",
  title: "Terms of Use",
  intro:
    "These terms cover your use of the Fabrything website and apps. By ordering from us you agree to them.",
  sections: [
    {
      h: "Who we are",
      body: [
        `Fabrything is operated by ${SUPPORT.entity} (trade licence ${SUPPORT.licence}), ${SUPPORT.address}.`,
      ],
    },
    {
      h: "Your account",
      body: [
        "You are responsible for keeping your login details private and for orders placed from your account. Tell us immediately if you think someone else has access to it.",
        "Give accurate contact and address details — deliveries fail when they are wrong, and repeated failed deliveries may lead us to suspend an account.",
      ],
    },
    {
      h: "Prices and payment",
      body: [
        "All prices are in Bangladeshi Taka (৳) and include our margin. Delivery charges are shown before you confirm an order.",
        "We accept Cash on Delivery only. You pay the rider when the order arrives.",
        "Prices and availability can change. If we cannot fulfil an item after you order, we will contact you and cancel that item at no charge.",
        "We try to keep product information accurate, but descriptions, images and specifications sourced from our suppliers may contain errors. If an item is materially different from its listing, you may refuse it on delivery.",
      ],
    },
    {
      h: "Food delivery",
      body: [
        "Food orders are prepared by independent restaurants. We handle ordering and delivery; the restaurant is responsible for the food itself, its preparation and its packaging.",
        "Delivery times are estimates. Weather, traffic and restaurant load affect them.",
      ],
    },
    {
      h: "Medicines and health products",
      body: [
        "We sell only non-prescription health and personal-care items. Products marked as requiring a prescription cannot be purchased through the platform and are blocked at checkout.",
        "Nothing on Fabrything is medical advice. Read the manufacturer's label and consult a qualified pharmacist or doctor before using any health product.",
      ],
    },
    {
      h: "Custom printing orders",
      body: [
        "For custom-printed items you either supply artwork or describe what you want and we prepare a design proof for your approval.",
        "You confirm that you own or have permission to use any logo, image or text you send us, and that it does not infringe anyone's rights. We may decline a request we believe is infringing, offensive or unlawful.",
        "Production starts only after you approve a proof. Because the item is made specifically for you, an approved custom order cannot be cancelled or returned once production has begun, except where the item is defective or differs from the approved proof.",
      ],
    },
    {
      h: "Affiliate content",
      body: [
        'Some items we show link to Rokomari.com and are labelled "via Rokomari". We may earn a commission on purchases made through those links. Those purchases are contracts between you and Rokomari — their terms, pricing, delivery and returns apply, not ours.',
      ],
    },
    {
      h: "Acceptable use",
      body: [
        "Do not misuse the platform: no fraudulent orders, no attempts to break or probe our systems, no abusive behaviour toward our staff, riders or restaurant partners, and no scraping or copying of our content for a competing service.",
      ],
    },
    {
      h: "Our liability",
      body: [
        "We are responsible for delivering what you ordered in the condition described. We are not liable for indirect or consequential losses, and our liability for any order is limited to the amount you paid for it.",
        "Nothing in these terms removes rights you have under Bangladeshi consumer law.",
      ],
    },
    {
      h: "Governing law",
      body: [
        "These terms are governed by the laws of Bangladesh, and disputes fall to the courts of Bangladesh.",
      ],
    },
  ],
};

export const SHIPPING = {
  slug: "shipping",
  title: "Delivery & Shipping Conditions",
  intro:
    "How, where and when we deliver — and what it costs. Please read the delivery area section before ordering.",
  sections: [
    {
      h: "Where we deliver",
      body: [
        "Food delivery covers Bancharampur upazila, Brahmanbaria — 13 unions and the villages within them. You choose your union and drop a pin at checkout.",
        "Store products are delivered within our serviceable areas. If your address falls outside the area a restaurant serves, checkout will tell you before you pay.",
        "Food deliveries beyond 12 km from the restaurant are not accepted, because they cannot be completed reliably or paid fairly to the rider.",
      ],
    },
    {
      h: "What delivery costs",
      body: [
        "Store orders use a standard delivery charge. Some products carry their own delivery charge because of size or weight; where a cart contains several such items, the highest applicable charge is used rather than adding them together.",
        'Products marked "Free delivery" are promotions and ship free when ordered on their own.',
        "Food delivery is priced by distance from the restaurant to your pinned location: a base charge plus a per-kilometre rate beyond the free distance, rounded up to the nearest ৳5.",
        "The exact delivery charge is always shown before you confirm an order. The amount you are charged is the amount you saw.",
      ],
    },
    {
      h: "When you will get it",
      body: [
        "Food orders are typically delivered within 30–60 minutes of the restaurant accepting, depending on distance, preparation time and weather.",
        "Store orders are usually delivered within 1–3 days inside our delivery area.",
        "You can follow your order's status in your account or in the app.",
      ],
    },
    {
      h: "Receiving your order",
      body: [
        "Payment is cash to the rider on delivery. Please have the exact amount ready where possible.",
        "Check your order in front of the rider. If an item is damaged, wrong or missing, refuse it or tell the rider immediately — that is much easier to resolve than a report the next day.",
        "If nobody is available at the address, the rider will attempt to call the number on the order. Orders that cannot be delivered after reasonable attempts are returned, and repeated failed deliveries may affect Cash on Delivery availability on your account.",
      ],
    },
    {
      h: "Returns and refunds",
      body: [
        "Tell us within 48 hours of delivery if an item is damaged, defective or not what you ordered, and we will arrange a replacement or refund. Keep the item and its packaging as delivered.",
        "Food, opened personal-care and hygiene items cannot be returned once accepted, for health and safety reasons, unless they were defective or incorrect on arrival.",
        "Custom-printed items made to your approved proof cannot be returned unless defective or different from what you approved.",
        "Because we take payment in cash, refunds are issued by the method we agree with you at the time — usually mobile financial services or cash.",
      ],
    },
    {
      h: "Problems with a delivery",
      body: [
        `Contact us on WhatsApp at ${SUPPORT.whatsapp}, through the chat on this site, or by email at ${SUPPORT.email}. Have your order number ready — it is on your order confirmation.`,
      ],
    },
  ],
};

export const LEGAL_PAGES = [PRIVACY, TERMS, SHIPPING];
