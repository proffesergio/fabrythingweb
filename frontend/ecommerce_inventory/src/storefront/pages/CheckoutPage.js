import React, { useState, useEffect } from 'react';
import {
    Box, Container, Typography, Grid, Button, Card, Divider,
    RadioGroup, Radio, FormControlLabel, TextField, Dialog,
    DialogTitle, DialogContent, DialogActions, Alert, CircularProgress,
    Stepper, Step, StepLabel, Stack, Chip,
} from '@mui/material';
import {
    CheckCircle, LocalShipping, Payments, LoginOutlined,
    PersonAddAlt, ShoppingBagOutlined,
} from '@mui/icons-material';
import { useNavigate } from 'react-router-dom';
import { useSelector, useDispatch } from 'react-redux';
import { motion, AnimatePresence } from 'framer-motion';
import { selectCartItems, selectCartTotal, clearCart } from '../../redux/reducer/cartSlice';
import { isAuthenticated } from '../../utils/Helper';
import useApi from '../../hooks/APIHandler';
import { taka } from '../format';

const STEPS = ['Delivery Details', 'Review & Confirm', 'Done'];

// Framer-motion presets — steps slide/fade so the flow feels light and guided.
const MotionCard = motion(Card);
const stepVariants = {
    enter: { opacity: 0, x: 40 },
    center: { opacity: 1, x: 0 },
    exit: { opacity: 0, x: -40 },
};
const listStagger = {
    show: { transition: { staggerChildren: 0.05 } },
};
const listItem = {
    hidden: { opacity: 0, y: 8 },
    show: { opacity: 1, y: 0 },
};

export default function CheckoutPage() {
    const items = useSelector(selectCartItems);
    const subtotal = useSelector(selectCartTotal);
    const dispatch = useDispatch();
    const navigate = useNavigate();
    const { callApi, loading } = useApi();

    const [authed] = useState(() => isAuthenticated());

    const [activeStep, setActiveStep] = useState(0);
    const [addresses, setAddresses] = useState([]);
    const [selectedAddress, setSelectedAddress] = useState('');
    const [contactName, setContactName] = useState('');
    const [contactPhone, setContactPhone] = useState('');
    const [notes, setNotes] = useState('');
    const [website, setWebsite] = useState(''); // honeypot — must stay empty
    const [addAddressOpen, setAddAddressOpen] = useState(false);
    const [orderPlaced, setOrderPlaced] = useState(null);
    const [error, setError] = useState('');

    const [shippingRate, setShippingRate] = useState(60);
    const [freeThreshold, setFreeThreshold] = useState(null);
    const [currency, setCurrency] = useState('BDT');

    const [newAddress, setNewAddress] = useState({
        address_type: 'Home', address: '', city: '', state: '', pincode: '', country: 'Bangladesh',
    });
    // Guest one-off delivery address (no account needed).
    const [guestAddress, setGuestAddress] = useState({
        address: '', city: '', state: '', pincode: '',
    });

    const deliveryCharge = (freeThreshold != null && subtotal >= freeThreshold) ? 0 : shippingRate;
    const total = subtotal + deliveryCharge;

    useEffect(() => {
        if (items.length === 0 && !orderPlaced) {
            navigate('/cart');
            return;
        }
        bootstrap();
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, []);

    const bootstrap = async () => {
        const cfgRes = await callApi({ url: 'store/config/' });
        const cfg = cfgRes?.data?.data;
        if (cfg) {
            setShippingRate(cfg.fixed_shipping_rate);
            setFreeThreshold(cfg.free_shipping_threshold);
            setCurrency(cfg.currency || 'BDT');
        }
        // Profile + saved addresses only exist for logged-in customers.
        if (authed) {
            const profRes = await callApi({ url: 'store/profile/' });
            const prof = profRes?.data?.data;
            if (prof) {
                setContactName(`${prof.first_name || ''} ${prof.last_name || ''}`.trim() || prof.username || '');
                setContactPhone(prof.phone || '');
            }
            await fetchAddresses();
        }
    };

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

    const phoneOk = contactPhone.replace(/\D/g, '').length >= 6;
    const canProceedFromDelivery = authed
        ? (selectedAddress && contactName.trim() && phoneOk)
        : (guestAddress.address.trim() && guestAddress.city.trim() && contactName.trim() && phoneOk);

    const handleNext = () => {
        setError('');
        if (activeStep === 0 && !canProceedFromDelivery) {
            setError('Please fill in a delivery address and a valid name and phone number.');
            return;
        }
        setActiveStep((s) => s + 1);
    };

    const handleBack = () => setActiveStep((s) => Math.max(0, s - 1));

    const handlePlaceOrder = async () => {
        setError('');
        const orderData = {
            contact_name: contactName.trim(),
            contact_phone: contactPhone.trim(),
            notes,
            website, // honeypot
            items: items.map((item) => ({ variant_id: item.variantId, quantity: item.quantity })),
            ...(authed
                ? { shipping_address_id: parseInt(selectedAddress, 10) }
                : {
                    shipping_address: {
                        address: guestAddress.address.trim(),
                        city: guestAddress.city.trim(),
                        state: guestAddress.state.trim(),
                        pincode: guestAddress.pincode.trim(),
                        country: 'Bangladesh',
                    },
                }),
        };
        const res = await callApi({ url: 'store/orders/', method: 'POST', body: orderData });
        if (res?.data?.data?.order_number) {
            setOrderPlaced(res.data.data);
            setActiveStep(2);
            dispatch(clearCart());
        } else if (res?.data?.errors) {
            setError(Array.isArray(res.data.errors) ? res.data.errors.join(' ') : String(res.data.errors));
        }
    };

    const money = (n) => taka(n);
    const goAuth = (mode) => navigate(`/auth/${mode}?redirect=/checkout`);

    // ── Confirmation ──
    if (orderPlaced) {
        return (
            <Container maxWidth="sm" sx={{ py: 8, textAlign: 'center' }}>
                <motion.div
                    initial={{ scale: 0, rotate: -30 }}
                    animate={{ scale: 1, rotate: 0 }}
                    transition={{ type: 'spring', stiffness: 200, damping: 12 }}
                >
                    <CheckCircle sx={{ fontSize: 88, color: 'success.main', mb: 2 }} />
                </motion.div>
                <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.15 }}>
                    <Typography variant="h4" gutterBottom>Order Placed! 🎉</Typography>
                    <Typography variant="body1" color="text.secondary" sx={{ mb: 3 }}>
                        Your order #{orderPlaced.order_number} has been placed successfully.
                    </Typography>
                    <Card sx={{ p: 3, mb: 3, textAlign: 'left' }}>
                        <Typography variant="subtitle2" color="text.secondary">Order Number</Typography>
                        <Typography variant="h6" fontWeight={700} gutterBottom>{orderPlaced.order_number}</Typography>
                        <Typography variant="subtitle2" color="text.secondary">Amount to Pay on Delivery</Typography>
                        <Typography variant="h6" fontWeight={700}>{money(orderPlaced.total_amount)}</Typography>
                    </Card>
                    <Alert severity="info" sx={{ mb: 3, textAlign: 'left' }}>
                        Please keep {money(orderPlaced.total_amount)} ready for Cash on Delivery.
                        Our delivery partner will call you on your provided number before delivery.
                        {!authed && ' Save your order number to track this order.'}
                    </Alert>
                    <Box sx={{ display: 'flex', gap: 2, justifyContent: 'center', flexWrap: 'wrap' }}>
                        {authed ? (
                            <Button variant="contained" onClick={() => navigate('/account/orders')}>View Orders</Button>
                        ) : (
                            <Button variant="contained" startIcon={<PersonAddAlt />} onClick={() => goAuth('signup')}>
                                Create an account to track orders
                            </Button>
                        )}
                        <Button variant="outlined" onClick={() => navigate('/shop')}>Continue Shopping</Button>
                    </Box>
                </motion.div>
            </Container>
        );
    }

    return (
        <Container maxWidth="lg" sx={{ py: 3 }}>
            <Typography variant="h4" sx={{ mb: 3 }}>Checkout</Typography>

            {/* Guests: a friendly, non-blocking prompt to sign in or register (or just continue). */}
            <AnimatePresence>
                {!authed && (
                    <MotionCard
                        initial={{ opacity: 0, y: -8 }}
                        animate={{ opacity: 1, y: 0 }}
                        exit={{ opacity: 0 }}
                        sx={{ p: 2, mb: 3, bgcolor: 'action.hover' }}
                    >
                        <Stack direction={{ xs: 'column', sm: 'row' }} spacing={1.5} alignItems={{ sm: 'center' }} justifyContent="space-between">
                            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                                <ShoppingBagOutlined color="secondary" />
                                <Typography variant="body2">
                                    You're checking out as a <b>guest</b> — no account needed.
                                    Have one, or want faster checkout next time?
                                </Typography>
                            </Box>
                            <Stack direction="row" spacing={1}>
                                <Button size="small" variant="outlined" color="secondary" startIcon={<LoginOutlined />} onClick={() => goAuth('login')}>
                                    Sign in
                                </Button>
                                <Button size="small" variant="contained" color="secondary" startIcon={<PersonAddAlt />} onClick={() => goAuth('signup')}>
                                    Create account
                                </Button>
                            </Stack>
                        </Stack>
                    </MotionCard>
                )}
            </AnimatePresence>

            <Stepper activeStep={activeStep} sx={{ mb: 4 }}>
                {STEPS.map((label) => (
                    <Step key={label}><StepLabel>{label}</StepLabel></Step>
                ))}
            </Stepper>

            <AnimatePresence>
                {error && (
                    <motion.div initial={{ opacity: 0, height: 0 }} animate={{ opacity: 1, height: 'auto' }} exit={{ opacity: 0, height: 0 }}>
                        <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>
                    </motion.div>
                )}
            </AnimatePresence>

            <Grid container spacing={3}>
                <Grid item xs={12} md={7}>
                    <AnimatePresence mode="wait">
                        {activeStep === 0 && (
                            <motion.div
                                key="step-delivery"
                                variants={stepVariants} initial="enter" animate="center" exit="exit"
                                transition={{ duration: 0.28, ease: 'easeOut' }}
                            >
                                {/* Shipping Address */}
                                <Card sx={{ p: 3, mb: 3 }}>
                                    <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
                                        <Typography variant="h6"><LocalShipping sx={{ mr: 1, verticalAlign: 'middle' }} />Delivery Address</Typography>
                                        {authed && <Button size="small" onClick={() => setAddAddressOpen(true)}>Add New</Button>}
                                    </Box>

                                    {authed ? (
                                        addresses.length === 0 ? (
                                            <Alert severity="warning">Please add a delivery address to continue.</Alert>
                                        ) : (
                                            <RadioGroup value={selectedAddress} onChange={(e) => setSelectedAddress(e.target.value)}>
                                                {addresses.map((addr) => (
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
                                        )
                                    ) : (
                                        // Guest: inline address, typed once, snapshotted onto the order.
                                        <Grid container spacing={2}>
                                            <Grid item xs={12}>
                                                <TextField
                                                    fullWidth required label="Full Address" multiline rows={2}
                                                    placeholder="House / Road / Area"
                                                    value={guestAddress.address}
                                                    onChange={(e) => setGuestAddress({ ...guestAddress, address: e.target.value })}
                                                />
                                            </Grid>
                                            <Grid item xs={12} sm={6}>
                                                <TextField
                                                    fullWidth required label="City"
                                                    value={guestAddress.city}
                                                    onChange={(e) => setGuestAddress({ ...guestAddress, city: e.target.value })}
                                                />
                                            </Grid>
                                            <Grid item xs={6} sm={3}>
                                                <TextField
                                                    fullWidth label="District/State"
                                                    value={guestAddress.state}
                                                    onChange={(e) => setGuestAddress({ ...guestAddress, state: e.target.value })}
                                                />
                                            </Grid>
                                            <Grid item xs={6} sm={3}>
                                                <TextField
                                                    fullWidth label="Postal Code"
                                                    value={guestAddress.pincode}
                                                    onChange={(e) => setGuestAddress({ ...guestAddress, pincode: e.target.value })}
                                                />
                                            </Grid>
                                        </Grid>
                                    )}
                                </Card>

                                {/* Contact (COD needs a reachable phone) */}
                                <Card sx={{ p: 3 }}>
                                    <Typography variant="h6" gutterBottom>Contact for Delivery</Typography>
                                    <Grid container spacing={2}>
                                        <Grid item xs={12} sm={6}>
                                            <TextField
                                                fullWidth required label="Full Name"
                                                value={contactName} onChange={(e) => setContactName(e.target.value)}
                                            />
                                        </Grid>
                                        <Grid item xs={12} sm={6}>
                                            <TextField
                                                fullWidth required label="Phone Number" placeholder="01XXXXXXXXX"
                                                value={contactPhone} onChange={(e) => setContactPhone(e.target.value)}
                                                helperText="The delivery partner will call this number."
                                            />
                                        </Grid>
                                    </Grid>
                                </Card>
                            </motion.div>
                        )}

                        {activeStep === 1 && (
                            <motion.div
                                key="step-review"
                                variants={stepVariants} initial="enter" animate="center" exit="exit"
                                transition={{ duration: 0.28, ease: 'easeOut' }}
                            >
                                {/* Delivering to — quick recap so users feel confident before placing */}
                                <Card sx={{ p: 3, mb: 3 }}>
                                    <Typography variant="h6" gutterBottom>Delivering To</Typography>
                                    <Typography variant="subtitle2" fontWeight={600}>{contactName} · {contactPhone}</Typography>
                                    <Typography variant="body2" color="text.secondary">
                                        {authed
                                            ? (() => {
                                                const a = addresses.find((x) => String(x.id) === String(selectedAddress));
                                                return a ? `${a.address}, ${a.city}, ${a.state} - ${a.pincode}` : '';
                                            })()
                                            : `${guestAddress.address}, ${guestAddress.city}${guestAddress.state ? ', ' + guestAddress.state : ''}${guestAddress.pincode ? ' - ' + guestAddress.pincode : ''}`}
                                    </Typography>
                                    <Button size="small" sx={{ mt: 1 }} onClick={handleBack}>Change</Button>
                                </Card>

                                {/* Payment method — COD only */}
                                <Card sx={{ p: 3, mb: 3 }}>
                                    <Typography variant="h6" gutterBottom>Payment Method</Typography>
                                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5, p: 2, border: '1px solid', borderColor: 'divider', borderRadius: 1 }}>
                                        <Payments color="secondary" />
                                        <Box>
                                            <Typography variant="subtitle2" fontWeight={600}>Cash on Delivery</Typography>
                                            <Typography variant="caption" color="text.secondary">Pay in cash when your order arrives.</Typography>
                                        </Box>
                                        <Chip label="Selected" color="secondary" size="small" sx={{ ml: 'auto' }} />
                                    </Box>
                                </Card>

                                {/* Notes */}
                                <Card sx={{ p: 3 }}>
                                    <Typography variant="h6" gutterBottom>Order Notes (optional)</Typography>
                                    <TextField
                                        fullWidth multiline rows={2}
                                        placeholder="Any special delivery instructions..."
                                        value={notes} onChange={(e) => setNotes(e.target.value)}
                                    />
                                    {/* Honeypot: hidden from real users, tempting to bots */}
                                    <TextField
                                        value={website}
                                        onChange={(e) => setWebsite(e.target.value)}
                                        name="website"
                                        tabIndex={-1}
                                        autoComplete="off"
                                        sx={{ position: 'absolute', left: '-9999px', width: 1, height: 1, opacity: 0 }}
                                        aria-hidden="true"
                                    />
                                </Card>
                            </motion.div>
                        )}
                    </AnimatePresence>
                </Grid>

                {/* Order Summary */}
                <Grid item xs={12} md={5}>
                    <Card sx={{ p: 3, position: 'sticky', top: 80 }}>
                        <Typography variant="h6" gutterBottom>Order Summary</Typography>
                        <Divider sx={{ mb: 2 }} />
                        <motion.div variants={listStagger} initial="hidden" animate="show">
                            {items.map((item) => (
                                <motion.div key={item.variantId} variants={listItem}>
                                    <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1 }}>
                                        <Typography variant="body2">
                                            {item.name}{item.size ? ` (${item.size})` : ''} x{item.quantity}
                                        </Typography>
                                        <Typography variant="body2" fontWeight={600}>{money(item.price * item.quantity)}</Typography>
                                    </Box>
                                </motion.div>
                            ))}
                        </motion.div>
                        <Divider sx={{ my: 2 }} />
                        <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1 }}>
                            <Typography color="text.secondary">Subtotal</Typography>
                            <Typography fontWeight={600}>{money(subtotal)}</Typography>
                        </Box>
                        <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1 }}>
                            <Typography color="text.secondary">Delivery ({currency})</Typography>
                            <Typography fontWeight={600} color={deliveryCharge === 0 ? 'success.main' : 'text.primary'}>
                                {deliveryCharge === 0 ? 'Free' : money(deliveryCharge)}
                            </Typography>
                        </Box>
                        <Divider sx={{ my: 2 }} />
                        <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 3 }}>
                            <Typography variant="h6">Total</Typography>
                            <motion.div key={total} initial={{ scale: 1.15 }} animate={{ scale: 1 }} transition={{ type: 'spring', stiffness: 300, damping: 15 }}>
                                <Typography variant="h6" fontWeight={800}>{money(total)}</Typography>
                            </motion.div>
                        </Box>

                        {activeStep === 0 && (
                            <Button
                                component={motion.button} whileTap={{ scale: 0.97 }}
                                variant="contained" color="secondary" size="large" fullWidth
                                onClick={handleNext} disabled={!canProceedFromDelivery} sx={{ py: 1.5 }}>
                                Continue to Review
                            </Button>
                        )}
                        {activeStep === 1 && (
                            <Box sx={{ display: 'flex', gap: 1 }}>
                                <Button variant="outlined" color="inherit" fullWidth onClick={handleBack} sx={{ py: 1.5 }}>
                                    Back
                                </Button>
                                <Button
                                    component={motion.button} whileTap={{ scale: 0.97 }}
                                    variant="contained" color="secondary" size="large" fullWidth
                                    onClick={handlePlaceOrder} disabled={loading} sx={{ py: 1.5 }}>
                                    {loading ? <CircularProgress size={24} /> : `Place Order · ${money(total)}`}
                                </Button>
                            </Box>
                        )}
                    </Card>
                </Grid>
            </Grid>

            {/* Add Address Dialog (logged-in users) */}
            <Dialog open={addAddressOpen} onClose={() => setAddAddressOpen(false)} maxWidth="sm" fullWidth>
                <DialogTitle>Add Delivery Address</DialogTitle>
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
