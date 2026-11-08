import { estimateShipping, INSIDE_DHAKA, OUTSIDE_DHAKA } from './shipping';

const config = { fixed_shipping_rate: 70, outside_dhaka_shipping_rate: 120, free_shipping_threshold: null };

test('regional base rates and product override are reflected in cart estimates', () => {
    expect(estimateShipping([{ shipping_fee: null }], 200, config, INSIDE_DHAKA)).toBe(70);
    expect(estimateShipping([{ shipping_fee: null }], 200, config, OUTSIDE_DHAKA)).toBe(120);
    expect(estimateShipping([{ shipping_fee: 250 }], 200, config, OUTSIDE_DHAKA)).toBe(250);
});

test('free promos and threshold override regional rates', () => {
    expect(estimateShipping([{ free_shipping: true }], 200, config, OUTSIDE_DHAKA)).toBe(0);
    expect(estimateShipping([{ free_shipping: true }, { shipping_fee: null }], 200, config, OUTSIDE_DHAKA)).toBe(120);
    expect(estimateShipping([{ shipping_fee: 250 }], 300, { ...config, free_shipping_threshold: 300 }, OUTSIDE_DHAKA)).toBe(0);
});
