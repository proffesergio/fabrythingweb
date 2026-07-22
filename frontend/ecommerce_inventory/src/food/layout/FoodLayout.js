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
    <Box sx={{ minHeight: '100vh', bgcolor: 'transparent', position: 'relative', pb: { xs: count && !onCartPages ? 10 : 0, sm: 0 } }}>
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
                sx={{ px: 1.25, py: 0.6, borderRadius: 999, bgcolor: 'background.paper',
                      border: 1, borderColor: 'divider',
                      color: 'text.primary', textTransform: 'none', maxWidth: { xs: 150, sm: 220 } }}
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
              sx={{ color: pathname === '/food/restaurants' ? 'primary.main' : 'text.secondary',
                    fontWeight: 700 }}
            >
              <Box component="span" sx={{ display: { xs: 'none', sm: 'inline' } }}>
                {loc.lang === 'bn' ? 'রেস্তোরাঁ দেখুন' : 'Browse Restaurants'}
              </Box>
              <Box component="span" sx={{ display: { xs: 'inline', sm: 'none' } }}>
                {loc.lang === 'bn' ? 'রেস্তোরাঁ' : 'Browse'}
              </Box>
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
            <IconButton onClick={() => navigate('/food/cart')} sx={{ color: 'text.primary' }}>
              <Badge badgeContent={count} color="primary"><ShoppingBagOutlinedIcon /></Badge>
            </IconButton>
          </Toolbar>
        </Container>
      </AppBar>

      <Container maxWidth="lg" sx={{ py: { xs: 2.5, md: 3.5 }, position: 'relative', zIndex: 1 }}>
        <Outlet />
      </Container>

      <LocationPicker />


      {/* Sticky cart bar — the food-app hallmark */}
      <AnimatePresence>
        {count > 0 && !onCartPages && (
          <Box
            component={motion.div}
            initial={{ y: 90 }} animate={{ y: 0 }} exit={{ y: 90 }}
            transition={{ type: 'spring', stiffness: 320, damping: 30 }}
            sx={{ position: 'fixed', left: 0, right: 0, bottom: 0, zIndex: 1200, px: 2, pb: 'calc(env(safe-area-inset-bottom) + 12px)' }}
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
