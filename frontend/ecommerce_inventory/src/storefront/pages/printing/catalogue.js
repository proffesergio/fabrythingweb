/**
 * What customers can order printed. Modelled on the corporate lineup at
 * fabrilife.com/corporate (fetched 2026-08-04) — the same product families a
 * Bangladeshi corporate-merch buyer expects to see, so a client can recognise
 * what is possible before writing a brief.
 *
 * This is a SHOWCASE, not a priced catalogue. Nothing here is a product row in
 * the database and nothing here is purchasable directly — every item routes
 * into the existing print-request flow (brief → our proof → your approval →
 * production), which is where quantity, fabric, colour and price get settled.
 * Keeping it as plain data means the owner edits one file to add a line.
 */

export const PRINT_TERMS = {
    // Straight from Fabrilife's corporate page — the industry norm here. State
    // it up front rather than letting a client submit a 5-piece brief and be
    // disappointed.
    minimumOrder: '20 pieces (10 for selected items) when the fabric and colour are in stock',
    turnaround: '10–14 days from the approved work order',
    artwork: 'AI or SVG vector files reproduce best. No file? Describe what you want — we design it for you.',
};

/**
 * Optional image per item. Deliberately EMPTY for now: the obvious source
 * would be Fabrilife's own corporate product photography, and lifting a
 * competitor's copyrighted studio shots for our marketing page is not
 * something to do quietly. Items without an image render a clean typographic
 * tile, which reads as intentional rather than broken.
 *
 * To add real photos: drop files in `public/print/` and map them here, e.g.
 *   'Round Neck T-Shirt': '/print/round-neck-tee.jpg'
 * Product shots we own, or licensed stock, are both fine.
 */
export const PRINT_IMAGES = {};

export const PRINT_CATEGORIES = [
    {
        key: 'apparel',
        title: 'Apparel',
        blurb: 'Team kits, uniforms, event tees and staff wear.',
        items: [
            { name: 'T-shirts', note: 'Round neck, half or full sleeve' },
            { name: 'Polo T-shirts', note: 'Classic and cut & stitch' },
            { name: 'Dye-sublimation T-shirts', note: 'Full-surface print, sports fit' },
            { name: 'Dye-sublimation polos', note: 'Full-surface print with a collar' },
            { name: 'Jerseys', note: 'Player name and number, full team rosters' },
            { name: 'Shirts', note: 'Casual and formal' },
            { name: 'Hoodies & sweatshirts' },
            { name: 'Jackets' },
            { name: 'Trousers' },
            { name: 'Aprons', note: 'Kitchen and service staff' },
            { name: 'Raincoats' },
            { name: 'Security vests' },
        ],
    },
    {
        key: 'headwear-bags',
        title: 'Headwear & bags',
        blurb: 'Everyday carry that puts your mark in public.',
        items: [
            { name: 'Caps' },
            { name: 'Tote bags' },
            { name: 'Umbrellas' },
            { name: 'Masks' },
            { name: 'Socks' },
        ],
    },
    {
        key: 'drinkware',
        title: 'Drinkware',
        blurb: 'Desk and gift items that stay in use.',
        items: [
            { name: 'Mugs' },
            { name: 'Closed cups' },
            { name: 'Water bottles' },
        ],
    },
    {
        key: 'office',
        title: 'Office & stationery',
        blurb: 'Corporate gifting, onboarding kits and client giveaways.',
        items: [
            { name: 'Notebooks & diaries' },
            { name: 'Desk calendars' },
            { name: 'Pens & pen holders' },
            { name: 'Paperweights' },
            { name: 'Visiting cards & card holders' },
            { name: 'Gift boxes' },
            { name: 'Onboarding kits' },
        ],
    },
    {
        key: 'accessories-tech',
        title: 'Accessories & tech',
        blurb: 'Higher-value gifts for staff and partners.',
        items: [
            { name: 'ID cards & lanyards' },
            { name: 'Keyrings' },
            { name: 'Wristbands' },
            { name: 'Wallets' },
            { name: 'Power banks' },
            { name: 'Pen drives' },
            { name: 'USB hubs' },
        ],
    },
];
