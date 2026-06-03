import React from 'react';
import {
    Box, Container, Typography, Grid, Button, IconButton, Divider, Card,
} from '@mui/material';
import { Add, Remove, Delete, ShoppingCart, ArrowForward } from '@mui/icons-material';
import { Link, useNavigate } from 'react-router-dom';
import { useSelector, useDispatch } from 'react-redux';
import { selectCartItems, selectCartTotal, removeFromCart, updateQuantity, clearCart } from '../../redux/reducer/cartSlice';
import { isAuthenticated } from '../../utils/Helper';

export default function CartPage() {
    const items = useSelector(selectCartItems);
    const total = useSelector(selectCartTotal);
    const dispatch = useDispatch();
    const navigate = useNavigate();

    const handleCheckout = () => {
        if (isAuthenticated()) {
            navigate('/checkout');
        } else {
            navigate('/auth/login?redirect=/checkout');
        }
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
                    {items.map((item, i) => {
                        const price = item.product.discount_price || item.product.initial_selling_price;
                        const imageUrl = Array.isArray(item.product.image) && item.product.image.length > 0
                            ? item.product.image[0] : '';
                        return (
                            <Card key={`${item.product.id}-${item.size}`} sx={{ mb: 2, p: 2 }}>
                                <Grid container spacing={2} alignItems="center">
                                    <Grid item xs={3} sm={2}>
                                        <Box
                                            component="img"
                                            src={imageUrl}
                                            alt={item.product.name}
                                            sx={{ width: '100%', height: 100, objectFit: 'cover', borderRadius: 1 }}
                                            onError={(e) => { e.target.src = 'https://via.placeholder.com/100?text=No+Image'; }}
                                        />
                                    </Grid>
                                    <Grid item xs={9} sm={4}>
                                        <Typography
                                            variant="subtitle2"
                                            component={Link}
                                            to={`/product/${item.product.slug}`}
                                            sx={{ textDecoration: 'none', color: 'text.primary', fontWeight: 600 }}
                                        >
                                            {item.product.name}
                                        </Typography>
                                        <Typography variant="body2" color="text.secondary">Size: {item.size}</Typography>
                                    </Grid>
                                    <Grid item xs={6} sm={3}>
                                        <Box sx={{ display: 'flex', alignItems: 'center', border: '1px solid', borderColor: 'divider', borderRadius: 1, width: 'fit-content' }}>
                                            <IconButton size="small" onClick={() => dispatch(updateQuantity({ productId: item.product.id, size: item.size, quantity: item.quantity - 1 }))}>
                                                <Remove fontSize="small" />
                                            </IconButton>
                                            <Typography sx={{ px: 1.5 }}>{item.quantity}</Typography>
                                            <IconButton size="small" onClick={() => dispatch(updateQuantity({ productId: item.product.id, size: item.size, quantity: item.quantity + 1 }))}>
                                                <Add fontSize="small" />
                                            </IconButton>
                                        </Box>
                                    </Grid>
                                    <Grid item xs={4} sm={2}>
                                        <Typography variant="subtitle2" fontWeight={700}>
                                            ৳{(price * item.quantity).toLocaleString()}
                                        </Typography>
                                    </Grid>
                                    <Grid item xs={2} sm={1}>
                                        <IconButton color="error" onClick={() => dispatch(removeFromCart({ productId: item.product.id, size: item.size }))}>
                                            <Delete />
                                        </IconButton>
                                    </Grid>
                                </Grid>
                            </Card>
                        );
                    })}
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
                            <Typography fontWeight={600}>৳{total.toLocaleString()}</Typography>
                        </Box>
                        <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1 }}>
                            <Typography color="text.secondary">Delivery</Typography>
                            <Typography fontWeight={600} color="success.main">
                                {total >= 1500 ? 'Free' : '৳60'}
                            </Typography>
                        </Box>
                        <Divider sx={{ my: 2 }} />
                        <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 3 }}>
                            <Typography variant="h6">Total</Typography>
                            <Typography variant="h6" fontWeight={800}>
                                ৳{(total + (total >= 1500 ? 0 : 60)).toLocaleString()}
                            </Typography>
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
