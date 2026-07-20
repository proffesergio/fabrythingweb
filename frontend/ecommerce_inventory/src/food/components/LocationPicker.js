import { Dialog, Box, Typography, Stack, Button, IconButton, List, ListItemButton, Divider } from '@mui/material';
import CloseRoundedIcon from '@mui/icons-material/CloseRounded';
import PlaceRoundedIcon from '@mui/icons-material/PlaceRounded';
import MyLocationRoundedIcon from '@mui/icons-material/MyLocationRounded';
import CheckCircleRoundedIcon from '@mui/icons-material/CheckCircleRounded';
import { toast } from 'react-toastify';
import { useFoodLocation } from '../context/FoodLocationContext';
import { FOOD } from '../theme';

export default function LocationPicker() {
  const { zones, zoneId, lang, setZoneId, detectLocation, pickerOpen, closePicker } = useFoodLocation() || {};
  const t = (en, bn) => (lang === 'bn' ? bn : en);

  const pick = (id) => { setZoneId(String(id)); closePicker(); };

  const useLocation = () => {
    detectLocation()
      .then(({ zone }) => {
        if (zone) { toast.success(t('Area detected', 'এলাকা শনাক্ত হয়েছে')); closePicker(); }
        else toast.info(t('We don’t deliver to your exact spot yet — pick the nearest area.', 'আপনার এলাকায় ডেলিভারি নেই — কাছের এলাকা বেছে নিন।'));
      })
      .catch(() => toast.error(t('Could not get your location', 'অবস্থান পাওয়া যায়নি')));
  };

  return (
    <Dialog
      open={!!pickerOpen} onClose={closePicker} fullWidth maxWidth="xs"
      PaperProps={{ sx: { position: { xs: 'fixed', sm: 'static' }, bottom: { xs: 0, sm: 'auto' }, m: { xs: 0, sm: 4 },
        width: { xs: '100%', sm: 'auto' }, borderRadius: { xs: '24px 24px 0 0', sm: 6 } } }}
    >
      <Box sx={{ p: 3 }}>
        <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 0.5 }}>
          <Typography variant="h6">{t('Deliver to', 'ডেলিভারি এলাকা')}</Typography>
          <IconButton onClick={closePicker} size="small"><CloseRoundedIcon /></IconButton>
        </Stack>
        <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
          {t('Choose your area so we show what delivers to you.', 'আপনার এলাকা বেছে নিন, আমরা সেখানে যা পাওয়া যায় দেখাবো।')}
        </Typography>

        <Button fullWidth variant="outlined" startIcon={<MyLocationRoundedIcon />} onClick={useLocation}
          sx={{ mb: 2, borderRadius: 3, borderColor: FOOD.line, color: 'primary.main', justifyContent: 'flex-start', py: 1.2 }}>
          {t('Use my current location', 'আমার অবস্থান ব্যবহার করুন')}
        </Button>

        <Typography variant="overline" color="text.secondary">{t('Service areas', 'সার্ভিস এলাকা')}</Typography>
        <List sx={{ maxHeight: 320, overflowY: 'auto' }}>
          {(zones || []).length === 0 && (
            <Typography variant="body2" color="text.secondary" sx={{ py: 2 }}>{t('No areas yet.', 'কোনো এলাকা নেই।')}</Typography>
          )}
          {(zones || []).map((z, i) => {
            const active = String(z.id) === String(zoneId);
            return (
              <Box key={z.id}>
                <ListItemButton onClick={() => pick(z.id)} sx={{ borderRadius: 2, py: 1.2 }}>
                  <PlaceRoundedIcon sx={{ mr: 1.5, color: active ? 'primary.main' : 'text.secondary' }} />
                  <Box sx={{ flex: 1 }}>
                    <Typography sx={{ fontWeight: active ? 800 : 600 }}>{lang === 'bn' && z.name_bn ? z.name_bn : z.name}</Typography>
                  </Box>
                  {active && <CheckCircleRoundedIcon color="primary" />}
                </ListItemButton>
                {i < zones.length - 1 && <Divider component="li" />}
              </Box>
            );
          })}
        </List>
      </Box>
    </Dialog>
  );
}
