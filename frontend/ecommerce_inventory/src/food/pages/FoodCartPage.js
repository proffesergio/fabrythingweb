import { useNavigate } from 'react-router-dom';
import { useSelector, useDispatch } from 'react-redux';
import { Box, Typography, Card, IconButton, Button, Divider, Stack } from '@mui/material';
import AddRoundedIcon from '@mui/icons-material/AddRounded';
import RemoveRoundedIcon from '@mui/icons-material/RemoveRounded';
import DeleteOutlineRoundedIcon from '@mui/icons-material/DeleteOutlineRounded';
import StorefrontRoundedIcon from '@mui/icons-material/StorefrontRounded';
import {
  selectFoodCart, selectFoodSubtotal, selectFoodRestaurant, updateFoodQty, removeFoodItem,
} from '../redux/foodCartSlice';

const linePrice = (i) =>
  (Number(i.unitPrice) + i.selectedOptions.reduce((s, o) => s + Number(o.priceDelta), 0)) * i.quantity;

function Stepper({ item, dispatch }) {
  return (
    <Stack direction="row" alignItems="center" spacing={0.5}
      sx={{ border: 1, borderColor: 'divider', borderRadius: 999, px: 0.5 }}>
      <IconButton size="small" color="primary" onClick={() => dispatch(updateFoodQty({ lineId: item.lineId, quantity: item.quantity - 1 }))}>
        <RemoveRoundedIcon fontSize="small" />
      </IconButton>
      <Typography sx={{ fontWeight: 800, minWidth: 18, textAlign: 'center' }}>{item.quantity}</Typography>
      <IconButton size="small" color="primary" onClick={() => dispatch(updateFoodQty({ lineId: item.lineId, quantity: item.quantity + 1 }))}>
        <AddRoundedIcon fontSize="small" />
      </IconButton>
    </Stack>
  );
}

export default function FoodCartPage() {
  const items = useSelector(selectFoodCart);
  const subtotal = useSelector(selectFoodSubtotal);
  const restaurant = useSelector(selectFoodRestaurant);
  const dispatch = useDispatch();
  const navigate = useNavigate();

  if (!items.length) {
    return (
      <Box sx={{ textAlign: 'center', py: 10 }}>
        <Box sx={{ fontSize: 60, mb: 1 }}>🛍️</Box>
        <Typography variant="h6">Your bag is empty</Typography>
        <Typography color="text.secondary" sx={{ mb: 3 }}>Add some delicious food to get started.</Typography>
        <Button variant="contained" onClick={() => navigate('/food')}>Browse restaurants</Button>
      </Box>
    );
  }

  return (
    <Box sx={{ maxWidth: 620, mx: 'auto' }}>
      <Typography variant="h4" sx={{ mb: 0.5 }}>Your bag</Typography>
      <Stack direction="row" spacing={0.5} alignItems="center" sx={{ mb: 2.5, color: 'text.secondary' }}>
        <StorefrontRoundedIcon sx={{ fontSize: 18 }} />
        <Typography variant="body2">{restaurant.name}</Typography>
      </Stack>

      <Card sx={{ p: { xs: 1.5, sm: 2 }, mb: 2.5 }}>
        {items.map((i, idx) => (
          <Box key={i.lineId}>
            <Stack direction="row" alignItems="center" spacing={2} sx={{ py: 1.5 }}>
              <Box sx={{ flex: 1, minWidth: 0 }}>
                <Typography sx={{ fontWeight: 700 }} noWrap>{i.name}</Typography>
                {i.selectedOptions.length > 0 && (
                  <Typography variant="caption" color="text.secondary">{i.selectedOptions.map((o) => o.name).join(', ')}</Typography>
                )}
                <Typography variant="subtitle2" color="primary.main" sx={{ fontWeight: 800 }}>৳{linePrice(i)}</Typography>
              </Box>
              <Stepper item={i} dispatch={dispatch} />
              <IconButton size="small" color="error" onClick={() => dispatch(removeFoodItem({ lineId: i.lineId }))}>
                <DeleteOutlineRoundedIcon fontSize="small" />
              </IconButton>
            </Stack>
            {idx < items.length - 1 && <Divider />}
          </Box>
        ))}
      </Card>

      <Card sx={{ p: 2.5, mb: 2.5 }}>
        <Stack direction="row" justifyContent="space-between" sx={{ mb: 0.5 }}>
          <Typography color="text.secondary">Subtotal</Typography>
          <Typography sx={{ fontWeight: 700 }}>৳{subtotal}</Typography>
        </Stack>
        <Typography variant="caption" color="text.secondary">
          Delivery fee and total are confirmed at checkout.
        </Typography>
      </Card>

      <Button fullWidth variant="contained" size="large" sx={{ py: 1.5, borderRadius: 999 }}
        onClick={() => navigate('/food/checkout')}>
        Proceed to checkout · ৳{subtotal}
      </Button>
    </Box>
  );
}
