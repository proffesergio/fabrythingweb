import { render, screen, within } from '@testing-library/react';
import { Provider } from 'react-redux';
import { configureStore } from '@reduxjs/toolkit';
import { MemoryRouter } from 'react-router-dom';
import cartReducer from '../../redux/reducer/cartSlice';
import StorefrontLayout from './StorefrontLayout';

const mockCallApi = jest.fn();
jest.mock('../../hooks/APIHandler', () => () => ({ callApi: mockCallApi, loading: false }));

beforeEach(() => {
  mockCallApi.mockReset();
  mockCallApi.mockResolvedValue({ data: {} });
});

// Minimal store — avoids importing the full app store (see FoodLayout.test.js
// for the same rationale: keeps axios ESM / thunk wiring out of this render).
const store = configureStore({ reducer: { cart: cartReducer } });

const renderLayout = (path = '/') =>
  render(
    <Provider store={store}>
      <MemoryRouter initialEntries={[path]}>
        <StorefrontLayout />
      </MemoryRouter>
    </Provider>
  );

test('renders Facebook link to the fabrything page', async () => {
  renderLayout();
  const fb = await screen.findByRole('link', { name: /facebook/i });
  expect(fb).toHaveAttribute('href', 'https://www.facebook.com/fabrything');
  expect(fb).toHaveAttribute('target', '_blank');
});

test('desktop header excludes NobleSeek and Company footer links to its portal beside Product Journal', () => {
  renderLayout();
  const header = screen.getByRole('banner');
  expect(within(header).queryByRole('link', { name: /nobleseek|নোবেলসিক/i })).not.toBeInTheDocument();
  expect(header.querySelector('a[href*="nobleseek"]')).toBeNull();

  const company = screen.getByText('Company').parentElement;
  const journal = within(company).getByRole('link', { name: 'Product Journal' });
  const portal = within(company).getByRole('link', { name: 'NobleSeek' });
  expect(journal).toHaveAttribute('href', '/blog');
  expect(journal.nextElementSibling).toBe(portal);
  expect(portal).toHaveAttribute('href', 'https://nobleseek.fabrything.com');
  expect(screen.getAllByRole('link', { name: /nobleseek|নোবেলসিক/i })).toEqual([portal]);
});

test('renders Messenger link to the fabrything messenger', async () => {
  renderLayout();
  const messenger = await screen.findByRole('link', { name: /messenger/i });
  expect(messenger).toHaveAttribute('href', 'https://m.me/fabrything');
  expect(messenger).toHaveAttribute('target', '_blank');
});

test('footer phone and WhatsApp button use the same configured contact', async () => {
  mockCallApi.mockImplementation(({ url }) => Promise.resolve({
    data: { data: url === 'store/config/' ? { whatsapp_chat_number: '8801353529899' } : [] },
  }));
  renderLayout();

  expect(await screen.findByRole('link', { name: '+8801353529899' }))
    .toHaveAttribute('href', 'tel:+8801353529899');
  expect(await screen.findByRole('link', { name: /chat with us on whatsapp/i }))
    .toHaveAttribute('href', 'https://wa.me/8801353529899');
});

test.each([
  ['/privacy', 'Privacy Policy'],
  ['/terms', 'Terms of Use'],
  ['/shipping', 'Delivery & Shipping Conditions'],
])('keeps a descriptive title and canonical URL for %s', (path, title) => {
  renderLayout(path);
  expect(document.title).toBe(`${title} — Fabrything`);
  expect(document.querySelector('link[rel="canonical"]')).toHaveAttribute(
    'href', `https://www.fabrything.com${path}`,
  );
});


test.each(['/blog', '/blog/buying-guide'])('preserves editorial page metadata at %s', (path) => {
  document.title = 'Guide title — Fabrything Journal';
  renderLayout(path);
  expect(document.title).toBe('Guide title — Fabrything Journal');
});
