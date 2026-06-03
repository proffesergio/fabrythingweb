import React from 'react';
import { Box, Typography, Button, Container } from '@mui/material';
import { ArrowForward } from '@mui/icons-material';
import { Link } from 'react-router-dom';
import { Swiper, SwiperSlide } from 'swiper/react';
import { Autoplay, Pagination, EffectFade } from 'swiper/modules';
import 'swiper/css';
import 'swiper/css/pagination';
import 'swiper/css/effect-fade';

const slides = [
    {
        title: 'Eid Collection 2026',
        subtitle: 'Discover premium Panjabis, Sarees & festive wear for the whole family',
        cta: 'Shop Eid Collection',
        link: '/shop',
        image: 'https://picsum.photos/seed/eid_fashion/1600/700',
        overlay: 'linear-gradient(135deg, rgba(26,26,46,0.82) 0%, rgba(15,52,96,0.72) 100%)',
    },
    {
        title: 'Summer Sale — Up to 50% Off',
        subtitle: 'Limited time offer on selected men\'s, women\'s & kids\' styles.',
        cta: 'Shop the Sale',
        link: '/shop?ordering=price_low',
        image: 'https://picsum.photos/seed/summer_sale/1600/700',
        overlay: 'linear-gradient(135deg, rgba(232,93,74,0.80) 0%, rgba(192,57,43,0.70) 100%)',
    },
    {
        title: 'New Arrivals Every Week',
        subtitle: 'Fresh styles added constantly. Stay ahead of the trends.',
        cta: 'See What\'s New',
        link: '/shop?ordering=newest',
        image: 'https://picsum.photos/seed/new_arrivals/1600/700',
        overlay: 'linear-gradient(135deg, rgba(45,45,45,0.82) 0%, rgba(99,99,99,0.72) 100%)',
    },
    {
        title: 'Free Delivery Nationwide',
        subtitle: 'On all orders over ৳1,500. Cash on Delivery & bKash accepted.',
        cta: 'Start Shopping',
        link: '/shop',
        image: 'https://picsum.photos/seed/delivery_fashion/1600/700',
        overlay: 'linear-gradient(135deg, rgba(27,94,32,0.82) 0%, rgba(56,142,60,0.72) 100%)',
    },
];

export default function HeroCarousel() {
    return (
        <Box sx={{ position: 'relative' }}>
            <Swiper
                modules={[Autoplay, Pagination, EffectFade]}
                effect="fade"
                autoplay={{ delay: 4000, disableOnInteraction: false }}
                pagination={{ clickable: true }}
                loop
                style={{ '--swiper-pagination-color': '#E85D4A', '--swiper-pagination-bullet-inactive-color': '#fff' }}
            >
                {slides.map((slide, i) => (
                    <SwiperSlide key={i}>
                        <Box
                            sx={{
                                position: 'relative',
                                color: 'white',
                                py: { xs: 8, md: 14 },
                                textAlign: 'center',
                                overflow: 'hidden',
                                minHeight: { xs: 280, md: 420 },
                                display: 'flex',
                                alignItems: 'center',
                                // Background image layer
                                '&::after': {
                                    content: '""',
                                    position: 'absolute',
                                    inset: 0,
                                    backgroundImage: `url(${slide.image})`,
                                    backgroundSize: 'cover',
                                    backgroundPosition: 'center',
                                    zIndex: 0,
                                },
                                // Gradient overlay on top of image
                                '&::before': {
                                    content: '""',
                                    position: 'absolute',
                                    inset: 0,
                                    backgroundImage: slide.overlay,
                                    zIndex: 1,
                                },
                            }}
                        >
                            <Container maxWidth="md" sx={{ position: 'relative', zIndex: 2, width: '100%' }}>
                                <Typography
                                    variant="h2"
                                    sx={{
                                        fontWeight: 800,
                                        mb: 2,
                                        fontSize: { xs: '2rem', sm: '2.5rem', md: '3.5rem' },
                                        textShadow: '0 2px 20px rgba(0,0,0,0.3)',
                                        letterSpacing: '-1px',
                                    }}
                                >
                                    {slide.title}
                                </Typography>
                                <Typography
                                    variant="h6"
                                    sx={{
                                        color: 'rgba(255,255,255,0.85)',
                                        mb: 4,
                                        fontWeight: 400,
                                        fontSize: { xs: '0.95rem', md: '1.25rem' },
                                        maxWidth: 600,
                                        mx: 'auto',
                                    }}
                                >
                                    {slide.subtitle}
                                </Typography>
                                <Button
                                    component={Link}
                                    to={slide.link}
                                    variant="contained"
                                    size="large"
                                    endIcon={<ArrowForward />}
                                    sx={{
                                        bgcolor: 'white',
                                        color: '#2D2D2D',
                                        fontWeight: 700,
                                        px: 4,
                                        py: 1.5,
                                        borderRadius: 3,
                                        fontSize: '1rem',
                                        '&:hover': {
                                            bgcolor: 'rgba(255,255,255,0.9)',
                                            transform: 'translateY(-2px)',
                                            boxShadow: '0 8px 25px rgba(0,0,0,0.3)',
                                        },
                                        transition: 'all 0.3s ease',
                                    }}
                                >
                                    {slide.cta}
                                </Button>
                            </Container>
                        </Box>
                    </SwiperSlide>
                ))}
            </Swiper>
        </Box>
    );
}
