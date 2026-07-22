import { useState, useMemo } from 'react';
import { useParams } from 'react-router-dom';
import { useDispatch, useSelector } from 'react-redux';
import { Box, Typography, Grid, Chip, Stack, CircularProgress, Button, Card, Alert } from '@mui/material';
import AddRoundedIcon from '@mui/icons-material/AddRounded';
import AccessTimeRoundedIcon from '@mui/icons-material/AccessTimeRounded';
import TwoWheelerRoundedIcon from '@mui/icons-material/TwoWheelerRounded';
import StarRoundedIcon from '@mui/icons-material/StarRounded';
import { motion } from 'framer-motion';
import { toast } from 'react-toastify';
import useCachedApi from '../../hooks/useCachedApi';
import { useFoodLocation } from '../context/FoodLocationContext';
import { addFoodItem, selectFoodRestaurant } from '../redux/foodCartSlice';
import ItemOptionModal from '../components/ItemOptionModal';
import { nextOpenText, closedToastText, formatTime, dayName } from '../utils/hours';
import { FOOD } from '../theme';

function VegDot() {
  return (
    <Box aria-label="veg" sx={{ width: 15, height: 15, borderRadius: '3px', border: `2px solid ${FOOD.cardamom}`,
      display: 'grid', placeItems: 'center', flexShrink: 0 }}>
      <Box sx={{ width: 6, height: 6, borderRadius: '50%', bgcolor: FOOD.cardamom }} />
    </Box>
  );
}

const TAG_META = {
  spicy: { label: 'Spicy', emoji: '🌶️' }, new: { label: 'New', emoji: '✨' },
  popular: { label: 'Popular', emoji: '🔥' }, veg: { label: 'Veg', emoji: '🌱' },
  bestseller: { label: 'Bestseller', emoji: '⭐' },
};
const fmt = (t) => (t ? String(t).slice(0, 5) : '');

function DishCard({ item, onClick, restaurantClosed, lang }) {
  const hasOptions = item.option_groups && item.option_groups.length > 0;
  // Two independent reasons a dish can't be ordered: the item has its own
  // availability window (breakfast-only, say), or the whole restaurant is shut.
  // The restaurant reason wins the label — "Available 8:00–11:00" would be a
  // lie at 9am on a day the kitchen never opens.
  const itemOff = item.available_now === false;
  const off = itemOff || restaurantClosed;
  // A closed restaurant's card is still tappable: the tap is what surfaces the
  // "opens at…" toast. It just can never reach the cart. An item that is off on
  // its own already says why on the card, so it stays inert.
  const tappable = !itemOff;
  const tags = (item.tags || []).filter((t) => TAG_META[t]);
  return (
    <Card component={motion.div} whileHover={off ? undefined : { y: -4 }} transition={{ type: 'spring', stiffness: 300, damping: 22 }}
      onClick={tappable ? onClick : undefined}
      aria-disabled={off || undefined}
      sx={{ cursor: tappable ? 'pointer' : 'default', overflow: 'hidden', height: '100%', display: 'flex', flexDirection: 'column',
            opacity: off ? 0.6 : 1, filter: off ? 'grayscale(0.4)' : 'none' }}>
      <Box sx={{ position: 'relative', pt: '62%' }}>
        <Box sx={{ position: 'absolute', inset: 0, background: item.image ? undefined
          : 'radial-gradient(120% 120% at 30% 0%, #FFE7C2, #F7B27A)' }}>
          {item.image
            ? <Box component="img" src={item.image} alt={item.display_name} loading="lazy"
                sx={{ width: '100%', height: '100%', objectFit: 'cover' }} />
            : <Box sx={{ width: '100%', height: '100%', display: 'grid', placeItems: 'center', fontSize: 46 }}>🍽️</Box>}
        </Box>
        <Chip size="small" label={`৳${item.effective_price}`}
          sx={{ position: 'absolute', bottom: 8, left: 8, bgcolor: 'rgba(36,24,18,0.82)', color: '#fff', fontWeight: 800 }} />
        {item.is_featured && (
          <Chip size="small" icon={<StarRoundedIcon sx={{ fontSize: 15 }} />} label="Bestseller"
            sx={{ position: 'absolute', top: 8, left: 8, bgcolor: FOOD.turmeric, color: '#3A2A05', fontWeight: 800,
                  '& .MuiChip-icon': { color: '#3A2A05' } }} />
        )}
        {item.discount_price && (
          <Chip size="small" label="Deal" sx={{ position: 'absolute', top: 8, right: 8, bgcolor: 'primary.main', color: '#fff', fontWeight: 800 }} />
        )}
      </Box>
      <Box sx={{ p: 1.75, display: 'flex', flexDirection: 'column', flexGrow: 1 }}>
        <Stack direction="row" spacing={0.75} alignItems="center" sx={{ mb: 0.5 }}>
          {item.is_veg && <VegDot />}
          <Typography variant="subtitle1" sx={{ fontWeight: 800, lineHeight: 1.2 }}>{item.display_name}</Typography>
        </Stack>
        {tags.length > 0 && (
          <Stack direction="row" spacing={0.5} sx={{ mb: 0.75, flexWrap: 'wrap', gap: 0.5 }}>
            {tags.map((t) => (
              <Chip key={t} size="small" label={`${TAG_META[t].emoji} ${TAG_META[t].label}`}
                sx={{ height: 22, bgcolor: 'rgba(244,166,42,0.16)', color: '#7a5310', fontWeight: 700 }} />
            ))}
          </Stack>
        )}
        {item.description && (
          <Typography variant="body2" color="text.secondary" sx={{ mb: 1.5,
            display: '-webkit-box', WebkitLineClamp: 2, WebkitBoxOrient: 'vertical', overflow: 'hidden' }}>
            {item.description}
          </Typography>
        )}
        {off ? (
          <Chip size="small" color="default" sx={{ mt: 'auto', alignSelf: 'flex-start', fontWeight: 700 }}
            label={restaurantClosed
              ? (lang === 'bn' ? 'এখন বন্ধ' : 'Closed Now')
              : (item.available_from ? `Available ${fmt(item.available_from)}–${fmt(item.available_to)}` : 'Unavailable now')} />
        ) : (
          <Button variant="contained" size="small" startIcon={<AddRoundedIcon />}
            sx={{ mt: 'auto', alignSelf: 'flex-start', borderRadius: 999 }}
            onClick={(e) => { e.stopPropagation(); onClick(); }}>
            {hasOptions ? 'Choose' : 'Add'}
          </Button>
        )}
      </Box>
    </Card>
  );
}

export default function RestaurantDetail() {
  const { slug } = useParams();
  const { lang } = useFoodLocation() || {};
  const dispatch = useDispatch();
  const cartRestaurant = useSelector(selectFoodRestaurant);
  const [modalItem, setModalItem] = useState(null);

  // Stale-while-revalidate: a revisited menu paints instantly from localStorage
  // and refreshes in the background. This is the heaviest payload in the app
  // (every category, item and option group), and the one customers re-open most.
  const params = useMemo(() => ({ lang }), [lang]);
  const { data, loading } = useCachedApi(`food/restaurants/${slug}/`, { params });

  const addLine = (line) => {
    // Second gate, for the option modal: it has its own Add button, so blocking
    // only onItemClick would still let a closed restaurant's dish reach the bag.
    if (!openNow) { announceClosed(); setModalItem(null); return; }
    if (cartRestaurant.id && cartRestaurant.id !== line.restaurantId) {
      if (!window.confirm(`Your bag has items from ${cartRestaurant.name}. Start a new order?`)) return;
      dispatch(addFoodItem({ ...line, force: true }));
    } else dispatch(addFoodItem(line));
  };

  // Whether the kitchen is actually open, not just switched on. Computed before
  // the early return so every handler below can rely on it; `data` is null
  // while loading, and a null menu can't be ordered from anyway.
  const openNow = data ? (data.is_open_now ?? data.is_open) : true;

  const announceClosed = () => {
    // Deliberately a toast rather than a silent no-op: a card that just refuses
    // to respond reads as a broken site. toastId keeps a customer tapping down
    // the menu from stacking six identical toasts.
    toast.info(closedToastText(data.display_name, data.next_open, lang), { toastId: 'restaurant-closed' });
  };

  const onItemClick = (item) => {
    // The server enforces this too (services.place_food_cod_order raises
    // "This restaurant is currently closed."); refusing here means the customer
    // finds out before building a bag, not at checkout.
    if (!openNow) { announceClosed(); return; }
    if (item.option_groups && item.option_groups.length) { setModalItem(item); return; }
    addLine({
      lineId: `${item.id}:`, restaurantId: data.id, restaurantSlug: data.slug, restaurantName: data.display_name,
      itemId: item.id, name: item.display_name, image: item.image || '',
      unitPrice: Number(item.effective_price ?? item.price), quantity: 1, selectedOptions: [],
    });
  };

  if (loading || !data) return <Box sx={{ textAlign: 'center', py: 10 }}><CircularProgress color="primary" /></Box>;

  return (
    <Box>
      <Box sx={{ position: 'relative', height: { xs: 190, md: 260 }, borderRadius: 4, overflow: 'hidden', mb: 2 }}>
        <Box sx={{ position: 'absolute', inset: 0, background: data.cover_image
          ? `linear-gradient(180deg, rgba(0,0,0,0.05), rgba(0,0,0,0.66)), url(${data.cover_image}) center/cover`
          : 'linear-gradient(135deg,#E8452B,#9E2A16)' }} />
        {!data.cover_image && <Box aria-hidden sx={{ position: 'absolute', right: 8, bottom: -18, fontSize: 140, opacity: 0.22 }}>🍛</Box>}
        <Box sx={{ position: 'absolute', left: 0, right: 0, bottom: 0, p: { xs: 2, md: 3 }, color: '#fff' }}>
          <Typography variant="h4" sx={{ textShadow: '0 2px 12px rgba(0,0,0,0.45)' }}>{data.display_name}</Typography>
          <Typography variant="body2" sx={{ opacity: 0.92 }}>{data.cuisine_type}</Typography>
        </Box>
      </Box>

      <Stack direction="row" spacing={1} sx={{ mb: 3, flexWrap: 'wrap', gap: 1 }}>
        {/* is_open_now consults the opening hours; is_open is only the master switch. */}
        <Chip label={openNow ? (lang === 'bn' ? 'এখন খোলা' : 'Open now') : (lang === 'bn' ? 'বন্ধ' : 'Closed')}
          color={openNow ? 'success' : 'default'} sx={{ fontWeight: 800 }} />
        <Chip icon={<AccessTimeRoundedIcon />} label={`${data.avg_prep_minutes}+ min`} variant="outlined" />
        <Chip icon={<TwoWheelerRoundedIcon />} label={`Delivery ৳${data.base_delivery_fee}`} variant="outlined" />
        {Number(data.min_order_amount) > 0 && <Chip label={`Min ৳${data.min_order_amount}`} variant="outlined" />}
      </Stack>

      {/* Browsing a closed menu is fine and even useful — ordering from it is
          not. Say when the kitchen reopens instead of leaving dead cards. */}
      {!openNow && (
        <Alert
          severity="info" icon={<AccessTimeRoundedIcon />}
          sx={{ mb: 3, borderRadius: 3, alignItems: 'center' }}
        >
          <Typography sx={{ fontWeight: 800 }}>
            {lang === 'bn' ? 'এখন বন্ধ' : 'Closed right now'} · {nextOpenText(data.next_open, lang)}
          </Typography>
          <Typography variant="body2" color="text.secondary">
            {lang === 'bn'
              ? 'আপনি মেনু দেখতে পারবেন, তবে খোলার আগে অর্ডার করা যাবে না।'
              : 'You can browse the menu, but orders can’t be placed until they reopen.'}
          </Typography>
          {(data.opening_hours || []).length > 0 && (
            <Stack sx={{ mt: 1 }} spacing={0.25}>
              {data.opening_hours.filter((h) => !h.is_closed).map((h) => (
                <Typography key={`${h.weekday}-${h.open_time}`} variant="caption" color="text.secondary">
                  {dayName(h.weekday, lang)} · {formatTime(h.open_time, lang)} – {formatTime(h.close_time, lang)}
                </Typography>
              ))}
            </Stack>
          )}
        </Alert>
      )}

      {(data.categories || []).map((cat) => (
        <Box key={cat.id} sx={{ mb: 4.5 }}>
          {/* display_name, not name — the serializer localizes it (Bangla with an
              English fallback); `name` is always the English column. */}
          <Typography variant="h5" sx={{ mb: 0.5 }}>{cat.display_name || cat.name}</Typography>
          <Box sx={{ width: 44, height: 3, borderRadius: 2, bgcolor: 'primary.main', mb: 2 }} />
          <Grid container spacing={2.5}>
            {cat.items.map((item) => (
              <Grid item xs={6} sm={4} md={3} key={item.id}>
                <DishCard item={item} onClick={() => onItemClick(item)}
                  restaurantClosed={!openNow} lang={lang} />
              </Grid>
            ))}
          </Grid>
        </Box>
      ))}

      <ItemOptionModal open={!!modalItem} item={modalItem} restaurant={data} onClose={() => setModalItem(null)} onAdd={addLine} />
    </Box>
  );
}
