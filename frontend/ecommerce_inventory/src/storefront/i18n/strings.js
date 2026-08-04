/**
 * Storefront translations. **Bangla is the default** — most Fabrything
 * customers browse in Bangla.
 *
 * HOW TO EXTEND (this file is the workflow for translating the rest of the
 * site, one page at a time, across future sessions):
 *
 *   1. Add a namespaced key per page, e.g. `cart.title`, so keys stay
 *      greppable and a page's strings live together.
 *   2. Add BOTH `en` and `bn`. A key present in one and missing in the other
 *      falls back to `en`, then to the key itself — visible, never a crash.
 *   3. In the page: `const t = useT();` then `t('printing.title')`.
 *   4. Move strings a page at a time and delete the hardcoded text as you go;
 *      a half-translated page is worse than an untranslated one.
 *
 * Interpolation is deliberately not supported yet. When a string needs a
 * value, split it or pass the value as a separate element — a mini template
 * language is not worth the complexity until several pages need it.
 */

export const LANGUAGES = [
    { code: 'bn', label: 'বাংলা' },
    { code: 'en', label: 'English' },
];

export const DEFAULT_LANGUAGE = 'bn';

export const strings = {
    en: {
        'lang.switch': 'Language',

        // Custom Printing page
        'printing.title': 'Custom Printing',
        'printing.intro':
            'Tell us what you need — a team jersey, a logo tee, anything. Our designer will draw it up and send you a proof to approve before we print.',
        'printing.tab.submit': 'Submit a Request',
        'printing.tab.mine': 'My Requests',

        // Showcase
        'printing.showcase.title': 'What we can print for you',
        'printing.showcase.intro':
            'Anything below can be branded with your logo, artwork or team details. Pick what you have in mind and describe it in the form — you do not need a design ready.',
        'printing.terms.minimum': 'Minimum order',
        'printing.terms.turnaround': 'Turnaround',
        'printing.terms.artwork': 'Artwork',
        'printing.terms.minimumValue': '20 pieces (10 for selected items) when the fabric and colour are in stock',
        'printing.terms.turnaroundValue': '10–14 days from the approved work order',
        'printing.terms.artworkValue':
            'AI or SVG vector files reproduce best. No file? Describe what you want — we design it for you.',

        // Showcase categories
        'printing.cat.apparel': 'Apparel',
        'printing.cat.apparel.blurb': 'Team kits, uniforms, event tees and staff wear.',
        'printing.cat.headwear-bags': 'Headwear & bags',
        'printing.cat.headwear-bags.blurb': 'Everyday carry that puts your mark in public.',
        'printing.cat.drinkware': 'Drinkware',
        'printing.cat.drinkware.blurb': 'Desk and gift items that stay in use.',
        'printing.cat.office': 'Office & stationery',
        'printing.cat.office.blurb': 'Corporate gifting, onboarding kits and client giveaways.',
        'printing.cat.accessories-tech': 'Accessories & tech',
        'printing.cat.accessories-tech.blurb': 'Higher-value gifts for staff and partners.',
    },

    bn: {
        'lang.switch': 'ভাষা',

        'printing.title': 'কাস্টম প্রিন্টিং',
        'printing.intro':
            'আপনার যা প্রয়োজন আমাদের জানান — টিম জার্সি, লোগো টি-শার্ট, যেকোনো কিছু। আমাদের ডিজাইনার সেটি তৈরি করে আপনাকে প্রুফ পাঠাবেন, আপনি অনুমোদন দিলে তবেই আমরা প্রিন্ট করব।',
        'printing.tab.submit': 'অর্ডারের অনুরোধ করুন',
        'printing.tab.mine': 'আমার অনুরোধসমূহ',

        'printing.showcase.title': 'আমরা আপনার জন্য যা যা প্রিন্ট করতে পারি',
        'printing.showcase.intro':
            'নিচের যেকোনো পণ্যে আপনার লোগো, ডিজাইন বা টিমের তথ্য প্রিন্ট করা যাবে। পছন্দের পণ্যটি বেছে নিয়ে ফর্মে বিস্তারিত লিখুন — আগে থেকে ডিজাইন তৈরি থাকার দরকার নেই।',
        'printing.terms.minimum': 'সর্বনিম্ন অর্ডার',
        'printing.terms.turnaround': 'সময় লাগবে',
        'printing.terms.artwork': 'ডিজাইন ফাইল',
        'printing.terms.minimumValue': '২০ পিস (নির্দিষ্ট কিছু পণ্যে ১০ পিস), কাপড় ও রঙ স্টকে থাকা সাপেক্ষে',
        'printing.terms.turnaroundValue': 'ওয়ার্ক অর্ডার অনুমোদনের পর ১০–১৪ দিন',
        'printing.terms.artworkValue':
            'AI বা SVG ভেক্টর ফাইলে সবচেয়ে ভালো প্রিন্ট হয়। ফাইল নেই? কী চান লিখে জানান — আমরা ডিজাইন করে দেব।',

        'printing.cat.apparel': 'পোশাক',
        'printing.cat.apparel.blurb': 'টিম কিট, ইউনিফর্ম, ইভেন্ট টি-শার্ট ও স্টাফ পোশাক।',
        'printing.cat.headwear-bags': 'ক্যাপ ও ব্যাগ',
        'printing.cat.headwear-bags.blurb': 'প্রতিদিনের ব্যবহারে আপনার ব্র্যান্ড সবার চোখে।',
        'printing.cat.drinkware': 'মগ ও বোতল',
        'printing.cat.drinkware.blurb': 'ডেস্ক ও উপহারের জিনিস, যা কাজে লাগে।',
        'printing.cat.office': 'অফিস ও স্টেশনারি',
        'printing.cat.office.blurb': 'কর্পোরেট গিফট, অনবোর্ডিং কিট ও ক্লায়েন্ট উপহার।',
        'printing.cat.accessories-tech': 'অ্যাকসেসরিজ ও টেক',
        'printing.cat.accessories-tech.blurb': 'স্টাফ ও পার্টনারদের জন্য উন্নতমানের উপহার।',
    },
};

export function translate(key, lang) {
    const table = strings[lang] || strings[DEFAULT_LANGUAGE];
    // en fallback, then the key itself — a missing translation shows up as a
    // readable English string or a visible key, never a blank or a crash.
    return table[key] ?? strings.en[key] ?? key;
}
