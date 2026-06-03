import React, { useEffect, useState } from 'react';
import { DataGrid } from '@mui/x-data-grid';
import {
    Box, Typography, TextField, InputAdornment, Chip, Button,
    Dialog, DialogTitle, DialogContent, DialogActions, FormControl,
    Select, MenuItem, Grid, Divider, Card,
} from '@mui/material';
import { Search, Visibility } from '@mui/icons-material';
import useApi from '../../hooks/APIHandler';
import { toast } from 'react-toastify';

const STATUS_COLORS = {
    DRAFT: 'default', SENT: 'info', DELIVERED: 'success',
    COMPLETED: 'success', CANCELLED: 'error', RETURNED: 'warning',
    'PARTIAL DELIVERED': 'warning',
};

const ManageSalesOrder = () => {
    const [orders, setOrders] = useState([]);
    const [page, setPage] = useState(0);
    const [pageSize, setPageSize] = useState(10);
    const [totalItems, setTotalItems] = useState(0);
    const [search, setSearch] = useState('');
    const [statusFilter, setStatusFilter] = useState('');
    const [selectedOrder, setSelectedOrder] = useState(null);
    const [updateStatusOpen, setUpdateStatusOpen] = useState(false);
    const [newStatus, setNewStatus] = useState('');
    const [cancelReason, setCancelReason] = useState('');
    const { callApi, loading } = useApi();

    const fetchOrders = async () => {
        const params = { page: page + 1, pageSize };
        if (search) params.search = search;
        if (statusFilter) params.status = statusFilter;

        const res = await callApi({ url: 'store/admin/orders/', params });
        if (res?.data?.data) {
            setOrders(res.data.data.data || []);
            setTotalItems(res.data.data.totalItems || 0);
        }
    };

    const fetchOrderDetail = async (id) => {
        const res = await callApi({ url: `store/admin/orders/${id}/` });
        if (res?.data?.data) setSelectedOrder(res.data.data);
    };

    const handleUpdateStatus = async () => {
        if (!selectedOrder || !newStatus) return;
        const body = { status: newStatus };
        if (newStatus === 'CANCELLED') body.reason = cancelReason;

        const res = await callApi({
            url: `store/admin/orders/${selectedOrder.id}/`,
            method: 'PATCH',
            body,
        });
        if (res?.data?.data) {
            toast.success(`Order status updated to ${newStatus}`);
            setUpdateStatusOpen(false);
            setSelectedOrder(null);
            setCancelReason('');
            fetchOrders();
        }
    };

    useEffect(() => { fetchOrders(); }, [page, pageSize, statusFilter]);

    const columns = [
        { field: 'so_code', headerName: 'Order #', width: 150, renderCell: (params) => (
            <Typography variant="body2" fontWeight={600}>{params.value}</Typography>
        )},
        { field: 'created_at', headerName: 'Date', width: 120, renderCell: (params) => (
            new Date(params.value).toLocaleDateString()
        )},
        { field: 'status', headerName: 'Status', width: 140, renderCell: (params) => (
            <Chip label={params.value} size="small" color={STATUS_COLORS[params.value] || 'default'} />
        )},
        { field: 'payment_status', headerName: 'Payment', width: 120, renderCell: (params) => (
            <Chip label={params.value} size="small" variant="outlined" />
        )},
        { field: 'item_count', headerName: 'Items', width: 80 },
        { field: 'total_amount', headerName: 'Total', width: 120, renderCell: (params) => (
            <Typography variant="body2" fontWeight={700}>৳{params.value?.toLocaleString()}</Typography>
        )},
        { field: 'actions', headerName: 'Actions', width: 120, sortable: false, renderCell: (params) => (
            <Button size="small" startIcon={<Visibility />} onClick={() => fetchOrderDetail(params.row.id)}>
                View
            </Button>
        )},
    ];

    return (
        <Box>
            <Typography variant="h5" gutterBottom>Sales Orders</Typography>

            <Box sx={{ display: 'flex', gap: 2, mb: 2, flexWrap: 'wrap' }}>
                <TextField
                    size="small" placeholder="Search orders..."
                    value={search} onChange={(e) => setSearch(e.target.value)}
                    onKeyDown={(e) => e.key === 'Enter' && fetchOrders()}
                    InputProps={{ startAdornment: <InputAdornment position="start"><Search /></InputAdornment> }}
                    sx={{ minWidth: 250 }}
                />
                <FormControl size="small" sx={{ minWidth: 150 }}>
                    <Select value={statusFilter} displayEmpty onChange={(e) => setStatusFilter(e.target.value)}>
                        <MenuItem value="">All Statuses</MenuItem>
                        {['DRAFT', 'SENT', 'DELIVERED', 'COMPLETED', 'CANCELLED', 'RETURNED'].map(s => (
                            <MenuItem key={s} value={s}>{s}</MenuItem>
                        ))}
                    </Select>
                </FormControl>
            </Box>

            <Card>
                <DataGrid
                    rows={orders}
                    columns={columns}
                    rowCount={totalItems}
                    loading={loading}
                    paginationMode="server"
                    paginationModel={{ page, pageSize }}
                    onPaginationModelChange={(model) => { setPage(model.page); setPageSize(model.pageSize); }}
                    pageSizeOptions={[10, 25, 50]}
                    disableRowSelectionOnClick
                    autoHeight
                    sx={{ border: 'none' }}
                />
            </Card>

            {/* Order Detail Dialog */}
            <Dialog open={!!selectedOrder} onClose={() => setSelectedOrder(null)} maxWidth="md" fullWidth>
                {selectedOrder && (
                    <>
                        <DialogTitle>
                            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                                Order #{selectedOrder.so_code}
                                <Chip label={selectedOrder.status} color={STATUS_COLORS[selectedOrder.status] || 'default'} />
                            </Box>
                        </DialogTitle>
                        <DialogContent>
                            <Grid container spacing={3}>
                                {/* Customer Info */}
                                {selectedOrder.customer && (
                                    <Grid item xs={12} md={6}>
                                        <Typography variant="subtitle2" color="text.secondary">Customer</Typography>
                                        <Typography fontWeight={600}>
                                            {selectedOrder.customer.name || selectedOrder.customer.username}
                                        </Typography>
                                        <Typography variant="body2">{selectedOrder.customer.email}</Typography>
                                        <Typography variant="body2">{selectedOrder.customer.phone}</Typography>
                                    </Grid>
                                )}
                                {/* Shipping Address */}
                                {selectedOrder.shipping_address && (
                                    <Grid item xs={12} md={6}>
                                        <Typography variant="subtitle2" color="text.secondary">Shipping Address</Typography>
                                        <Typography variant="body2">{selectedOrder.shipping_address.address}</Typography>
                                        <Typography variant="body2">
                                            {selectedOrder.shipping_address.city}, {selectedOrder.shipping_address.state} - {selectedOrder.shipping_address.pincode}
                                        </Typography>
                                    </Grid>
                                )}
                            </Grid>

                            <Divider sx={{ my: 2 }} />

                            {/* Items */}
                            <Typography variant="subtitle2" gutterBottom>Order Items</Typography>
                            {selectedOrder.items?.map(item => (
                                <Box key={item.id} sx={{
                                    display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                                    py: 1, borderBottom: '1px solid', borderColor: 'divider',
                                }}>
                                    <Box>
                                        <Typography variant="body2" fontWeight={600}>{item.product_name}</Typography>
                                        <Typography variant="caption" color="text.secondary">
                                            Qty: {item.quantity_ordered}
                                        </Typography>
                                    </Box>
                                    <Typography variant="body2" fontWeight={600}>
                                        ৳{Number(item.amount_ordered).toLocaleString()}
                                    </Typography>
                                </Box>
                            ))}

                            <Divider sx={{ my: 2 }} />

                            <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
                                <Typography variant="h6">Total</Typography>
                                <Typography variant="h6" fontWeight={700}>
                                    ৳{selectedOrder.total_amount?.toLocaleString()}
                                </Typography>
                            </Box>
                        </DialogContent>
                        <DialogActions>
                            <Button onClick={() => {
                                setNewStatus(selectedOrder.status);
                                setUpdateStatusOpen(true);
                            }} variant="contained">
                                Update Status
                            </Button>
                            <Button onClick={() => setSelectedOrder(null)}>Close</Button>
                        </DialogActions>
                    </>
                )}
            </Dialog>

            {/* Update Status Dialog */}
            <Dialog open={updateStatusOpen} onClose={() => setUpdateStatusOpen(false)} maxWidth="xs" fullWidth>
                <DialogTitle>Update Order Status</DialogTitle>
                <DialogContent>
                    <FormControl fullWidth sx={{ mt: 1 }}>
                        <Select value={newStatus} onChange={(e) => setNewStatus(e.target.value)}>
                            {['DRAFT', 'SENT', 'DELIVERED', 'PARTIAL DELIVERED', 'COMPLETED', 'CANCELLED', 'RETURNED'].map(s => (
                                <MenuItem key={s} value={s}>{s}</MenuItem>
                            ))}
                        </Select>
                    </FormControl>
                    {newStatus === 'CANCELLED' && (
                        <TextField
                            fullWidth multiline rows={2} label="Cancellation Reason" sx={{ mt: 2 }}
                            value={cancelReason} onChange={(e) => setCancelReason(e.target.value)}
                        />
                    )}
                </DialogContent>
                <DialogActions>
                    <Button onClick={() => setUpdateStatusOpen(false)}>Cancel</Button>
                    <Button variant="contained" onClick={handleUpdateStatus}>Update</Button>
                </DialogActions>
            </Dialog>
        </Box>
    );
};

export default ManageSalesOrder;
