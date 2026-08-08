import { CATEGORY_META, FALLBACK_META, metaFor } from './categoryMeta';

// Every slug the categories API actually serves, captured from
// GET /api/products/categories/ against production on 2026-08-07. The source
// of truth is TAXONOMY in
// backend/EcommerceInventory/catalog/management/commands/seed_store_catalog.py.
//
// The previous map still listed pre-taxonomy slugs while the live top-level
// categories had changed underneath it, so all but one homepage tile rendered
// the fallback bag. Nothing failed -- it just looked generic. This test is what
// makes that failure loud.
const LIVE_SLUGS = [
  'eyewear',
  'fashion', 'mens-fashion', 'men-tshirts', 'men-polos', 'men-shirts', 'men-panjabi',
  'men-hoodies', 'men-jackets', 'men-bottoms', 'men-shorts',
  'womens-fashion', 'women-kurti-tops', 'women-tshirts', 'women-salwar-kameez',
  'women-coords', 'women-bottoms',
  'fashion-kids', 'kids-boys', 'kids-girls',
  'phones', 'phones-smartphones', 'phones-tablets',
  'computers', 'computers-laptops', 'computers-desktops', 'computers-monitors',
  'computers-components', 'computers-keyboards-mice', 'computers-printers-office',
  'computers-networking',
  'gadgets', 'gadgets-smart-watches', 'gadgets-earbuds', 'gadgets-speakers',
  'gadgets-power', 'gadgets-cases', 'gadgets-cameras', 'gadgets-smart-home',
  'beauty-health', 'beauty-hand-sanitizer', 'beauty-perfume', 'beauty-body-spray',
  'beauty-air-freshener', 'beauty-adult-diaper', 'beauty-shaving-grooming',
  'beauty-talcum-powder', 'beauty-personal-care', 'beauty-medical-supplies',
  'beauty-makeup', 'beauty-herbal-skin-care', 'beauty-nail-care', 'beauty-tools',
  'beauty-herbal-hair-care', 'beauty-deodorant',
  'sports', 'sports-jersey', 'sports-tshirts', 'sports-shorts', 'sports-trousers',
  'sports-accessories',
  'health', 'health-medicine', 'health-healthcare', 'health-supplement',
  'health-baby-mom-care', 'health-herbal', 'health-food-nutrition',
  'health-sexual-wellness', 'health-home-care',
];

describe('category tiles', () => {
  it.each(LIVE_SLUGS)('%s has its own icon, not the fallback', (slug) => {
    expect(metaFor(slug)).not.toBe(FALLBACK_META);
  });

  it('falls back for a slug that does not exist yet', () => {
    expect(metaFor('brand-new-category')).toBe(FALLBACK_META);
    expect(metaFor(undefined)).toBe(FALLBACK_META);
  });

  // Per-slug cases so a bad entry names itself in the failure output.
  it.each(Object.keys(CATEGORY_META))('%s has an icon and a valid hex colour', (slug) => {
    expect(CATEGORY_META[slug].icon).toBeTruthy();
    expect(CATEGORY_META[slug].color).toMatch(/^#[0-9A-Fa-f]{6}$/);
  });

  it('gives the pharmacy branch medical iconography, not shopping bags', () => {
    // These tiles sit next to cosmetics on the homepage; a customer should be
    // able to tell medicine from makeup at a glance.
    expect(metaFor('health').icon).toBe('💊');
    expect(metaFor('health-medicine').icon).toBe('💊');
    expect(metaFor('health-healthcare').icon).toBe('🩺');
  });
});
