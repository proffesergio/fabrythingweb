import React, { useEffect, useState, useCallback } from 'react';
import {
    Box, Typography, TextField, InputAdornment, Chip, Button, Tabs, Tab, Card, Stack,
    Table, TableBody, TableCell, TableHead, TableRow, TableContainer, Paper, LinearProgress,
    Drawer, Divider, IconButton, Stepper, Step, StepLabel, Pagination,
} from '@mui/material';
import { Search, Close } from '@mui/icons-material';
import useApi from '../../hooks/APIHandler';
import { toast } from 'react-toastify';

// COD Order lifecycle (matches orders.models.Order.Status).
const FLOW = ['PENDING_VERIFICATION', 'CONFIRMED', 'OUT_FOR_DELIVERY', 'DELIVERED'];
const LABEL = {
    PENDING_VERIFICATION: 'Pending', CONFIRMED: 'Confirmed', OUT_FOR_DELIVERY: 'Out for delivery',
    DELIVERED: 'Delivered', CANCELED: 'Canceled', RETURNED: 'Returned',
};
const COLOR = {
    PENDING_VERIFICATION: 'warning', CONFIRMED: 'info', OUT_FOR_DELIVERY: 'primary',
    DELIVERED: 'success', CANCELED: 'error', RETURNED: 'default',
};
const ACTION_LABEL = {
    CONFIRMED: 'Confirm', OUT_FOR_DELIVERY: 'Send out', DELIVERED: 'Mark delivered',
    CANCELED: 'Cancel', RETURNED: 'Mark returned',
};
const TABS = ['', 'PENDING_VERIFICATION', 'CONFIRMED', 'OUT_FOR_DELIVERY', 'DELIVERED', 'CANCELED'];

const ManageSalesOrder = () => {
    const { callApi, loading } = useApi();
    const [orders, setOrders] = useState([]);
    const [page, setPage] = useState(1);
    const [totalPages, setTotalPages] = useState(1);
    const [search, setSearch] = useState('');
    const [status, setStatus] = useState('');
    const [detail, setDetail] = useState(null);

    const fetchOrders = useCallback(async () => {
        const params = { page };
        if (search) params.search = search;
        if (status) params.status = status;
        const res = await callApi({ url: 'store/admin/orders/', method: 'GET', params });
        if (res?.status === 200) {
            setOrders(res.data.data.data || []);
            setTotalPages(res.data.data.totalPages || 1);
        }
    }, [page, search, status]); // eslint-disable-line react-hooks/exhaustive-deps

    useEffect(() => { fetchOrders(); }, [page, status, fetchOrders]);

    const openDetail = async (id) => {
        const res = await callApi({ url: `store/admin/orders/${id}/`, method: 'GET' });
        if (res?.status === 200) setDetail(res.data.data);
    };

    const advance = async (newStatus) => {
        const res = await callApi({
            url: `store/admin/orders/${detail.id}/`, method: 'PATCH', body: { status: newStatus },
        });
        if (res?.status === 200) {
            toast.success(`Order ${LABEL[newStatus] || newStatus}`);
            await openDetail(detail.id);
            fetchOrders();
        }
    };

    const activeStep = detail ? FLOW.indexOf(detail.status) : -1;

    return (
        <Box>
            <Typography variant="h5" fontWeight={800} gutterBottom>Store Orders</Typography>

            <Card sx={{ mb: 2 }}>
                <Box sx={{ p: 2, pb: 0 }}>
                    <TextField
                        size="small" placeholder="Search by order # or customer…" value={search}
                        onChange={(e) => setSearch(e.target.value)}
                        onKeyDown={(e) => e.key === 'Enter' && (setPage(1), fetchOrders())}
                        InputProps={{ startAdornment: <InputAdornment position="start"><Search /></InputAdornment> }}
                        sx={{ minWidth: 280 }}
                    />
                </Box>
                <Tabs value={status} onChange={(_, v) => { setPage(1); setStatus(v); }} variant="scrollable">
                    {TABS.map((s) => <Tab key={s || 'all'} label={s ? (LABEL[s] || s) : 'All'} value={s} />)}
                </Tabs>
            </Card>

            {loading && <LinearProgress sx={{ mb: 1 }} />}
            <TableContainer component={Paper}>
                <Table>
                    <TableHead>
                        <TableRow>
                            <TableCell>Order #</TableCell><TableCell>Customer</TableCell>
                            <TableCell>Date</TableCell><TableCell align="center">Items</TableCell>
                            <TableCell align="right">Total</TableCell><TableCell>Status</TableCell>
                            <TableCell align="right">Action</TableCell>
                        </TableRow>
                    </TableHead>
                    <TableBody>
                        {orders.length === 0 && !loading && (
                            <TableRow><TableCell colSpan={7} align="center">No orders found</TableCell></TableRow>
                        )}
                        {orders.map((o) => (
                            <TableRow key={o.id} hover sx={{ cursor: 'pointer' }} onClick={() => openDetail(o.id)}>
                                <TableCell><Typography variant="body2" fontWeight={700}>{o.order_number}</Typography></TableCell>
                                <TableCell>{o.contact_name || '—'}</TableCell>
                                <TableCell>{o.created_at ? new Date(o.created_at).toLocaleDateString() : '—'}</TableCell>
                                <TableCell align="center">{o.item_count}</TableCell>
                                <TableCell align="right"><Typography fontWeight={700}>৳{Number(o.total_amount || 0).toLocaleString()}</Typography></TableCell>
                                <TableCell><Chip size="small" label={o.status_display || LABEL[o.status] || o.status} color={COLOR[o.status] || 'default'} /></TableCell>
                                <TableCell align="right"><Button size="small">View</Button></TableCell>
                            </TableRow>
                        ))}
                    </TableBody>
                </Table>
            </TableContainer>

            {totalPages > 1 && (
                <Stack alignItems="center" sx={{ mt: 2 }}>
                    <Pagination count={totalPages} page={page} onChange={(_, p) => setPage(p)} color="primary" />
                </Stack>
            )}

            <Drawer anchor="right" open={!!detail} onClose={() => setDetail(null)}
                PaperProps={{ sx: { width: { xs: '100%', sm: 460 }, p: 3 } }}>
                {detail && (
                    <Box>
                        <Stack direction="row" justifyContent="space-between" alignItems="center">
                            <Typography variant="h6">{detail.order_number}</Typography>
                            <IconButton onClick={() => setDetail(null)}><Close /></IconButton>
                        </Stack>
                        <Chip size="small" sx={{ my: 1 }} label={detail.status_display || LABEL[detail.status]} color={COLOR[detail.status] || 'default'} />

                        {detail.status !== 'CANCELED' && detail.status !== 'RETURNED' && (
                            <Stepper activeStep={activeStep} alternativeLabel sx={{ my: 2 }}>
                                {FLOW.map((s) => <Step key={s}><StepLabel>{LABEL[s]}</StepLabel></Step>)}
                            </Stepper>
                        )}

                        <Typography variant="subtitle2">Customer</Typography>
                        <Typography variant="body2">{detail.contact_name} · {detail.contact_phone}</Typography>
                        {detail.shipping_address && (
                            <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                                {detail.shipping_address.address}, {detail.shipping_address.city}
                            </Typography>
                        )}

                        <Typography variant="subtitle2" gutterBottom>Items</Typography>
                        {(detail.items || []).map((it) => (
                            <Stack key={it.id} direction="row" justifyContent="space-between" sx={{ py: 0.5 }}>
                                <Typography variant="body2">{it.quantity}× {it.product_name}</Typography>
                                <Typography variant="body2">৳{Number(it.line_total).toLocaleString()}</Typography>
                            </Stack>
                        ))}
                        <Divider sx={{ my: 1 }} />
                        <Stack direction="row" justifyContent="space-between">
                            <Typography fontWeight={700}>Total ({detail.payment_method || 'COD'})</Typography>
                            <Typography fontWeight={700}>৳{Number(detail.total_amount || 0).toLocaleString()}</Typography>
                        </Stack>

                        <Divider sx={{ my: 2 }} />
                        <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
                            {(detail.allowed_transitions || []).map((s) => (
                                <Button key={s} size="small"
                                    variant={s === 'CANCELED' || s === 'RETURNED' ? 'outlined' : 'contained'}
                                    color={s === 'CANCELED' ? 'error' : s === 'RETURNED' ? 'warning' : 'primary'}
                                    onClick={() => advance(s)}>
                                    {ACTION_LABEL[s] || s}
                                </Button>
                            ))}
                        </Stack>

                        {detail.status_logs?.length > 0 && (
                            <Box sx={{ mt: 3 }}>
                                <Typography variant="subtitle2" gutterBottom>History</Typography>
                                {detail.status_logs.map((l, i) => (
                                    <Typography key={i} variant="caption" display="block" color="text.secondary">
                                        {new Date(l.created_at).toLocaleString()} — {LABEL[l.to_status] || l.to_status}
                                    </Typography>
                                ))}
                            </Box>
                        )}
                    </Box>
                )}
            </Drawer>
        </Box>
    );
};

export default ManageSalesOrder;
