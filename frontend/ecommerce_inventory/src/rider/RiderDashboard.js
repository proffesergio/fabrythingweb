import { useEffect, useState, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import {
    Box, Container, AppBar, Toolbar, Typography, Button, IconButton, CircularProgress,
} from "@mui/material";
import LogoutIcon from "@mui/icons-material/Logout";
import TwoWheelerIcon from "@mui/icons-material/TwoWheeler";
import { toast } from "react-toastify";
import useApi from "../hooks/APIHandler";
import RiderHeader from "./RiderHeader";
import EarningsPanel from "./EarningsPanel";
import DeliveryCard from "./DeliveryCard";
import useRiderHeartbeat from "./useRiderHeartbeat";
import BrandLogo from "../components/BrandLogo";

export default function RiderDashboard() {
    const { callApi } = useApi();
    const navigate = useNavigate();
    const [me, setMe] = useState(null);
    const [orders, setOrders] = useState([]);
    const [earnings, setEarnings] = useState(null);
    const [loading, setLoading] = useState(true);

    const online = !!me?.is_available;
    const { position, error: locationError } = useRiderHeartbeat(online);

    const load = useCallback(async () => {
        const [m, o, e] = await Promise.all([
            callApi({ url: "food/rider/me/", method: "GET", silent: true }),
            callApi({ url: "food/rider/orders/", method: "GET", silent: true }),
            callApi({ url: "food/rider/earnings/", method: "GET", silent: true }),
        ]);
        setMe(m?.status === 200 ? m.data.data : null);
        setOrders(o?.data?.data || []);
        setEarnings(e?.status === 200 ? e.data.data : null);
        setLoading(false);
    }, []); // eslint-disable-line react-hooks/exhaustive-deps
    useEffect(() => { load(); }, [load]);

    const toggle = async (v) => {
        const res = await callApi({ url: "food/rider/availability/", method: "POST", body: { is_available: v } });
        if (res?.status === 200) setMe((s) => ({ ...s, is_available: v }));
    };
    const advance = async (id, status) => {
        const res = await callApi({ url: `food/rider/orders/${id}/status/`, method: "PATCH", body: { status } });
        if (res?.status === 200) { toast.success("Updated"); load(); }
    };
    // Both of these used to point at "/auth/login" — the customer page, which
    // redirects to "/" after a successful login. That is the bounce riders hit:
    // dashboard fails to load → "Log in" → storefront homepage → never /rider.
    const logout = () => { localStorage.removeItem("token"); navigate("/rider/login"); };

    if (loading) return <Box sx={{ textAlign: "center", py: 10 }}><CircularProgress /></Box>;
    if (!me) return (
        <Box sx={{ textAlign: "center", py: 10 }}>
            <Typography variant="h6">Rider access required</Typography>
            <Typography color="text.secondary" sx={{ mb: 2 }}>Log in with your rider account.</Typography>
            <Button variant="contained" onClick={() => navigate("/rider/login")}>Log in</Button>
        </Box>
    );

    return (
        <Box sx={{ minHeight: "100vh", bgcolor: "#FDF8F3" }}>
            <AppBar position="sticky" color="default" elevation={1} sx={{ bgcolor: "#fff" }}>
                <Toolbar sx={{ gap: 1 }}>
                    {/* Food-module surface, and the bar is pinned white, so the
                        light-canvas Food mark is correct regardless of OS theme. */}
                    <BrandLogo brand="food" variant="horizontal" mode="light" height={24} />
                    <TwoWheelerIcon sx={{ color: "#E8452B" }} />
                    <Typography variant="h6" sx={{ flexGrow: 1, fontWeight: 800 }}>Rider</Typography>
                    <IconButton onClick={logout}><LogoutIcon /></IconButton>
                </Toolbar>
            </AppBar>
            <Container maxWidth="sm" sx={{ py: 3 }}>
                <RiderHeader me={me} online={online} onToggle={toggle} locationError={locationError} />
                <EarningsPanel earnings={earnings} />

                <Typography variant="h6" sx={{ mb: 1 }}>Your deliveries</Typography>
                {orders.length === 0 && (
                    <Typography color="text.secondary" sx={{ py: 4, textAlign: "center" }}>
                        No active deliveries right now.
                        {!online && " Go online to start receiving orders."}
                    </Typography>
                )}
                {orders.map((o) => (
                    <DeliveryCard key={o.id} order={o} riderPosition={position} onAdvance={advance} />
                ))}
            </Container>
        </Box>
    );
}
