import React, { useEffect, useState } from 'react';
import { Box, Container, Grid, Typography, Chip, Skeleton } from '@mui/material';
import { Restaurant as RestaurantIcon, LocationOn } from '@mui/icons-material';
import { motion } from 'framer-motion';
import useApi from '../../hooks/APIHandler';

// Phase 1 stub: rural Bangladesh customers see a friendly "coming soon" hero
// plus whichever restaurants an admin has already approved for their zone.
// Full browse/ordering (menus, cart, checkout) lands in Phase 2.
export default function FoodComingSoon() {
    const [restaurants, setRestaurants] = useState([]);
    const [fetched, setFetched] = useState(false);
    const { callApi, loading } = useApi();

    useEffect(() => {
        let active = true;
        callApi({ url: 'food/restaurants/' }).then(res => {
            if (!active) return;
            setRestaurants(res?.data?.data?.data || []);
            setFetched(true);
        });
        return () => { active = false; };
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, []);

    return (
        <Container maxWidth="lg" sx={{ py: { xs: 4, md: 6 } }}>
            {/* Hero */}
            <Box
                sx={{
                    textAlign: 'center',
                    borderRadius: 3,
                    p: { xs: 4, md: 6 },
                    mb: 5,
                    background: theme => theme.palette.mode === 'dark'
                        ? 'linear-gradient(135deg,#1e1b4b 0%,#312E81 50%,#7C2D12 100%)'
                        : 'linear-gradient(135deg,#4F46E5 0%,#6366F1 50%,#E85D4A 100%)',
                    color: 'white',
                }}
            >
                <motion.div
                    animate={{ scale: [1, 1.06, 1] }}
                    transition={{ repeat: Infinity, duration: 2, ease: 'easeInOut' }}
                    style={{ display: 'inline-block' }}
                >
                    <RestaurantIcon sx={{ fontSize: { xs: 40, md: 56 }, mb: 1 }} />
                </motion.div>
                <Typography variant="h4" component="h1" sx={{ fontWeight: 900, mb: 1 }}>
                    Food delivery is coming to your community
                </Typography>
                <Typography variant="body1" sx={{ opacity: 0.9, maxWidth: 560, mx: 'auto' }}>
                    We're bringing hot meals from local restaurants straight to your door —
                    starting in rural Bangladesh, one zone at a time. Cash on Delivery, just
                    like the rest of Fabrything.
                </Typography>
                <Chip
                    icon={<LocationOn sx={{ color: 'inherit !important' }} />}
                    label="Coming soon to your area"
                    sx={{
                        mt: 3, bgcolor: 'rgba(255,255,255,0.18)', color: 'white',
                        fontWeight: 600, px: 1,
                    }}
                />
            </Box>

            {/* Restaurant grid / empty state */}
            <Typography variant="h5" sx={{ fontWeight: 800, mb: 2 }}>
                Restaurants joining Fabrything Food
            </Typography>

            {loading && !fetched ? (
                <Grid container spacing={2}>
                    {[...Array(4)].map((_, i) => (
                        <Grid item xs={6} sm={4} md={3} key={i}>
                            <Skeleton variant="rectangular" height={140} sx={{ borderRadius: 2 }} />
                            <Skeleton width="70%" sx={{ mt: 1 }} />
                        </Grid>
                    ))}
                </Grid>
            ) : restaurants.length === 0 ? (
                <Box sx={{ textAlign: 'center', py: 6 }}>
                    <Typography variant="h6" color="text.secondary" sx={{ mb: 1 }}>
                        No restaurants have gone live in your area just yet
                    </Typography>
                    <Typography variant="body2" color="text.secondary">
                        Check back soon — we're onboarding local kitchens across Bangladesh's
                        villages and towns. Meanwhile, keep shopping the rest of Fabrything!
                    </Typography>
                </Box>
            ) : (
                <Grid container spacing={2}>
                    {restaurants.map(r => (
                        <Grid item xs={6} sm={4} md={3} key={r.id}>
                            <Box
                                sx={{
                                    borderRadius: 2,
                                    overflow: 'hidden',
                                    border: '1px solid',
                                    borderColor: 'divider',
                                    height: '100%',
                                    display: 'flex',
                                    flexDirection: 'column',
                                }}
                            >
                                <Box
                                    component="img"
                                    src={r.logo || 'https://placehold.co/300x200/e2e8f0/64748b?text=Restaurant'}
                                    alt={r.display_name || r.name}
                                    loading="lazy"
                                    onError={(e) => { e.target.src = 'https://placehold.co/300x200/e2e8f0/64748b?text=Restaurant'; }}
                                    sx={{ width: '100%', height: 100, objectFit: 'cover', bgcolor: 'action.hover' }}
                                />
                                <Box sx={{ p: 1.25, flex: 1 }}>
                                    <Typography variant="subtitle2" fontWeight={700} noWrap>
                                        {r.display_name || r.name}
                                    </Typography>
                                    {r.cuisine_type && (
                                        <Typography variant="caption" color="text.secondary">
                                            {r.cuisine_type}
                                        </Typography>
                                    )}
                                </Box>
                            </Box>
                        </Grid>
                    ))}
                </Grid>
            )}
        </Container>
    );
}
