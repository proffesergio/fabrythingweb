/**
 * Money formatting for the storefront.
 *
 * Prices are floats server-side and the revenue markup (`max(floor, price ×
 * percentage)`) routinely lands on fractions — a ৳3,590 product marked up 3%
 * becomes 3697.7, which rendered as "৳3697.7". Bangladeshi retail prices are
 * whole taka, so round for display.
 *
 * Display only. Never round before sending an amount back to the server: the
 * server is authoritative on what is charged, and a rounded value posted back
 * would disagree with the order it creates.
 */
export function formatTaka(value) {
    const n = Number(value);
    if (!Number.isFinite(n)) return '';
    return Math.round(n).toLocaleString('en-BD');
}

/** `formatTaka` with the currency symbol, for the common case. */
export function taka(value) {
    const formatted = formatTaka(value);
    return formatted === '' ? '' : `৳${formatted}`;
}
