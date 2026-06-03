import React, { useState, useEffect } from 'react';
import {
    Box, Container, Typography, Grid, Button, Card, Divider,
    RadioGroup, Radio, FormControlLabel, TextField, Dialog,
    DialogTitle, DialogContent, DialogActions, Alert, CircularProgress,
} from '@mui/material';
import { CheckCircle, LocalShipping } from '@mui/icons-material';
import { useNavigate } from 'react-router-dom';
import { useSelector, useDispatch } from 'react-redux';
import { selectCartItems, selectCartTotal, clearCart } from '../../redux/reducer/cartSlice';
import useApi from '../../hooks/APIHandler';

export default function CheckoutPage() {
    const items = useSelector(selectCartItems);
    const subtotal = useSelector(selectCartTotal);
    const dispatch = useDispatch();
    const navigate = useNavigate();
    const { callApi, loading } = useApi();

    const [addresses, setAddresses] = useState([]);
    const [selectedAddress, setSelectedAddress] = useState('');
    const [paymentMethod, setPaymentMethod] = useState('COD');
    const [notes, setNotes] = useState('');
    const [addAddressOpen, setAddAddressOpen] = useState(false);
    const [orderPlaced, setOrderPlaced] = useState(null);
    const [newAddress, setNewAddress] = useState({
        address_type: 'Home', address: '', city: '', state: '', pincode: '', country: 'Bangladesh',
    });

    const deliveryCharge = subtotal >= 1500 ? 0 : 60;
    const total = subtotal + deliveryCharge;

    useEffect(() => {
        if (items.length === 0 && !orderPlaced) navigate('/cart');
        fetchAddresses();
    }, []);

    const fetchAddresses = async () => {
        const res = await callApi({ url: 'store/addresses/' });
        if (res?.data?.data) {
            setAddresses(res.data.data);
            if (res.data.data.length > 0) setSelectedAddress(String(res.data.data[0].id));
        }
    };

    const handleAddAddress = async () => {
        const res = await callApi({ url: 'store/addresses/', method: 'POST', body: newAddress });
        if (res?.data?.data) {
            await fetchAddresses();
            setSelectedAddress(String(res.data.data.id));
            setAddAddressOpen(false);
            setNewAddress({ address_type: 'Home', address: '', city: '', state: '', pincode: '', country: 'Bangladesh' });
        }
    };

    const handlePlaceOrder = async () => {
        if (!selectedAddress) return;
        const orderData = {
            shipping_address_id: parseInt(selectedAddress),
            payment_method: paymentMethod,
            notes,
            items: items.map(item => ({
                product_id: item.product.id,
                quantity: item.quantity,
                size: item.size,
            })),
        };
        const res = await callApi({ url: 'store/orders/', method: 'POST', body: orderData });
        if (res?.data?.data) {
            setOrderPlaced(res.data.data);
            dispatch(clearCart());
        }
    };

    // Order Confirmation
    if (orderPlaced) {
        return (
            <Container maxWidth="sm" sx={{ py: 8, textAlign: 'center' }}>
                <CheckCircle sx={{ fontSize: 80, color: 'success.main', mb: 2 }} />
                <Typography variant="h4" gutterBottom>Order Placed!</Typography>
                <Typography variant="body1" color="text.secondary" sx={{ mb: 3 }}>
                    Your order #{orderPlaced.so_code} has been placed successfully.
                </Typography>
                <Card sx={{ p: 3, mb: 3, textAlign: 'left' }}>
                    <Typography variant="subtitle2" color="text.secondary">Order Number</Typography>
                    <Typography variant="h6" fontWeight={700} gutterBottom>{orderPlaced.so_code}</Typography>
                    <Typography variant="subtitle2" color="text.secondary">Total Amount</Typography>
                    <Typography variant="h6" fontWeight={700} gutterBottom>৳{orderPlaced.total_amount?.toLocaleString()}</Typography>
                    <Typography variant="subtitle2" color="text.secondary">Expected Delivery</Typography>
                    <Typography variant="h6" fontWeight={700}>{orderPlaced.expected_delivery_date}</Typography>
                </Card>
                {paymentMethod === 'COD' && (
                    <Alert severity="info" sx={{ mb: 3, textAlign: 'left' }}>
                        Please keep ৳{orderPlaced.total_amount?.toLocaleString()} ready for Cash on Delivery.
                        Our delivery partner will contact you before delivery.
                    </Alert>
                )}
                {paymentMethod === 'BKASH' && (
                    <Alert severity="warning" sx={{ mb: 3, textAlign: 'left' }}>
                        Please send ৳{orderPlaced.total_amount?.toLocaleString()} to our bKash number: <strong>01XXX-XXXXXX</strong>.
                        Use your order number {orderPlaced.so_code} as reference.
                    </Alert>
                )}
                <Box sx={{ display: 'flex', gap: 2, justifyContent: 'center' }}>
                    <Button variant="contained" onClick={() => navigate('/account/orders')}>View Orders</Button>
                    <Button variant="outlined" onClick={() => navigate('/shop')}>Continue Shopping</Button>
                </Box>
            </Container>
        );
    }

    return (
        <Container maxWidth="lg" sx={{ py: 3 }}>
            <Typography variant="h4" sx={{ mb: 3 }}>Checkout</Typography>
            <Grid container spacing={3}>
                <Grid item xs={12} md={7}>
                    {/* Shipping Address */}
                    <Card sx={{ p: 3, mb: 3 }}>
                        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
                            <Typography variant="h6"><LocalShipping sx={{ mr: 1, verticalAlign: 'middle' }} />Shipping Address</Typography>
                            <Button size="small" onClick={() => setAddAddressOpen(true)}>Add New</Button>
                        </Box>
                        {addresses.length === 0 ? (
                            <Alert severity="warning">
                                Please add a shipping address to continue.
                            </Alert>
                        ) : (
                            <RadioGroup value={selectedAddress} onChange={(e) => setSelectedAddress(e.target.value)}>
                                {addresses.map(addr => (
                                    <FormControlLabel
                                        key={addr.id}
                                        value={String(addr.id)}
                                        control={<Radio />}
                                        label={
                                            <Box>
                                                <Typography variant="subtitle2" fontWeight={600}>{addr.address_type}</Typography>
                                                <Typography variant="body2" color="text.secondary">
                                                    {addr.address}, {addr.city}, {addr.state} - {addr.pincode}
                                                </Typography>
                                            </Box>
                                        }
                                        sx={{ mb: 1, alignItems: 'flex-start' }}
                                    />
                                ))}
                            </RadioGroup>
                        )}
                    </Card>

                    {/* Payment Method */}
                    <Card sx={{ p: 3, mb: 3 }}>
                        <Typography variant="h6" gutterBottom>Payment Method</Typography>
                        <RadioGroup value={paymentMethod} onChange={(e) => setPaymentMethod(e.target.value)}>
                            <FormControlLabel
                                value="COD"
                                control={<Radio />}
                                label={
                                    <Box>
                                        <Typography variant="subtitle2" fontWeight={600}>Cash on Delivery</Typography>
                                        <Typography variant="caption" color="text.secondary">Pay when you receive your order</Typography>
                                    </Box>
                                }
                                sx={{ mb: 1, alignItems: 'flex-start' }}
                            />
                            <FormControlLabel
                                value="BKASH"
                                control={<Radio />}
                                label={
                                    <Box>
                                        <Typography variant="subtitle2" fontWeight={600}>bKash</Typography>
                                        <Typography variant="caption" color="text.secondary">Send payment to our bKash merchant number</Typography>
                                    </Box>
                                }
                                sx={{ alignItems: 'flex-start' }}
                            />
                        </RadioGroup>
                    </Card>

                    {/* Notes */}
                    <Card sx={{ p: 3 }}>
                        <Typography variant="h6" gutterBottom>Order Notes (optional)</Typography>
                        <TextField
                            fullWidth
                            multiline
                            rows={2}
                            placeholder="Any special instructions..."
                            value={notes}
                            onChange={(e) => setNotes(e.target.value)}
                        />
                    </Card>
                </Grid>

                {/* Order Summary */}
                <Grid item xs={12} md={5}>
                    <Card sx={{ p: 3, position: 'sticky', top: 80 }}>
                        <Typography variant="h6" gutterBottom>Order Summary</Typography>
                        <Divider sx={{ mb: 2 }} />
                        {items.map(item => {
                            const price = item.product.discount_price || item.product.initial_selling_price;
                            return (
                                <Box key={`${item.product.id}-${item.size}`} sx={{ display: 'flex', justifyContent: 'space-between', mb: 1 }}>
                                    <Typography variant="body2">
                                        {item.product.name} ({item.size}) x{item.quantity}
                                    </Typography>
                                    <Typography variant="body2" fontWeight={600}>৳{(price * item.quantity).toLocaleString()}</Typography>
                                </Box>
                            );
                        })}
                        <Divider sx={{ my: 2 }} />
                        <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1 }}>
                            <Typography color="text.secondary">Subtotal</Typography>
                            <Typography fontWeight={600}>৳{subtotal.toLocaleString()}</Typography>
                        </Box>
                        <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1 }}>
                            <Typography color="text.secondary">Delivery</Typography>
                            <Typography fontWeight={600} color={deliveryCharge === 0 ? 'success.main' : 'text.primary'}>
                                {deliveryCharge === 0 ? 'Free' : `৳${deliveryCharge}`}
                            </Typography>
                        </Box>
                        <Divider sx={{ my: 2 }} />
                        <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 3 }}>
                            <Typography variant="h6">Total</Typography>
                            <Typography variant="h6" fontWeight={800}>৳{total.toLocaleString()}</Typography>
                        </Box>
                        <Button
                            variant="contained"
                            color="secondary"
                            size="large"
                            fullWidth
                            onClick={handlePlaceOrder}
                            disabled={loading || !selectedAddress}
                            sx={{ py: 1.5 }}
                        >
                            {loading ? <CircularProgress size={24} /> : `Place Order - ৳${total.toLocaleString()}`}
                        </Button>
                    </Card>
                </Grid>
            </Grid>

            {/* Add Address Dialog */}
            <Dialog open={addAddressOpen} onClose={() => setAddAddressOpen(false)} maxWidth="sm" fullWidth>
                <DialogTitle>Add Shipping Address</DialogTitle>
                <DialogContent>
                    <Grid container spacing={2} sx={{ mt: 0.5 }}>
                        <Grid item xs={12}>
                            <TextField fullWidth label="Full Address" multiline rows={2} required
                                value={newAddress.address} onChange={(e) => setNewAddress({ ...newAddress, address: e.target.value })} />
                        </Grid>
                        <Grid item xs={6}>
                            <TextField fullWidth label="City" required
                                value={newAddress.city} onChange={(e) => setNewAddress({ ...newAddress, city: e.target.value })} />
                        </Grid>
                        <Grid item xs={6}>
                            <TextField fullWidth label="District/State" required
                                value={newAddress.state} onChange={(e) => setNewAddress({ ...newAddress, state: e.target.value })} />
                        </Grid>
                        <Grid item xs={6}>
                            <TextField fullWidth label="Postal Code" required
                                value={newAddress.pincode} onChange={(e) => setNewAddress({ ...newAddress, pincode: e.target.value })} />
                        </Grid>
                        <Grid item xs={6}>
                            <TextField fullWidth label="Country" value="Bangladesh" disabled />
                        </Grid>
                    </Grid>
                </DialogContent>
                <DialogActions>
                    <Button onClick={() => setAddAddressOpen(false)}>Cancel</Button>
                    <Button variant="contained" onClick={handleAddAddress} disabled={loading}>Save Address</Button>
                </DialogActions>
            </Dialog>
        </Container>
    );
}
