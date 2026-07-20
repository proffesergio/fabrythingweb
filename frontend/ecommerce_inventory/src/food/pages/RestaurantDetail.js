import { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import { useDispatch, useSelector } from 'react-redux';
import { Box, Typography, Grid, Chip, Stack, Divider, CircularProgress, IconButton } from '@mui/material';
import AddRoundedIcon from '@mui/icons-material/AddRounded';
import AccessTimeRoundedIcon from '@mui/icons-material/AccessTimeRounded';
import TwoWheelerRoundedIcon from '@mui/icons-material/TwoWheelerRounded';
import { motion } from 'framer-motion';
import useApi from '../../hooks/APIHandler';
import { useFoodLocation } from '../context/FoodLocationContext';
import { addFoodItem, selectFoodRestaurant } from '../redux/foodCartSlice';
import ItemOptionModal from '../components/ItemOptionModal';
import { FOOD } from '../theme';

function DishRow({ item, onClick }) {
  return (
    <Box
      onClick={onClick}
      sx={{ display: 'flex', gap: 2, py: 2, cursor: 'pointer', alignItems: 'center',
            borderBottom: `1px solid ${FOOD.line}`, '&:hover .dish-name': { color: 'primary.main' } }}
    >
      <Box sx={{ flex: 1, minWidth: 0 }}>
        {item.is_veg && (
          <Box aria-label="veg" sx={{ width: 14, height: 14, mb: 0.5, borderRadius: '3px',
            border: `2px solid ${FOOD.cardamom}`, display: 'grid', placeItems: 'center' }}>
            <Box sx={{ width: 6, height: 6, borderRadius: '50%', bgcolor: FOOD.cardamom }} />
          </Box>
        )}
        <Typography className="dish-name" variant="subtitle1" sx={{ fontWeight: 700, transition: 'color .15s' }}>
          {item.display_name}
        </Typography>
        {item.description && (
          <Typography variant="body2" color="text.secondary" sx={{ mb: 0.75, display: '-webkit-box',
            WebkitLineClamp: 2, WebkitBoxOrient: 'vertical', overflow: 'hidden' }}>
            {item.description}
          </Typography>
        )}
        <Typography variant="subtitle2" sx={{ fontWeight: 800 }}>৳{item.effective_price}</Typography>
      </Box>

      <Box sx={{ position: 'relative', flexShrink: 0 }}>
        <Box sx={{ width: 96, height: 96, borderRadius: 3, overflow: 'hidden',
          background: item.image ? undefined : `radial-gradient(120% 120% at 30% 0%, #FFE7C2, #F7B27A)` }}>
          {item.image
            ? <Box component="img" src={item.image} alt={item.display_name} loading="lazy" sx={{ width: '100%', height: '100%', objectFit: 'cover' }} />
            : <Box sx={{ width: '100%', height: '100%', display: 'grid', placeItems: 'center', fontSize: 34 }}>🍽️</Box>}
        </Box>
        <IconButton
          component={motion.button} whileTap={{ scale: 0.8 }}
          sx={{ position: 'absolute', bottom: -12, right: '50%', transform: 'translateX(50%)',
                bgcolor: '#fff', border: `1px solid ${FOOD.line}`, color: 'primary.main',
                boxShadow: '0 6px 14px rgba(120,60,20,0.16)', width: 36, height: 36,
                '&:hover': { bgcolor: 'primary.main', color: '#fff' } }}
        >
          <AddRoundedIcon />
        </IconButton>
      </Box>
    </Box>
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
      {/* Hero cover with scrim + name overlay */}
      <Box sx={{ position: 'relative', height: { xs: 180, md: 240 }, borderRadius: 4, overflow: 'hidden', mb: 2 }}>
        <Box sx={{ position: 'absolute', inset: 0,
          background: data.cover_image
            ? `linear-gradient(180deg, rgba(0,0,0,0.05), rgba(0,0,0,0.62)), url(${data.cover_image}) center/cover`
            : `linear-gradient(135deg, #E8452B, #C4361F)` }} />
        {!data.cover_image && (
          <Box aria-hidden sx={{ position: 'absolute', right: 8, bottom: -14, fontSize: 130, opacity: 0.22 }}>🍛</Box>
        )}
        <Box sx={{ position: 'absolute', left: 0, right: 0, bottom: 0, p: { xs: 2, md: 3 }, color: '#fff' }}>
          <Typography variant="h4" sx={{ textShadow: '0 2px 12px rgba(0,0,0,0.4)' }}>{data.display_name}</Typography>
          <Typography variant="body2" sx={{ opacity: 0.9 }}>{data.cuisine_type}</Typography>
        </Box>
      </Box>

      <Stack direction="row" spacing={1} sx={{ mb: 3, flexWrap: 'wrap', gap: 1 }}>
        <Chip label={data.is_open ? 'Open now' : 'Closed'} color={data.is_open ? 'success' : 'default'} sx={{ fontWeight: 800 }} />
        <Chip icon={<AccessTimeRoundedIcon />} label={`${data.avg_prep_minutes}+ min`} variant="outlined" />
        <Chip icon={<TwoWheelerRoundedIcon />} label={`Delivery ৳${data.base_delivery_fee}`} variant="outlined" />
        {Number(data.min_order_amount) > 0 && <Chip label={`Min ৳${data.min_order_amount}`} variant="outlined" />}
      </Stack>

      {(data.categories || []).map((cat) => (
        <Box key={cat.id} sx={{ mb: 4 }}>
          <Typography variant="h5" sx={{ mb: 0.5 }}>{cat.name}</Typography>
          <Divider sx={{ borderColor: 'primary.main', borderBottomWidth: 2, width: 44, mb: 1 }} />
          <Grid container columnSpacing={4}>
            {cat.items.map((item) => (
              <Grid item xs={12} md={6} key={item.id}>
                <DishRow item={item} onClick={() => onItemClick(item)} />
              </Grid>
            ))}
          </Grid>
        </Box>
      ))}

      <ItemOptionModal open={!!modalItem} item={modalItem} restaurant={data} onClose={() => setModalItem(null)} onAdd={addLine} />
    </Box>
  );
}
