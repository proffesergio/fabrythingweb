import React from 'react';
import { Box, Typography, Container } from '@mui/material';
import { LocalFireDepartment } from '@mui/icons-material';
import { Swiper, SwiperSlide } from 'swiper/react';
import { Navigation, FreeMode } from 'swiper/modules';
import { motion } from 'framer-motion';
import 'swiper/css';
import 'swiper/css/navigation';
import CountdownTimer from './CountdownTimer';
import ProductCard from './ProductCard';

export default function FlashSaleSection({ products, endTime }) {
    if (!products || products.length === 0) return null;

    return (
        <motion.div
            initial={{ opacity: 0, y: 30 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true, margin: '-50px' }}
            transition={{ duration: 0.5 }}
        >
            <Box
                sx={{
                    background: 'linear-gradient(135deg, #FFF5F5 0%, #FED7D7 100%)',
                    py: { xs: 3, md: 5 },
                    mb: 6,
                    borderRadius: 3,
                    overflow: 'hidden',
                }}
            >
                <Container maxWidth="lg">
                    <Box
                        sx={{
                            display: 'flex',
                            flexDirection: { xs: 'column', sm: 'row' },
                            justifyContent: 'space-between',
                            alignItems: { xs: 'flex-start', sm: 'center' },
                            mb: 3,
                            gap: 2,
                        }}
                    >
                        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                            <LocalFireDepartment sx={{ color: '#E85D4A', fontSize: 32 }} />
                            <Typography
                                variant="h4"
                                sx={{ fontWeight: 800, color: '#E85D4A', letterSpacing: '-0.5px' }}
                            >
                                Flash Sale
                            </Typography>
                        </Box>
                        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5 }}>
                            <Typography variant="body2" sx={{ fontWeight: 600, color: 'text.secondary' }}>
                                Ends in:
                            </Typography>
                            <CountdownTimer targetDate={endTime} />
                        </Box>
                    </Box>

                    <Swiper
                        modules={[Navigation, FreeMode]}
                        freeMode={{ enabled: true, sticky: true }}
                        spaceBetween={16}
                        slidesPerView={1.5}
                        breakpoints={{
                            480: { slidesPerView: 2.2 },
                            768: { slidesPerView: 3.2 },
                            1024: { slidesPerView: 4 },
                        }}
                    >
                        {products.map(product => (
                            <SwiperSlide key={product.id}>
                                <ProductCard product={product} showFlashBadge />
                            </SwiperSlide>
                        ))}
                    </Swiper>
                </Container>
            </Box>
        </motion.div>
    );
}
