import React, { useEffect, useState } from 'react';
import {
    Box, Container, Typography, Grid, Card, Tabs, Tab, Button,
    TextField, Chip, Divider,
    IconButton, Dialog, DialogTitle, DialogContent, DialogActions,
} from '@mui/material';
import { Logout, Edit, Delete, Visibility } from '@mui/icons-material';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { useDispatch } from 'react-redux';
import { logout } from '../../redux/reducer/IsLoggedInReducer';
import useApi from '../../hooks/APIHandler';

const STATUS_COLORS = {
    PENDING_VERIFICATION: 'default', CONFIRMED: 'info', OUT_FOR_DELIVERY: 'info',
    DELIVERED: 'success', CANCELED: 'error', RETURNED: 'warning',
};
const CANCELABLE = ['PENDING_VERIFICATION', 'CONFIRMED', 'OUT_FOR_DELIVERY'];

export default function CustomerAccount() {
    const [tab, setTab] = useState(0);
    const [orders, setOrders] = useState([]);
    const [profile, setProfile] = useState(null);
    const [addresses, setAddresses] = useState([]);
    const [selectedOrder, setSelectedOrder] = useState(null);
    const [editProfile, setEditProfile] = useState(false);
    const [profileForm, setProfileForm] = useState({});
    const { callApi, loading } = useApi();
    const navigate = useNavigate();
    const dispatch = useDispatch();
    const [searchParams] = useSearchParams();

    useEffect(() => {
        if (searchParams.get('tab') === 'orders' || window.location.pathname.includes('/orders')) setTab(1);
        fetchProfile();
        fetchOrders();
        fetchAddresses();
    }, []);

    const fetchProfile = async () => {
        const res = await callApi({ url: 'store/profile/' });
        if (res?.data?.data) {
            setProfile(res.data.data);
            setProfileForm(res.data.data);
        }
    };

    const fetchOrders = async () => {
        const res = await callApi({ url: 'store/orders/list/' });
        if (res?.data?.data?.data) setOrders(res.data.data.data);
    };

    const fetchAddresses = async () => {
        const res = await callApi({ url: 'store/addresses/' });
        if (res?.data?.data) setAddresses(res.data.data);
    };

    const fetchOrderDetail = async (id) => {
        const res = await callApi({ url: `store/orders/${id}/` });
        if (res?.data?.data) setSelectedOrder(res.data.data);
    };

    const handleUpdateProfile = async () => {
        const res = await callApi({
            url: 'store/profile/',
            method: 'PUT',
            body: { first_name: profileForm.first_name, last_name: profileForm.last_name, phone: profileForm.phone },
        });
        if (res?.data?.data) {
            setProfile(res.data.data);
            setEditProfile(false);
        }
    };

    const handleDeleteAddress = async (id) => {
        await callApi({ url: `store/addresses/${id}/`, method: 'DELETE' });
        fetchAddresses();
    };

    const handleCancelOrder = async (id) => {
        const res = await callApi({ url: `store/orders/${id}/cancel/`, method: 'POST', body: { reason: 'Canceled by customer' } });
        if (res?.data) {
            setSelectedOrder(null);
            fetchOrders();
        }
    };

    const handleLogout = () => {
        localStorage.removeItem('token');
        dispatch(logout());
        navigate('/');
    };

    return (
        <Container maxWidth="lg" sx={{ py: 3 }}>
            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
                <Typography variant="h4">My Account</Typography>
                <Button variant="outlined" color="error" startIcon={<Logout />} onClick={handleLogout}>
                    Logout
                </Button>
            </Box>

            <Tabs value={tab} onChange={(_, v) => setTab(v)} sx={{ mb: 3 }}>
                <Tab label="Profile" />
                <Tab label="Orders" />
                <Tab label="Addresses" />
            </Tabs>

            {/* Profile */}
            {tab === 0 && profile && (
                <Card sx={{ p: 3, maxWidth: 600 }}>
                    {editProfile ? (
                        <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
                            <TextField label="First Name" value={profileForm.first_name || ''}
                                onChange={(e) => setProfileForm({ ...profileForm, first_name: e.target.value })} />
                            <TextField label="Last Name" value={profileForm.last_name || ''}
                                onChange={(e) => setProfileForm({ ...profileForm, last_name: e.target.value })} />
                            <TextField label="Phone" value={profileForm.phone || ''}
                                onChange={(e) => setProfileForm({ ...profileForm, phone: e.target.value })} />
                            <Box sx={{ display: 'flex', gap: 1 }}>
                                <Button variant="contained" onClick={handleUpdateProfile} disabled={loading}>Save</Button>
                                <Button variant="outlined" onClick={() => setEditProfile(false)}>Cancel</Button>
                            </Box>
                        </Box>
                    ) : (
                        <>
                            <Typography variant="subtitle2" color="text.secondary">Username</Typography>
                            <Typography variant="body1" gutterBottom>{profile.username}</Typography>
                            <Typography variant="subtitle2" color="text.secondary">Email</Typography>
                            <Typography variant="body1" gutterBottom>{profile.email}</Typography>
                            <Typography variant="subtitle2" color="text.secondary">Name</Typography>
                            <Typography variant="body1" gutterBottom>{profile.first_name} {profile.last_name}</Typography>
                            <Typography variant="subtitle2" color="text.secondary">Phone</Typography>
                            <Typography variant="body1" gutterBottom>{profile.phone || 'Not set'}</Typography>
                            <Button startIcon={<Edit />} onClick={() => setEditProfile(true)} sx={{ mt: 2 }}>Edit Profile</Button>
                        </>
                    )}
                </Card>
            )}

            {/* Orders */}
            {tab === 1 && (
                <Box>
                    {orders.length === 0 ? (
                        <Card sx={{ p: 4, textAlign: 'center' }}>
                            <Typography color="text.secondary">No orders yet.</Typography>
                            <Button variant="contained" onClick={() => navigate('/shop')} sx={{ mt: 2 }}>Start Shopping</Button>
                        </Card>
                    ) : (
                        orders.map(order => (
                            <Card key={order.id} sx={{ p: 2, mb: 2 }}>
                                <Grid container spacing={2} alignItems="center">
                                    <Grid item xs={12} sm={3}>
                                        <Typography variant="subtitle2" fontWeight={700}>{order.order_number}</Typography>
                                        <Typography variant="caption" color="text.secondary">
                                            {new Date(order.created_at).toLocaleDateString()}
                                        </Typography>
                                    </Grid>
                                    <Grid item xs={4} sm={2}>
                                        <Chip label={order.status_display || order.status} size="small" color={STATUS_COLORS[order.status] || 'default'} />
                                    </Grid>
                                    <Grid item xs={4} sm={2}>
                                        <Typography variant="body2">{order.item_count} items</Typography>
                                    </Grid>
                                    <Grid item xs={4} sm={3}>
                                        <Typography variant="subtitle2" fontWeight={700}>৳{order.total_amount?.toLocaleString()}</Typography>
                                    </Grid>
                                    <Grid item xs={12} sm={2}>
                                        <Button size="small" startIcon={<Visibility />} onClick={() => fetchOrderDetail(order.id)}>
                                            Details
                                        </Button>
                                    </Grid>
                                </Grid>
                            </Card>
                        ))
                    )}
                </Box>
            )}

            {/* Addresses */}
            {tab === 2 && (
                <Grid container spacing={2}>
                    {addresses.map(addr => (
                        <Grid item xs={12} sm={6} md={4} key={addr.id}>
                            <Card sx={{ p: 2 }}>
                                <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
                                    <Chip label={addr.address_type} size="small" />
                                    <IconButton size="small" color="error" onClick={() => handleDeleteAddress(addr.id)}>
                                        <Delete fontSize="small" />
                                    </IconButton>
                                </Box>
                                <Typography variant="body2" sx={{ mt: 1 }}>{addr.address}</Typography>
                                <Typography variant="body2" color="text.secondary">
                                    {addr.city}, {addr.state} - {addr.pincode}
                                </Typography>
                            </Card>
                        </Grid>
                    ))}
                </Grid>
            )}

            {/* Order Detail Dialog */}
            <Dialog open={!!selectedOrder} onClose={() => setSelectedOrder(null)} maxWidth="sm" fullWidth>
                {selectedOrder && (
                    <>
                        <DialogTitle>Order #{selectedOrder.order_number}</DialogTitle>
                        <DialogContent>
                            <Box sx={{ mb: 2 }}>
                                <Chip label={selectedOrder.status_display || selectedOrder.status} color={STATUS_COLORS[selectedOrder.status] || 'default'} sx={{ mb: 1 }} />
                                <Typography variant="body2" color="text.secondary">
                                    Placed on {new Date(selectedOrder.created_at).toLocaleDateString()}
                                </Typography>
                            </Box>
                            <Divider sx={{ mb: 2 }} />
                            {selectedOrder.items?.map(item => (
                                <Box key={item.id} sx={{ display: 'flex', justifyContent: 'space-between', mb: 1 }}>
                                    <Box>
                                        <Typography variant="body2" fontWeight={600}>{item.product_name}</Typography>
                                        <Typography variant="caption" color="text.secondary">
                                            Qty: {item.quantity} {item.size ? `| Size: ${item.size}` : ''}
                                        </Typography>
                                    </Box>
                                    <Typography variant="body2" fontWeight={600}>৳{Number(item.line_total).toLocaleString()}</Typography>
                                </Box>
                            ))}
                            <Divider sx={{ my: 2 }} />
                            <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
                                <Typography variant="subtitle2">Total</Typography>
                                <Typography variant="subtitle2" fontWeight={700}>৳{selectedOrder.total_amount?.toLocaleString()}</Typography>
                            </Box>
                            {selectedOrder.shipping_address && (
                                <Box sx={{ mt: 2 }}>
                                    <Typography variant="subtitle2" color="text.secondary">Shipping To</Typography>
                                    <Typography variant="body2">
                                        {selectedOrder.shipping_address.address}, {selectedOrder.shipping_address.city}
                                    </Typography>
                                </Box>
                            )}
                        </DialogContent>
                        <DialogActions>
                            {CANCELABLE.includes(selectedOrder.status) && (
                                <Button color="error" onClick={() => handleCancelOrder(selectedOrder.id)} disabled={loading}>
                                    Cancel Order
                                </Button>
                            )}
                            <Button onClick={() => setSelectedOrder(null)}>Close</Button>
                        </DialogActions>
                    </>
                )}
            </Dialog>
        </Container>
    );
}
