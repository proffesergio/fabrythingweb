import { Box, Button, Container, Divider, Stack, Typography } from '@mui/material';
import { Link } from 'react-router-dom';
import { useFoodLocation } from '../context/FoodLocationContext';

const t = (en, bn, lang) => (lang === 'bn' ? bn : en);

// Quiet site footer: navigation, support and partner entry live here instead
// of interrupting browsing as mid-page cards. Bilingual like the rest of food.
export default function FoodFooter() {
  const loc = useFoodLocation() || {};
  const lang = loc.lang || 'en';
  const links = [
    [t('Home', 'হোম', lang), '/food'],
    [t('Restaurants', 'রেস্তোরাঁ', lang), '/food/restaurants'],
    [t('My orders', 'আমার অর্ডার', lang), '/food/orders'],
    [t('Become a Partner', 'পার্টনার হোন', lang), '/food/partner'],
  ];
  return (
    <Box component="footer" sx={{ borderTop: 1, borderColor: 'divider', mt: 5, bgcolor: 'background.paper' }}>
      <Container maxWidth="lg" sx={{ py: 4 }}>
        <Stack direction={{ xs: 'column', sm: 'row' }} spacing={3} justifyContent="space-between">
          <Box sx={{ maxWidth: 320 }}>
            <Typography variant="subtitle1" sx={{ fontWeight: 900 }}>
              {t('Fabrything Food', 'ফেব্রিথিং ফুড', lang)}
            </Typography>
            <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>
              {t('Hot meals from your neighbourhood — cash on delivery.',
                 'আপনার এলাকার গরম খাবার — ক্যাশ অন ডেলিভারি।', lang)}
            </Typography>
          </Box>
          <Box sx={{ display: 'flex', gap: 3, flexWrap: 'wrap' }}>
            {links.map(([label, to]) => (
              <Typography
                key={to} component={Link} to={to} variant="body2"
                sx={{ color: 'text.secondary', textDecoration: 'none', '&:hover': { color: 'primary.main' } }}
              >
                {label}
              </Typography>
            ))}
          </Box>
          <Box>
            <Typography variant="body2" color="text.secondary">
              {t('Support', 'সহায়তা', lang)}: support@fabrything.com
            </Typography>
            <Button
              component={Link} to="/food/partner" variant="outlined" size="small"
              sx={{ mt: 1.5, borderRadius: 999, fontWeight: 800 }}
            >
              {t('Own a restaurant? Partner with us', 'রেস্তোরাঁর মালিক? পার্টনার হোন', lang)}
            </Button>
          </Box>
        </Stack>
        <Divider sx={{ my: 2 }} />
        <Typography variant="caption" color="text.secondary" sx={{ display: 'block', textAlign: 'center' }}>
          © {new Date().getFullYear()} {t('Fabrything Food', 'ফেব্রিথিং ফুড', lang)}
        </Typography>
      </Container>
    </Box>
  );
}
