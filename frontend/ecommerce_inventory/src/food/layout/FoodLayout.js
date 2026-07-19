import { Outlet, Link, useNavigate } from 'react-router-dom';
import { AppBar, Toolbar, Box, Typography, IconButton, Badge, Button, Container, MenuItem, Select } from '@mui/material';
import ShoppingBagOutlinedIcon from '@mui/icons-material/ShoppingBagOutlined';
import StorefrontOutlinedIcon from '@mui/icons-material/StorefrontOutlined';
import { useSelector } from 'react-redux';
import { selectFoodCount } from '../redux/foodCartSlice';
import { useFoodLocation } from '../context/FoodLocationContext';

export default function FoodLayout() {
  const count = useSelector(selectFoodCount);
  const navigate = useNavigate();
  const loc = useFoodLocation() || {};
  return (
    <Box sx={{ minHeight: '100vh', bgcolor: 'background.default' }}>
      <AppBar position="sticky" elevation={0}>
        <Container maxWidth="lg">
          <Toolbar disableGutters sx={{ gap: { xs: 1, sm: 2 } }}>
            <Typography
              variant="h5"
              component={Link}
              to="/food"
              sx={{ color: 'primary.main', textDecoration: 'none', fontWeight: 900, whiteSpace: 'nowrap' }}
            >
              Fabrything<Box component="span" sx={{ color: 'text.primary' }}>Food</Box>
            </Typography>
            {loc.zones && (
              <Select
                size="small"
                value={loc.zoneId || ''}
                displayEmpty
                onChange={(e) => loc.setZoneId(e.target.value)}
                sx={{ minWidth: { xs: 110, sm: 150 } }}
              >
                <MenuItem value=""><em>Choose area</em></MenuItem>
                {loc.zones.map((z) => (
                  <MenuItem key={z.id} value={String(z.id)}>{z.name}</MenuItem>
                ))}
              </Select>
            )}
            <Box sx={{ flexGrow: 1 }} />
            {loc.setLang && (
              <Button size="small" color="inherit" onClick={() => loc.setLang(loc.lang === 'en' ? 'bn' : 'en')}>
                {loc.lang === 'en' ? 'বাংলা' : 'EN'}
              </Button>
            )}
            <Button
              size="small"
              color="inherit"
              startIcon={<StorefrontOutlinedIcon />}
              component={Link}
              to="/"
              sx={{ display: { xs: 'none', sm: 'inline-flex' } }}
            >
              Store
            </Button>
            <IconButton color="inherit" onClick={() => navigate('/food/cart')}>
              <Badge badgeContent={count} color="primary"><ShoppingBagOutlinedIcon /></Badge>
            </IconButton>
          </Toolbar>
        </Container>
      </AppBar>
      <Container maxWidth="lg" sx={{ py: 3 }}><Outlet /></Container>
    </Box>
  );
}
