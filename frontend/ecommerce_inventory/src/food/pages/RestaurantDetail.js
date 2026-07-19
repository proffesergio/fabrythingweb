import { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import { useDispatch, useSelector } from 'react-redux';
import { Box, Typography, Card, CardContent, Grid, Chip, Stack, Divider, CircularProgress, Button } from '@mui/material';
import useApi from '../../hooks/APIHandler';
import { useFoodLocation } from '../context/FoodLocationContext';
import { addFoodItem, selectFoodRestaurant } from '../redux/foodCartSlice';
import ItemOptionModal from '../components/ItemOptionModal';

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
      if (!window.confirm(`Your cart has items from ${cartRestaurant.name}. Start a new order?`)) return;
      dispatch(addFoodItem({ ...line, force: true }));
    } else {
      dispatch(addFoodItem(line));
    }
  };

  const onItemClick = (item) => {
    if (item.option_groups && item.option_groups.length) { setModalItem(item); return; }
    addLine({
      lineId: `${item.id}:`, restaurantId: data.id, restaurantSlug: data.slug, restaurantName: data.display_name,
      itemId: item.id, name: item.display_name, image: item.image || '',
      unitPrice: Number(item.effective_price ?? item.price), quantity: 1, selectedOptions: [],
    });
  };

  if (loading || !data) return <Box sx={{ textAlign: 'center', py: 8 }}><CircularProgress /></Box>;

  return (
    <Box>
      <Box
        sx={{
          height: 200, borderRadius: 4, mb: 2,
          backgroundImage: `url(${data.cover_image || 'https://placehold.co/1200x400/17191F/FF6B35?text=Food'})`,
          backgroundSize: 'cover', backgroundPosition: 'center',
        }}
      />
      <Typography variant="h4">{data.display_name}</Typography>
      <Stack direction="row" spacing={1} sx={{ my: 1, flexWrap: 'wrap', gap: 1 }}>
        <Chip size="small" label={data.is_open ? 'Open' : 'Closed'} color={data.is_open ? 'success' : 'default'} />
        <Chip size="small" label={`${data.avg_prep_minutes}+ min`} />
        <Chip size="small" label={`Delivery ৳${data.base_delivery_fee}`} />
        {Number(data.min_order_amount) > 0 && <Chip size="small" label={`Min ৳${data.min_order_amount}`} />}
      </Stack>
      {(data.categories || []).map((cat) => (
        <Box key={cat.id} sx={{ mt: 3 }}>
          <Typography variant="h6" sx={{ mb: 1 }}>{cat.name}</Typography>
          <Divider sx={{ mb: 2 }} />
          <Grid container spacing={2}>
            {cat.items.map((item) => (
              <Grid item xs={12} sm={6} key={item.id}>
                <Card sx={{ display: 'flex', justifyContent: 'space-between', p: 2, cursor: 'pointer' }} onClick={() => onItemClick(item)}>
                  <CardContent sx={{ flex: 1, p: 0 }}>
                    <Typography variant="subtitle1">{item.display_name}</Typography>
                    <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>{item.description}</Typography>
                    <Typography variant="subtitle2" color="primary.main">৳{item.effective_price}</Typography>
                  </CardContent>
                  <Button variant="contained" size="small" sx={{ alignSelf: 'center' }}>Add</Button>
                </Card>
              </Grid>
            ))}
          </Grid>
        </Box>
      ))}
      <ItemOptionModal open={!!modalItem} item={modalItem} restaurant={data} onClose={() => setModalItem(null)} onAdd={addLine} />
    </Box>
  );
}
