import { Navigate, useLocation } from "react-router-dom"
import { isAuthenticated } from "./Helper"

// Each audience bounces to its OWN login screen. Sending riders to the customer
// page at /auth/login is what produced the redirect loop: that page defaults its
// post-login target to "/", so a rider signed in and landed on the storefront
// homepage instead of /rider.
const loginPathFor = (pathname) => {
    if (pathname.startsWith('/admin')) return '/admin/auth';
    if (pathname.startsWith('/rider')) return '/rider/login';
    return `/auth/login?redirect=${encodeURIComponent(pathname)}`;
}

const ProtectedRoute=({element})=>{
    const location = useLocation();
    return isAuthenticated()?element:<Navigate to={loginPathFor(location.pathname)}/>
}
export default ProtectedRoute
