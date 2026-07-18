import './App.css';
import Home from './pages/Home';
import Layout from './layout/layout';
import {RouterProvider, createBrowserRouter} from 'react-router-dom'
import ProtectedRoute from './utils/ProtectedRoute';
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
import Error404Page from './pages/Error404Page';
import ManageWarhouse from './pages/warehouse/ManageWarehouse';
import ManageUsers from './pages/users/ManageUsers';
import ManageModuleUrls from './pages/module/ManageModuleUrls';
import CreatePurchaseOrder from './pages/purchaseorder/CreatePurchaseOrder';
import ManagePurchaseOrder from './pages/purchaseorder/ManagePurchaseOrder';
import ManageSalesOrder from './pages/salesorder/ManageSalesOrder';

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
          {path:"manage/warehouse",element:<ProtectedRoute element={<ManageWarhouse/>}/>},
          {path:"manage/users",element:<ProtectedRoute element={<ManageUsers/>}/>},
          {path:"manage/moduleurls",element:<ProtectedRoute element={<ManageModuleUrls/>}/>},
          {path:"create/po",element:<ProtectedRoute element={<CreatePurchaseOrder/>}/>},
          {path:"create/po/:id",element:<ProtectedRoute element={<CreatePurchaseOrder/>}/>},
          {path:"manage/purchaseorder",element:<ProtectedRoute element={<ManagePurchaseOrder/>}/>},
          {path:"manage/salesorder",element:<ProtectedRoute element={<ManageSalesOrder/>}/>},
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
