import './App.css';
import Home from './pages/Home';
import Layout from './layout/layout';
import {RouterProvider, createBrowserRouter} from 'react-router-dom'
import ProtectedRoute from './utils/ProtectedRoute';
import VendorRoute from './utils/VendorRoute';
import {ToastContainer} from 'react-toastify';
import Auth from './pages/Auth';
import { useSelector } from 'react-redux';
import { fetchSidebar } from './redux/reducer/sidebardata';
import { useEffect } from 'react';
import { useDispatch } from 'react-redux';
import DynamicForm from './pages/DynamicForm';
import 'react-toastify/dist/ReactToastify.css';
import './style/style.css';
import ManageCategories from './pages/category/ManageCategories';
import ManageProducts from './pages/products/ManageProducts';
import ImportProducts from './pages/products/ImportProducts';
import Error404Page from './pages/Error404Page';
import ManageWarhouse from './pages/warehouse/ManageWarehouse';
import ManageUsers from './pages/users/ManageUsers';
import ManageModuleUrls from './pages/module/ManageModuleUrls';
import CreatePurchaseOrder from './pages/purchaseorder/CreatePurchaseOrder';
import ManagePurchaseOrder from './pages/purchaseorder/ManagePurchaseOrder';
import ManageSalesOrder from './pages/salesorder/ManageSalesOrder';
import ManageRestaurants from './pages/food/ManageRestaurants';
import ManageZones from './pages/food/ManageZones';
import FoodDashboard from './pages/food/FoodDashboard';
import ManageFoodOrders from './pages/food/ManageFoodOrders';
import FoodMenuManager from './pages/food/FoodMenuManager';
import RestaurantDetailAdmin from './pages/food/RestaurantDetailAdmin';
import ManageCustomers from './pages/customers/ManageCustomers';
import ManageCoupons from './pages/food/ManageCoupons';
import ManageRiders from './pages/food/ManageRiders';
import FoodPayments from './pages/food/FoodPayments';
import PartnerApplications from './pages/food/PartnerApplications';
import RiderCash from './pages/food/RiderCash';
import ChatInbox from './pages/chat/ChatInbox';
import ManageBanners from './pages/banners/ManageBanners';
import RiderDashboard from './rider/RiderDashboard';
import RiderLogin from './rider/RiderLogin';

// Storefront imports
import { ThemeProvider } from '@mui/material/styles';
import { getStorefrontTheme } from './storefront/theme';
import StorefrontLayout from './storefront/layout/StorefrontLayout';
import HomePage from './storefront/pages/HomePage';
import ProductCatalog from './storefront/pages/ProductCatalog';
import ProductDetail from './storefront/pages/ProductDetail';
import CartPage from './storefront/pages/CartPage';
import CheckoutPage from './storefront/pages/CheckoutPage';
import CustomerAuth from './storefront/pages/CustomerAuth';
import CustomerAccount from './storefront/pages/CustomerAccount';
import { useMemo, useState } from 'react';

// Vendor (Restaurant-role) dashboard imports
import VendorLayout from './vendor/VendorLayout';
import VendorRestaurant from './vendor/VendorRestaurant';
import VendorMenu from './vendor/VendorMenu';
import VendorOrders from './vendor/VendorOrders';

// Food delivery app (separate themed experience mounted at /food)
import { FoodThemeProvider } from './food/context/FoodThemeContext';
import { FoodLocationProvider } from './food/context/FoodLocationContext';
import FoodLayout from './food/layout/FoodLayout';
import FoodHome from './food/pages/FoodHome';
import RestaurantDetail from './food/pages/RestaurantDetail';
import FoodCartPage from './food/pages/FoodCartPage';
import BrowseRestaurants from './food/pages/BrowseRestaurants';
import FoodCheckout from './food/pages/FoodCheckout';
import FoodOrderTrack from './food/pages/FoodOrderTrack';
import FoodMyOrders from './food/pages/FoodMyOrders';
import BecomePartner from './food/pages/BecomePartner';

// Wraps the storefront with a dark-mode-aware theme.
// Lives inside the router so it re-renders cleanly on toggle.
function StorefrontWrapper() {
  const [darkMode, setDarkMode] = useState(
    () => localStorage.getItem('sf_dark') === 'true'
  );
  const theme = useMemo(
    () => getStorefrontTheme(darkMode ? 'dark' : 'light'),
    [darkMode]
  );
  const toggleDarkMode = () =>
    setDarkMode(d => {
      localStorage.setItem('sf_dark', String(!d));
      return !d;
    });

  return (
    <ThemeProvider theme={theme}>
      <StorefrontLayout toggleDarkMode={toggleDarkMode} darkMode={darkMode} />
    </ThemeProvider>
  );
}

// Food delivery app shell: its own dark theme + location provider + layout,
// mounted OUTSIDE the storefront wrapper so selecting "Food" switches the whole UI.
function FoodApp() {
  // FoodThemeProvider owns the MUI ThemeProvider so the light/dark toggle in the
  // header can re-create the theme; it persists the choice in localStorage.
  return (
    <FoodThemeProvider>
      <FoodLocationProvider><FoodLayout /></FoodLocationProvider>
    </FoodThemeProvider>
  );
}

function StorefrontAuthTheme({ children }) {
  const theme = useMemo(
    () => getStorefrontTheme(localStorage.getItem('sf_dark') === 'true' ? 'dark' : 'light'),
    []
  );
  return <ThemeProvider theme={theme}>{children}</ThemeProvider>;
}

function App() {
  const {status,error,items}=useSelector(state=>state.sidebardata);
  const {isLoggedIn}=useSelector(state=>state.isLoggedInReducer);
  const dispatch=useDispatch();

  useEffect(()=>{
    if(status=='idle'){
      dispatch(fetchSidebar());
    }
  },[status,dispatch])

  useEffect(()=>{
    if(isLoggedIn){
      dispatch(fetchSidebar());
    }
  },[isLoggedIn])

  const router=createBrowserRouter(
    [
      // ── Storefront Routes ──
      {
        path:"/",
        element:<StorefrontWrapper/>,
        children:[
          {index:true,element:<HomePage/>},
          {path:"shop",element:<ProductCatalog/>},
          {path:"product/:slug",element:<ProductDetail/>},
          {path:"cart",element:<CartPage/>},
          {path:"checkout",element:<CheckoutPage/>},
          {path:"account",element:<ProtectedRoute element={<CustomerAccount/>}/>},
          {path:"account/orders",element:<ProtectedRoute element={<CustomerAccount/>}/>},
        ]
      },
      // Storefront Auth (standalone page, no layout)
      {path:"/auth/login",element:<StorefrontAuthTheme><CustomerAuth/></StorefrontAuthTheme>},
      {path:"/auth/signup",element:<StorefrontAuthTheme><CustomerAuth/></StorefrontAuthTheme>},

      // ── Food Delivery Routes (separate themed app) ──
      {
        path:"/food",
        element:<FoodApp/>,
        children:[
          {index:true,element:<FoodHome/>},
          {path:"restaurants",element:<BrowseRestaurants/>},
          {path:"restaurant/:slug",element:<RestaurantDetail/>},
          {path:"cart",element:<FoodCartPage/>},
          {path:"checkout",element:<FoodCheckout/>},
          {path:"order/:code",element:<FoodOrderTrack/>},
          // Not ProtectedRoute: that navigates away to the standalone /auth/login
          // page, which drops the food layout — and with it the bottom tab bar,
          // stranding a signed-out phone user on a bare form. FoodMyOrders renders
          // its own sign-in prompt inside the layout instead.
          {path:"orders",element:<FoodMyOrders/>},
          // Public by design — the approval gate is the PENDING status, not auth.
          {path:"partner",element:<BecomePartner/>},
        ]
      },

      // ── Vendor Routes (restaurant-owner dashboard) ──
      // Gated by role, not just auth: VendorRoute decodes the JWT (see utils/VendorRoute.js)
      // and requires role === 'Restaurant'. The backend independently enforces owner-scoping
      // on every vendor/* endpoint (request.user.restaurant), so this gate is UX only, not
      // the security boundary.
      {
        path:"/vendor",
        element:<VendorRoute element={<VendorLayout/>}/>,
        children:[
          {index:true,element:<VendorRestaurant/>},
          {path:"menu",element:<VendorMenu/>},
          {path:"orders",element:<VendorOrders/>},
        ]
      },

      // ── Rider dashboard (role: Rider) ──
      // Riders get their own login route. Routing them through the customer page
      // at /auth/login sent them to the storefront homepage after signing in,
      // because that page defaults its post-login redirect to "/".
      {path:"/rider/login",element:<RiderLogin/>},
      {path:"/rider",element:<ProtectedRoute element={<RiderDashboard/>}/>},

      // ── Admin Routes ──
      {path:"/admin/auth",element:<Auth/>},
      {
        path:"/admin",
        element:<Layout sidebarList={items}/>,
        errorElement:<Layout sidebarList={items} childPage={<Error404Page/>}/>,
        children:[
          {index:true,element:<ProtectedRoute element={<Home/>}/>},
          {path:"home",element:<ProtectedRoute element={<Home/>}/>},
          {path:"form/:formName",element:<ProtectedRoute element={<DynamicForm/>}/>},
          {path:"form/:formName/:id",element:<ProtectedRoute element={<DynamicForm/>}/>},
          {path:"manage/category",element:<ProtectedRoute element={<ManageCategories/>}/>},
          {path:"manage/product",element:<ProtectedRoute element={<ManageProducts/>}/>},
          {path:"manage/product-import",element:<ProtectedRoute element={<ImportProducts/>}/>},
          {path:"manage/warehouse",element:<ProtectedRoute element={<ManageWarhouse/>}/>},
          {path:"manage/users",element:<ProtectedRoute element={<ManageUsers/>}/>},
          {path:"manage/moduleurls",element:<ProtectedRoute element={<ManageModuleUrls/>}/>},
          {path:"create/po",element:<ProtectedRoute element={<CreatePurchaseOrder/>}/>},
          {path:"create/po/:id",element:<ProtectedRoute element={<CreatePurchaseOrder/>}/>},
          {path:"manage/purchaseorder",element:<ProtectedRoute element={<ManagePurchaseOrder/>}/>},
          {path:"manage/salesorder",element:<ProtectedRoute element={<ManageSalesOrder/>}/>},
          {path:"manage/customers",element:<ProtectedRoute element={<ManageCustomers/>}/>},
          {path:"manage/food/dashboard",element:<ProtectedRoute element={<FoodDashboard/>}/>},
          {path:"manage/food/restaurants",element:<ProtectedRoute element={<ManageRestaurants/>}/>},
          {path:"manage/food/restaurants/:id",element:<ProtectedRoute element={<RestaurantDetailAdmin/>}/>},
          {path:"manage/food/zones",element:<ProtectedRoute element={<ManageZones/>}/>},
          {path:"manage/food/orders",element:<ProtectedRoute element={<ManageFoodOrders/>}/>},
          {path:"manage/food/menu",element:<ProtectedRoute element={<FoodMenuManager/>}/>},
          {path:"manage/food/coupons",element:<ProtectedRoute element={<ManageCoupons/>}/>},
          {path:"manage/food/riders",element:<ProtectedRoute element={<ManageRiders/>}/>},
          {path:"manage/food/payments",element:<ProtectedRoute element={<FoodPayments/>}/>},
          {path:"manage/food/partners",element:<ProtectedRoute element={<PartnerApplications/>}/>},
          {path:"manage/food/rider-cash",element:<ProtectedRoute element={<RiderCash/>}/>},
          {path:"manage/chat/inbox",element:<ProtectedRoute element={<ChatInbox/>}/>},
          {path:"manage/banners",element:<ProtectedRoute element={<ManageBanners/>}/>},
          {path:"*",element:<Error404Page/>},
        ]},
    ]
  )

  return (
    <>
        <RouterProvider router={router}/>
        <ToastContainer position="bottom-right" theme='colored' autoclose={3000} hideProgressBar={false} style={{marginBottom:'30px'}}/>
    </>
  );
}

export default App;
