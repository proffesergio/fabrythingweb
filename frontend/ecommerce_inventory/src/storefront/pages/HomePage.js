import React from 'react';
import { Box, Container, Typography, Grid, Card, Skeleton } from '@mui/material';
import { LocalShipping, Payment, Verified, Support } from '@mui/icons-material';
import { motion } from 'framer-motion';
import useCachedApi from '../../hooks/useCachedApi';
import HeroCarousel from '../components/HeroCarousel';
import FlashSaleSection from '../components/FlashSaleSection';
import TabbedProductSection from '../components/TabbedProductSection';
import ProductCarousel from '../components/ProductCarousel';
import PromoBanner from '../components/PromoBanner';
import CategoryGrid from '../components/CategoryGrid';
import AffiliateWidget from '../components/AffiliateWidget';

export default function HomePage() {
    // Stale-while-revalidate: renders instantly from the last cached homepage,
    // then refreshes in the background (masks the free-tier backend cold start).
    const { data, loading } = useCachedApi('store/homepage/');

    const trustSignals = [
        { icon: <LocalShipping />, title: 'Free Delivery', desc: 'On orders over ৳1,500' },
        { icon: <Payment />, title: 'Cash on Delivery', desc: 'Pay when you receive' },
        { icon: <Verified />, title: 'Quality Assured', desc: '100% authentic products' },
        { icon: <Support />, title: '24/7 Support', desc: "We're here to help" },
    ];

    return (
        <Box>
            {/* Hero Banner Carousel */}
            <HeroCarousel />

            {/* Trust Signals */}
            <Container maxWidth="lg" sx={{ mt: -3, mb: 5, position: 'relative', zIndex: 1 }}>
                <Grid container spacing={2}>
                    {trustSignals.map((signal, i) => (
                        <Grid item xs={6} md={3} key={i}>
                            <motion.div
                                initial={{ opacity: 0, y: 20 }}
                                animate={{ opacity: 1, y: 0 }}
                                transition={{ duration: 0.4, delay: i * 0.1 }}
                            >
                                <Card sx={{ textAlign: 'center', py: 2, px: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 0.5 }}>
                                    <Box sx={{ color: 'secondary.main', mb: 0.5 }}>{signal.icon}</Box>
                                    <Typography variant="subtitle2" fontWeight={700}>{signal.title}</Typography>
                                    <Typography variant="caption" color="text.secondary">{signal.desc}</Typography>
                                </Card>
                            </motion.div>
                        </Grid>
                    ))}
                </Grid>
            </Container>

            {/* Colourful category tiles */}
            <CategoryGrid categories={data?.categories || []} />

            {/* Flash Sale */}
            {data?.flash_sale?.length > 0 && (
                <FlashSaleSection products={data.flash_sale} endTime={data.flash_sale_end} />
            )}

            {/* Tabbed Products: Trending / New Arrivals / Best Sellers */}
            <Container maxWidth="lg">
                {loading && !data ? (
                    <Grid container spacing={2} sx={{ mb: 6 }}>
                        {[1, 2, 3, 4].map(i => (
                            <Grid item xs={6} sm={3} key={i}>
                                <Skeleton variant="rectangular" height={260} sx={{ borderRadius: 2 }} />
                                <Skeleton width="60%" sx={{ mt: 1 }} />
                                <Skeleton width="40%" />
                            </Grid>
                        ))}
                    </Grid>
                ) : (
                    <TabbedProductSection
                        trending={data?.trending}
                        newArrivals={data?.new_arrivals}
                        bestSellers={data?.best_sellers}
                    />
                )}
            </Container>

            {/* Rotating affiliate deals (Rokomari) -- homepage section widget */}
            <Container maxWidth="lg">
                <AffiliateWidget placement="sidebar" title="Deals from Rokomari" />
            </Container>

            {/* Promo Banners */}
            <PromoBanner />

            {/* On Sale Carousel */}
            <Container maxWidth="lg">
                <ProductCarousel
                    title="On Sale"
                    products={data?.on_sale}
                    viewAllLink="/shop"
                    titleColor="secondary.main"
                />
            </Container>

            {/* Top Rated Carousel */}
            <Container maxWidth="lg">
                <ProductCarousel
                    title="Top Rated"
                    products={data?.best_rated}
                    viewAllLink="/shop"
                />
            </Container>
        </Box>
    );
}
