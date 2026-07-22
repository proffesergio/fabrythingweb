import React, { useState, useEffect } from 'react';
import { Outlet, Link, useNavigate } from 'react-router-dom';
import {
    AppBar, Toolbar, Typography, IconButton, Badge, Box, Container,
    Drawer,
    BottomNavigation, BottomNavigationAction, Paper, Divider, Grid,
    useMediaQuery, useTheme, GlobalStyles, Tooltip, useScrollTrigger,
} from '@mui/material';
import {
    ShoppingCart, Person, Menu as MenuIcon, Search, Close,
    Home as HomeIcon, Category, AccountCircle,
    Phone, Email, Facebook, Instagram,
    DarkMode, LightMode, Restaurant as RestaurantIcon,
} from '@mui/icons-material';
import { motion } from 'framer-motion';
import { useSelector } from 'react-redux';
import { selectCartItemCount } from '../../redux/reducer/cartSlice';
import { isAuthenticated } from '../../utils/Helper';
import useApi from '../../hooks/APIHandler';
import MegaMenu, { MobileCategoryMenu } from '../components/MegaMenu';
import LiveSearch from '../components/LiveSearch';
import BrandLogo from '../../components/BrandLogo';

// Highlighted "Food" nav entry pointing at `/food`. Two separate motions, and
// only two: the icon blinks (opacity) and the background gradient slides
// (background-position). The whole badge used to scale-pulse, which made the
// nav bar's text shift as it grew — the animation is now confined to paint-only
// properties that can't affect layout or reflow its neighbours.
function FoodNavBadge() {
    return (
        <Box
            component={Link}
            to="/food"
            sx={{
                display: 'flex', alignItems: 'center', gap: 0.5,
                textDecoration: 'none',
                px: 1.5, py: 0.5,
                borderRadius: 5,
                fontWeight: 700,
                fontSize: '0.85rem',
                color: 'white',
                // Oversized gradient panned by background-position — the cheap way
                // to animate a gradient, since gradient color-stops themselves are
                // not interpolable.
                backgroundImage: 'linear-gradient(100deg,#F97316,#E85D4A,#F2A03D,#F97316)',
                backgroundSize: '300% 100%',
                animation: 'foodBadgeGradient 6s linear infinite',
                boxShadow: '0 2px 10px rgba(232,93,74,0.45)',
                transition: 'box-shadow .22s ease',
                '&:hover': { boxShadow: '0 4px 14px rgba(232,93,74,0.6)' },
                '@keyframes foodBadgeGradient': {
                    '0%': { backgroundPosition: '0% 50%' },
                    '100%': { backgroundPosition: '300% 50%' },
                },
                '@media (prefers-reduced-motion: reduce)': { animation: 'none' },
            }}
        >
            <Box
                component={motion.span}
                aria-hidden
                animate={{ opacity: [1, 0.25, 1] }}
                transition={{ repeat: Infinity, duration: 1.6, ease: 'easeInOut' }}
                sx={{ display: 'inline-flex' }}
            >
                <RestaurantIcon fontSize="small" />
            </Box>
            Food
        </Box>
    );
}

export default function StorefrontLayout({ toggleDarkMode, darkMode }) {
    const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
    const [searchOpen, setSearchOpen]         = useState(false);
    const [categories, setCategories]         = useState([]);
    const cartItemCount = useSelector(selectCartItemCount);
    const navigate      = useNavigate();
    const theme         = useTheme();
    const isMobile      = useMediaQuery(theme.breakpoints.down('md'));
    const isLoggedIn    = isAuthenticated();
    const { callApi }   = useApi();

    // Header shrinks / gains a shadow once the page scrolls past ~40px.
    const scrolled = useScrollTrigger({ disableHysteresis: true, threshold: 40 });

    useEffect(() => {
        callApi({ url: 'store/categories/' }).then(res => {
            if (res?.data?.data) setCategories(res.data.data);
        });
    }, []);

    return (
        <>
            {/* ── Global animation keyframes ── */}
            <GlobalStyles styles={{
                '@keyframes blobMove1': {
                    '0%':   { transform: 'translate(0,0) scale(1)' },
                    '100%': { transform: 'translate(8vw,12vh) scale(1.15)' },
                },
                '@keyframes blobMove2': {
                    '0%':   { transform: 'translate(0,0) scale(1.1)' },
                    '100%': { transform: 'translate(-6vw,-10vh) scale(0.9)' },
                },
                '@keyframes blobMove3': {
                    '0%':   { transform: 'translate(0,0) scale(1)' },
                    '100%': { transform: 'translate(-5vw,8vh) scale(1.2)' },
                },
                '@keyframes marqueeScroll': {
                    '0%':   { transform: 'translateX(0%)' },
                    '100%': { transform: 'translateX(-50%)' },
                },
                '@keyframes flashPulse': {
                    '0%, 100%': { opacity: 1, transform: 'scale(1)' },
                    '50%':      { opacity: 0.5, transform: 'scale(1.25)' },
                },
                '@keyframes barShimmer': {
                    '0%':   { backgroundPosition: '0% 50%' },
                    '50%':  { backgroundPosition: '100% 50%' },
                    '100%': { backgroundPosition: '0% 50%' },
                },
            }} />

            <Box sx={{
                display: 'flex', flexDirection: 'column',
                minHeight: '100vh',
                bgcolor: 'background.default',
                color:   'text.primary',
                position: 'relative',
            }}>
                {/* ── Animated gradient blobs (fixed, behind everything) ── */}
                <Box sx={{ position: 'fixed', inset: 0, zIndex: 0, pointerEvents: 'none', overflow: 'hidden' }}>
                    <Box sx={{
                        position: 'absolute',
                        width: '80vmax', height: '80vmax',
                        borderRadius: '50%',
                        top: '-30vmax', left: '-20vmax',
                        background: darkMode
                            ? 'radial-gradient(circle, rgba(99,102,241,0.20) 0%, transparent 65%)'
                            : 'radial-gradient(circle, rgba(99,102,241,0.10) 0%, transparent 65%)',
                        animation: 'blobMove1 18s ease-in-out infinite alternate',
                    }} />
                    <Box sx={{
                        position: 'absolute',
                        width: '60vmax', height: '60vmax',
                        borderRadius: '50%',
                        bottom: '-20vmax', right: '-15vmax',
                        background: darkMode
                            ? 'radial-gradient(circle, rgba(232,93,74,0.14) 0%, transparent 65%)'
                            : 'radial-gradient(circle, rgba(232,93,74,0.07) 0%, transparent 65%)',
                        animation: 'blobMove2 22s ease-in-out infinite alternate',
                    }} />
                    <Box sx={{
                        position: 'absolute',
                        width: '50vmax', height: '50vmax',
                        borderRadius: '50%',
                        top: '40%', left: '55%',
                        background: darkMode
                            ? 'radial-gradient(circle, rgba(244,114,182,0.12) 0%, transparent 65%)'
                            : 'radial-gradient(circle, rgba(244,114,182,0.05) 0%, transparent 65%)',
                        animation: 'blobMove3 26s ease-in-out infinite alternate',
                    }} />
                </Box>

                {/* ── Everything above blobs needs z-index ── */}
                <Box sx={{ position: 'relative', zIndex: 1, display: 'flex', flexDirection: 'column', flex: 1 }}>
                    {/* ── Announcement marquee bar ── */}
                    <Box sx={{
                        background: darkMode
                            ? 'linear-gradient(270deg,#1e1b4b,#312E81,#4F46E5,#7C3AED,#312E81,#1e1b4b)'
                            : 'linear-gradient(270deg,#3730a3,#4F46E5,#6366F1,#E85D4A,#6366F1,#4F46E5)',
                        backgroundSize: '300% 300%',
                        animation: 'barShimmer 6s ease infinite',
                        py: 0.55,
                        overflow: 'hidden',
                        position: 'relative',
                    }}>
                        {/* Scrolling track — duplicate text so the loop is seamless */}
                        <Box sx={{
                            display: 'inline-flex',
                            whiteSpace: 'nowrap',
                            animation: 'marqueeScroll 22s linear infinite',
                            willChange: 'transform',
                        }}>
                            {[0, 1].map(copy => (
                                <Box key={copy} component="span" sx={{ display: 'inline-flex', alignItems: 'center' }}>
                                    {[
                                        '⚡ Free delivery on orders over ৳1,500',
                                        '🎁 Cash on Delivery available everywhere in Bangladesh',
                                        '🔥 Authentic branded products — fashion, watches, home & beauty',
                                        '✨ Use code FABRYTHING for 10% off your first order',
                                        '📦 Easy returns within 7 days',
                                    ].map((msg, i) => (
                                        <Typography
                                            key={i}
                                            component="span"
                                            variant="caption"
                                            sx={{
                                                color: 'rgba(255,255,255,0.95)',
                                                fontWeight: 600,
                                                fontSize: '0.72rem',
                                                letterSpacing: '0.04em',
                                                px: 3,
                                                '&:not(:last-child)::after': {
                                                    content: '"  ·  "',
                                                    opacity: 0.5,
                                                },
                                            }}
                                        >
                                            {msg}
                                        </Typography>
                                    ))}
                                </Box>
                            ))}
                        </Box>
                    </Box>

                    {/* ── Main Header (animated: shrinks + gains shadow on scroll) ── */}
                    <AppBar
                        position="sticky"
                        elevation={0}
                        sx={{
                            transition: 'box-shadow 0.25s ease, background-color 0.25s ease',
                            boxShadow: scrolled
                                ? (darkMode ? '0 6px 24px rgba(0,0,0,0.5)' : '0 6px 24px rgba(15,23,42,0.10)')
                                : 'none',
                        }}
                    >
                        <Toolbar
                            sx={{
                                justifyContent: 'space-between',
                                gap: { xs: 1, md: 2 },
                                minHeight: scrolled ? { xs: 54, md: 60 } : { xs: 60, md: 72 },
                                transition: 'min-height 0.25s ease',
                            }}
                        >
                            {/* Left: hamburger + logo */}
                            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, flexShrink: 0 }}>
                                {isMobile && (
                                    <IconButton onClick={() => setMobileMenuOpen(true)} color="inherit" size="small">
                                        <MenuIcon />
                                    </IconButton>
                                )}
                                <Box component={Link} to="/" sx={{ display: 'flex', alignItems: 'center' }}>
                                    <BrandLogo
                                        brand="fabrything"
                                        variant="horizontal"
                                        mode={darkMode ? 'dark' : 'light'}
                                        height={scrolled ? { xs: 20, md: 24 } : { xs: 22, md: 28 }}
                                        sx={{ transition: 'height 0.25s ease' }}
                                    />
                                </Box>
                            </Box>

                            {/* Center: live search (desktop) grows to fill */}
                            {!isMobile && (
                                <Box sx={{ flex: 1, display: 'flex', justifyContent: 'center', maxWidth: 560 }}>
                                    <LiveSearch fullWidth />
                                </Box>
                            )}

                            {/* Right: dark mode, account, cart */}
                            <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5, flexShrink: 0 }}>
                                {isMobile && (
                                    <IconButton color="inherit" size="small" onClick={() => setSearchOpen(v => !v)}>
                                        {searchOpen ? <Close /> : <Search />}
                                    </IconButton>
                                )}

                                {/* Dark mode toggle */}
                                <Tooltip title={darkMode ? 'Switch to light mode' : 'Switch to dark mode'}>
                                    <IconButton color="inherit" size="small" onClick={toggleDarkMode}>
                                        {darkMode ? <LightMode fontSize="small" /> : <DarkMode fontSize="small" />}
                                    </IconButton>
                                </Tooltip>

                                <IconButton
                                    color="inherit" size="small"
                                    onClick={() => navigate(isLoggedIn ? '/account' : '/auth/login')}
                                >
                                    <Person />
                                </IconButton>
                                <IconButton color="inherit" size="small" onClick={() => navigate('/cart')}>
                                    <Badge badgeContent={cartItemCount} color="secondary">
                                        <ShoppingCart />
                                    </Badge>
                                </IconButton>
                            </Box>
                        </Toolbar>

                        {/* Mobile search bar */}
                        {isMobile && searchOpen && (
                            <Box sx={{ px: 2, pb: 1.25 }}>
                                <LiveSearch fullWidth autoFocus onNavigate={() => setSearchOpen(false)} />
                            </Box>
                        )}

                        {/* Desktop category nav row (AliExpress-style) */}
                        {!isMobile && (
                            <Box sx={{ borderTop: '1px solid', borderColor: 'divider' }}>
                                <Toolbar variant="dense" sx={{ minHeight: 44, gap: 1, justifyContent: 'space-between' }}>
                                    <MegaMenu categories={categories} />
                                    <FoodNavBadge />
                                </Toolbar>
                            </Box>
                        )}
                    </AppBar>

                    {/* Mobile Drawer */}
                    <Drawer anchor="left" open={mobileMenuOpen} onClose={() => setMobileMenuOpen(false)}>
                        <Box sx={{ width: 280, pt: 2 }}>
                            <Box sx={{ px: 2, pb: 2, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                                <BrandLogo
                                    brand="fabrything"
                                    variant="horizontal"
                                    mode={darkMode ? 'dark' : 'light'}
                                    height={24}
                                />
                                <IconButton size="small" onClick={toggleDarkMode}>
                                    {darkMode ? <LightMode fontSize="small" /> : <DarkMode fontSize="small" />}
                                </IconButton>
                            </Box>
                            <Box sx={{ px: 2, pb: 2 }} onClick={() => setMobileMenuOpen(false)}>
                                <FoodNavBadge />
                            </Box>
                            <Divider />
                            <MobileCategoryMenu
                                categories={categories}
                                onClose={() => setMobileMenuOpen(false)}
                            />
                            <Divider />
                            {isLoggedIn ? (
                                <>
                                    <Box component={Link} to="/account" onClick={() => setMobileMenuOpen(false)}
                                        sx={{ display: 'block', px: 2, py: 1.5, textDecoration: 'none', color: 'text.primary', fontWeight: 600 }}>
                                        My Account
                                    </Box>
                                    <Box component={Link} to="/account?tab=orders" onClick={() => setMobileMenuOpen(false)}
                                        sx={{ display: 'block', px: 2, py: 1.5, textDecoration: 'none', color: 'text.primary', fontWeight: 600 }}>
                                        My Orders
                                    </Box>
                                </>
                            ) : (
                                <Box component={Link} to="/auth/login" onClick={() => setMobileMenuOpen(false)}
                                    sx={{ display: 'block', px: 2, py: 1.5, textDecoration: 'none', color: 'secondary.main', fontWeight: 600 }}>
                                    Login / Sign Up
                                </Box>
                            )}
                        </Box>
                    </Drawer>

                    {/* ── Main Content ── */}
                    <Box sx={{ flex: 1 }}>
                        <Outlet />
                    </Box>

                    {/* ── Footer ── */}
                    <Box sx={{
                        background: darkMode
                            ? 'linear-gradient(135deg,#0F172A 0%,#1E1B4B 100%)'
                            : 'linear-gradient(135deg,#0F172A 0%,#1E1B4B 100%)',
                        color: 'white',
                        mt: 6, pt: 6, pb: isMobile ? 10 : 4,
                    }}>
                        <Container maxWidth="lg">
                            <Grid container spacing={4}>
                                <Grid item xs={12} md={4}>
                                    {/* The footer canvas is dark in both themes, so the logo is
                                        pinned to the dark artwork rather than following darkMode. */}
                                    <BrandLogo
                                        brand="fabrything"
                                        variant="horizontal"
                                        mode="dark"
                                        height={30}
                                        sx={{ mb: 2 }}
                                    />
                                    <Typography variant="body2" sx={{ color: 'rgba(255,255,255,0.6)', mb: 2 }}>
                                        Bangladesh's destination for authentic branded fashion, footwear, watches, home appliances & beauty — with Cash on Delivery nationwide.
                                    </Typography>
                                    <Box sx={{ display: 'flex', gap: 1 }}>
                                        <IconButton size="small" sx={{ color: 'rgba(255,255,255,0.7)', '&:hover': { color: '#A5B4FC' } }}><Facebook /></IconButton>
                                        <IconButton size="small" sx={{ color: 'rgba(255,255,255,0.7)', '&:hover': { color: '#E879F9' } }}><Instagram /></IconButton>
                                    </Box>
                                </Grid>
                                <Grid item xs={6} md={2}>
                                    <Typography variant="subtitle2" fontWeight={700} gutterBottom>Shop</Typography>
                                    {(categories.length ? categories.slice(0, 6) : [
                                        { name: "Men's Fashion", slug: 'mens-fashion' },
                                        { name: "Women's Fashion", slug: 'womens-fashion' },
                                        { name: 'Shoes', slug: 'shoes' },
                                        { name: 'Watches', slug: 'watches' },
                                    ]).map(cat => (
                                        <Typography key={cat.slug} component={Link} to={`/shop?category=${cat.slug}`}
                                            variant="body2" sx={{ display: 'block', mb: 0.5, color: 'rgba(255,255,255,0.6)', textDecoration: 'none', '&:hover': { color: '#A5B4FC' } }}>
                                            {cat.name}
                                        </Typography>
                                    ))}
                                </Grid>
                                <Grid item xs={6} md={3}>
                                    <Typography variant="subtitle2" fontWeight={700} gutterBottom>Customer Service</Typography>
                                    {['Shipping & Delivery', 'Returns & Exchanges', 'Size Guide'].map(item => (
                                        <Typography key={item} variant="body2" sx={{ mb: 0.5, color: 'rgba(255,255,255,0.6)' }}>{item}</Typography>
                                    ))}
                                </Grid>
                                <Grid item xs={12} md={3}>
                                    <Typography variant="subtitle2" fontWeight={700} gutterBottom>Contact</Typography>
                                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
                                        <Phone fontSize="small" sx={{ color: 'rgba(255,255,255,0.6)' }} />
                                        <Typography variant="body2" sx={{ color: 'rgba(255,255,255,0.6)' }}>+880 1XXX-XXXXXX</Typography>
                                    </Box>
                                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                                        <Email fontSize="small" sx={{ color: 'rgba(255,255,255,0.6)' }} />
                                        <Typography variant="body2" sx={{ color: 'rgba(255,255,255,0.6)' }}>support@fabrything.com</Typography>
                                    </Box>
                                </Grid>
                            </Grid>
                            <Divider sx={{ my: 3, borderColor: 'rgba(255,255,255,0.12)' }} />
                            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 1 }}>
                                <Typography variant="caption" sx={{ color: 'rgba(255,255,255,0.4)' }}>
                                    &copy; 2026 Fabrything. All rights reserved.
                                </Typography>
                                <Box sx={{ display: 'flex', gap: 2 }}>
                                    <Typography variant="caption" sx={{ color: 'rgba(255,255,255,0.6)' }}>Cash on Delivery</Typography>
                                </Box>
                            </Box>
                        </Container>
                    </Box>

                    {/* Mobile Bottom Nav */}
                    {isMobile && (
                        <Paper sx={{ position: 'fixed', bottom: 0, left: 0, right: 0, zIndex: 1200 }} elevation={3}>
                            <BottomNavigation showLabels>
                                <BottomNavigationAction label="Home"    icon={<HomeIcon />}    onClick={() => navigate('/')} />
                                <BottomNavigationAction label="Shop"    icon={<Category />}    onClick={() => navigate('/shop')} />
                                <BottomNavigationAction label="Cart"
                                    icon={<Badge badgeContent={cartItemCount} color="secondary"><ShoppingCart /></Badge>}
                                    onClick={() => navigate('/cart')} />
                                <BottomNavigationAction label="Account" icon={<AccountCircle />}
                                    onClick={() => navigate(isLoggedIn ? '/account' : '/auth/login')} />
                            </BottomNavigation>
                        </Paper>
                    )}
                </Box>
            </Box>
        </>
    );
}
