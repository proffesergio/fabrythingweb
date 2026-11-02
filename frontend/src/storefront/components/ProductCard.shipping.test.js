/* Per-product shipping fee display on the card -- small, quiet text that
 * always shows something (the product's own fee, or the store's flat rate
 * when it has none) rather than nothing, per docs/SHIPPING_FEES.md.
 */
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import ProductCard from './ProductCard';

const baseProduct = {
  id: 1, name: 'Cotton Shirt', slug: 'cotton-shirt', image: ['https://x/img.jpg'],
  initial_selling_price: 900, discount_price: null,
};

const renderCard = (product) => render(
  <MemoryRouter><ProductCard product={product} /></MemoryRouter>
);

test('shows "Free delivery" when effective_shipping_fee is 0', () => {
  renderCard({ ...baseProduct, effective_shipping_fee: 0 });
  expect(screen.getByText('Free delivery')).toBeInTheDocument();
});

test('shows the delivery fee when the product carries its own override', () => {
  renderCard({ ...baseProduct, effective_shipping_fee: 250 });
  expect(screen.getByText('+৳250 delivery')).toBeInTheDocument();
});

test('shows the store flat rate as the delivery fee when the product has no override', () => {
  // The storefront API always resolves effective_shipping_fee to the store's
  // flat rate when the product itself has none -- displayed identically to
  // an explicit override, so the customer always sees a number.
  renderCard({ ...baseProduct, effective_shipping_fee: 60 });
  expect(screen.getByText('+৳60 delivery')).toBeInTheDocument();
});

test('renders no delivery line at all when the field is entirely absent', () => {
  renderCard({ ...baseProduct });
  expect(screen.queryByText(/delivery/i)).not.toBeInTheDocument();
});

// free_shipping is the explicit per-product promo flag (distinct from
// shipping_fee == 0) -- see docs/SHIPPING_FEES.md.
test('shows "Free delivery" when free_shipping is true, even with a nonzero effective_shipping_fee', () => {
  renderCard({ ...baseProduct, free_shipping: true, effective_shipping_fee: 60 });
  expect(screen.getByText('Free delivery')).toBeInTheDocument();
});

test('never shows both "Free delivery" and the delivery-fee text at once', () => {
  renderCard({ ...baseProduct, free_shipping: true, effective_shipping_fee: 250 });
  expect(screen.getByText('Free delivery')).toBeInTheDocument();
  expect(screen.queryByText(/^\+৳/)).not.toBeInTheDocument();
});

test('a non-promo product with no fee still shows the store flat rate, not "Free delivery"', () => {
  renderCard({ ...baseProduct, free_shipping: false, effective_shipping_fee: 60 });
  expect(screen.getByText('+৳60 delivery')).toBeInTheDocument();
  expect(screen.queryByText('Free delivery')).not.toBeInTheDocument();
});
