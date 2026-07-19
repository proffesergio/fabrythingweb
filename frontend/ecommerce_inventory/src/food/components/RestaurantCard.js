import { Card, CardMedia, CardContent, Box, Typography, Chip, Stack } from '@mui/material';
import AccessTimeIcon from '@mui/icons-material/AccessTime';
import TwoWheelerIcon from '@mui/icons-material/TwoWheeler';
import { Link } from 'react-router-dom';

export default function RestaurantCard({ restaurant: r }) {
  return (
    <Card
      component={Link}
      to={`/food/restaurant/${r.slug}`}
      sx={{ textDecoration: 'none', display: 'block', overflow: 'hidden', opacity: r.is_open ? 1 : 0.6 }}
    >
      <Box sx={{ position: 'relative' }}>
        <CardMedia
          component="img"
          height="150"
          image={r.cover_image || 'https://placehold.co/600x300/17191F/FF6B35?text=Food'}
          alt={r.display_name}
          loading="lazy"
        />
        {!r.is_open && (
          <Chip label="Closed" size="small" sx={{ position: 'absolute', top: 10, left: 10 }} />
        )}
      </Box>
      <CardContent>
        <Typography variant="h6" noWrap sx={{ color: 'text.primary' }}>{r.display_name}</Typography>
        <Typography variant="body2" color="text.secondary" noWrap>{r.cuisine_type || 'Restaurant'}</Typography>
        <Stack direction="row" spacing={1} sx={{ mt: 1 }}>
          <Chip size="small" icon={<AccessTimeIcon />} label={`${r.avg_prep_minutes}+ min`} />
          <Chip size="small" icon={<TwoWheelerIcon />} label={`৳${r.base_delivery_fee}`} />
        </Stack>
      </CardContent>
    </Card>
  );
}
