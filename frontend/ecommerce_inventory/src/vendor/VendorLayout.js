import React from "react";
import { AppBar, Toolbar, Typography, Tabs, Tab, Box, IconButton, Container } from "@mui/material";
import { Logout } from "@mui/icons-material";
import { Outlet, useLocation, useNavigate } from "react-router-dom";
import { useDispatch } from "react-redux";
import { logout } from "../redux/reducer/IsLoggedInReducer";

// Slim, mobile-first layout for the vendor (restaurant-owner) dashboard.
// Deliberately lighter than the admin `Layout` (no theme switcher, no
// collapsible drawer) — vendors are expected to manage their storefront
// mostly from a phone with a slow connection.
const NAV_ITEMS = [
    { label: "Restaurant", path: "/vendor" },
    { label: "Menu", path: "/vendor/menu" },
    { label: "Orders", path: "/vendor/orders" },
];

const VendorLayout = () => {
    const location = useLocation();
    const navigate = useNavigate();
    const dispatch = useDispatch();

    const activeTab = NAV_ITEMS.some((item) => item.path === location.pathname)
        ? location.pathname
        : "/vendor";

    const handleLogout = () => {
        localStorage.removeItem("token");
        dispatch(logout());
        navigate("/auth/login");
    };

    return (
        <Box sx={{ minHeight: "100vh", display: "flex", flexDirection: "column", bgcolor: "background.default" }}>
            <AppBar position="sticky" color="default" elevation={1}>
                <Toolbar>
                    <Typography variant="h6" sx={{ flexGrow: 1, fontWeight: 700 }}>
                        Vendor Dashboard
                    </Typography>
                    <IconButton aria-label="logout" onClick={handleLogout} color="inherit">
                        <Logout />
                    </IconButton>
                </Toolbar>
                <Tabs
                    value={activeTab}
                    onChange={(_, value) => navigate(value)}
                    variant="fullWidth"
                >
                    {NAV_ITEMS.map((item) => (
                        <Tab key={item.path} label={item.label} value={item.path} />
                    ))}
                </Tabs>
            </AppBar>
            <Container maxWidth="md" component="main" sx={{ py: 2, flexGrow: 1 }}>
                <Outlet />
            </Container>
        </Box>
    );
};

export default VendorLayout;
