import { useNavigate, useLocation } from 'react-router-dom';
import { Paper, BottomNavigation, BottomNavigationAction, Badge } from '@mui/material';
import HomeRoundedIcon from '@mui/icons-material/HomeRounded';
import RestaurantMenuRoundedIcon from '@mui/icons-material/RestaurantMenuRounded';
import ReceiptLongRoundedIcon from '@mui/icons-material/ReceiptLongRounded';
import ShoppingBagRoundedIcon from '@mui/icons-material/ShoppingBagRounded';
import { useSelector } from 'react-redux';
import { selectFoodCount } from '../redux/foodCartSlice';
import { useFoodLocation } from '../context/FoodLocationContext';

// Phone-only tab bar. On a 360px screen the header could not hold the logo, the
// area picker, Browse, theme, language, notifications and the bag without
// shrinking everything to unlabelled circles — so navigation moves down here,
// where a thumb reaches it, and the header keeps only identity + location.
const TABS = [
  { to: '/food', icon: <HomeRoundedIcon />, en: 'Home', bn: 'হোম', match: (p) => p === '/food' || p === '/food/' },
  { to: '/food/restaurants', icon: <RestaurantMenuRoundedIcon />, en: 'Restaurants', bn: 'রেস্তোরাঁ',
    match: (p) => p.startsWith('/food/restaurant') },
  { to: '/food/orders', icon: <ReceiptLongRoundedIcon />, en: 'Orders', bn: 'অর্ডার',
    // Not /food/order* — that prefix also matches the guest tracking page, and
    // more importantly this must not light up on /food/partner.
    match: (p) => p === '/food/orders' || p.startsWith('/food/order/') },
  { to: '/food/cart', icon: 'bag', en: 'Bag', bn: 'ব্যাগ',
    match: (p) => p.startsWith('/food/cart') || p.startsWith('/food/checkout') },
];

export default function FoodBottomNav() {
  const navigate = useNavigate();
  const { pathname } = useLocation();
  const count = useSelector(selectFoodCount);
  const { lang } = useFoodLocation() || {};

  // -1 rather than 0, so a page that matches no tab (a menu, say) highlights
  // nothing instead of falsely highlighting Home.
  const current = TABS.findIndex((t) => t.match(pathname));

  return (
    <Paper
      elevation={0}
      sx={{
        display: { xs: 'block', md: 'none' },
        position: 'fixed', left: 0, right: 0, bottom: 0, zIndex: 1250,
        borderTop: 1, borderColor: 'divider', borderRadius: 0,
        // Clears the iOS home indicator; 0 on everything else.
        pb: 'env(safe-area-inset-bottom)',
        bgcolor: 'background.paper',
      }}
    >
      <BottomNavigation
        value={current} showLabels
        onChange={(e, i) => navigate(TABS[i].to)}
        sx={{ bgcolor: 'transparent', height: 60,
              '& .MuiBottomNavigationAction-root': { minWidth: 0, px: 0.5 },
              '& .MuiBottomNavigationAction-label': { fontSize: 11, fontWeight: 700 } }}
      >
        {TABS.map((t) => (
          <BottomNavigationAction
            key={t.to}
            label={lang === 'bn' ? t.bn : t.en}
            icon={t.icon === 'bag'
              ? <Badge badgeContent={count} color="primary"><ShoppingBagRoundedIcon /></Badge>
              : t.icon}
          />
        ))}
      </BottomNavigation>
    </Paper>
  );
}
