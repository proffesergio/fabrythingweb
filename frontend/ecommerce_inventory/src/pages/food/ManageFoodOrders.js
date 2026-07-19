import { useEffect, useState, useCallback } from "react";
import {
    Box, Typography, Tabs, Tab, Table, TableBody, TableCell, TableHead, TableRow, Paper,
    TableContainer, Chip, LinearProgress, Drawer, Stack, Divider, Button, IconButton,
} from "@mui/material";
import CloseIcon from "@mui/icons-material/Close";
import { toast } from "react-toastify";
import useApi from "../../hooks/APIHandler";

const STATUS_COLORS = {
    PLACED: "warning", CONFIRMED: "info", PREPARING: "secondary",
    OUT_FOR_DELIVERY: "primary", DELIVERED: "success", CANCELLED: "error",
};
const STATUS_TABS = ["", "PLACED", "CONFIRMED", "PREPARING", "OUT_FOR_DELIVERY", "DELIVERED", "CANCELLED"];
const LABELS = {
    CONFIRMED: "Confirm", PREPARING: "Start preparing", OUT_FOR_DELIVERY: "Send out",
    DELIVERED: "Mark delivered", CANCELLED: "Cancel",
};

export default function ManageFoodOrders() {
    const { callApi, loading } = useApi();
    const [orders, setOrders] = useState([]);
    const [status, setStatus] = useState("");
    const [detail, setDetail] = useState(null);

    const fetchOrders = useCallback(async (st) => {
        const params = {};
        if (st) params.status = st;
        const res = await callApi({ url: "food/admin/orders/", method: "GET", params });
        if (res?.status === 200) setOrders(res.data.data || []);
    }, []); // eslint-disable-line react-hooks/exhaustive-deps

    useEffect(() => { fetchOrders(status); }, [status, fetchOrders]);

    const openDetail = async (id) => {
        const res = await callApi({ url: `food/admin/orders/${id}/`, method: "GET" });
        if (res?.status === 200) setDetail(res.data.data);
    };

    const advance = async (newStatus) => {
        const res = await callApi({
            url: `food/admin/orders/${detail.id}/status/`, method: "PATCH", body: { status: newStatus },
        });
        if (res?.status === 200) {
            toast.success(`Order ${newStatus.toLowerCase()}`);
            await openDetail(detail.id);
            fetchOrders(status);
        }
    };

    return (
        <Box>
            <Typography variant="h5" fontWeight={800} sx={{ mb: 2 }}>Food Orders</Typography>
            <Tabs value={status} onChange={(_, v) => setStatus(v)} variant="scrollable" sx={{ mb: 2 }}>
                {STATUS_TABS.map((s) => <Tab key={s || "all"} label={s ? s.replace(/_/g, " ") : "All"} value={s} />)}
            </Tabs>
            {loading && <LinearProgress />}
            <TableContainer component={Paper}>
                <Table>
                    <TableHead>
                        <TableRow>
                            <TableCell>Code</TableCell><TableCell>Restaurant</TableCell>
                            <TableCell>Customer</TableCell><TableCell>Total</TableCell><TableCell>Status</TableCell>
                        </TableRow>
                    </TableHead>
                    <TableBody>
                        {orders.length === 0 && !loading && (
                            <TableRow><TableCell colSpan={5} align="center">No orders</TableCell></TableRow>
                        )}
                        {orders.map((o) => (
                            <TableRow key={o.id} hover sx={{ cursor: "pointer" }} onClick={() => openDetail(o.id)}>
                                <TableCell>{o.order_code}</TableCell>
                                <TableCell>{o.restaurant_name}</TableCell>
                                <TableCell>{o.guest_name}</TableCell>
                                <TableCell>৳{o.total}</TableCell>
                                <TableCell><Chip size="small" label={o.status} color={STATUS_COLORS[o.status] || "default"} /></TableCell>
                            </TableRow>
                        ))}
                    </TableBody>
                </Table>
            </TableContainer>

            <Drawer anchor="right" open={!!detail} onClose={() => setDetail(null)}
                PaperProps={{ sx: { width: { xs: "100%", sm: 420 }, p: 3 } }}>
                {detail && (
                    <Box>
                        <Stack direction="row" justifyContent="space-between" alignItems="center">
                            <Typography variant="h6">{detail.order_code}</Typography>
                            <IconButton onClick={() => setDetail(null)}><CloseIcon /></IconButton>
                        </Stack>
                        <Chip size="small" sx={{ my: 1 }} label={detail.status} color={STATUS_COLORS[detail.status] || "default"} />
                        <Typography variant="body2" color="text.secondary">{detail.restaurant_name}</Typography>
                        <Divider sx={{ my: 2 }} />
                        <Typography variant="subtitle2">Customer</Typography>
                        <Typography variant="body2">{detail.guest_name} · {detail.guest_phone}</Typography>
                        <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>{detail.delivery_address}</Typography>
                        <Typography variant="subtitle2" gutterBottom>Items</Typography>
                        {(detail.items || []).map((it) => (
                            <Stack key={it.id} direction="row" justifyContent="space-between">
                                <Typography variant="body2">{it.quantity}× {it.item_name}</Typography>
                                <Typography variant="body2">৳{it.line_total}</Typography>
                            </Stack>
                        ))}
                        <Divider sx={{ my: 1 }} />
                        <Stack direction="row" justifyContent="space-between">
                            <Typography fontWeight={700}>Total (COD)</Typography>
                            <Typography fontWeight={700}>৳{detail.total}</Typography>
                        </Stack>
                        <Divider sx={{ my: 2 }} />
                        <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
                            {(detail.allowed_transitions || []).map((s) => (
                                <Button key={s} size="small"
                                    variant={s === "CANCELLED" ? "outlined" : "contained"}
                                    color={s === "CANCELLED" ? "error" : "primary"}
                                    onClick={() => advance(s)}>
                                    {LABELS[s] || s}
                                </Button>
                            ))}
                        </Stack>
                    </Box>
                )}
            </Drawer>
        </Box>
    );
}
