import './App.css';
import Home from './pages/Home';
import Layout from './layout/layout';
import {RouterProvider, createBrowserRouter} from 'react-router-dom'
import ProtectedRoute from './utils/ProtectedRoute';
import VendorRoute from './utils/VendorRoute';
import {ToastContainer} from 'react-toastify';
import { useSelector } from 'react-redux';
import { fetchSidebar } from './redux/reducer/sidebardata';
import { Suspense, lazy, useEffect } from 'react';
import { useDispatch } from 'react-redux';
import 'react-toastify/dist/ReactToastify.css';
import './style/style.css';

// Storefront imports
import { ThemeProvider } from '@mui/material/styles';
import { getStorefrontTheme } from './storefront/theme';
import StorefrontLayout from './storefront/layout/StorefrontLayout';
import { PRIVACY, SHIPPING, TERMS } from './storefront/pages/legal/content';
import { useMemo, useState } from 'react';
import CircularProgress from '@mui/material/CircularProgress';
import AppSplash from './storefront/components/AppSplash';
import InstallPrompt from './storefront/components/InstallPrompt';
import Box from '@mui/material/Box';

// Vendor (Restaurant-role) dashboard imports
import VendorLayout from './vendor/VendorLayout';

// Food delivery app (separate themed experience mounted at /food)
import { FoodThemeProvider } from './food/context/FoodThemeContext';
import { FoodLocationProvider } from './food/context/FoodLocationContext';
import FoodLayout from './food/layout/FoodLayout';

// ── Code-split routes ────────────────────────────────────────────────
// Every page below loads as its own chunk. Before this, App.js imported all
// of them statically, so a customer opening the storefront homepage also
// downloaded the admin panel, the vendor panel, the rider dashboard, the MUI
// data grid, the charting library and the map before first paint.
// Declared after the imports because `import/first` is an error in this
// build, not a warning.
const Auth = lazy(() => import('./pages/Auth'));
const DynamicForm = lazy(() => import('./pages/DynamicForm'));
const ManageCategories = lazy(() => import('./pages/category/ManageCategories'));
const ManageProducts = lazy(() => import('./pages/products/ManageProducts'));
const ImportProducts = lazy(() => import('./pages/products/ImportProducts'));
const Error404Page = lazy(() => import('./pages/Error404Page'));
const ManageWarhouse = lazy(() => import('./pages/warehouse/ManageWarehouse'));
const ManageUsers = lazy(() => import('./pages/users/ManageUsers'));
const ManageModuleUrls = lazy(() => import('./pages/module/ManageModuleUrls'));
const CreatePurchaseOrder = lazy(() => import('./pages/purchaseorder/CreatePurchaseOrder'));
const ManagePurchaseOrder = lazy(() => import('./pages/purchaseorder/ManagePurchaseOrder'));
const ManageSalesOrder = lazy(() => import('./pages/salesorder/ManageSalesOrder'));
const ManageRestaurants = lazy(() => import('./pages/food/ManageRestaurants'));
const ManageZones = lazy(() => import('./pages/food/ManageZones'));
const FoodDashboard = lazy(() => import('./pages/food/FoodDashboard'));
const ManageFoodOrders = lazy(() => import('./pages/food/ManageFoodOrders'));
const FoodMenuManager = lazy(() => import('./pages/food/FoodMenuManager'));
const RestaurantDetailAdmin = lazy(() => import('./pages/food/RestaurantDetailAdmin'));
const ManageCustomers = lazy(() => import('./pages/customers/ManageCustomers'));
const ManageCoupons = lazy(() => import('./pages/food/ManageCoupons'));
const ManageRiders = lazy(() => import('./pages/food/ManageRiders'));
const FoodPayments = lazy(() => import('./pages/food/FoodPayments'));
const PartnerApplications = lazy(() => import('./pages/food/PartnerApplications'));
const RiderCash = lazy(() => import('./pages/food/RiderCash'));
const ChatInbox = lazy(() => import('./pages/chat/ChatInbox'));
const ManageBanners = lazy(() => import('./pages/banners/ManageBanners'));
const ManageAffiliateProducts = lazy(() => import('./pages/affiliate/ManageAffiliateProducts'));
const ManagePrintRequests = lazy(() => import('./pages/printing/ManagePrintRequests'));
const PrintSetup = lazy(() => import('./pages/printing/PrintSetup'));
const RiderDashboard = lazy(() => import('./rider/RiderDashboard'));
const RiderLogin = lazy(() => import('./rider/RiderLogin'));
const HomePage = lazy(() => import('./storefront/pages/HomePage'));
const ProductCatalog = lazy(() => import('./storefront/pages/ProductCatalog'));
const ProductDetail = lazy(() => import('./storefront/pages/ProductDetail'));
const CartPage = lazy(() => import('./storefront/pages/CartPage'));
const CheckoutPage = lazy(() => import('./storefront/pages/CheckoutPage'));
const CustomerAuth = lazy(() => import('./storefront/pages/CustomerAuth'));
const CustomerAccount = lazy(() => import('./storefront/pages/CustomerAccount'));
const CustomPrintingPage = lazy(() => import('./storefront/pages/CustomPrintingPage'));
const PrintRequestDetail = lazy(() => import('./storefront/pages/PrintRequestDetail'));
const DealsPage = lazy(() => import('./storefront/pages/DealsPage'));
const LegalPage = lazy(() => import('./storefront/pages/legal/LegalPage'));
const VendorRestaurant = lazy(() => import('./vendor/VendorRestaurant'));
const VendorMenu = lazy(() => import('./vendor/VendorMenu'));
const VendorOrders = lazy(() => import('./vendor/VendorOrders'));
const FoodHome = lazy(() => import('./food/pages/FoodHome'));
const RestaurantDetail = lazy(() => import('./food/pages/RestaurantDetail'));
const FoodCartPage = lazy(() => import('./food/pages/FoodCartPage'));
const BrowseRestaurants = lazy(() => import('./food/pages/BrowseRestaurants'));
const FoodCheckout = lazy(() => import('./food/pages/FoodCheckout'));
const FoodOrderTrack = lazy(() => import('./food/pages/FoodOrderTrack'));
const FoodMyOrders = lazy(() => import('./food/pages/FoodMyOrders'));
const BecomePartner = lazy(() => import('./food/pages/BecomePartner'));

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

// Shown while a route's JS chunk downloads. Every page below is code-split
// (see the `lazy(...)` declarations above): before this, a customer opening
// the storefront homepage also downloaded the admin panel, the vendor panel,
// the rider dashboard, the data grid, the charting library and the map -- all
// of it parsed before first paint.
function RouteFallback() {
  return (
    <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: '60vh' }}>
      <CircularProgress />
    </Box>
  );
}

function App() {
  // `items` was dropped here when Layout started subscribing to the store
  // itself — App no longer renders the menu, it only triggers the fetch.
  const {status,error}=useSelector(state=>state.sidebardata);
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

  const router=useMemo(()=>createBrowserRouter(
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
          {path:"custom-printing",element:<CustomPrintingPage/>},
          {path:"deals",element:<DealsPage/>},
          // Public, login-free URLs — both app stores require a reachable
          // privacy policy link, and it must not sit behind auth.
          {path:"privacy",element:<LegalPage doc={PRIVACY}/>},
          {path:"terms",element:<LegalPage doc={TERMS}/>},
          {path:"shipping",element:<LegalPage doc={SHIPPING}/>},
          // Not ProtectedRoute: an anonymous visitor can still land here (e.g. a
          // shared link) and the page itself prompts login for the parts that need it.
          {path:"custom-printing/requests/:id",element:<ProtectedRoute element={<PrintRequestDetail/>}/>},
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
        element:<Layout/>,
        errorElement:<Layout childPage={<Error404Page/>}/>,
        children:[
          {index:true,element:<ProtectedRoute element={<Home/>}/>},
          {path:"home",element:<ProtectedRoute element={<Home/>}/>},
          {path:"form/:formName",element:<ProtectedRoute element={<DynamicForm/>}/>},
          {path:"form/:formName/:id",element:<ProtectedRoute element={<DynamicForm/>}/>},
          {path:"manage/category",element:<ProtectedRoute element={<ManageCategories/>}/>},
          {path:"manage/product",element:<ProtectedRoute element={<ManageProducts/>}/>},
          {path:"manage/product-import",element:<ProtectedRoute element={<ImportProducts/>}/>},
          // Per-source entry points (sidebar: Import from Fabrilife / Arogga).
          // Same screen, source pre-selected and locked.
          {path:"manage/import/:sourceSlug",element:<ProtectedRoute element={<ImportProducts/>}/>},
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
          {path:"manage/affiliate",element:<ProtectedRoute element={<ManageAffiliateProducts/>}/>},
          {path:"manage/print/requests",element:<ProtectedRoute element={<ManagePrintRequests/>}/>},
          {path:"manage/print/setup",element:<ProtectedRoute element={<PrintSetup/>}/>},
          {path:"*",element:<Error404Page/>},
        ]},
    ]
  ), [])

  return (
    <>
        {/* Installed-app only: covers the handover from the system splash. */}
        <AppSplash/>
        {/* One boundary above the router catches every lazy route chunk. */}
        <Suspense fallback={<RouteFallback/>}>
          <RouterProvider router={router}/>
        </Suspense>
        <InstallPrompt/>
        <ToastContainer position="bottom-right" theme='colored' autoclose={3000} hideProgressBar={false} style={{marginBottom:'30px'}}/>
    </>
  );
}

export default App;
