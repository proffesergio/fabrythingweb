import React from 'react';
import { Box, Typography, Button, Grid, Container } from '@mui/material';
import { ArrowForward } from '@mui/icons-material';
import { Link } from 'react-router-dom';
import { motion } from 'framer-motion';

const banners = [
    {
        title: 'Panjabi Collection',
        subtitle: 'Celebrate Eid in style with our premium collection',
        cta: 'Shop Panjabis',
        link: '/shop?category=men-panjabi',
        gradient: 'linear-gradient(135deg, #1a1a2e 0%, #16213e 100%)',
    },
    {
        title: "Women's Summer Range",
        subtitle: 'Lightweight fabrics for the perfect summer look',
        cta: 'Shop Women',
        link: '/shop?gender=WOMEN',
        gradient: 'linear-gradient(135deg, #E85D4A 0%, #c0392b 100%)',
    },
];

export default function PromoBanner() {
    return (
        <Container maxWidth="lg" sx={{ mb: 6 }}>
            <Grid container spacing={2}>
                {banners.map((banner, i) => (
                    <Grid item xs={12} md={6} key={i}>
                        <motion.div
                            initial={{ opacity: 0, x: i === 0 ? -30 : 30 }}
                            whileInView={{ opacity: 1, x: 0 }}
                            viewport={{ once: true, margin: '-50px' }}
                            transition={{ duration: 0.5, delay: i * 0.15 }}
                        >
                            <Box
                                sx={{
                                    backgroundImage: banner.gradient,
                                    color: 'white',
                                    borderRadius: 3,
                                    p: { xs: 3, md: 4 },
                                    minHeight: { xs: 160, md: 200 },
                                    display: 'flex',
                                    flexDirection: 'column',
                                    justifyContent: 'center',
                                    position: 'relative',
                                    overflow: 'hidden',
                                    '&::after': {
                                        content: '""',
                                        position: 'absolute',
                                        top: -40, right: -40,
                                        width: 200, height: 200,
                                        borderRadius: '50%',
                                        background: 'rgba(255,255,255,0.05)',
                                    },
                                }}
                            >
                                <Typography
                                    variant="h5"
                                    sx={{ fontWeight: 800, mb: 1, fontSize: { xs: '1.3rem', md: '1.6rem' } }}
                                >
                                    {banner.title}
                                </Typography>
                                <Typography
                                    variant="body2"
                                    sx={{ color: 'rgba(255,255,255,0.8)', mb: 2.5, maxWidth: 280 }}
                                >
                                    {banner.subtitle}
                                </Typography>
                                <Box>
                                    <Button
                                        component={Link}
                                        to={banner.link}
                                        variant="contained"
                                        size="small"
                                        endIcon={<ArrowForward />}
                                        sx={{
                                            bgcolor: 'white',
                                            color: '#2D2D2D',
                                            fontWeight: 700,
                                            '&:hover': {
                                                bgcolor: 'rgba(255,255,255,0.9)',
                                                transform: 'translateY(-1px)',
                                            },
                                            transition: 'all 0.2s',
                                        }}
                                    >
                                        {banner.cta}
                                    </Button>
                                </Box>
                            </Box>
                        </motion.div>
                    </Grid>
                ))}
            </Grid>
        </Container>
    );
}
