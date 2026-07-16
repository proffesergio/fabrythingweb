import React, { useEffect, useState } from 'react';
import {
    Box, Container, Typography, Grid, Button, IconButton, Divider, Card,
} from '@mui/material';
import { Add, Remove, Delete, ShoppingCart, ArrowForward } from '@mui/icons-material';
import { Link, useNavigate } from 'react-router-dom';
import { useSelector, useDispatch } from 'react-redux';
import { selectCartItems, selectCartTotal, removeFromCart, updateQuantity, clearCart } from '../../redux/reducer/cartSlice';
import { isAuthenticated } from '../../utils/Helper';
import useApi from '../../hooks/APIHandler';

export default function CartPage() {
    const items = useSelector(selectCartItems);
    const subtotal = useSelector(selectCartTotal);
    const dispatch = useDispatch();
    const navigate = useNavigate();
    const { callApi } = useApi();

    const [shippingRate, setShippingRate] = useState(60);
    const [freeThreshold, setFreeThreshold] = useState(null);

    useEffect(() => {
        (async () => {
            const res = await callApi({ url: 'store/config/' });
            const cfg = res?.data?.data;
            if (cfg) {
                setShippingRate(cfg.fixed_shipping_rate);
                setFreeThreshold(cfg.free_shipping_threshold);
            }
        })();
    }, []);

    const deliveryCharge = (freeThreshold != null && subtotal >= freeThreshold) ? 0 : shippingRate;
    const total = subtotal + deliveryCharge;

    const handleCheckout = () => {
        if (isAuthenticated()) navigate('/checkout');
        else navigate('/auth/login?redirect=/checkout');
    };

    if (items.length === 0) {
        return (
            <Container maxWidth="md" sx={{ py: 8, textAlign: 'center' }}>
                <ShoppingCart sx={{ fontSize: 80, color: 'text.secondary', mb: 2 }} />
                <Typography variant="h5" gutterBottom>Your cart is empty</Typography>
                <Typography variant="body1" color="text.secondary" sx={{ mb: 3 }}>
                    Looks like you haven't added anything to your cart yet.
                </Typography>
                <Button component={Link} to="/shop" variant="contained" color="secondary" size="large">
                    Continue Shopping
                </Button>
            </Container>
        );
    }

    return (
        <Container maxWidth="lg" sx={{ py: 3 }}>
            <Typography variant="h4" sx={{ mb: 3 }}>Shopping Cart ({items.length} items)</Typography>
            <Grid container spacing={3}>
                {/* Cart Items */}
                <Grid item xs={12} md={8}>
                    {items.map((item) => (
                        <Card key={item.variantId} sx={{ mb: 2, p: 2 }}>
                            <Grid container spacing={2} alignItems="center">
                                <Grid item xs={3} sm={2}>
                                    <Box
                                        component="img"
                                        src={item.image || 'https://via.placeholder.com/100?text=No+Image'}
                                        alt={item.name}
                                        sx={{ width: '100%', height: 100, objectFit: 'cover', borderRadius: 1 }}
                                        onError={(e) => { e.target.src = 'https://via.placeholder.com/100?text=No+Image'; }}
                                    />
                                </Grid>
                                <Grid item xs={9} sm={4}>
                                    <Typography
                                        variant="subtitle2"
                                        component={Link}
                                        to={`/product/${item.slug}`}
                                        sx={{ textDecoration: 'none', color: 'text.primary', fontWeight: 600 }}
                                    >
                                        {item.name}
                                    </Typography>
                                    <Typography variant="body2" color="text.secondary">
                                        {item.size && `Size: ${item.size}`}{item.color ? ` · ${item.color}` : ''}
                                    </Typography>
                                </Grid>
                                <Grid item xs={6} sm={3}>
                                    <Box sx={{ display: 'flex', alignItems: 'center', border: '1px solid', borderColor: 'divider', borderRadius: 1, width: 'fit-content' }}>
                                        <IconButton size="small" onClick={() => dispatch(updateQuantity({ variantId: item.variantId, quantity: item.quantity - 1 }))}>
                                            <Remove fontSize="small" />
                                        </IconButton>
                                        <Typography sx={{ px: 1.5 }}>{item.quantity}</Typography>
                                        <IconButton
                                            size="small"
                                            disabled={item.stock ? item.quantity >= item.stock : false}
                                            onClick={() => dispatch(updateQuantity({ variantId: item.variantId, quantity: item.quantity + 1 }))}
                                        >
                                            <Add fontSize="small" />
                                        </IconButton>
                                    </Box>
                                </Grid>
                                <Grid item xs={4} sm={2}>
                                    <Typography variant="subtitle2" fontWeight={700}>
                                        ৳{(item.price * item.quantity).toLocaleString()}
                                    </Typography>
                                </Grid>
                                <Grid item xs={2} sm={1}>
                                    <IconButton color="error" onClick={() => dispatch(removeFromCart({ variantId: item.variantId }))}>
                                        <Delete />
                                    </IconButton>
                                </Grid>
                            </Grid>
                        </Card>
                    ))}
                    <Box sx={{ display: 'flex', justifyContent: 'space-between', mt: 2 }}>
                        <Button component={Link} to="/shop" variant="outlined" color="inherit">Continue Shopping</Button>
                        <Button variant="text" color="error" onClick={() => dispatch(clearCart())}>Clear Cart</Button>
                    </Box>
                </Grid>

                {/* Order Summary */}
                <Grid item xs={12} md={4}>
                    <Card sx={{ p: 3, position: 'sticky', top: 80 }}>
                        <Typography variant="h6" gutterBottom>Order Summary</Typography>
                        <Divider sx={{ mb: 2 }} />
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
                            endIcon={<ArrowForward />}
                            onClick={handleCheckout}
                        >
                            Proceed to Checkout
                        </Button>
                        <Typography variant="caption" color="text.secondary" sx={{ display: 'block', textAlign: 'center', mt: 1 }}>
                            Cash on Delivery available
                        </Typography>
                    </Card>
                </Grid>
            </Grid>
        </Container>
    );
}
