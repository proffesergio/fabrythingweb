import React, { useState } from 'react';
import {
    Box, Typography, Paper, Grid,
    List, ListItemButton, ListItemText,
} from '@mui/material';
import { Apps, Whatshot, FiberNew, Storefront as StorefrontIcon } from '@mui/icons-material';
import { Link } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { CATEGORY_META, metaFor } from './categoryMeta';

// Emoji glyph + accent colour per category slug (AliExpress-style colourful tiles).

const quickLinks = [
    { label: 'Home',         path: '/',                    icon: <StorefrontIcon fontSize="small" /> },
    { label: 'Shop All',     path: '/shop',                icon: <Apps fontSize="small" /> },
    { label: 'Flash Deals',  path: '/shop?ordering=price_low', icon: <Whatshot fontSize="small" />, hot: true },
    { label: 'New Arrivals', path: '/shop?ordering=newest',    icon: <FiberNew fontSize="small" /> },
];

// ── Desktop nav: "All Categories" flyout + quick links ────────────────────────
export default function MegaMenu({ categories = [] }) {
    const [open, setOpen] = useState(false);

    return (
        <Box sx={{ display: 'flex', gap: 0.5, alignItems: 'center' }}>
            {/* All Categories flyout */}
            <Box
                onMouseEnter={() => setOpen(true)}
                onMouseLeave={() => setOpen(false)}
                sx={{ position: 'relative' }}
            >
                <Box
                    sx={{
                        display: 'flex', alignItems: 'center', gap: 0.75,
                        px: 1.5, py: 1, borderRadius: 2, cursor: 'pointer',
                        color: open ? 'primary.main' : 'text.primary',
                        fontWeight: 700, fontSize: '0.92rem',
                        bgcolor: open ? 'action.hover' : 'transparent',
                        transition: 'all 0.15s',
                    }}
                >
                    <Apps fontSize="small" />
                    <span>All Categories</span>
                </Box>

                {/* transparent bridge so moving into the panel doesn't close it */}
                <Box sx={{ position: 'absolute', top: '100%', left: 0, width: '100%', height: 10, zIndex: 1300 }} />

                <AnimatePresence>
                    {open && (
                        <motion.div
                            initial={{ opacity: 0, y: 8 }}
                            animate={{ opacity: 1, y: 0 }}
                            exit={{ opacity: 0, y: 8 }}
                            transition={{ duration: 0.16 }}
                            style={{ position: 'absolute', top: 'calc(100% + 10px)', left: 0, zIndex: 1300 }}
                        >
                            <Paper
                                elevation={12}
                                sx={{
                                    width: 560, borderRadius: 3, p: 2.5,
                                    border: '1px solid', borderColor: 'divider',
                                }}
                            >
                                <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 1.5 }}>
                                    <Typography variant="subtitle1" fontWeight={800}>Shop by Category</Typography>
                                    <Typography
                                        component={Link} to="/shop" onClick={() => setOpen(false)}
                                        variant="body2" sx={{ color: 'secondary.main', fontWeight: 700, textDecoration: 'none', '&:hover': { textDecoration: 'underline' } }}
                                    >
                                        View all →
                                    </Typography>
                                </Box>
                                <Grid container spacing={1}>
                                    {categories.map((cat) => {
                                        const meta = metaFor(cat.slug);
                                        return (
                                            <Grid item xs={6} key={cat.id}>
                                                <Box
                                                    component={Link}
                                                    to={`/shop?category=${cat.slug}`}
                                                    onClick={() => setOpen(false)}
                                                    sx={{
                                                        display: 'flex', alignItems: 'center', gap: 1.25,
                                                        p: 1, borderRadius: 2, textDecoration: 'none',
                                                        color: 'text.primary', transition: 'all 0.15s',
                                                        '&:hover': { bgcolor: 'action.hover', transform: 'translateX(3px)' },
                                                    }}
                                                >
                                                    <Box sx={{
                                                        width: 40, height: 40, borderRadius: 2, flexShrink: 0,
                                                        display: 'flex', alignItems: 'center', justifyContent: 'center',
                                                        fontSize: '1.25rem',
                                                        bgcolor: `${meta.color}1A`,
                                                    }}>
                                                        {meta.icon}
                                                    </Box>
                                                    <Box sx={{ minWidth: 0 }}>
                                                        <Typography variant="body2" fontWeight={700} noWrap>{cat.name}</Typography>
                                                        <Typography variant="caption" color="text.secondary" noWrap sx={{ display: 'block', maxWidth: 200 }}>
                                                            {cat.description || 'Explore collection'}
                                                        </Typography>
                                                    </Box>
                                                </Box>
                                            </Grid>
                                        );
                                    })}
                                </Grid>
                            </Paper>
                        </motion.div>
                    )}
                </AnimatePresence>
            </Box>

            {/* Quick links */}
            {quickLinks.map((link) => (
                <Typography
                    key={link.label}
                    component={Link}
                    to={link.path}
                    sx={{
                        display: 'flex', alignItems: 'center', gap: 0.5,
                        textDecoration: 'none',
                        color: link.hot ? 'secondary.main' : 'text.primary',
                        fontSize: '0.92rem', fontWeight: 600,
                        px: 1.25, py: 1, borderRadius: 2,
                        transition: 'color 0.15s, background 0.15s',
                        '&:hover': { color: 'primary.main', bgcolor: 'action.hover' },
                    }}
                >
                    {link.icon}
                    {link.label}
                </Typography>
            ))}
        </Box>
    );
}

// ── Mobile drawer menu ────────────────────────────────────────────────────────
export function MobileCategoryMenu({ categories = [], onClose }) {
    return (
        <List>
            <ListItemButton component={Link} to="/" onClick={onClose}>
                <ListItemText primary="Home" primaryTypographyProps={{ fontWeight: 600 }} />
            </ListItemButton>
            <ListItemButton component={Link} to="/shop" onClick={onClose}>
                <ListItemText primary="Shop All" primaryTypographyProps={{ fontWeight: 600 }} />
            </ListItemButton>
            <ListItemButton component={Link} to="/shop?ordering=newest" onClick={onClose}>
                <ListItemText primary="New Arrivals" primaryTypographyProps={{ fontWeight: 600, color: 'primary.main' }} />
            </ListItemButton>

            <Typography variant="overline" sx={{ px: 2, pt: 1.5, display: 'block', color: 'text.secondary', fontWeight: 700 }}>
                Categories
            </Typography>
            {categories.map((cat) => {
                const meta = metaFor(cat.slug);
                return (
                    <ListItemButton
                        key={cat.id}
                        component={Link}
                        to={`/shop?category=${cat.slug}`}
                        onClick={onClose}
                    >
                        <Box sx={{
                            width: 32, height: 32, mr: 1.5, borderRadius: 1.5, flexShrink: 0,
                            display: 'flex', alignItems: 'center', justifyContent: 'center',
                            fontSize: '1.05rem', bgcolor: `${meta.color}1A`,
                        }}>
                            {meta.icon}
                        </Box>
                        <ListItemText primary={cat.name} primaryTypographyProps={{ fontSize: '0.95rem', fontWeight: 500 }} />
                    </ListItemButton>
                );
            })}
        </List>
    );
}

export { CATEGORY_META, metaFor };
