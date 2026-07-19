import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useSelector, useDispatch } from 'react-redux';
import { Box, Typography, TextField, Button, Card, Stack, Divider, MenuItem, Alert } from '@mui/material';
import { toast } from 'react-toastify';
import useApi from '../../hooks/APIHandler';
import { useFoodLocation } from '../context/FoodLocationContext';
import {
  selectFoodCart, selectFoodSubtotal, selectFoodRestaurant, selectFoodTip, clearFoodCart,
} from '../redux/foodCartSlice';

export default function FoodCheckout() {
  const items = useSelector(selectFoodCart);
  const subtotal = useSelector(selectFoodSubtotal);
  const restaurant = useSelector(selectFoodRestaurant);
  const tip = useSelector(selectFoodTip);
  const { zoneId, zones, coords, detectLocation } = useFoodLocation() || {};
  const { callApi, loading } = useApi();
  const dispatch = useDispatch();
  const navigate = useNavigate();
  const [form, setForm] = useState({ name: '', phone: '', address: '' });
  const [zone, setZone] = useState(zoneId || '');
  const [err, setErr] = useState('');

  const set = (k) => (e) => setForm((f) => ({ ...f, [k]: e.target.value }));

  const submit = async () => {
    setErr('');
    if (!form.name || !form.phone || !form.address) { setErr('Name, phone and address are required.'); return; }
    if (!zone && !coords) { setErr('Choose a delivery area or use your location.'); return; }
    const body = {
      restaurant_slug: restaurant.slug, contact_name: form.name, contact_phone: form.phone,
      delivery_address: form.address, tip,
      items: items.map((i) => ({
        item_id: i.itemId, quantity: i.quantity, option_ids: i.selectedOptions.map((o) => o.optionId),
      })),
    };
    if (zone) body.zone_id = zone;
    else if (coords) { body.lat = coords.lat; body.lng = coords.lng; }
    const res = await callApi({ url: 'food/orders/', method: 'POST', body });
    if (res?.status === 201) {
      const code = res.data.data.order_code;
      dispatch(clearFoodCart());
      toast.success('Order placed!');
      navigate(`/food/order/${code}`);
    } else if (res?.data?.data) {
      setErr(Array.isArray(res.data.data) ? res.data.data.join(' ') : String(res.data.data));
    }
  };

  if (!items.length) {
    return <Typography color="text.secondary" sx={{ py: 8, textAlign: 'center' }}>Your food bag is empty.</Typography>;
  }

  return (
    <Box sx={{ maxWidth: 560, mx: 'auto' }}>
      <Typography variant="h5" sx={{ mb: 2 }}>Checkout</Typography>
      {err && <Alert severity="error" sx={{ mb: 2 }}>{err}</Alert>}
      <Card sx={{ p: 2, mb: 2 }}>
        <Stack spacing={2}>
          <TextField label="Name" value={form.name} onChange={set('name')} fullWidth />
          <TextField label="Phone" value={form.phone} onChange={set('phone')} fullWidth />
          <TextField label="Delivery address" value={form.address} onChange={set('address')} fullWidth multiline rows={2} />
          <TextField select label="Delivery area" value={zone} onChange={(e) => setZone(e.target.value)} fullWidth>
            <MenuItem value=""><em>Select area</em></MenuItem>
            {(zones || []).map((z) => <MenuItem key={z.id} value={String(z.id)}>{z.name}</MenuItem>)}
          </TextField>
          <Button
            variant="outlined" color="inherit"
            onClick={() => detectLocation && detectLocation().then(() => toast.info('Location detected')).catch(() => toast.error('Could not get location'))}
          >
            Use my location instead
          </Button>
        </Stack>
      </Card>
      <Card sx={{ p: 2, mb: 2 }}>
        <Stack direction="row" justifyContent="space-between"><Typography>Subtotal</Typography><Typography>৳{subtotal}</Typography></Stack>
        <Typography variant="caption" color="text.secondary">Delivery fee & total are confirmed by the restaurant at checkout.</Typography>
        <Divider sx={{ my: 1 }} />
        <Typography variant="subtitle2">Payment: Cash on Delivery</Typography>
      </Card>
      <Button fullWidth variant="contained" disabled={loading} onClick={submit}>Place order (COD)</Button>
    </Box>
  );
}
