import { useEffect, useState, useCallback } from 'react';
import { Grid, Box, Typography, TextField, Stack, Button, CircularProgress, InputAdornment } from '@mui/material';
import SearchRoundedIcon from '@mui/icons-material/SearchRounded';
import VoiceSearchButton from '../components/VoiceSearchButton';
import PlaceRoundedIcon from '@mui/icons-material/PlaceRounded';
import { motion, AnimatePresence } from 'framer-motion';
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

// Rotating, appetite-driven hero copy (curated set, bilingual) + a rotating food motif.
const HEADLINES = [
  { en: 'Good food, right to your door.', bn: 'ভালো খাবার, আপনার দরজায়।', emoji: '🍛' },
  { en: 'Craving something? We deliver.', bn: 'ক্ষুধা লেগেছে? আমরা পৌঁছে দিই।', emoji: '🍔' },
  { en: 'Hot meals, fast — near you.', bn: 'গরম খাবার, দ্রুত — আপনার কাছেই।', emoji: '🍚' },
  { en: 'Neighbourhood kitchens, one tap away.', bn: 'এলাকার রান্নাঘর, এক ট্যাপ দূরে।', emoji: '🍜' },
];
const FLOAT = ['🍛', '🍔', '🍕', '🍗', '🥘', '🧁', '🍜', '🍚'];

function PlateTile({ item, active, onClick }) {
  return (
    <Stack alignItems="center" spacing={0.75} onClick={onClick} sx={{ cursor: 'pointer', minWidth: 68 }}>
      <Box
        component={motion.div} whileTap={{ scale: 0.9 }} whileHover={{ y: -3 }}
        sx={{
          width: 62, height: 62, borderRadius: '50%', display: 'grid', placeItems: 'center', fontSize: 28,
          background: active ? 'linear-gradient(180deg,#FFF0DC,#FFDCA8)' : '#FFFFFF',
          border: `2px solid ${active ? FOOD.turmeric : FOOD.line}`,
          boxShadow: active ? '0 8px 18px rgba(244,166,42,0.28)' : '0 4px 12px rgba(120,60,20,0.05)',
          transition: 'background .2s, border-color .2s',
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
  const { zoneId, lang, currentZone, openPicker } = useFoodLocation() || {};
  const { callApi, loading } = useApi();
  const [restaurants, setRestaurants] = useState([]);
  const [search, setSearch] = useState('');
  const [cuisine, setCuisine] = useState('');
  const [hi, setHi] = useState(0);

  useEffect(() => {
    const t = setInterval(() => setHi((n) => (n + 1) % HEADLINES.length), 4200);
    return () => clearInterval(t);
  }, []);

  const fetchRestaurants = useCallback(async () => {
    const params = { lang };
    if (zoneId) params.zone = zoneId;
    if (search) params.search = search;
    if (cuisine) params.cuisine = cuisine;
    const res = await callApi({ url: 'food/restaurants/', method: 'GET', params });
    setRestaurants(res?.data?.data?.data || []);
  }, [zoneId, lang, search, cuisine]); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => { fetchRestaurants(); }, [fetchRestaurants]);

  const headline = HEADLINES[hi];

  return (
    <Box>
      {/* Animated hero */}
      <Box sx={{ position: 'relative', overflow: 'hidden', borderRadius: 5, p: { xs: 3, md: 5 }, mb: 3, color: '#fff',
        background: 'linear-gradient(135deg,#E8452B 0%,#C4361F 60%,#9E2A16 100%)' }}>
        {/* drifting food motifs (animated background) */}
        {FLOAT.map((e, i) => (
          <Box key={i} component={motion.span} aria-hidden
            initial={{ y: 0 }} animate={{ y: [0, -14, 0], rotate: [0, 8, 0] }}
            transition={{ duration: 5 + i, repeat: Infinity, ease: 'easeInOut', delay: i * 0.4 }}
            sx={{ position: 'absolute', fontSize: 30 + (i % 3) * 10, opacity: 0.12,
              top: `${(i * 26) % 80}%`, left: `${(i * 37) % 92}%`, pointerEvents: 'none' }}>
            {e}
          </Box>
        ))}

        {openPicker && (
          <Button onClick={openPicker} startIcon={<PlaceRoundedIcon />}
            sx={{ mb: 1.5, color: '#fff', bgcolor: 'rgba(255,255,255,0.16)', borderRadius: 999, textTransform: 'none',
                  '&:hover': { bgcolor: 'rgba(255,255,255,0.26)' } }}>
            {currentZone ? (lang === 'bn' && currentZone.name_bn ? currentZone.name_bn : currentZone.name) : (lang === 'bn' ? 'এলাকা নির্বাচন করুন' : 'Choose your area')}
          </Button>
        )}

        <Box sx={{ position: 'relative', minHeight: { xs: 96, md: 76 } }}>
          <AnimatePresence mode="wait">
            <Typography key={hi} component={motion.div} variant="h3"
              initial={{ opacity: 0, y: 18 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -18 }}
              transition={{ duration: 0.45 }} sx={{ maxWidth: 620, lineHeight: 1.05 }}>
              <Box component="span" sx={{ mr: 1 }}>{headline.emoji}</Box>
              {lang === 'bn' ? headline.bn : headline.en}
            </Typography>
          </AnimatePresence>
        </Box>

        <Box sx={{ position: 'relative', maxWidth: 560, mt: 2 }}>
          <TextField
            fullWidth size="small" placeholder={lang === 'bn' ? 'রেস্তোরাঁ বা খাবার খুঁজুন' : 'Search restaurants or dishes'}
            value={search} onChange={(e) => setSearch(e.target.value)}
            sx={{ bgcolor: '#fff', borderRadius: 3, '& fieldset': { border: 'none' } }}
            InputProps={{
              startAdornment: <InputAdornment position="start"><SearchRoundedIcon color="action" /></InputAdornment>,
              endAdornment: <InputAdornment position="end"><VoiceSearchButton lang={lang} onResult={setSearch} /></InputAdornment>,
            }}
          />
        </Box>
      </Box>

      {/* Plate category tiles */}
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
          {openPicker && <Button sx={{ mt: 1 }} onClick={openPicker}>Change area</Button>}
        </Box>
      ) : (
        <Grid container spacing={2.5}>
          {restaurants.map((r, i) => (
            <Grid item xs={12} sm={6} md={4} key={r.id}>
              <Box component={motion.div} initial={{ opacity: 0, y: 14 }} animate={{ opacity: 1, y: 0 }}
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
