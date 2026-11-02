import React, { useId } from 'react';
import { Box, Typography, Button, IconButton } from '@mui/material';
import { ArrowForward, ChevronLeft, ChevronRight } from '@mui/icons-material';
import { Link } from 'react-router-dom';
import { Swiper, SwiperSlide } from 'swiper/react';
import { A11y, Keyboard, Navigation, FreeMode } from 'swiper/modules';
import { motion, useReducedMotion } from 'framer-motion';
import 'swiper/css';
import 'swiper/css/navigation';
import ProductCard from './ProductCard';

export default function ProductCarousel({ title, products, viewAllLink, titleColor }) {
    const id = useId().replace(/:/g, '');
    const reduceMotion = useReducedMotion();
    if (!products || products.length === 0) return null;

    const prevId = `prev-${id}`;
    const nextId = `next-${id}`;

    return (
        <motion.div
            initial={reduceMotion ? false : { opacity: 0, y: 30 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true, margin: '-50px' }}
            transition={{ duration: 0.5 }}
        >
            <Box sx={{ mb: 6 }}>
                <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 1.5, mb: 3 }}>
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
                        <Typography variant="h4" component="h2" sx={{ fontWeight: 800, fontSize: { xs: '1.5rem', md: '2.125rem' }, color: titleColor || 'text.primary' }}>
                            {title}
                        </Typography>
                        <Box sx={{ display: 'flex', gap: 0.5 }}>
                            <IconButton
                                id={prevId}
                                aria-label={`Previous ${title} products`}
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
                                aria-label={`Next ${title} products`}
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
                    modules={[A11y, Keyboard, Navigation, FreeMode]}
                    a11y={{
                        containerMessage: `${title} products`,
                        prevSlideMessage: `Previous ${title} products`,
                        nextSlideMessage: `Next ${title} products`,
                    }}
                    keyboard={{ enabled: true, onlyInViewport: true }}
                    speed={reduceMotion ? 0 : 350}
                    watchOverflow
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
                    {products.map((product, index) => (
                        <SwiperSlide key={product.id} style={{ height: 'auto' }}>
                            <motion.div
                                initial={reduceMotion ? false : { opacity: 0, y: 16 }}
                                whileInView={{ opacity: 1, y: 0 }}
                                viewport={{ once: true, amount: 0.1 }}
                                transition={{ duration: 0.35, delay: reduceMotion ? 0 : (index % 4) * 0.06 }}
                                style={{ height: '100%' }}
                            >
                                <ProductCard product={product} />
                            </motion.div>
                        </SwiperSlide>
                    ))}
                </Swiper>
            </Box>
        </motion.div>
    );
}
