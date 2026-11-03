import { render, screen } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import AdminRoute from './AdminRoute';
import { getUser, isAuthenticated } from './Helper';

jest.mock('./Helper', () => ({ getUser: jest.fn(), isAuthenticated: jest.fn() }));

const mount = () => render(<MemoryRouter initialEntries={['/admin/manage/users']}><Routes>
  <Route path="/admin/*" element={<AdminRoute element={<div>ADMIN CONTENT</div>} />} />
  <Route path="/admin/auth" element={<div>ADMIN LOGIN</div>} />
  <Route path="/" element={<div>SHOP</div>} />
  <Route path="/rider" element={<div>RIDER</div>} />
  <Route path="/vendor/orders" element={<div>VENDOR</div>} />
</Routes></MemoryRouter>);

test('anonymous visitors reach login before the admin shell mounts', () => {
  isAuthenticated.mockReturnValue(false);
  mount();
  expect(screen.getByText('ADMIN LOGIN')).toBeInTheDocument();
  expect(screen.queryByText('ADMIN CONTENT')).not.toBeInTheDocument();
});

test.each(['Admin', 'Super Admin', 'Staff'])('%s can enter the admin shell', (role) => {
  isAuthenticated.mockReturnValue(true); getUser.mockReturnValue({ role });
  mount(); expect(screen.getByText('ADMIN CONTENT')).toBeInTheDocument();
});

test.each([['Customer', 'SHOP'], ['Rider', 'RIDER'], ['Restaurant', 'VENDOR'], ['Unknown', 'SHOP']])('%s is kept out of admin routes', (role, destination) => {
  isAuthenticated.mockReturnValue(true); getUser.mockReturnValue({ role });
  mount(); expect(screen.getByText(destination)).toBeInTheDocument();
  expect(screen.queryByText('ADMIN CONTENT')).not.toBeInTheDocument();
});
