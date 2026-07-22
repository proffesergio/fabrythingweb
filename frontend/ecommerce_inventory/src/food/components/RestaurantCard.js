import { Card, Box, Typography, Chip, Stack } from '@mui/material';
import AccessTimeRoundedIcon from '@mui/icons-material/AccessTimeRounded';
import TwoWheelerRoundedIcon from '@mui/icons-material/TwoWheelerRounded';
import PlaceRoundedIcon from '@mui/icons-material/PlaceRounded';
import { Link } from 'react-router-dom';
import { motion } from 'framer-motion';
import { FOOD } from '../theme';

const EMOJI = {
  bengali: '🍛', biryani: '🍚', biriyani: '🍚', 'fast food': '🍔', chinese: '🥡',
  pizza: '🍕', dessert: '🧁', cafe: '☕', kebab: '🍢', default: '🍽️',
};
const emojiFor = (cuisine = '') => {
  const k = cuisine.toLowerCase();
  return Object.keys(EMOJI).find((key) => k.includes(key)) ? EMOJI[Object.keys(EMOJI).find((key) => k.includes(key))] : EMOJI.default;
};

export default function RestaurantCard({ restaurant: r, lang }) {
  // is_open_now, not is_open: the latter is only the owner's master switch and
  // ignores the opening hours, so cards read "Open now" around the clock while
  // checkout rejected the order as closed. Fall back to is_open for a cached
  // response written before the field existed.
  const closed = !(r.is_open_now ?? r.is_open);
  // Only present when the caller asked for distance (the "Nearest" row and the
  // Browse page); null for a restaurant with no pickup pin.
  const distance = r.distance_km;
  // Explicitly false only on the Browse page, which lists restaurants outside
  // your union too. Undefined elsewhere, so nothing is marked by accident.
  const undeliverable = r.delivers_to_zone === false;
  return (
    <Card
      component={motion.a}
      whileHover={{ y: -4 }}
      transition={{ type: 'spring', stiffness: 300, damping: 22 }}
      href={undefined}
      sx={{ textDecoration: 'none', display: 'block', overflow: 'hidden', height: '100%',
            filter: closed || undeliverable ? 'grayscale(0.5)' : 'none',
            opacity: closed || undeliverable ? 0.85 : 1 }}
    >
      <Link to={`/food/restaurant/${r.slug}`} style={{ textDecoration: 'none', color: 'inherit' }}>
        {/* Cover: real photo if present, else a warm gradient + cuisine emoji */}
        <Box sx={{ position: 'relative', height: 158, overflow: 'hidden' }}>
          {r.cover_image ? (
            <Box component="img" src={r.cover_image} alt={r.display_name} loading="lazy"
              sx={{ width: '100%', height: '100%', objectFit: 'cover',
                    transition: 'transform .5s ease', '.MuiCard-root:hover &': { transform: 'scale(1.06)' } }} />
          ) : (
            <Box sx={{ width: '100%', height: '100%', display: 'grid', placeItems: 'center',
                       background: `radial-gradient(120% 120% at 20% 0%, #FFE7C2 0%, #FFD0A6 45%, #F7B27A 100%)` }}>
              <Box component="span" sx={{ fontSize: 54, filter: 'drop-shadow(0 6px 10px rgba(120,60,20,.25))' }}>
                {emojiFor(r.cuisine_type)}
              </Box>
            </Box>
          )}
          {/* Floating ETA pill (turmeric) — the signature detail */}
          <Chip
            size="small" icon={<AccessTimeRoundedIcon sx={{ fontSize: 15 }} />}
            label={`${r.avg_prep_minutes}+ min`}
            sx={{ position: 'absolute', bottom: 10, left: 10, bgcolor: FOOD.turmeric, color: '#3A2A05',
                  fontWeight: 800, '& .MuiChip-icon': { color: '#3A2A05' } }}
          />
          {distance != null && (
            <Chip
              size="small" icon={<PlaceRoundedIcon sx={{ fontSize: 15 }} />}
              label={`${distance < 1 ? `${Math.round(distance * 1000)} m` : `${distance.toFixed(1)} km`}`}
              sx={{ position: 'absolute', bottom: 10, right: 10, bgcolor: 'rgba(36,24,18,0.78)',
                    color: '#fff', fontWeight: 800, '& .MuiChip-icon': { color: '#fff' } }}
            />
          )}
          <Chip
            size="small" label={closed ? 'Closed' : 'Open now'}
            color={closed ? 'default' : 'success'}
            sx={{ position: 'absolute', top: 10, right: 10, fontWeight: 800,
                  bgcolor: closed ? 'rgba(36,24,18,0.72)' : undefined, color: closed ? '#fff' : undefined }}
          />
        </Box>

        <Box sx={{ p: 2 }}>
          <Typography variant="h6" noWrap sx={{ color: 'text.primary', lineHeight: 1.2 }}>{r.display_name}</Typography>
          <Typography variant="body2" color="text.secondary" noWrap sx={{ mb: 1.2 }}>
            {r.cuisine_type || 'Restaurant'}
          </Typography>
          {undeliverable && (
            <Typography variant="caption" sx={{ display: 'block', mb: 1, color: 'warning.main', fontWeight: 700 }}>
              {lang === 'bn' ? 'আপনার এলাকায় ডেলিভারি করে না' : "Doesn't deliver to your area"}
            </Typography>
          )}
          <Stack direction="row" spacing={2} alignItems="center">
            <Stack direction="row" spacing={0.5} alignItems="center">
              <TwoWheelerRoundedIcon sx={{ fontSize: 18, color: 'text.secondary' }} />
              <Typography variant="body2" fontWeight={700}>৳{r.base_delivery_fee}</Typography>
            </Stack>
            {Number(r.min_order_amount) > 0 && (
              <Typography variant="caption" color="text.secondary">Min ৳{r.min_order_amount}</Typography>
            )}
          </Stack>
        </Box>
      </Link>
    </Card>
  );
}
