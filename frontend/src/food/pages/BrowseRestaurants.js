import { useCallback, useEffect, useState } from 'react';
import {
  Box, Grid, Typography, TextField, Stack, Button, CircularProgress, InputAdornment,
  FormControlLabel, Switch, Chip, Pagination,
} from '@mui/material';
import SearchRoundedIcon from '@mui/icons-material/SearchRounded';
import PlaceRoundedIcon from '@mui/icons-material/PlaceRounded';
import { motion } from 'framer-motion';
import useApi from '../../hooks/APIHandler';
import { useFoodLocation } from '../context/FoodLocationContext';
import RestaurantCard from '../components/RestaurantCard';
import VoiceSearchButton from '../components/VoiceSearchButton';

const CUISINES = ['', 'Bengali', 'Fast Food', 'Biryani', 'Chinese', 'Pizza', 'Dessert'];

/**
 * Every active restaurant on the platform.
 *
 * The "only ones that deliver to me" switch defaults ON, so the page opens
 * showing what the customer can actually order. Turning it off keeps the same
 * list but stops filtering — cards outside their union stay visible and are
 * marked undeliverable by RestaurantCard rather than silently vanishing.
 */
export default function BrowseRestaurants() {
  const { zoneId, lang, currentZone, coords, openPicker } = useFoodLocation() || {};
  const { callApi, loading } = useApi();
  const [restaurants, setRestaurants] = useState([]);
  const [search, setSearch] = useState('');
  const [cuisine, setCuisine] = useState('');
  const [deliverableOnly, setDeliverableOnly] = useState(true);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);

  const fetch = useCallback(async () => {
    const params = { lang, page };
    if (zoneId) params.zone = zoneId;
    // `all=true` stops the backend filtering by zone; it then only annotates
    // delivers_to_zone so the cards can say which ones reach you.
    if (!deliverableOnly) params.all = 'true';
    if (search) params.search = search;
    if (cuisine) params.cuisine = cuisine;

    const origin = coords || (currentZone
      ? { lat: Number(currentZone.center_lat), lng: Number(currentZone.center_lng) }
      : null);
    if (origin) { params.lat = origin.lat; params.lng = origin.lng; }

    const res = await callApi({ url: 'food/restaurants/', method: 'GET', params });
    setRestaurants(res?.data?.data?.data || []);
    setTotalPages(res?.data?.data?.totalPages || 1);
  }, [zoneId, lang, search, cuisine, deliverableOnly, page, coords, currentZone]); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => { fetch(); }, [fetch]);
  // Any filter change invalidates the current page number.
  useEffect(() => { setPage(1); }, [search, cuisine, deliverableOnly, zoneId]);

  const areaLabel = currentZone
    ? (lang === 'bn' && currentZone.name_bn ? currentZone.name_bn : currentZone.name)
    : (lang === 'bn' ? 'এলাকা নির্বাচন করুন' : 'Choose your area');

  return (
    <Box>
      <Typography variant="h4" sx={{ mb: 0.5 }}>
        {lang === 'bn' ? 'সব রেস্তোরাঁ' : 'Browse restaurants'}
      </Typography>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
        {lang === 'bn'
          ? 'ফ্যাব্রিথিং-এ থাকা সব রেস্তোরাঁ খুঁজে দেখুন।'
          : 'Every restaurant on Fabrything, searchable by name and cuisine.'}
      </Typography>

      <Stack spacing={2} sx={{ mb: 3 }}>
        <TextField
          fullWidth size="small"
          placeholder={lang === 'bn' ? 'রেস্তোরাঁ খুঁজুন' : 'Search restaurants'}
          value={search} onChange={(e) => setSearch(e.target.value)}
          InputProps={{
            startAdornment: <InputAdornment position="start"><SearchRoundedIcon color="action" /></InputAdornment>,
            endAdornment: <InputAdornment position="end"><VoiceSearchButton lang={lang} onResult={setSearch} /></InputAdornment>,
          }}
        />

        <Stack direction="row" spacing={1} sx={{ overflowX: 'auto', pb: 0.5, '::-webkit-scrollbar': { display: 'none' } }}>
          {CUISINES.map((c) => (
            <Chip
              key={c || 'all'}
              label={c || (lang === 'bn' ? 'সব' : 'All')}
              onClick={() => setCuisine(c)}
              color={cuisine === c ? 'primary' : 'default'}
              variant={cuisine === c ? 'filled' : 'outlined'}
            />
          ))}
        </Stack>

        <Stack direction="row" spacing={1} alignItems="center" flexWrap="wrap" useFlexGap>
          <Button size="small" startIcon={<PlaceRoundedIcon />} onClick={openPicker}
                  sx={{ color: 'text.secondary' }}>
            {areaLabel}
          </Button>
          <FormControlLabel
            control={<Switch size="small" checked={deliverableOnly}
                             onChange={(e) => setDeliverableOnly(e.target.checked)} />}
            label={
              <Typography variant="body2">
                {lang === 'bn' ? 'শুধু আমার এলাকায় ডেলিভারি করে' : 'Only ones that deliver to me'}
              </Typography>
            }
          />
        </Stack>
      </Stack>

      {loading ? (
        <Box sx={{ textAlign: 'center', py: 8 }}><CircularProgress color="primary" /></Box>
      ) : restaurants.length === 0 ? (
        <Box sx={{ textAlign: 'center', py: 8 }}>
          <Box sx={{ fontSize: 56, mb: 1 }}>🔍</Box>
          <Typography color="text.secondary">
            {lang === 'bn' ? 'কোনো রেস্তোরাঁ পাওয়া যায়নি।' : 'No restaurants match that.'}
          </Typography>
          {deliverableOnly && (
            <Button sx={{ mt: 1 }} onClick={() => setDeliverableOnly(false)}>
              {lang === 'bn' ? 'সব এলাকায় খুঁজুন' : 'Search every area'}
            </Button>
          )}
        </Box>
      ) : (
        <>
          <Grid container spacing={2.5}>
            {restaurants.map((r, i) => (
              <Grid item xs={12} sm={6} md={4} key={r.id}>
                <Box component={motion.div} initial={{ opacity: 0, y: 14 }} animate={{ opacity: 1, y: 0 }}
                     transition={{ delay: Math.min(i * 0.04, 0.3) }} sx={{ height: '100%' }}>
                  <RestaurantCard restaurant={r} lang={lang} />
                </Box>
              </Grid>
            ))}
          </Grid>
          {totalPages > 1 && (
            <Stack alignItems="center" sx={{ mt: 4 }}>
              <Pagination count={totalPages} page={page} onChange={(_, p) => setPage(p)} color="primary" />
            </Stack>
          )}
        </>
      )}
    </Box>
  );
}
