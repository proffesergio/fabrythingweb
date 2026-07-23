import { Outlet, Link, useNavigate, useLocation } from 'react-router-dom';
import { AppBar, Toolbar, Box, Typography, IconButton, Badge, Button, Container, Stack, Tooltip } from '@mui/material';
import ShoppingBagOutlinedIcon from '@mui/icons-material/ShoppingBagOutlined';
import RestaurantMenuRoundedIcon from '@mui/icons-material/RestaurantMenuRounded';
import DarkModeRoundedIcon from '@mui/icons-material/DarkModeRounded';
import LightModeRoundedIcon from '@mui/icons-material/LightModeRounded';
import StorefrontOutlinedIcon from '@mui/icons-material/StorefrontOutlined';
import PlaceRoundedIcon from '@mui/icons-material/PlaceRounded';
import KeyboardArrowDownRoundedIcon from '@mui/icons-material/KeyboardArrowDownRounded';
import { useSelector } from 'react-redux';
import { motion, AnimatePresence } from 'framer-motion';
import { selectFoodCount, selectFoodSubtotal } from '../redux/foodCartSlice';
import { useFoodLocation } from '../context/FoodLocationContext';
import LocationPicker from '../components/LocationPicker';
import FoodGalaxy from '../components/FoodGalaxy';
import NotificationsBell from '../components/NotificationsBell';
import NoticeMarquee from '../components/NoticeMarquee';
import FoodBottomNav from '../components/FoodBottomNav';
import { useFoodTheme } from '../context/FoodThemeContext';
import BrandLogo from '../../components/BrandLogo';

export default function FoodLayout() {
  const count = useSelector(selectFoodCount);
  const subtotal = useSelector(selectFoodSubtotal);
  const navigate = useNavigate();
  const { pathname } = useLocation();
  const loc = useFoodLocation() || {};
  const { mode, toggleMode } = useFoodTheme();
  const isDark = mode === 'dark';
  const onCartPages = pathname.includes('/food/cart') || pathname.includes('/food/checkout');

  return (
    <Box sx={{
      minHeight: '100vh', bgcolor: 'transparent', position: 'relative',
      // Nothing may sit under the fixed furniture at the bottom of a phone:
      // the tab bar (~60px) always, plus the cart bar (~64px) when it is up.
      // md and above has neither.
      pb: { xs: count && !onCartPages ? 17 : 9, md: 0 },
      // A single overflowing child used to make the whole page pan sideways,
      // which on a phone reads as a broken app rather than a wide element.
      overflowX: 'hidden',
    }}>
      <FoodGalaxy />
      <AppBar position="sticky" elevation={0} sx={{ zIndex: 2 }}>
        <Container maxWidth="lg">
          <Toolbar disableGutters sx={{ gap: { xs: 1, sm: 2 }, minHeight: 68 }}>
            <Box component={Link} to="/food" sx={{ display: 'flex', alignItems: 'center', flexShrink: 0 }}>
              <BrandLogo
                brand="food"
                variant="horizontal"
                mode={isDark ? 'dark' : 'light'}
                height={{ xs: 24, sm: 28 }}
              />
            </Box>

            {loc.openPicker && (
              <Button
                onClick={loc.openPicker}
                // flexShrink:0 is load-bearing: without it the toolbar's flex row
                // squeezed this button down to a bare circle on narrow screens,
                // hiding the area name entirely. minWidth keeps the label legible.
                sx={{ px: 1.25, py: 0.6, borderRadius: 999, bgcolor: 'background.paper',
                      border: 1, borderColor: 'divider', flexShrink: 0,
                      color: 'text.primary', textTransform: 'none',
                      minWidth: { xs: 118, sm: 150 }, maxWidth: { xs: 160, sm: 220 } }}
              >
                <PlaceRoundedIcon sx={{ fontSize: 18, color: 'primary.main', mr: 0.5 }} />
                <Box sx={{ textAlign: 'left', minWidth: 0, lineHeight: 1.1 }}>
                  <Typography variant="caption" sx={{ display: 'block', color: 'text.secondary', fontSize: 10 }}>
                    {loc.lang === 'bn' ? 'ডেলিভারি' : 'Deliver to'}
                  </Typography>
                  <Typography variant="body2" noWrap sx={{ fontWeight: 800 }}>
                    {loc.currentVillage
                      ? (loc.lang === 'bn' && loc.currentVillage.name_bn ? loc.currentVillage.name_bn : loc.currentVillage.name)
                      : loc.currentZone
                        ? (loc.lang === 'bn' && loc.currentZone.name_bn ? loc.currentZone.name_bn : loc.currentZone.name)
                        : (loc.lang === 'bn' ? 'এলাকা নির্বাচন' : 'Choose area')}
                  </Typography>
                </Box>
                <KeyboardArrowDownRoundedIcon sx={{ fontSize: 18, color: 'text.secondary', ml: 0.25 }} />
              </Button>
            )}

            <Box sx={{ flexGrow: 1 }} />

            <Button
              size="small" color="inherit" startIcon={<RestaurantMenuRoundedIcon />}
              component={Link} to="/food/restaurants"
              // Hidden on phones: FoodBottomNav owns navigation there, and this
              // was one of seven controls competing for a 360px toolbar.
              sx={{ display: { xs: 'none', md: 'inline-flex' },
                    color: pathname === '/food/restaurants' ? 'primary.main' : 'text.secondary',
                    fontWeight: 700, minWidth: 0 }}
            >
              {loc.lang === 'bn' ? 'রেস্তোরাঁ দেখুন' : 'Browse Restaurants'}
            </Button>

            <Tooltip title={isDark ? 'Switch to light' : 'Switch to dark'}>
              <IconButton
                size="small" onClick={toggleMode} sx={{ color: 'text.secondary' }}
                aria-label={isDark ? 'Switch to light theme' : 'Switch to dark theme'}
              >
                {isDark ? <LightModeRoundedIcon fontSize="small" /> : <DarkModeRoundedIcon fontSize="small" />}
              </IconButton>
            </Tooltip>

            {loc.setLang && (
              <Button
                size="small" onClick={() => loc.setLang(loc.lang === 'en' ? 'bn' : 'en')}
                sx={{ color: 'text.secondary', minWidth: 0, fontWeight: 700 }}
              >
                {loc.lang === 'en' ? 'বাংলা' : 'EN'}
              </Button>
            )}
            <Button
              size="small" color="inherit" startIcon={<StorefrontOutlinedIcon />}
              component={Link} to="/"
              sx={{ display: { xs: 'none', sm: 'inline-flex' }, color: 'text.secondary' }}
            >
              Store
            </Button>
            <NotificationsBell />
            {/* The bag lives in the tab bar on phones. */}
            <IconButton onClick={() => navigate('/food/cart')}
              sx={{ display: { xs: 'none', md: 'inline-flex' }, color: 'text.primary' }}>
              <Badge badgeContent={count} color="primary"><ShoppingBagOutlinedIcon /></Badge>
            </IconButton>
          </Toolbar>
        </Container>
        {/* Inside the AppBar so it sticks with the header rather than scrolling
            away — these notices apply to every page of the food module. */}
        <NoticeMarquee />
      </AppBar>

      <Container maxWidth="lg" sx={{ py: { xs: 2.5, md: 3.5 }, position: 'relative', zIndex: 1 }}>
        <Outlet />
      </Container>

      {/* Partner recruitment. A footer strip rather than a header button: it is
          for shop owners, who are a rounding error next to the customers the
          header serves — but it has to be findable without being told.
          Not on the cart/checkout pages: those end in a fixed "Place order" bar
          that this strip scrolls under, and a shop-owner CTA has no business
          competing with the customer's primary action anyway. */}
      {!pathname.startsWith('/food/partner') && !onCartPages && (
        <Container maxWidth="lg" sx={{ position: 'relative', zIndex: 1, pb: 3 }}>
          <Box sx={{ p: 2.5, borderRadius: 4, border: 1, borderColor: 'divider',
                     bgcolor: 'background.paper', display: 'flex', gap: 2,
                     flexDirection: { xs: 'column', sm: 'row' },
                     alignItems: { xs: 'stretch', sm: 'center' }, justifyContent: 'space-between' }}>
            <Box>
              <Typography sx={{ fontWeight: 800 }}>
                {loc.lang === 'bn' ? 'রেস্তোরাঁর মালিক?' : 'Own a restaurant?'}
              </Typography>
              <Typography variant="body2" color="text.secondary">
                {loc.lang === 'bn'
                  ? 'ফেব্রিথিং ফুডে যুক্ত হয়ে আপনার এলাকা থেকে অর্ডার নিন।'
                  : 'Partner with Fabrything Food and take orders from your area.'}
              </Typography>
            </Box>
            <Button component={Link} to="/food/partner" variant="outlined"
              sx={{ borderRadius: 999, fontWeight: 800, flexShrink: 0 }}>
              {loc.lang === 'bn' ? 'পার্টনার হোন' : 'Become a Partner'}
            </Button>
          </Box>
        </Container>
      )}

      <LocationPicker />
      <FoodBottomNav />


      {/* Sticky cart bar — the food-app hallmark */}
      <AnimatePresence>
        {count > 0 && !onCartPages && (
          <Box
            component={motion.div}
            initial={{ y: 90 }} animate={{ y: 0 }} exit={{ y: 90 }}
            transition={{ type: 'spring', stiffness: 320, damping: 30 }}
            // Rides above the tab bar on phones, flush to the bottom on desktop
            // where there is no tab bar to clear.
            sx={{ position: 'fixed', left: 0, right: 0, bottom: 0, zIndex: 1200, px: 2,
                  pb: { xs: 'calc(env(safe-area-inset-bottom) + 72px)',
                        md: 'calc(env(safe-area-inset-bottom) + 12px)' } }}
          >
            <Container maxWidth="sm" disableGutters>
              <Button
                fullWidth variant="contained" onClick={() => navigate('/food/cart')}
                sx={{ py: 1.5, borderRadius: 999, boxShadow: '0 12px 30px rgba(232,69,43,0.35)' }}
              >
                <Stack direction="row" alignItems="center" justifyContent="space-between" sx={{ width: '100%' }}>
                  <span>{count} item{count > 1 ? 's' : ''} in bag</span>
                  <span>View bag · ৳{subtotal}</span>
                </Stack>
              </Button>
            </Container>
          </Box>
        )}
      </AnimatePresence>
    </Box>
  );
}
