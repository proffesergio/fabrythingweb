import React from 'react';
import { Box, Typography, Button, IconButton } from '@mui/material';
import { ArrowForward, ChevronLeft, ChevronRight } from '@mui/icons-material';
import { Link } from 'react-router-dom';
import { Swiper, SwiperSlide } from 'swiper/react';
import { Navigation, FreeMode } from 'swiper/modules';
import { motion } from 'framer-motion';
import 'swiper/css';
import 'swiper/css/navigation';
import ProductCard from './ProductCard';

export default function ProductCarousel({ title, products, viewAllLink, titleColor }) {
    if (!products || products.length === 0) return null;

    const prevId = `prev-${title?.replace(/\s/g, '-')}`;
    const nextId = `next-${title?.replace(/\s/g, '-')}`;

    return (
        <motion.div
            initial={{ opacity: 0, y: 30 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true, margin: '-50px' }}
            transition={{ duration: 0.5 }}
        >
            <Box sx={{ mb: 6 }}>
                <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
                        <Typography variant="h4" sx={{ fontWeight: 800, color: titleColor || 'text.primary' }}>
                            {title}
                        </Typography>
                        <Box sx={{ display: { xs: 'none', md: 'flex' }, gap: 0.5 }}>
                            <IconButton
                                id={prevId}
                                size="small"
                                sx={{
                                    border: '1px solid',
                                    borderColor: 'divider',
                                    '&:hover': { bgcolor: 'primary.main', color: 'white' },
                                }}
                            >
                                <ChevronLeft />
                            </IconButton>
                            <IconButton
                                id={nextId}
                                size="small"
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
                    {viewAllLink && (
                        <Button
                            component={Link}
                            to={viewAllLink}
                            endIcon={<ArrowForward />}
                            sx={{ fontWeight: 600 }}
                        >
                            View All
                        </Button>
                    )}
                </Box>

                <Swiper
                    modules={[Navigation, FreeMode]}
                    navigation={{ prevEl: `#${prevId}`, nextEl: `#${nextId}` }}
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
                    {products.map(product => (
                        <SwiperSlide key={product.id}>
                            <ProductCard product={product} />
                        </SwiperSlide>
                    ))}
                </Swiper>
            </Box>
        </motion.div>
    );
}
