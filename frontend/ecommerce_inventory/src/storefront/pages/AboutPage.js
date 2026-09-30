import React, { useEffect } from 'react';
import { Box, Button, Card, Container, Grid, Link as MuiLink, Typography } from '@mui/material';
import {
    Checkroom, Devices, LocalShipping, MedicalServices, Payments,
    Restaurant, SupportAgent, Verified,
} from '@mui/icons-material';
import { Link } from 'react-router-dom';
import { SUPPORT } from './legal/content';

/**
 * Public About page (/about) — who runs Fabrything, what it sells, and how to
 * reach a human. Written against what the platform actually does (COD
 * nationwide, local food delivery, custom printing, Rokomari partner deals).
 * AdSense reviewers look for exactly this page: a real operator behind the
 * store, with contact details that match the footer and the legal pages.
 */
const CATEGORIES = [
    {
        icon: <Checkroom fontSize="large" color="secondary" />,
        title: 'Fashion & Lifestyle',
        body: 'Clothing for men, women and kids — everyday wear sourced for quality and fit, with size charts on every product.',
    },
    {
        icon: <Devices fontSize="large" color="secondary" />,
        title: 'Electronics & Gadgets',
        body: 'Phones, computers and accessories from verified partner sellers, listed with full specifications.',
    },
    {
        icon: <MedicalServices fontSize="large" color="secondary" />,
        title: 'Health & Pharmacy Essentials',
        body: 'Everyday health and wellness essentials. Prescription medicines are never sold online.',
    },
    {
        icon: <Restaurant fontSize="large" color="secondary" />,
        title: 'Food Delivery',
        body: 'Hot meals from local restaurants, delivered to your door with live order tracking from kitchen to doorstep.',
    },
];

const PROMISES = [
    {
        icon: <Payments color="secondary" />,
        title: 'Cash on Delivery',
        body: 'Pay in cash when your order arrives. No cards, no advance payments, no risk.',
    },
    {
        icon: <LocalShipping color="secondary" />,
        title: 'Nationwide Delivery',
        body: 'We deliver across Bangladesh — and delivery is free on orders over ৳1,500.',
    },
    {
        icon: <Verified color="secondary" />,
        title: 'Quality Assured',
        body: 'Every product is checked before dispatch. Wrong or damaged item? We make it right.',
    },
    {
        icon: <SupportAgent color="secondary" />,
        title: 'Human Support',
        body: 'Chat with us on this site, message us on WhatsApp, or email — a person answers.',
    },
];

export default function AboutPage() {
    useEffect(() => {
        document.title = 'About Us — Fabrything';
        window.scrollTo(0, 0);
    }, []);

    const waNumber = SUPPORT.whatsapp.replace(/[^0-9]/g, '');

    return (
        <Box>
            {/* Hero */}
            <Box sx={{
                background: 'linear-gradient(135deg, #E85D4A 0%, #C2410C 100%)',
                color: '#fff', py: { xs: 6, md: 9 }, mb: { xs: 4, md: 6 },
            }}>
                <Container maxWidth="md" sx={{ textAlign: 'center' }}>
                    <Typography variant="h3" component="h1" fontWeight={800} gutterBottom>
                        About Fabrything
                    </Typography>
                    <Typography variant="h6" sx={{ opacity: 0.92, fontWeight: 400, maxWidth: 640, mx: 'auto' }}>
                        Bangladesh's everyday superstore — fashion, electronics, health
                        essentials and hot food, all payable in cash at your door.
                    </Typography>
                </Container>
            </Box>

            <Container maxWidth="lg">
                {/* Story */}
                <Box sx={{ maxWidth: 760, mx: 'auto', mb: { xs: 4, md: 6 } }}>
                    <Typography variant="h5" fontWeight={800} gutterBottom>
                        What we do
                    </Typography>
                    <Typography variant="body1" color="text.secondary" sx={{ mb: 2, lineHeight: 1.8 }}>
                        Fabrything started with a simple observation: online shopping in
                        Bangladesh works best when it works like the neighbourhood shop —
                        see it, order it, pay cash when it arrives. So we built exactly
                        that, online: a curated store where every order is Cash on
                        Delivery, every product page shows real prices in taka, and every
                        delivery is tracked until it reaches your hands.
                    </Typography>
                    <Typography variant="body1" color="text.secondary" sx={{ lineHeight: 1.8 }}>
                        Alongside the store we run a local food-delivery service and a
                        custom print shop — design your own t-shirt, mug or gift and we
                        print it on demand. We also hand-pick deals from partner programs
                        (clearly badged <em>via Rokomari</em>) so bargain hunters get the
                        best of both worlds.
                    </Typography>
                </Box>

                {/* Categories */}
                <Grid container spacing={2} sx={{ mb: { xs: 4, md: 6 } }}>
                    {CATEGORIES.map((c) => (
                        <Grid item xs={12} sm={6} md={3} key={c.title}>
                            <Card sx={{ p: 3, height: '100%', textAlign: 'center' }}>
                                <Box sx={{ mb: 1.5 }}>{c.icon}</Box>
                                <Typography variant="subtitle1" fontWeight={700} gutterBottom>
                                    {c.title}
                                </Typography>
                                <Typography variant="body2" color="text.secondary">
                                    {c.body}
                                </Typography>
                            </Card>
                        </Grid>
                    ))}
                </Grid>

                {/* Promises */}
                <Typography variant="h5" fontWeight={800} gutterBottom sx={{ textAlign: 'center', mb: 3 }}>
                    Why shop with us
                </Typography>
                <Grid container spacing={2} sx={{ mb: { xs: 4, md: 6 } }}>
                    {PROMISES.map((p) => (
                        <Grid item xs={12} sm={6} key={p.title}>
                            <Box sx={{ display: 'flex', gap: 2, alignItems: 'flex-start' }}>
                                <Box>{p.icon}</Box>
                                <Box>
                                    <Typography variant="subtitle1" fontWeight={700}>
                                        {p.title}
                                    </Typography>
                                    <Typography variant="body2" color="text.secondary">
                                        {p.body}
                                    </Typography>
                                </Box>
                            </Box>
                        </Grid>
                    ))}
                </Grid>

                {/* Operator + contact */}
                <Card sx={{ p: { xs: 3, md: 4 }, mb: { xs: 4, md: 6 }, bgcolor: 'action.hover' }}>
                    <Grid container spacing={3} alignItems="center">
                        <Grid item xs={12} md={7}>
                            <Typography variant="h6" fontWeight={800} gutterBottom>
                                The operator
                            </Typography>
                            <Typography variant="body2" color="text.secondary" sx={{ mb: 0.5 }}>
                                {SUPPORT.entity} · Trade Licence No. {SUPPORT.licence}
                            </Typography>
                            <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                                Email: <MuiLink href={`mailto:${SUPPORT.email}`}>{SUPPORT.email}</MuiLink>
                                {' · '}WhatsApp:{' '}
                                <MuiLink href={`https://wa.me/${waNumber}`} target="_blank" rel="noopener noreferrer">
                                    {SUPPORT.whatsapp}
                                </MuiLink>
                            </Typography>
                            <Box sx={{ display: 'flex', gap: 1.5, flexWrap: 'wrap' }}>
                                <Button variant="contained" component={Link} to="/shop">
                                    Start shopping
                                </Button>
                                <Button variant="outlined" component={Link} to="/custom-printing">
                                    Try custom printing
                                </Button>
                            </Box>
                        </Grid>
                        <Grid item xs={12} md={5}>
                            <Box sx={{ display: 'flex', gap: 2, flexWrap: 'wrap' }}>
                                {[
                                    { label: 'Privacy Policy', to: '/privacy' },
                                    { label: 'Terms of Use', to: '/terms' },
                                    { label: 'Delivery & Shipping', to: '/shipping' },
                                ].map((l) => (
                                    <MuiLink key={l.to} component={Link} to={l.to} variant="body2">
                                        {l.label}
                                    </MuiLink>
                                ))}
                            </Box>
                        </Grid>
                    </Grid>
                </Card>
            </Container>
        </Box>
    );
}
