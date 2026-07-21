import { useMemo, useState, useEffect } from 'react';
import {
  Dialog, Box, Typography, Stack, Button, IconButton, TextField, MenuItem, Autocomplete, Divider,
} from '@mui/material';
import CloseRoundedIcon from '@mui/icons-material/CloseRounded';
import MyLocationRoundedIcon from '@mui/icons-material/MyLocationRounded';
import { toast } from 'react-toastify';
import { useFoodLocation } from '../context/FoodLocationContext';
import MapPicker from './MapPicker';
import { FOOD } from '../theme';

export default function LocationPicker() {
  const {
    zones, zoneId, villageId, lang, setZoneId, setVillageId, coords, setCoords,
    detectLocation, pickerOpen, closePicker,
  } = useFoodLocation() || {};
  const t = (en, bn) => (lang === 'bn' ? bn : en);
  const zName = (z) => (lang === 'bn' && z?.name_bn ? z.name_bn : z?.name);
  const vName = (v) => (lang === 'bn' && v?.name_bn ? v.name_bn : v?.name);

  // Local draft so the sheet only commits on "Confirm".
  const [union, setUnion] = useState(zoneId || '');
  const [village, setVillage] = useState(villageId || '');
  useEffect(() => { if (pickerOpen) { setUnion(zoneId || ''); setVillage(villageId || ''); } }, [pickerOpen, zoneId, villageId]);

  const currentUnion = useMemo(
    () => (zones || []).find((z) => String(z.id) === String(union)) || null, [zones, union]);
  const villageOptions = currentUnion?.villages || [];
  const selectedVillage = villageOptions.find((v) => String(v.id) === String(village)) || null;

  const useLocation = () => {
    detectLocation()
      .then(({ coords: c }) => {
        if (c) { setCoords(c); toast.success(t('Pin set to your location', 'পিন আপনার অবস্থানে সেট হয়েছে')); }
      })
      .catch(() => toast.error(t('Could not get your location', 'অবস্থান পাওয়া যায়নি')));
  };

  const confirm = () => {
    if (!union) { toast.info(t('Pick your union first', 'প্রথমে আপনার ইউনিয়ন বেছে নিন')); return; }
    setZoneId(String(union));
    setVillageId(village || '');
    closePicker();
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
          {t('We deliver across Bancharampur. Pick your village, then drop a pin on your house.',
             'আমরা বাঞ্ছারামপুর জুড়ে ডেলিভারি করি। আপনার গ্রাম বেছে নিন, তারপর বাড়ির উপর পিন দিন।')}
        </Typography>

        <Stack spacing={2}>
          <TextField select fullWidth size="small" label={t('Union', 'ইউনিয়ন')}
            value={union} onChange={(e) => { setUnion(e.target.value); setVillage(''); }}>
            <MenuItem value=""><em>{t('Select union', 'ইউনিয়ন বেছে নিন')}</em></MenuItem>
            {(zones || []).map((z) => <MenuItem key={z.id} value={String(z.id)}>{zName(z)}</MenuItem>)}
          </TextField>

          <Autocomplete
            size="small" disabled={!currentUnion} options={villageOptions}
            getOptionLabel={vName} value={selectedVillage}
            onChange={(_, v) => setVillage(v ? String(v.id) : '')}
            isOptionEqualToValue={(o, v) => o.id === v.id}
            noOptionsText={t('No villages', 'কোনো গ্রাম নেই')}
            renderInput={(params) => <TextField {...params} label={t('Village', 'গ্রাম')}
              placeholder={t('Search your village…', 'আপনার গ্রাম খুঁজুন…')} />}
          />

          <Button fullWidth variant="outlined" startIcon={<MyLocationRoundedIcon />} onClick={useLocation}
            sx={{ borderRadius: 3, borderColor: FOOD.line, color: 'primary.main', justifyContent: 'flex-start', py: 1 }}>
            {t('Use my current location', 'আমার অবস্থান ব্যবহার করুন')}
          </Button>

          <MapPicker value={coords} onChange={setCoords} height={200} />
          <Typography variant="caption" color="text.secondary">
            {coords?.lat
              ? t(`Pin: ${coords.lat.toFixed(4)}, ${coords.lng.toFixed(4)}`, `পিন: ${coords.lat.toFixed(4)}, ${coords.lng.toFixed(4)}`)
              : t('Tap the map to drop a delivery pin (optional).', 'ডেলিভারি পিন দিতে ম্যাপে ট্যাপ করুন (ঐচ্ছিক)।')}
          </Typography>
        </Stack>

        <Divider sx={{ my: 2 }} />
        <Button fullWidth variant="contained" onClick={confirm} sx={{ borderRadius: 999, py: 1.2 }}>
          {t('Confirm area', 'এলাকা নিশ্চিত করুন')}
        </Button>
      </Box>
    </Dialog>
  );
}
