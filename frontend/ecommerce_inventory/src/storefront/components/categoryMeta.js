// Emoji + accent colour per category slug, used by the homepage tiles
// (CategoryGrid), the mega menu and the mobile category drawer.
//
// This map had drifted badly: it still listed pre-taxonomy slugs
// ('shoes', 'watches', 'wallets-bags', 'home-appliances', 'skincare-cosmetics')
// while the live top-level categories are fashion / phones / computers /
// gadgets / beauty-health / health. Only 'eyewear' still matched, so every
// other tile on the homepage rendered the generic fallback bag.
//
// categoryMeta.test.js pins every slug the API actually serves, so the next
// taxonomy change fails a test instead of silently degrading to 🛍️.
export const CATEGORY_META = {
    // Top level
    fashion:              { icon: '👕', color: '#4F46E5' },
    phones:               { icon: '📱', color: '#0EA5E9' },
    computers:            { icon: '💻', color: '#2563EB' },
    gadgets:              { icon: '🎧', color: '#7C3AED' },
    eyewear:              { icon: '🕶️', color: '#8B5CF6' },
    'beauty-health':      { icon: '💄', color: '#E85D4A' },
    health:               { icon: '💊', color: '#059669' },

    // Fashion
    'mens-fashion':       { icon: '👔', color: '#4F46E5' },
    'womens-fashion':     { icon: '👗', color: '#EC4899' },
    'fashion-kids':       { icon: '🧒', color: '#F59E0B' },
    'men-tshirts':        { icon: '👕', color: '#4F46E5' },
    'men-polos':          { icon: '👕', color: '#4338CA' },
    'men-shirts':         { icon: '👔', color: '#4F46E5' },
    'men-panjabi':        { icon: '🥻', color: '#0F766E' },
    'men-hoodies':        { icon: '🧥', color: '#334155' },
    'men-jackets':        { icon: '🧥', color: '#1E293B' },
    'men-bottoms':        { icon: '👖', color: '#1D4ED8' },
    'men-shorts':         { icon: '🩳', color: '#0EA5E9' },
    'women-kurti-tops':   { icon: '👚', color: '#EC4899' },
    'women-tshirts':      { icon: '👕', color: '#DB2777' },
    'women-salwar-kameez':{ icon: '🥻', color: '#BE185D' },
    'women-coords':       { icon: '👗', color: '#F472B6' },
    'women-bottoms':      { icon: '👖', color: '#9D174D' },
    'kids-boys':          { icon: '👦', color: '#F59E0B' },
    'kids-girls':         { icon: '👧', color: '#F472B6' },

    // Phones / computers / gadgets
    'phones-smartphones': { icon: '📱', color: '#0EA5E9' },
    'phones-tablets':     { icon: '📲', color: '#0284C7' },
    'computers-laptops':  { icon: '💻', color: '#2563EB' },
    'computers-desktops': { icon: '🖥️', color: '#1D4ED8' },
    'computers-monitors': { icon: '🖥️', color: '#3B82F6' },
    'computers-components': { icon: '🧩', color: '#1E40AF' },
    'computers-keyboards-mice': { icon: '⌨️', color: '#4338CA' },
    'computers-printers-office': { icon: '🖨️', color: '#475569' },
    'computers-networking': { icon: '📶', color: '#0891B2' },
    'gadgets-smart-watches': { icon: '⌚', color: '#0EA5E9' },
    'gadgets-earbuds':    { icon: '🎧', color: '#7C3AED' },
    'gadgets-speakers':   { icon: '🔊', color: '#6D28D9' },
    'gadgets-power':      { icon: '🔋', color: '#16A34A' },
    'gadgets-cases':      { icon: '📦', color: '#B45309' },
    'gadgets-cameras':    { icon: '📷', color: '#334155' },
    'gadgets-smart-home': { icon: '🏠', color: '#10B981' },

    // Beauty & personal care
    'beauty-hand-sanitizer': { icon: '🧴', color: '#0EA5E9' },
    'beauty-perfume':     { icon: '🌸', color: '#DB2777' },
    'beauty-body-spray':  { icon: '🧴', color: '#8B5CF6' },
    'beauty-air-freshener': { icon: '🌬️', color: '#06B6D4' },
    'beauty-adult-diaper': { icon: '🩹', color: '#64748B' },
    'beauty-shaving-grooming': { icon: '🪒', color: '#334155' },
    'beauty-talcum-powder': { icon: '🧴', color: '#F59E0B' },
    'beauty-personal-care': { icon: '🧼', color: '#0891B2' },
    'beauty-medical-supplies': { icon: '🩺', color: '#DC2626' },
    'beauty-makeup':      { icon: '💄', color: '#E85D4A' },
    'beauty-herbal-skin-care': { icon: '🌿', color: '#16A34A' },
    'beauty-nail-care':   { icon: '💅', color: '#EC4899' },
    'beauty-tools':       { icon: '🪞', color: '#7C3AED' },
    'beauty-herbal-hair-care': { icon: '🌿', color: '#15803D' },
    'beauty-deodorant':   { icon: '🧴', color: '#0EA5E9' },

    // Health & pharmacy
    'health-medicine':    { icon: '💊', color: '#DC2626' },
    'health-healthcare':  { icon: '🩺', color: '#0891B2' },
    'health-supplement':  { icon: '🍊', color: '#F59E0B' },
    'health-baby-mom-care': { icon: '🍼', color: '#F472B6' },
    'health-herbal':      { icon: '🌿', color: '#16A34A' },
    'health-food-nutrition': { icon: '🥗', color: '#65A30D' },
    'health-sexual-wellness': { icon: '❤️', color: '#BE123C' },
    'health-home-care':   { icon: '🧽', color: '#0EA5E9' },
};

export const FALLBACK_META = { icon: '🛍️', color: '#4F46E5' };

export const metaFor = (slug) => CATEGORY_META[slug] || FALLBACK_META;
