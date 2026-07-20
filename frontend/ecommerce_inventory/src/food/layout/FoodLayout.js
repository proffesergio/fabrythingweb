import { Outlet, Link, useNavigate, useLocation } from 'react-router-dom';
import { AppBar, Toolbar, Box, Typography, IconButton, Badge, Button, Container, MenuItem, Select, Stack } from '@mui/material';
import ShoppingBagOutlinedIcon from '@mui/icons-material/ShoppingBagOutlined';
import StorefrontOutlinedIcon from '@mui/icons-material/StorefrontOutlined';
import PlaceOutlinedIcon from '@mui/icons-material/PlaceOutlined';
import { useSelector } from 'react-redux';
import { motion, AnimatePresence } from 'framer-motion';
import { selectFoodCount, selectFoodSubtotal } from '../redux/foodCartSlice';
import { useFoodLocation } from '../context/FoodLocationContext';
import { FOOD } from '../theme';

export default function FoodLayout() {
  const count = useSelector(selectFoodCount);
  const subtotal = useSelector(selectFoodSubtotal);
  const navigate = useNavigate();
  const { pathname } = useLocation();
  const loc = useFoodLocation() || {};
  const onCartPages = pathname.includes('/food/cart') || pathname.includes('/food/checkout');

  return (
    <Box sx={{ minHeight: '100vh', bgcolor: 'background.default', pb: { xs: count && !onCartPages ? 10 : 0, sm: 0 } }}>
      <AppBar position="sticky" elevation={0}>
        <Container maxWidth="lg">
          <Toolbar disableGutters sx={{ gap: { xs: 1, sm: 2 }, minHeight: 68 }}>
            <Typography
              variant="h5" component={Link} to="/food"
              sx={{ textDecoration: 'none', whiteSpace: 'nowrap', color: 'text.primary', fontWeight: 800 }}
            >
              Fabrything<Box component="span" sx={{ color: 'primary.main' }}>·Food</Box>
            </Typography>

            {loc.zones && (
              <Select
                size="small" value={loc.zoneId || ''} displayEmpty
                onChange={(e) => loc.setZoneId(e.target.value)}
                startAdornment={<PlaceOutlinedIcon sx={{ fontSize: 18, color: 'primary.main', mr: 0.5 }} />}
                sx={{
                  minWidth: { xs: 120, sm: 168 }, bgcolor: '#fff', borderRadius: 999,
                  '& .MuiOutlinedInput-notchedOutline': { borderColor: FOOD.line },
                  '& .MuiSelect-select': { py: 0.9, fontWeight: 600, fontSize: 14 },
                }}
              >
                <MenuItem value=""><em>Choose your area</em></MenuItem>
                {loc.zones.map((z) => <MenuItem key={z.id} value={String(z.id)}>{z.name}</MenuItem>)}
              </Select>
            )}

            <Box sx={{ flexGrow: 1 }} />

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
            <IconButton onClick={() => navigate('/food/cart')} sx={{ color: 'text.primary' }}>
              <Badge badgeContent={count} color="primary"><ShoppingBagOutlinedIcon /></Badge>
            </IconButton>
          </Toolbar>
        </Container>
      </AppBar>

      <Container maxWidth="lg" sx={{ py: { xs: 2.5, md: 3.5 } }}>
        <Outlet />
      </Container>

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
