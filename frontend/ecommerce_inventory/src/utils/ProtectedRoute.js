import { Navigate, useLocation } from "react-router-dom"
import { isAuthenticated } from "./Helper"

const ProtectedRoute=({element})=>{
    const location = useLocation();
    const isAdmin = location.pathname.startsWith('/admin');
    const loginPath = isAdmin ? '/admin/auth' : `/auth/login?redirect=${encodeURIComponent(location.pathname)}`;
    return isAuthenticated()?element:<Navigate to={loginPath}/>
}
export default ProtectedRoute
