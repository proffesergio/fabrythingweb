import React from 'react';
import { Box, Container, Typography, Grid } from '@mui/material';
import { Link } from 'react-router-dom';
import { motion } from 'framer-motion';
import { metaFor } from './MegaMenu';

/**
 * AliExpress-style colourful category tiles. Each tile links to the filtered
 * catalog. Emoji + accent colour come from the shared CATEGORY_META map.
 */
export default function CategoryGrid({ categories = [] }) {
    if (!categories.length) return null;

    return (
        <Container maxWidth="lg" sx={{ mb: 5 }}>
            <Typography variant="h4" sx={{ fontWeight: 800, mb: 0.5 }}>Shop by Category</Typography>
            <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
                Authentic brands across every category — Cash on Delivery nationwide
            </Typography>

            <Grid container spacing={{ xs: 1.5, sm: 2 }}>
                {categories.map((cat, i) => {
                    const meta = metaFor(cat.slug);
                    return (
                        <Grid item xs={3} sm={3} key={cat.id} sx={{ flexBasis: { md: '12.5%' }, maxWidth: { md: '12.5%' } }}>
                            <motion.div
                                initial={{ opacity: 0, y: 20 }}
                                whileInView={{ opacity: 1, y: 0 }}
                                viewport={{ once: true }}
                                transition={{ duration: 0.35, delay: i * 0.05 }}
                            >
                                <Box
                                    component={Link}
                                    to={`/shop?category=${cat.slug}`}
                                    sx={{
                                        display: 'flex', flexDirection: 'column', alignItems: 'center',
                                        gap: 1, textDecoration: 'none', color: 'text.primary',
                                        p: { xs: 1, sm: 1.5 }, borderRadius: 3,
                                        transition: 'transform 0.2s ease, background 0.2s ease',
                                        '&:hover': { transform: 'translateY(-4px)', bgcolor: 'action.hover' },
                                        '&:hover .cat-icon': { boxShadow: `0 8px 20px ${meta.color}55` },
                                    }}
                                >
                                    <Box
                                        className="cat-icon"
                                        sx={{
                                            width: { xs: 52, sm: 64 }, height: { xs: 52, sm: 64 },
                                            borderRadius: '50%',
                                            display: 'flex', alignItems: 'center', justifyContent: 'center',
                                            fontSize: { xs: '1.5rem', sm: '1.9rem' },
                                            background: `linear-gradient(135deg, ${meta.color}22, ${meta.color}0D)`,
                                            border: '2px solid', borderColor: `${meta.color}33`,
                                            transition: 'box-shadow 0.25s ease',
                                        }}
                                    >
                                        {meta.icon}
                                    </Box>
                                    <Typography
                                        variant="caption"
                                        sx={{ fontWeight: 600, textAlign: 'center', lineHeight: 1.2, fontSize: { xs: '0.7rem', sm: '0.78rem' } }}
                                    >
                                        {cat.name}
                                    </Typography>
                                </Box>
                            </motion.div>
                        </Grid>
                    );
                })}
            </Grid>
        </Container>
    );
}
