import { render, screen } from '@testing-library/react';
import { Provider } from 'react-redux';
import { configureStore } from '@reduxjs/toolkit';
import { MemoryRouter } from 'react-router-dom';
import cartReducer from '../../redux/reducer/cartSlice';
import StorefrontLayout, { getActiveBottomNavTab } from './StorefrontLayout';

jest.mock('../../hooks/APIHandler', () => () => ({ callApi: jest.fn().mockResolvedValue({ data: {} }), loading: false }));

// Bottom nav only renders once `isMobile` (theme.breakpoints.down('md')) is
// true, which MUI's useMediaQuery derives from window.matchMedia. jsdom has
// no real viewport, so force every query to match — the same effect as
// viewing the page on a phone. This has to be re-applied in beforeEach, not
// beforeAll: react-scripts' jest config sets `resetMocks: true`, which wipes
// jest.fn() mockImplementations before every test.
beforeEach(() => {
  Object.defineProperty(window, 'matchMedia', {
    writable: true,
    value: jest.fn().mockImplementation(query => ({
      matches: true,
      media: query,
      onchange: null,
      addListener: jest.fn(),
      removeListener: jest.fn(),
      addEventListener: jest.fn(),
      removeEventListener: jest.fn(),
      dispatchEvent: jest.fn(),
    })),
  });
});

const store = configureStore({ reducer: { cart: cartReducer } });

const renderAt = (pathname) =>
  render(
    <Provider store={store}>
      <MemoryRouter initialEntries={[pathname]}>
        <StorefrontLayout />
      </MemoryRouter>
    </Provider>
  );

// getActiveBottomNavTab is the pure route->tab mapping the component's
// `value` prop is derived from — pinned directly so the mapping can't drift
// silently the way the missing `value` prop did before this fix.
describe('getActiveBottomNavTab', () => {
  test('maps the homepage to home', () => {
    expect(getActiveBottomNavTab('/')).toBe('home');
  });

  test('maps /shop and product browsing routes to shop', () => {
    expect(getActiveBottomNavTab('/shop')).toBe('shop');
    expect(getActiveBottomNavTab('/product/some-slug')).toBe('shop');
  });

  test('maps /cart to cart', () => {
    expect(getActiveBottomNavTab('/cart')).toBe('cart');
  });

  test('maps account routes to account', () => {
    expect(getActiveBottomNavTab('/account')).toBe('account');
    expect(getActiveBottomNavTab('/account/orders')).toBe('account');
  });

  test('routes matching no tab (e.g. checkout) return false so nothing highlights', () => {
    expect(getActiveBottomNavTab('/checkout')).toBe(false);
  });
});

// The footer also has a "Shop" heading and shop-category links, so text
// queries must be scoped to actual buttons — BottomNavigationAction is the
// only "Shop"/"Home"/"Cart"/"Account" text that renders as a <button>.
describe('StorefrontLayout bottom navigation', () => {
  test('highlights Home on /', async () => {
    renderAt('/');
    expect(await screen.findByRole('button', { name: 'Home' })).toHaveClass('Mui-selected');
    expect(screen.getByRole('button', { name: 'Shop' })).not.toHaveClass('Mui-selected');
  });

  test('highlights Shop on /shop', async () => {
    renderAt('/shop');
    expect(await screen.findByRole('button', { name: 'Shop' })).toHaveClass('Mui-selected');
    expect(screen.getByRole('button', { name: 'Home' })).not.toHaveClass('Mui-selected');
  });

  test('highlights Cart on /cart', async () => {
    renderAt('/cart');
    expect(await screen.findByRole('button', { name: 'Cart' })).toHaveClass('Mui-selected');
  });

  test('highlights nothing on a route with no tab, e.g. /checkout', async () => {
    renderAt('/checkout');
    expect(await screen.findByRole('button', { name: 'Home' })).not.toHaveClass('Mui-selected');
    expect(screen.getByRole('button', { name: 'Shop' })).not.toHaveClass('Mui-selected');
    expect(screen.getByRole('button', { name: 'Cart' })).not.toHaveClass('Mui-selected');
    expect(screen.getByRole('button', { name: 'Account' })).not.toHaveClass('Mui-selected');
  });
});
