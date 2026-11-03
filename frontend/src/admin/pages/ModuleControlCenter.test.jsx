import { fireEvent, render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { Provider } from 'react-redux';
import { configureStore } from '@reduxjs/toolkit';
import ModuleControlCenter, { toolGroups } from './ModuleControlCenter';

jest.mock('./ShopOverview', () => () => <div>SHOP OPERATIONS</div>);
jest.mock('./FoodOverview', () => () => <div>FOOD OPERATIONS</div>);
jest.mock('./NewsOverview', () => () => <div>NEWS OPERATIONS</div>);
jest.mock('./PrintOverview', () => () => <div>PRINT OPERATIONS</div>);
jest.mock('./ShopControlCenter', () => () => <div>AUTOMATION</div>);
jest.mock('../../pages/Home', () => () => <div>BUSINESS REPORT</div>);
const menus = [
  { module: 'shop', module_name: 'Products', submenus: [{ module_name: 'Manage products', module_url: '/manage/product' }] },
  { module: 'food', module_name: 'Food orders', module_url: '/manage/food/orders' },
  { module: 'shared', module_name: 'Users', module_url: '/manage/users' },
];
function mount(module, search = '') {
  const store = configureStore({ reducer: { sidebardata: () => ({ items: menus, status: 'success' }) } });
  return render(<Provider store={store}><MemoryRouter initialEntries={[`/admin/${module}${search}`]}><ModuleControlCenter module={module} /></MemoryRouter></Provider>);
}
test.each([['shop', 'Shop', 'SHOP'], ['food', 'Food', 'FOOD'], ['news', 'News', 'NEWS'], ['print', 'Custom Printing', 'PRINT']])('one control center for %s', async (module, title, operations) => {
  mount(module);
  expect(screen.getByRole('heading', { level: 1, name: `${title} Control Center` })).toBeInTheDocument();
  expect(await screen.findByText(`${operations} OPERATIONS`)).toBeInTheDocument();
  expect(screen.queryByRole('tab', { name: 'Overview' })).not.toBeInTheDocument();
});
test('automation and business report remain available inside Shop', async () => {
  mount('shop', '?tab=automation');
  expect(await screen.findByText('AUTOMATION')).toBeInTheDocument();
  fireEvent.click(screen.getByRole('tab', { name: 'Business report' }));
  expect(await screen.findByText('BUSINESS REPORT')).toBeInTheDocument();
});
test('management tools use only granted module menus plus shared administration', () => {
  mount('shop', '?tab=tools');
  expect(screen.getByRole('link', { name: /Manage products/ })).toHaveAttribute('href', '/admin/manage/product');
  expect(screen.getByRole('link', { name: /Users/ })).toBeInTheDocument();
  expect(screen.queryByRole('link', { name: /Food orders/ })).not.toBeInTheDocument();
  fireEvent.change(screen.getByRole('textbox', { name: 'Find a management tool' }), { target: { value: 'Users' } });
  expect(screen.queryByRole('link', { name: /Manage products/ })).not.toBeInTheDocument();
});
test('ungranted tools are never invented', () => {
  expect(toolGroups([], 'shop')).toEqual({ module: [], shared: [] });
});
