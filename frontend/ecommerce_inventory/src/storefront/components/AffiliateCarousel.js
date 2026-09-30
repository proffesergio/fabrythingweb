import React, { useEffect, useState } from 'react';
import { Box, Button, Chip, IconButton, Skeleton, Typography } from '@mui/material';
import { ArrowForward, ChevronLeft, ChevronRight } from '@mui/icons-material';
import StorefrontIcon from '@mui/icons-material/Storefront';
import { Link } from 'react-router-dom';
import { Swiper, SwiperSlide } from 'swiper/react';
import { Navigation, FreeMode } from 'swiper/modules';
import { motion } from 'framer-motion';
import 'swiper/css';
import 'swiper/css/navigation';
import useApi from '../../hooks/APIHandler';
import AffiliateProductCard from './AffiliateProductCard';

/**
 * Homepage "Deals from Rokomari" section — a multi-card Swiper carousel fed by
 * GET /api/store/partner-picks/?placement=deals (the SAME flag that feeds
 * /deals, so one admin switch drives both surfaces).
 *
 * This replaces the old single rotating card (AffiliateWidget) here. That
 * widget shows one item at a time, so with a single product in the database
 * the whole full-width section was one card plus empty space — and even with
 * many products, shoppers only ever saw one. A carousel shows 2–4 at once
 * with swipe on mobile, and scales to 10+ products without redesign.
 * AffiliateWidget itself is untouched (ProductCatalog still uses it as a
 * genuine narrow sidebar).
 */
export default function AffiliateCarousel({ title = 'Deals from Rokomari' }) {
    const { callApi } = useApi();
    const [items, setItems] = useState(null); // null = loading

    useEffect(() => {
        let mounted = true;
        callApi({ url: 'store/partner-picks/', params: { placement: 'deals' }, silent: true }).then((res) => {
            if (mounted) setItems(res?.data?.data || []);
        });
        return () => { mounted = false; };
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, []);

    if (items !== null && items.length === 0) return null;

    const navSuffix = 'affiliate-deals';

    return (
        <motion.div
            initial={{ opacity: 0, y: 30 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true, margin: '-50px' }}
            transition={{ duration: 0.5 }}
        >
            <Box sx={{ mb: 6 }}>
                <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5 }}>
                        <StorefrontIcon color="secondary" />
                        <Typography variant="h4" sx={{ fontWeight: 800 }}>
                            {title}
                        </Typography>
                        {items !== null && (
                            <Chip
                                size="small"
                                label={`${items.length} deal${items.length === 1 ? '' : 's'}`}
                                color="secondary"
                                sx={{ fontWeight: 700 }}
                            />
                        )}
                        <Box sx={{ display: { xs: 'none', md: 'flex' }, gap: 0.5 }}>
                            <IconButton
                                id={`prev-${navSuffix}`}
                                size="small"
                                aria-label="Scroll deals back"
                                sx={{
                                    border: '1px solid',
                                    borderColor: 'divider',
                                    '&:hover': { bgcolor: 'primary.main', color: 'white' },
                                }}
                            >
                                <ChevronLeft />
                            </IconButton>
                            <IconButton
                                id={`next-${navSuffix}`}
                                size="small"
                                aria-label="Scroll deals forward"
                                sx={{
                                    border: '1px solid',
                                    borderColor: 'divider',
                                    '&:hover': { bgcolor: 'primary.main', color: 'white' },
                                }}
                            >
                                <ChevronRight />
                            </IconButton>
                        </Box>
                    </Box>
                    <Button
                        component={Link}
                        to="/deals"
                        endIcon={<ArrowForward />}
                        sx={{ fontWeight: 600 }}
                    >
                        View All
                    </Button>
                </Box>

                {items === null ? (
                    <Box sx={{ display: 'flex', gap: 2, overflow: 'hidden' }}>
                        {[1, 2, 3, 4].map((i) => (
                            <Skeleton key={i} variant="rectangular" height={280}
                                sx={{ borderRadius: 2, flex: '1 0 220px' }} />
                        ))}
                    </Box>
                ) : (
                    <Swiper
                        modules={[Navigation, FreeMode]}
                        navigation={{ prevEl: `#prev-${navSuffix}`, nextEl: `#next-${navSuffix}` }}
                        freeMode={{ enabled: true, sticky: true }}
                        spaceBetween={16}
                        slidesPerView={1.5}
                        breakpoints={{
                            480: { slidesPerView: 2.2 },
                            768: { slidesPerView: 3.2 },
                            1024: { slidesPerView: 4.2 },
                            1280: { slidesPerView: 4.5 },
                        }}
                    >
                        {items.map((item) => (
                            <SwiperSlide key={item.id}>
                                <AffiliateProductCard item={item} />
                            </SwiperSlide>
                        ))}
                    </Swiper>
                )}
            </Box>
        </motion.div>
    );
}
