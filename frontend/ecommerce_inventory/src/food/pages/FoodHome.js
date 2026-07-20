import { useEffect, useState, useCallback } from 'react';
import { Grid, Box, Typography, TextField, Stack, Button, CircularProgress, InputAdornment } from '@mui/material';
import SearchRoundedIcon from '@mui/icons-material/SearchRounded';
import MyLocationRoundedIcon from '@mui/icons-material/MyLocationRounded';
import { motion } from 'framer-motion';
import useApi from '../../hooks/APIHandler';
import { useFoodLocation } from '../context/FoodLocationContext';
import RestaurantCard from '../components/RestaurantCard';
import { FOOD } from '../theme';

const CATEGORIES = [
  { label: 'All', value: '', emoji: '🍽️' },
  { label: 'Bengali', value: 'Bengali', emoji: '🍛' },
  { label: 'Fast Food', value: 'Fast Food', emoji: '🍔' },
  { label: 'Biryani', value: 'Biryani', emoji: '🍚' },
  { label: 'Chinese', value: 'Chinese', emoji: '🥡' },
  { label: 'Pizza', value: 'Pizza', emoji: '🍕' },
  { label: 'Dessert', value: 'Dessert', emoji: '🧁' },
];

function PlateTile({ item, active, onClick }) {
  return (
    <Stack alignItems="center" spacing={0.75} onClick={onClick} sx={{ cursor: 'pointer', minWidth: 68 }}>
      <Box
        component={motion.div} whileTap={{ scale: 0.92 }}
        sx={{
          width: 62, height: 62, borderRadius: '50%', display: 'grid', placeItems: 'center', fontSize: 28,
          background: active ? `linear-gradient(180deg,#FFF0DC,#FFDCA8)` : '#FFFFFF',
          border: `2px solid ${active ? FOOD.turmeric : FOOD.line}`,
          boxShadow: active ? '0 8px 18px rgba(244,166,42,0.28)' : '0 4px 12px rgba(120,60,20,0.05)',
          transition: 'all .2s ease',
        }}
      >
        {item.emoji}
      </Box>
      <Typography variant="caption" sx={{ fontWeight: active ? 800 : 600, color: active ? 'text.primary' : 'text.secondary' }}>
        {item.label}
      </Typography>
    </Stack>
  );
}

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
      {/* Hero — appetite-first, bilingual for the local audience */}
      <Box
        sx={{
          position: 'relative', overflow: 'hidden', borderRadius: 4, p: { xs: 3, md: 5 }, mb: 3,
          background: `linear-gradient(135deg, #E8452B 0%, #C4361F 100%)`, color: '#fff',
        }}
      >
        <Box aria-hidden sx={{ position: 'absolute', right: -10, top: -20, fontSize: 150, opacity: 0.16, transform: 'rotate(-12deg)' }}>🍛</Box>
        <Typography sx={{ opacity: 0.85, fontWeight: 700, letterSpacing: '0.12em', mb: 0.5 }} variant="overline">
          {lang === 'bn' ? 'আপনার এলাকায় ডেলিভারি' : 'DELIVERING IN YOUR AREA'}
        </Typography>
        <Typography variant="h3" sx={{ maxWidth: 560, lineHeight: 1.05, mb: 2 }}>
          {lang === 'bn' ? 'ভালো খাবার, আপনার দরজায়।' : 'Good food, right to your door.'}
        </Typography>
        <Box sx={{ maxWidth: 560, display: 'flex', gap: 1, flexDirection: { xs: 'column', sm: 'row' } }}>
          <TextField
            fullWidth size="small" placeholder={lang === 'bn' ? 'রেস্তোরাঁ খুঁজুন' : 'Search restaurants'}
            value={search} onChange={(e) => setSearch(e.target.value)}
            sx={{ bgcolor: '#fff', borderRadius: 3 }}
            InputProps={{ startAdornment: <InputAdornment position="start"><SearchRoundedIcon color="action" /></InputAdornment> }}
          />
          <Button
            variant="contained" color="secondary" startIcon={<MyLocationRoundedIcon />}
            onClick={() => detectLocation && detectLocation()}
            sx={{ whiteSpace: 'nowrap', color: '#3A2A05' }}
          >
            {lang === 'bn' ? 'আমার অবস্থান' : 'Near me'}
          </Button>
        </Box>
      </Box>

      {/* Plate category tiles — the signature */}
      <Stack direction="row" spacing={1.5} sx={{ mb: 3.5, overflowX: 'auto', pb: 1, '::-webkit-scrollbar': { display: 'none' } }}>
        {CATEGORIES.map((c) => (
          <PlateTile key={c.label} item={c} active={cuisine === c.value} onClick={() => setCuisine(c.value)} />
        ))}
      </Stack>

      <Typography variant="h5" sx={{ mb: 2 }}>
        {cuisine ? `${cuisine} places` : (lang === 'bn' ? 'আপনার কাছের রেস্তোরাঁ' : 'Restaurants near you')}
      </Typography>

      {loading ? (
        <Box sx={{ textAlign: 'center', py: 8 }}><CircularProgress color="primary" /></Box>
      ) : restaurants.length === 0 ? (
        <Box sx={{ textAlign: 'center', py: 8 }}>
          <Box sx={{ fontSize: 56, mb: 1 }}>🧺</Box>
          <Typography color="text.secondary">No restaurants deliver to this area yet.</Typography>
          <Typography variant="body2" color="text.secondary">Try choosing a different area above.</Typography>
        </Box>
      ) : (
        <Grid container spacing={2.5}>
          {restaurants.map((r, i) => (
            <Grid item xs={12} sm={6} md={4} key={r.id}>
              <Box component={motion.div} initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }}
                transition={{ delay: Math.min(i * 0.05, 0.3) }} sx={{ height: '100%' }}>
                <RestaurantCard restaurant={r} />
              </Box>
            </Grid>
          ))}
        </Grid>
      )}
    </Box>
  );
}
