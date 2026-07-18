import { Navigate, useLocation } from "react-router-dom"
import { isAuthenticated, getUser } from "./Helper"

// Gates /vendor/* to authenticated users whose JWT carries role === 'Restaurant'.
// The role claim is embedded server-side at login time (see storefront/views.py
// issue_tokens() and accounts/controllers/AuthController.py LoginAPIView — both
// set access['role'] = user.role), so it's available here purely by decoding the
// token already in localStorage; no extra API call needed.
//
// This is a UX gate, not the security boundary: every food/vendor/* endpoint
// independently scopes to request.user.restaurant on the backend
// (food/permissions.py::IsRestaurantOwner), so a non-vendor can't read/write
// another restaurant's data even if they bypassed this route guard.
const VendorRoute = ({ element }) => {
    const location = useLocation();

    if (!isAuthenticated()) {
        return <Navigate to={`/auth/login?redirect=${encodeURIComponent(location.pathname)}`} />;
    }

    const user = getUser();
    if (!user || user.role !== "Restaurant") {
        return <Navigate to="/" />;
    }

    return element;
};

export default VendorRoute;
