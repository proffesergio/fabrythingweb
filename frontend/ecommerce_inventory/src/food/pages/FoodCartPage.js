import { useNavigate } from 'react-router-dom';
import { useSelector, useDispatch } from 'react-redux';
import { Box, Typography, Card, IconButton, Button, Divider, Stack } from '@mui/material';
import AddIcon from '@mui/icons-material/Add';
import RemoveIcon from '@mui/icons-material/Remove';
import DeleteOutlineIcon from '@mui/icons-material/DeleteOutline';
import {
  selectFoodCart, selectFoodSubtotal, selectFoodRestaurant, updateFoodQty, removeFoodItem,
} from '../redux/foodCartSlice';

const linePrice = (i) =>
  (Number(i.unitPrice) + i.selectedOptions.reduce((s, o) => s + Number(o.priceDelta), 0)) * i.quantity;

export default function FoodCartPage() {
  const items = useSelector(selectFoodCart);
  const subtotal = useSelector(selectFoodSubtotal);
  const restaurant = useSelector(selectFoodRestaurant);
  const dispatch = useDispatch();
  const navigate = useNavigate();

  if (!items.length) {
    return <Typography color="text.secondary" sx={{ py: 8, textAlign: 'center' }}>Your food bag is empty.</Typography>;
  }

  return (
    <Box sx={{ maxWidth: 600, mx: 'auto' }}>
      <Typography variant="h5" sx={{ mb: 2 }}>Your bag · {restaurant.name}</Typography>
      {items.map((i) => (
        <Card key={i.lineId} sx={{ p: 2, mb: 1, display: 'flex', alignItems: 'center', gap: 2 }}>
          <Box sx={{ flex: 1 }}>
            <Typography>{i.name}</Typography>
            {i.selectedOptions.length > 0 && (
              <Typography variant="caption" color="text.secondary">
                {i.selectedOptions.map((o) => o.name).join(', ')}
              </Typography>
            )}
            <Typography variant="body2" color="primary.main">৳{linePrice(i)}</Typography>
          </Box>
          <IconButton size="small" onClick={() => dispatch(updateFoodQty({ lineId: i.lineId, quantity: i.quantity - 1 }))}><RemoveIcon /></IconButton>
          <Typography>{i.quantity}</Typography>
          <IconButton size="small" onClick={() => dispatch(updateFoodQty({ lineId: i.lineId, quantity: i.quantity + 1 }))}><AddIcon /></IconButton>
          <IconButton size="small" color="error" onClick={() => dispatch(removeFoodItem({ lineId: i.lineId }))}><DeleteOutlineIcon /></IconButton>
        </Card>
      ))}
      <Divider sx={{ my: 2 }} />
      <Stack direction="row" justifyContent="space-between"><Typography>Subtotal</Typography><Typography>৳{subtotal}</Typography></Stack>
      <Button fullWidth variant="contained" sx={{ mt: 2 }} onClick={() => navigate('/food/checkout')}>Proceed to checkout</Button>
    </Box>
  );
}
