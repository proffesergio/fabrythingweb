import { useEffect, useState, useMemo } from 'react';
import { Grid, Box, Typography, TextField, Stack, Button, CircularProgress, InputAdornment } from '@mui/material';
import { Link } from 'react-router-dom';
import SearchRoundedIcon from '@mui/icons-material/SearchRounded';
import VoiceSearchButton from '../components/VoiceSearchButton';
import PlaceRoundedIcon from '@mui/icons-material/PlaceRounded';
import { motion, AnimatePresence } from 'framer-motion';
import useCachedApi from '../../hooks/useCachedApi';
import { useFoodLocation } from '../context/FoodLocationContext';
import RestaurantCard from '../components/RestaurantCard';

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

// How many cards the "Nearest" row shows before the "Also available" row starts.
const NEAR_LIMIT = 6;
// One page big enough to hold every restaurant in Bancharampur, so the homepage
// is a single request that we split into rows client-side. Capped at the API's
// max_page_size (CustomPageNumberPagination).
const PAGE_SIZE = 100;

function PlateTile({ item, active, onClick }) {
  return (
    <Stack alignItems="center" spacing={0.75} onClick={onClick} sx={{ cursor: 'pointer', minWidth: 68 }}>
      <Box
        component={motion.div} whileTap={{ scale: 0.9 }} whileHover={{ y: -3 }}
        sx={{
          width: 62, height: 62, borderRadius: '50%', display: 'grid', placeItems: 'center', fontSize: 28,
          background: (t) => active
            ? 'linear-gradient(180deg,#FFF0DC,#FFDCA8)'
            : t.palette.background.paper,
          border: (t) => `2px solid ${active ? t.palette.secondary.main : t.palette.divider}`,
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

function RestaurantRow({ title, subtitle, restaurants, lang, sx }) {
  return (
    <Box sx={sx}>
      <Stack direction="row" alignItems="baseline" spacing={1.5} sx={{ mb: 2 }}>
        <Typography variant="h5">{title}</Typography>
        {subtitle && (
          <Typography variant="caption" color="text.secondary">{subtitle}</Typography>
        )}
      </Stack>
      <Grid container spacing={2.5}>
        {restaurants.map((r, i) => (
          <Grid item xs={12} sm={6} md={4} key={r.id}>
            <Box component={motion.div} initial={{ opacity: 0, y: 14 }} animate={{ opacity: 1, y: 0 }}
              transition={{ delay: Math.min(i * 0.05, 0.3) }} sx={{ height: '100%' }}>
              <RestaurantCard restaurant={r} lang={lang} />
            </Box>
          </Grid>
        ))}
      </Grid>
    </Box>
  );
}

export default function FoodHome() {
  const { zoneId, lang, currentZone, openPicker, coords } = useFoodLocation() || {};
  const [search, setSearch] = useState('');
  const [debouncedSearch, setDebouncedSearch] = useState('');
  const [cuisine, setCuisine] = useState('');
  const [hi, setHi] = useState(0);

  useEffect(() => {
    const t = setInterval(() => setHi((n) => (n + 1) % HEADLINES.length), 4200);
    return () => clearInterval(t);
  }, []);

  // Typing fired one request per keystroke and wrote a cache entry for every
  // prefix. Settle first, then ask.
  useEffect(() => {
    const t = setTimeout(() => setDebouncedSearch(search), 350);
    return () => clearTimeout(t);
  }, [search]);

  // ONE request for the whole page, split into rows below. Two requests used to
  // fetch overlapping sets and needed an `exclude` param to stop a restaurant
  // appearing twice; slicing a single ordered list makes that impossible and
  // halves the homepage's network cost.
  const params = useMemo(() => {
    const p = { lang, pageSize: PAGE_SIZE };
    // No zone selected is legitimate: the customer can browse everything and
    // choose their area at checkout. Omitting `zone` returns every restaurant.
    if (zoneId) p.zone = zoneId;
    if (debouncedSearch) p.search = debouncedSearch;
    if (cuisine) p.cuisine = cuisine;

    // Sorted by real distance from the customer's dropped pin. With no pin we
    // fall back to the selected zone's centre, so the row is still meaningfully
    // ordered rather than alphabetical.
    const origin = coords || (currentZone
      ? { lat: Number(currentZone.center_lat), lng: Number(currentZone.center_lng) }
      : null);
    if (origin) {
      p.lat = origin.lat;
      p.lng = origin.lng;
      p.sort = 'distance';
    }
    return p;
  }, [zoneId, lang, debouncedSearch, cuisine, coords, currentZone]);

  // Cached: a returning customer sees their restaurants immediately from
  // localStorage while the fresh list loads behind it.
  const { data, loading } = useCachedApi('food/restaurants/', { params });
  const restaurants = data?.data || [];

  const headline = HEADLINES[hi];
  const hasDistance = restaurants.some((r) => r.distance_km != null);
  // While searching or filtering by cuisine the split is noise — the customer
  // asked a question, so show the whole answer in one row.
  // debouncedSearch, not search: this must describe the data on screen, which
  // still reflects the previous query until the debounce fires.
  const filtering = Boolean(debouncedSearch || cuisine);
  const nearest = restaurants.slice(0, NEAR_LIMIT);
  const alsoAvailable = filtering ? [] : restaurants.slice(NEAR_LIMIT);

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

      {loading ? (
        <Box sx={{ textAlign: 'center', py: 8 }}><CircularProgress color="primary" /></Box>
      ) : restaurants.length === 0 ? (
        <Box sx={{ textAlign: 'center', py: 8 }}>
          <Box sx={{ fontSize: 56, mb: 1 }}>🧺</Box>
          <Typography color="text.secondary">
            {/* Don't blame the area when no area is set — that message sent
                customers to the picker to "fix" something that was fine. */}
            {filtering
              ? (lang === 'bn' ? 'কোনো রেস্তোরাঁ পাওয়া যায়নি।' : 'No restaurants match that.')
              : zoneId
                ? (lang === 'bn'
                    ? 'এই এলাকায় এখনো কোনো রেস্তোরাঁ ডেলিভারি করে না।'
                    : 'No restaurants deliver to this area yet.')
                : (lang === 'bn'
                    ? 'এখনো কোনো রেস্তোরাঁ নেই।'
                    : 'No restaurants available yet.')}
          </Typography>
          <Stack direction="row" spacing={1} justifyContent="center" sx={{ mt: 1.5 }}>
            {openPicker && (
              <Button onClick={openPicker}>{lang === 'bn' ? 'এলাকা বদলান' : 'Change area'}</Button>
            )}
            {/* Always give them somewhere to go: the Browse page lists every
                restaurant, including ones outside this union. */}
            <Button component={Link} to="/food/restaurants" variant="outlined">
              {lang === 'bn' ? 'সব রেস্তোরাঁ দেখুন' : 'Browse all restaurants'}
            </Button>
          </Stack>
        </Box>
      ) : (
        <>
          <RestaurantRow
            title={cuisine
              ? `${cuisine} places`
              : zoneId
                ? (lang === 'bn' ? 'আপনার এলাকার সবচেয়ে কাছে' : 'Nearest to your area')
                : (lang === 'bn' ? 'সব রেস্তোরাঁ' : 'All restaurants')}
            subtitle={!cuisine && hasDistance
              ? (lang === 'bn' ? 'দূরত্ব অনুসারে সাজানো' : 'Sorted by distance from you')
              : ''}
            restaurants={filtering ? restaurants : nearest}
            lang={lang}
          />

          {/* Everything else that delivers here — so no restaurant is stranded
              off the homepage just because it isn't in the nearest handful.
              Sliced from the same ordered list, so the rows can never repeat. */}
          {alsoAvailable.length > 0 && (
            <RestaurantRow
              title={lang === 'bn' ? 'আরও পাওয়া যাচ্ছে' : 'Also available'}
              subtitle={zoneId
                ? (lang === 'bn' ? 'আপনার এলাকায় ডেলিভারি করে' : 'Also delivering to your area')
                : ''}
              restaurants={alsoAvailable}
              lang={lang}
              sx={{ mt: 5 }}
            />
          )}
        </>
      )}
    </Box>
  );
}
