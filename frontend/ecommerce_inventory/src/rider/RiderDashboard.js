import { useEffect, useState, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import {
    Box, Container, AppBar, Toolbar, Typography, Switch, FormControlLabel, Card, Stack,
    Button, Chip, IconButton, Divider, CircularProgress, Avatar,
} from "@mui/material";
import LogoutIcon from "@mui/icons-material/Logout";
import TwoWheelerIcon from "@mui/icons-material/TwoWheeler";
import { toast } from "react-toastify";
import useApi from "../hooks/APIHandler";

const NEXT = {
    OUT_FOR_DELIVERY: ["DELIVERED", "Mark delivered"],
    PREPARING: ["OUT_FOR_DELIVERY", "Picked up"],
    CONFIRMED: ["OUT_FOR_DELIVERY", "Picked up"],
};

export default function RiderDashboard() {
    const { callApi } = useApi();
    const navigate = useNavigate();
    const [me, setMe] = useState(null);
    const [orders, setOrders] = useState([]);
    const [loading, setLoading] = useState(true);

    const load = useCallback(async () => {
        const [m, o] = await Promise.all([
            callApi({ url: "food/rider/me/", method: "GET", silent: true }),
            callApi({ url: "food/rider/orders/", method: "GET", silent: true }),
        ]);
        setMe(m?.status === 200 ? m.data.data : null);
        setOrders(o?.data?.data || []);
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
    const logout = () => { localStorage.removeItem("token"); navigate("/auth/login"); };

    if (loading) return <Box sx={{ textAlign: "center", py: 10 }}><CircularProgress /></Box>;
    if (!me) return (
        <Box sx={{ textAlign: "center", py: 10 }}>
            <Typography variant="h6">Rider access required</Typography>
            <Typography color="text.secondary" sx={{ mb: 2 }}>Log in with your rider account.</Typography>
            <Button variant="contained" onClick={() => navigate("/auth/login")}>Log in</Button>
        </Box>
    );

    return (
        <Box sx={{ minHeight: "100vh", bgcolor: "#FDF8F3" }}>
            <AppBar position="sticky" color="default" elevation={1} sx={{ bgcolor: "#fff" }}>
                <Toolbar>
                    <TwoWheelerIcon sx={{ mr: 1, color: "#E8452B" }} />
                    <Typography variant="h6" sx={{ flexGrow: 1, fontWeight: 800 }}>Rider</Typography>
                    <IconButton onClick={logout}><LogoutIcon /></IconButton>
                </Toolbar>
            </AppBar>
            <Container maxWidth="sm" sx={{ py: 3 }}>
                <Card sx={{ p: 2.5, mb: 2 }}>
                    <Stack direction="row" alignItems="center" spacing={2}>
                        <Avatar sx={{ bgcolor: "#E8452B", width: 48, height: 48 }}>{(me.name || "?")[0]}</Avatar>
                        <Box sx={{ flexGrow: 1 }}>
                            <Typography fontWeight={800}>{me.name}</Typography>
                            <Typography variant="caption" color="text.secondary">{me.rider_code} · {me.total_deliveries} deliveries · ৳{me.total_earnings} earned</Typography>
                        </Box>
                        <FormControlLabel labelPlacement="top" control={<Switch checked={me.is_available} onChange={(e) => toggle(e.target.checked)} />}
                            label={<Typography variant="caption">{me.is_available ? "Online" : "Offline"}</Typography>} />
                    </Stack>
                </Card>

                <Typography variant="h6" sx={{ mb: 1 }}>Your deliveries</Typography>
                {orders.length === 0 && <Typography color="text.secondary" sx={{ py: 4, textAlign: "center" }}>No active deliveries right now.</Typography>}
                {orders.map((o) => {
                    const next = NEXT[o.status];
                    return (
                        <Card key={o.id} sx={{ p: 2, mb: 1.5 }}>
                            <Stack direction="row" justifyContent="space-between" alignItems="center">
                                <Box><Typography fontWeight={800}>{o.order_code}</Typography>
                                    <Typography variant="body2" color="text.secondary">{o.restaurant_name} → {o.guest_name}</Typography></Box>
                                <Chip size="small" label={o.status.replace(/_/g, " ")} />
                            </Stack>
                            <Typography variant="body2" sx={{ mt: 1 }}>{o.delivery_address}</Typography>
                            <Typography variant="caption" color="text.secondary">{o.guest_phone} · ৳{o.total} ({o.payment_method})</Typography>
                            <Divider sx={{ my: 1 }} />
                            {next && <Button fullWidth variant="contained" onClick={() => advance(o.id, next[0])}>{next[1]}</Button>}
                        </Card>
                    );
                })}
            </Container>
        </Box>
    );
}
