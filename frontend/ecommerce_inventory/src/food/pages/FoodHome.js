import { useEffect, useState, useCallback } from 'react';
import { Grid, Box, Typography, TextField, Chip, Stack, Button, CircularProgress } from '@mui/material';
import MyLocationIcon from '@mui/icons-material/MyLocation';
import useApi from '../../hooks/APIHandler';
import { useFoodLocation } from '../context/FoodLocationContext';
import RestaurantCard from '../components/RestaurantCard';

const CUISINES = ['Bengali', 'Fast Food', 'Biryani', 'Chinese', 'Pizza', 'Dessert'];

export default function FoodHome() {
  const { zoneId, lang, detectLocation } = useFoodLocation() || {};
  const { callApi, loading } = useApi();
  const [restaurants, setRestaurants] = useState([]);
  const [search, setSearch] = useState('');
  const [cuisine, setCuisine] = useState('');

  const fetchRestaurants = useCallback(async () => {
    const params = { lang };
    if (zoneId) params.zone = zoneId;
    if (search) params.search = search;
    if (cuisine) params.cuisine = cuisine;
    const res = await callApi({ url: 'food/restaurants/', method: 'GET', params });
    setRestaurants(res?.data?.data?.data || []);
  }, [zoneId, lang, search, cuisine]); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => { fetchRestaurants(); }, [fetchRestaurants]);

  return (
    <Box>
      <Box
        sx={{
          p: { xs: 3, md: 5 }, mb: 3, borderRadius: 4,
          background: 'linear-gradient(135deg,#1B1D24,#0E0F12)', border: '1px solid #262A32',
        }}
      >
        <Typography variant="h4" sx={{ color: 'text.primary', mb: 1 }}>Hungry? Order in.</Typography>
        <Typography color="text.secondary" sx={{ mb: 2 }}>Fresh food from restaurants near you.</Typography>
        <Stack direction={{ xs: 'column', sm: 'row' }} spacing={1}>
          <TextField
            fullWidth size="small" placeholder="Search restaurants"
            value={search} onChange={(e) => setSearch(e.target.value)}
          />
          <Button
            variant="outlined" color="inherit" startIcon={<MyLocationIcon />}
            onClick={() => detectLocation && detectLocation()}
          >
            Use my location
          </Button>
        </Stack>
      </Box>

      <Stack direction="row" spacing={1} sx={{ mb: 3, overflowX: 'auto', pb: 1 }}>
        <Chip label="All" color={cuisine === '' ? 'primary' : 'default'} onClick={() => setCuisine('')} />
        {CUISINES.map((c) => (
          <Chip key={c} label={c} color={cuisine === c ? 'primary' : 'default'} onClick={() => setCuisine(c)} />
        ))}
      </Stack>

      {loading ? (
        <Box sx={{ textAlign: 'center', py: 6 }}><CircularProgress /></Box>
      ) : restaurants.length === 0 ? (
        <Typography color="text.secondary" sx={{ py: 6, textAlign: 'center' }}>
          No restaurants deliver to this area yet.
        </Typography>
      ) : (
        <Grid container spacing={2}>
          {restaurants.map((r) => (
            <Grid item xs={12} sm={6} md={4} key={r.id}>
              <RestaurantCard restaurant={r} />
            </Grid>
          ))}
        </Grid>
      )}
    </Box>
  );
}
