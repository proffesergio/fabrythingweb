import { Navigate } from 'react-router-dom';
import { getUser, isAuthenticated } from './Helper';

// UX boundary only. The API independently verifies permissions and tenant scope.
export default function AdminRoute({ element }) {
  if (!isAuthenticated()) return <Navigate to="/admin/auth" replace />;
  const role = getUser()?.role;
  if (['Admin', 'Super Admin', 'Staff'].includes(role)) return element;
  const home = role === 'Rider' ? '/rider' : role === 'Restaurant' ? '/vendor/orders' : '/';
  return <Navigate to={home} replace />;
}
