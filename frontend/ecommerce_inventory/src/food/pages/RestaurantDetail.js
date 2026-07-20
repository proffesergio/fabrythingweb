import { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import { useDispatch, useSelector } from 'react-redux';
import { Box, Typography, Grid, Chip, Stack, CircularProgress, Button, Card } from '@mui/material';
import AddRoundedIcon from '@mui/icons-material/AddRounded';
import AccessTimeRoundedIcon from '@mui/icons-material/AccessTimeRounded';
import TwoWheelerRoundedIcon from '@mui/icons-material/TwoWheelerRounded';
import StarRoundedIcon from '@mui/icons-material/StarRounded';
import { motion } from 'framer-motion';
import useApi from '../../hooks/APIHandler';
import { useFoodLocation } from '../context/FoodLocationContext';
import { addFoodItem, selectFoodRestaurant } from '../redux/foodCartSlice';
import ItemOptionModal from '../components/ItemOptionModal';
import { FOOD } from '../theme';

function VegDot() {
  return (
    <Box aria-label="veg" sx={{ width: 15, height: 15, borderRadius: '3px', border: `2px solid ${FOOD.cardamom}`,
      display: 'grid', placeItems: 'center', flexShrink: 0 }}>
      <Box sx={{ width: 6, height: 6, borderRadius: '50%', bgcolor: FOOD.cardamom }} />
    </Box>
  );
}

function DishCard({ item, onClick }) {
  const hasOptions = item.option_groups && item.option_groups.length > 0;
  return (
    <Card component={motion.div} whileHover={{ y: -4 }} transition={{ type: 'spring', stiffness: 300, damping: 22 }}
      onClick={onClick} sx={{ cursor: 'pointer', overflow: 'hidden', height: '100%', display: 'flex', flexDirection: 'column' }}>
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
        {item.description && (
          <Typography variant="body2" color="text.secondary" sx={{ mb: 1.5,
            display: '-webkit-box', WebkitLineClamp: 2, WebkitBoxOrient: 'vertical', overflow: 'hidden' }}>
            {item.description}
          </Typography>
        )}
        <Button variant="contained" size="small" startIcon={<AddRoundedIcon />}
          sx={{ mt: 'auto', alignSelf: 'flex-start', borderRadius: 999 }}
          onClick={(e) => { e.stopPropagation(); onClick(); }}>
          {hasOptions ? 'Choose' : 'Add'}
        </Button>
      </Box>
    </Card>
  );
}

export default function RestaurantDetail() {
  const { slug } = useParams();
  const { lang } = useFoodLocation() || {};
  const { callApi, loading } = useApi();
  const dispatch = useDispatch();
  const cartRestaurant = useSelector(selectFoodRestaurant);
  const [data, setData] = useState(null);
  const [modalItem, setModalItem] = useState(null);

  useEffect(() => {
    (async () => {
      const res = await callApi({ url: `food/restaurants/${slug}/`, method: 'GET', params: { lang } });
      setData(res?.data?.data || null);
    })();
  }, [slug, lang]); // eslint-disable-line react-hooks/exhaustive-deps

  const addLine = (line) => {
    if (cartRestaurant.id && cartRestaurant.id !== line.restaurantId) {
      if (!window.confirm(`Your bag has items from ${cartRestaurant.name}. Start a new order?`)) return;
      dispatch(addFoodItem({ ...line, force: true }));
    } else dispatch(addFoodItem(line));
  };

  const onItemClick = (item) => {
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
        <Chip label={data.is_open ? 'Open now' : 'Closed'} color={data.is_open ? 'success' : 'default'} sx={{ fontWeight: 800 }} />
        <Chip icon={<AccessTimeRoundedIcon />} label={`${data.avg_prep_minutes}+ min`} variant="outlined" />
        <Chip icon={<TwoWheelerRoundedIcon />} label={`Delivery ৳${data.base_delivery_fee}`} variant="outlined" />
        {Number(data.min_order_amount) > 0 && <Chip label={`Min ৳${data.min_order_amount}`} variant="outlined" />}
      </Stack>

      {(data.categories || []).map((cat) => (
        <Box key={cat.id} sx={{ mb: 4.5 }}>
          <Typography variant="h5" sx={{ mb: 0.5 }}>{cat.name}</Typography>
          <Box sx={{ width: 44, height: 3, borderRadius: 2, bgcolor: 'primary.main', mb: 2 }} />
          <Grid container spacing={2.5}>
            {cat.items.map((item) => (
              <Grid item xs={6} sm={4} md={3} key={item.id}>
                <DishCard item={item} onClick={() => onItemClick(item)} />
              </Grid>
            ))}
          </Grid>
        </Box>
      ))}

      <ItemOptionModal open={!!modalItem} item={modalItem} restaurant={data} onClose={() => setModalItem(null)} onAdd={addLine} />
    </Box>
  );
}
