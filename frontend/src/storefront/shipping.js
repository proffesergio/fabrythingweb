export const INSIDE_DHAKA = 'inside_dhaka';
export const OUTSIDE_DHAKA = 'outside_dhaka';

// Mirrors StoreConfiguration.shipping_for for a cart preview. The server
// recalculates from current product records when the order is placed.
export function estimateShipping(items, subtotal, config, zone) {
    const threshold = config?.free_shipping_threshold;
    if (threshold != null && subtotal >= Number(threshold)) return 0;
    if (items.length && items.every((item) => item.free_shipping === true)) return 0;
    const base = zone === OUTSIDE_DHAKA
        ? Number(config?.outside_dhaka_shipping_rate ?? 120)
        : Number(config?.fixed_shipping_rate ?? 70);
    return Math.max(base, ...items.filter((item) => !item.free_shipping)
        .map((item) => item.shipping_fee == null ? 0 : Number(item.shipping_fee)));
}
