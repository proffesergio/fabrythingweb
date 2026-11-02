import { act, render, screen } from '@testing-library/react';
import { Provider } from 'react-redux';
import { MemoryRouter } from 'react-router-dom';
import { configureStore, createSlice } from '@reduxjs/toolkit';
import Layout from './layout';

// Regression test for an empty admin sidebar after logging in.
//
// App.js builds the router inside useMemo(..., []) and the admin branch was
// `element: <Layout sidebarList={items}/>` where `items` is redux menu state.
// A React element freezes its props at creation, so the router captured
// whatever `items` was on the FIRST render — which for a logged-out visitor is
// `[]` (cachedMenus() returns [] with no token). Logging in navigates via
// react-router without remounting App, so the memo never recomputed and the
// admin panel rendered with no navigation at all until a hard reload.
//
// The fix is for Layout to read the menu from the store rather than receive a
// snapshot through a memoised element.

jest.mock('./style.scss', () => ({}), { virtual: true });
jest.mock('../components/BrandLogo', () => ({ __esModule: true, default: () => <div /> }));
jest.mock('react-router-dom', () => ({
  ...jest.requireActual('react-router-dom'),
  Outlet: () => <div data-testid="outlet" />,
  useNavigate: () => jest.fn(),
  useLocation: () => ({ pathname: '/admin/home' }),
}));

const MENU = [
  { id: 1, module_name: 'Dashboard', module_url: '/home', module_icon: 'Dashboard', submenus: [] },
  { id: 2, module_name: 'Product Import', module_url: null, module_icon: 'CloudDownload',
    submenus: [{ id: 3, module_name: 'Import from Arogga', module_url: '/manage/import/arogga', module_icon: 'Inventory' }] },
];

const makeStore = (items) => {
  const slice = createSlice({
    name: 'data',
    initialState: { items, status: 'idle', error: null },
    reducers: {
      expandItem: () => {}, activateItem: () => {}, triggerPageChange: () => {},
      setItems: (state, action) => { state.items = action.payload; },
    },
  });
  const store = configureStore({
    reducer: { sidebardata: slice.reducer, isLoggedInReducer: () => ({ isLoggedIn: true }) },
  });
  return { store, setItems: slice.actions.setItems };
};

const renderLayout = (store) =>
  render(
    <Provider store={store}>
      <MemoryRouter><Layout /></MemoryRouter>
    </Provider>,
  );

// The shell renders the drawer twice (mobile + desktop), so a menu label can
// legitimately appear more than once — assert presence, not uniqueness.
const menuLabels = () => screen.queryAllByText('Product Import').length;

test('renders the menu that is in the store', () => {
  const { store } = makeStore(MENU);
  renderLayout(store);
  expect(screen.queryAllByText('Dashboard').length).toBeGreaterThan(0);
  expect(menuLabels()).toBeGreaterThan(0);
});

test('picks up menus that arrive AFTER the first render', () => {
  // The actual bug: the store starts empty (logged-out visitor), the admin
  // logs in, fetchSidebar() resolves, and the sidebar must fill in.
  const { store, setItems } = makeStore([]);
  renderLayout(store);
  expect(menuLabels()).toBe(0);

  act(() => { store.dispatch(setItems(MENU)); });
  expect(menuLabels()).toBeGreaterThan(0);
  expect(screen.queryAllByText('Dashboard').length).toBeGreaterThan(0);
});

test('an empty menu renders a sidebar rather than crashing', () => {
  const { store } = makeStore([]);
  expect(() => renderLayout(store)).not.toThrow();
});
