import React, { useState } from 'react';
import { Box, Typography, Tabs, Tab, Grid } from '@mui/material';
import { TrendingUp, FiberNew, Star } from '@mui/icons-material';
import { motion, AnimatePresence } from 'framer-motion';
import ProductCard from './ProductCard';

const tabs = [
    { label: 'New Arrivals', icon: <FiberNew />, key: 'newArrivals' },
    { label: 'Trending', icon: <TrendingUp />, key: 'trending' },
    { label: 'Best Sellers', icon: <Star />, key: 'bestSellers' },
];

export default function TabbedProductSection({ trending, newArrivals, bestSellers }) {
    const [activeTab, setActiveTab] = useState(0);

    const data = { trending, newArrivals, bestSellers };
    const activeKey = tabs[activeTab].key;
    const activeProducts = data[activeKey] || [];

    if (!trending?.length && !newArrivals?.length && !bestSellers?.length) return null;

    return (
        <motion.div
            initial={{ opacity: 0, y: 30 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true, margin: '-50px' }}
            transition={{ duration: 0.5 }}
        >
            <Box sx={{ mb: 6 }}>
                <Box sx={{ display: 'flex', flexDirection: { xs: 'column', sm: 'row' }, justifyContent: 'space-between', alignItems: { xs: 'flex-start', sm: 'center' }, mb: 3, gap: 2 }}>
                    <Typography variant="h4" sx={{ fontWeight: 800 }}>
                        Popular Products
                    </Typography>
                    <Tabs
                        value={activeTab}
                        onChange={(_, v) => setActiveTab(v)}
                        sx={{
                            '& .MuiTab-root': {
                                textTransform: 'none',
                                fontWeight: 600,
                                fontSize: { xs: '0.85rem', sm: '0.95rem' },
                                minHeight: 42,
                            },
                            '& .MuiTabs-indicator': {
                                height: 3,
                                borderRadius: 2,
                            },
                        }}
                    >
                        {tabs.map((tab, i) => (
                            <Tab key={i} icon={tab.icon} iconPosition="start" label={tab.label} />
                        ))}
                    </Tabs>
                </Box>

                <AnimatePresence mode="wait">
                    <motion.div
                        key={activeTab}
                        initial={{ opacity: 0, y: 15 }}
                        animate={{ opacity: 1, y: 0 }}
                        exit={{ opacity: 0, y: -15 }}
                        transition={{ duration: 0.3 }}
                    >
                        <Grid container spacing={2}>
                            {activeProducts.slice(0, 8).map(product => (
                                <Grid item xs={6} sm={4} md={3} key={product.id}>
                                    <ProductCard product={product} />
                                </Grid>
                            ))}
                        </Grid>
                    </motion.div>
                </AnimatePresence>
            </Box>
        </motion.div>
    );
}
