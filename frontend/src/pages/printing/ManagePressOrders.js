import { useEffect, useState, useCallback } from "react";
import {
    Box, Typography, Tabs, Tab, Table, TableBody, TableCell, TableHead, TableRow, Paper,
    TableContainer, Chip, LinearProgress, Drawer, Stack, Divider, Button, IconButton,
    TextField, Alert, MenuItem,
} from "@mui/material";
import CloseIcon from "@mui/icons-material/Close";
import { toast } from "react-toastify";
import useApi from "../../hooks/APIHandler";

const STATUS_COLORS = {
    PENDING_PAYMENT: "warning", ARTWORK_REVIEW: "info", IN_PRODUCTION: "secondary",
    READY_FOR_DISPATCH: "primary", SHIPPED: "default", DELIVERED: "success", CANCELLED: "error",
};
const STATUS_TABS = ["", "PENDING_PAYMENT", "ARTWORK_REVIEW", "IN_PRODUCTION", "READY_FOR_DISPATCH", "SHIPPED", "DELIVERED", "CANCELLED"];

// Next legal production step — mirrors PressOrder.ALLOWED_TRANSITIONS on the
// backend, which is the real enforcement; this is just what the button offers.
const NEXT_STATUS = {
    PENDING_PAYMENT: "ARTWORK_REVIEW",
    ARTWORK_REVIEW: "IN_PRODUCTION",
    IN_PRODUCTION: "READY_FOR_DISPATCH",
    READY_FOR_DISPATCH: "SHIPPED",
    SHIPPED: "DELIVERED",
};
const PAYMENT_STATUSES = ["PENDING", "PARTIAL", "PAID", "FAILED", "COD_DUE"];

export default function ManagePressOrders() {
    const { callApi, loading } = useApi();
    const [orders, setOrders] = useState([]);
    const [status, setStatus] = useState("");
    const [detail, setDetail] = useState(null);
    const [exportData, setExportData] = useState(null);
    const [notesDraft, setNotesDraft] = useState("");
    const [payForm, setPayForm] = useState({ payment_status: "PAID", payment_txn_id: "" });

    const fetchOrders = useCallback(async (st) => {
        const params = {};
        if (st) params.status = st;
        const res = await callApi({ url: "print/press/admin/orders/", method: "GET", params, rawError: true });
        if (res?.status === 200) setOrders(res.data.data);
        else toast.error("Could not load press orders.");
    }, []); // eslint-disable-line react-hooks/exhaustive-deps

    useEffect(() => { fetchOrders(status); }, [status, fetchOrders]);

    const openDetail = async (id) => {
        const res = await callApi({ url: `print/press/admin/orders/${id}/`, method: "GET", rawError: true });
        if (res?.status === 200) {
            setDetail(res.data.data);
            setNotesDraft(res.data.data.staff_notes || "");
            setPayForm({ payment_status: res.data.data.payment_status || "PAID", payment_txn_id: "" });
            setExportData(null);
        } else {
            toast.error("Could not load this order.");
        }
    };

    const advanceStatus = async (newStatus) => {
        const res = await callApi({
            url: `print/press/admin/orders/${detail.id}/status/`, method: "POST", body: { status: newStatus }, rawError: true,
        });
        if (res?.status === 200) {
            toast.success(`Status: ${newStatus.replace(/_/g, " ")}`);
            openDetail(detail.id);
            fetchOrders(status);
        } else {
            toast.error(res?.data?.data || res?.data?.message || "Illegal status transition");
        }
    };

    const saveNotes = async () => {
        const res = await callApi({
            url: `print/press/admin/orders/${detail.id}/`, method: "PATCH", body: { staff_notes: notesDraft }, rawError: true,
        });
        if (res?.status === 200) toast.success("Notes saved");
        else toast.error("Could not save notes.");
    };

    const savePayment = async () => {
        const res = await callApi({
            url: `print/press/admin/orders/${detail.id}/payment/`, method: "POST", body: payForm, rawError: true,
        });
        if (res?.status === 200) {
            toast.success("Payment updated");
            openDetail(detail.id);
            fetchOrders(status);
        } else {
            toast.error(res?.data?.message || "Could not update payment");
        }
    };

    const loadExport = async () => {
        const res = await callApi({ url: `print/press/admin/orders/${detail.id}/export/`, method: "GET", rawError: true });
        if (res?.status === 200) setExportData(res.data.data);
        else toast.error("Could not load export data.");
    };

    const fmt = (n) => `৳${Number(n || 0).toLocaleString("en-US")}`;

    return (
        <Box>
            <Typography variant="h5" fontWeight={800} sx={{ mb: 2 }}>Press Orders</Typography>
            <Tabs value={status} onChange={(_, v) => setStatus(v)} variant="scrollable" sx={{ mb: 2 }}>
                {STATUS_TABS.map((s) => <Tab key={s || "all"} label={s ? s.replace(/_/g, " ") : "All"} value={s} />)}
            </Tabs>
            {loading && <LinearProgress />}
            <TableContainer component={Paper}>
                <Table>
                    <TableHead>
                        <TableRow>
                            <TableCell>ID</TableCell><TableCell>Customer</TableCell>
                            <TableCell>Product</TableCell><TableCell>Qty</TableCell>
                            <TableCell>Total</TableCell><TableCell>Payment</TableCell><TableCell>Status</TableCell>
                        </TableRow>
                    </TableHead>
                    <TableBody>
                        {orders.length === 0 && !loading && (
                            <TableRow><TableCell colSpan={7} align="center">No press orders</TableCell></TableRow>
                        )}
                        {orders.map((o) => (
                            <TableRow key={o.id} hover sx={{ cursor: "pointer" }} onClick={() => openDetail(o.id)}>
                                <TableCell>#{o.id}</TableCell>
                                <TableCell>{o.customer_username || o.customer_email}</TableCell>
                                <TableCell>{o.product_name}</TableCell>
                                <TableCell>{o.quantity}</TableCell>
                                <TableCell><strong>{fmt(o.total_bdt)}</strong></TableCell>
                                <TableCell><Chip size="small" label={`${o.payment_method} · ${o.payment_status}`} variant="outlined" /></TableCell>
                                <TableCell><Chip size="small" label={o.status.replace(/_/g, " ")} color={STATUS_COLORS[o.status] || "default"} /></TableCell>
                            </TableRow>
                        ))}
                    </TableBody>
                </Table>
            </TableContainer>

            <Drawer anchor="right" open={!!detail} onClose={() => setDetail(null)}
                PaperProps={{ sx: { width: { xs: "100%", sm: 520 }, p: 3 } }}>
                {detail && (
                    <Box>
                        <Stack direction="row" justifyContent="space-between" alignItems="center">
                            <Typography variant="h6">Press Order #{detail.id}</Typography>
                            <IconButton onClick={() => setDetail(null)}><CloseIcon /></IconButton>
                        </Stack>
                        <Stack direction="row" spacing={1} sx={{ my: 1 }}>
                            <Chip size="small" label={detail.status.replace(/_/g, " ")} color={STATUS_COLORS[detail.status] || "default"} />
                            <Chip size="small" variant="outlined" label={`${detail.payment_method} · ${detail.payment_status}`} />
                            {detail.is_corporate && <Chip size="small" color="secondary" label={detail.po_number ? `PO ${detail.po_number}` : "Corporate"} />}
                        </Stack>
                        <Typography variant="body2" color="text.secondary">
                            {detail.customer_username || detail.customer_email}
                        </Typography>
                        <Divider sx={{ my: 2 }} />

                        <Typography variant="subtitle2">Specification</Typography>
                        <Typography variant="body2" sx={{ mb: 1 }}>
                            {detail.product_name} · {detail.size_name} · {detail.sides} · Qty {detail.quantity}
                        </Typography>
                        <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
                            Paper: {detail.paper_name || "—"} · Finishing: {(detail.finishing_names || []).join(", ") || "—"}
                        </Typography>
                        {detail.price_breakdown && (
                            <Box component="pre" sx={{ p: 1.5, bgcolor: "action.hover", borderRadius: 1, fontSize: 12, overflowX: "auto", whiteSpace: "pre-wrap" }}>
                                {JSON.stringify(detail.price_breakdown, null, 2)}
                            </Box>
                        )}
                        <Typography variant="body2" sx={{ mt: 1 }}>
                            Total: <strong>{fmt(detail.total_bdt)} BDT</strong>
                            {detail.currency === "USD" && <> (charged ${detail.total_charged})</>}
                            {" · "}Shipping {fmt(detail.shipping_fee_bdt)} via {detail.shipping_courier}
                        </Typography>

                        {detail.artwork_validation?.warnings?.length > 0 && (
                            <Alert severity={detail.artwork_validation.low_dpi ? "warning" : "info"} sx={{ mt: 2 }}>
                                {(detail.artwork_validation.warnings || []).join(" ")}
                            </Alert>
                        )}
                        {detail.artwork_files?.length > 0 && (
                            <Box sx={{ mt: 1 }}>
                                <Typography variant="subtitle2" sx={{ mb: 1 }}>
                                    Artwork files ({detail.artwork_files.length}) — full resolution, uncompressed
                                </Typography>
                                {detail.artwork_files.map((f, i) => (
                                    <Stack key={i} direction="row" spacing={1} alignItems="center" sx={{ mb: 0.5 }}>
                                        <Typography variant="body2" sx={{ flex: 1, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                                            {f.name || f.url}
                                        </Typography>
                                        <Button size="small" href={f.url} target="_blank" rel="noreferrer">Download</Button>
                                    </Stack>
                                ))}
                            </Box>
                        )}

                        <Divider sx={{ my: 2 }} />
                        <Typography variant="subtitle2" sx={{ mb: 1 }}>Payment</Typography>
                        <Stack direction="row" spacing={1}>
                            <TextField size="small" select label="Status" value={payForm.payment_status}
                                onChange={(e) => setPayForm({ ...payForm, payment_status: e.target.value })} sx={{ minWidth: 150 }}>
                                {PAYMENT_STATUSES.map((s) => <MenuItem key={s} value={s}>{s}</MenuItem>)}
                            </TextField>
                            <TextField size="small" label="Txn ID (optional)" value={payForm.payment_txn_id}
                                onChange={(e) => setPayForm({ ...payForm, payment_txn_id: e.target.value })} />
                            <Button variant="outlined" onClick={savePayment}>Save</Button>
                        </Stack>

                        {NEXT_STATUS[detail.status] && (
                            <>
                                <Divider sx={{ my: 2 }} />
                                <Button variant="contained" onClick={() => advanceStatus(NEXT_STATUS[detail.status])}>
                                    Advance to {NEXT_STATUS[detail.status].replace(/_/g, " ")}
                                </Button>
                            </>
                        )}
                        {!["DELIVERED", "CANCELLED"].includes(detail.status) && (
                            <Button color="error" sx={{ mt: 1, display: "block" }} onClick={() => advanceStatus("CANCELLED")}>
                                Cancel order
                            </Button>
                        )}

                        <Divider sx={{ my: 2 }} />
                        <Typography variant="subtitle2" sx={{ mb: 1 }}>Staff notes</Typography>
                        <TextField fullWidth multiline minRows={2} size="small" value={notesDraft}
                            onChange={(e) => setNotesDraft(e.target.value)} sx={{ mb: 1 }} />
                        <Button size="small" onClick={saveNotes}>Save notes</Button>

                        <Divider sx={{ my: 2 }} />
                        <Button size="small" onClick={loadExport}>Load production export (grouped by Order ID)</Button>
                        {exportData && (
                            <Box component="pre" sx={{
                                mt: 1, p: 1.5, bgcolor: "action.hover", borderRadius: 1,
                                fontSize: 12, overflowX: "auto", whiteSpace: "pre-wrap",
                            }}>
                                {JSON.stringify(exportData, null, 2)}
                            </Box>
                        )}
                    </Box>
                )}
            </Drawer>
        </Box>
    );
}
