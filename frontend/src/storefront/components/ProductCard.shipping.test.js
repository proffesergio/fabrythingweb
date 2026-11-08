/* Cards advertise explicit free-shipping promos; regional paid rates live on the detail page. */
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

test('a zero product fee does not advertise free delivery without a promo', () => {
  renderCard({ ...baseProduct, effective_shipping_fee: 0 });
  expect(screen.queryByText(/delivery/i)).not.toBeInTheDocument();
});

test('exposes a crawlable product link with the product name', () => {
  renderCard(baseProduct);
  expect(screen.getByRole('link', { name: 'Cotton Shirt' })).toHaveAttribute('href', '/product/cotton-shirt');
});

test('keeps paid delivery off cards with product overrides', () => {
  renderCard({ ...baseProduct, effective_shipping_fee: 250 });
  expect(screen.queryByText(/delivery/i)).not.toBeInTheDocument();
});

test('keeps the legacy flat delivery rate off product cards', () => {
  // The storefront API always resolves effective_shipping_fee to the store's
  // flat rate when the product itself has none -- displayed identically to
  // an explicit override, so the customer always sees a number.
  renderCard({ ...baseProduct, effective_shipping_fee: 60 });
  expect(screen.queryByText(/delivery/i)).not.toBeInTheDocument();
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

test('a non-promo product does not advertise "Free delivery"', () => {
  renderCard({ ...baseProduct, free_shipping: false, effective_shipping_fee: 60 });
  expect(screen.queryByText(/delivery/i)).not.toBeInTheDocument();
  expect(screen.queryByText('Free delivery')).not.toBeInTheDocument();
});
