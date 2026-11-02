import { useMemo, useState, useEffect } from 'react';
import {
  Dialog, Box, Typography, Stack, Button, IconButton, TextField, Autocomplete, Chip,
} from '@mui/material';
import CloseRoundedIcon from '@mui/icons-material/CloseRounded';
import MyLocationRoundedIcon from '@mui/icons-material/MyLocationRounded';
import PlaceRoundedIcon from '@mui/icons-material/PlaceRounded';
import RestartAltRoundedIcon from '@mui/icons-material/RestartAltRounded';
import { toast } from 'react-toastify';
import { useFoodLocation } from '../context/FoodLocationContext';
import MapPicker from './MapPicker';

export default function LocationPicker() {
  const {
    zones, zoneId, villageId, lang, setZoneId, setVillageId, coords, setCoords,
    detectLocation, pickerOpen, closePicker,
  } = useFoodLocation() || {};
  const t = (en, bn) => (lang === 'bn' ? bn : en);
  const zName = (z) => (lang === 'bn' && z?.name_bn ? z.name_bn : z?.name) || '';
  const vName = (v) => (lang === 'bn' && v?.name_bn ? v.name_bn : v?.name) || '';

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
      .then(({ coords: c, zone }) => {
        if (c) toast.success(t('Pin set to your location', 'পিন আপনার অবস্থানে সেট হয়েছে'));
        // detectLocation already resolves a serviceable zone when the pin lands in
        // one — mirror it into the draft, or Confirm would discard the match.
        if (zone) { setUnion(String(zone.id)); setVillage(''); }
      })
      .catch(() => toast.error(t('Could not get your location', 'অবস্থান পাওয়া যায়নি')));
  };

  const confirm = () => {
    if (!union) { toast.info(t('Pick your union first', 'প্রথমে আপনার ইউনিয়ন বেছে নিন')); return; }
    setZoneId(String(union));
    setVillageId(village || '');
    closePicker();
  };

  // Escape hatch for picking the wrong area. The map pin is deliberately kept:
  // it's an independent signal that's still useful (and fiddly to re-place), and
  // an area is no longer required to browse or reach checkout.
  const clearArea = () => {
    setUnion(''); setVillage('');
    setZoneId(''); setVillageId('');
    toast.info(t('Area cleared — showing all restaurants',
                 'এলাকা মুছে ফেলা হয়েছে — সব রেস্তোরাঁ দেখানো হচ্ছে'));
    closePicker();
  };

  // Both are Autocompletes so 13 unions and 121 villages stay typeable rather than
  // forcing a scroll through a long menu.
  const fields = (
    <Stack spacing={2}>
      <Autocomplete
        size="small" options={zones || []} getOptionLabel={zName} value={currentUnion}
        onChange={(_, z) => { setUnion(z ? String(z.id) : ''); setVillage(''); }}
        isOptionEqualToValue={(o, v) => o.id === v.id}
        noOptionsText={t('No areas found', 'কোনো এলাকা পাওয়া যায়নি')}
        renderInput={(params) => <TextField {...params} label={t('Union', 'ইউনিয়ন')}
          placeholder={t('Type to search…', 'খুঁজতে টাইপ করুন…')} />}
      />

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
        sx={{ borderRadius: 3, borderColor: 'divider', color: 'primary.main', justifyContent: 'flex-start', py: 1 }}>
        {t('Use my current location', 'আমার অবস্থান ব্যবহার করুন')}
      </Button>

      {currentUnion && (
        <Chip
          icon={<PlaceRoundedIcon />} variant="outlined" color="primary"
          sx={{ alignSelf: 'flex-start', maxWidth: '100%' }}
          label={selectedVillage ? `${vName(selectedVillage)} · ${zName(currentUnion)}` : zName(currentUnion)}
        />
      )}
    </Stack>
  );

  const map = (
    <Stack spacing={1}>
      {/* MapPicker puts `height` straight into a style prop, so '100%' only
          resolves against a parent with a real height — hence the fixed box. */}
      <Box sx={{ height: { xs: 190, md: 320 } }}>
        <MapPicker value={coords} onChange={setCoords} height="100%" />
      </Box>
      <Typography variant="caption" color="text.secondary">
        {coords?.lat
          ? t(`Pin: ${coords.lat.toFixed(4)}, ${coords.lng.toFixed(4)}`, `পিন: ${coords.lat.toFixed(4)}, ${coords.lng.toFixed(4)}`)
          : t('Tap the map to drop a delivery pin (optional).', 'ডেলিভারি পিন দিতে ম্যাপে ট্যাপ করুন (ঐচ্ছিক)।')}
      </Typography>
    </Stack>
  );

  return (
    <Dialog
      open={!!pickerOpen} onClose={closePicker} fullWidth maxWidth="md"
      // Bottom sheet on phones, centred two-column panel from md up. `maxWidth="xs"`
      // squeezed the fields and the map into a thin ribbon down the middle of a
      // desktop viewport.
      PaperProps={{ sx: {
        position: { xs: 'fixed', sm: 'static' }, bottom: { xs: 0, sm: 'auto' },
        m: { xs: 0, sm: 4 }, width: { xs: '100%', sm: 'auto' },
        maxWidth: { sm: 560, md: 900 },
        borderRadius: { xs: '24px 24px 0 0', sm: 6 },
      } }}
    >
      <Box sx={{ p: { xs: 2.5, md: 3.5 } }}>
        <Stack direction="row" justifyContent="space-between" alignItems="flex-start" sx={{ mb: 2.5 }}>
          <Box>
            <Typography variant="h6">{t('Deliver to', 'ডেলিভারি এলাকা')}</Typography>
            <Typography variant="body2" color="text.secondary">
              {t('We deliver across Bancharampur. Pick your village, then drop a pin on your house.',
                 'আমরা বাঞ্ছারামপুর জুড়ে ডেলিভারি করি। আপনার গ্রাম বেছে নিন, তারপর বাড়ির উপর পিন দিন।')}
            </Typography>
          </Box>
          <IconButton onClick={closePicker} size="small" sx={{ ml: 1 }}><CloseRoundedIcon /></IconButton>
        </Stack>

        <Box sx={{
          display: 'grid', gap: { xs: 2, md: 3 },
          gridTemplateColumns: { xs: '1fr', md: 'minmax(260px, 5fr) 7fr' },
          alignItems: 'start',
        }}>
          <Box>{fields}</Box>
          <Box>{map}</Box>
        </Box>

        <Stack direction={{ xs: 'column-reverse', md: 'row' }} spacing={1.5}
               justifyContent="flex-end" alignItems={{ md: 'center' }} sx={{ mt: 3 }}>
          {/* Only offered once an area is actually set — nothing to clear otherwise. */}
          {zoneId && (
            <Button onClick={clearArea} startIcon={<RestartAltRoundedIcon />}
                    sx={{ borderRadius: 999, px: 3, color: 'text.secondary', mr: { md: 'auto' } }}>
              {t('Clear area', 'এলাকা মুছুন')}
            </Button>
          )}
          <Button onClick={closePicker} sx={{ borderRadius: 999, px: 3, color: 'text.secondary' }}>
            {t('Cancel', 'বাতিল')}
          </Button>
          <Button variant="contained" onClick={confirm} disabled={!union}
                  sx={{ borderRadius: 999, px: 4, py: 1.2, minWidth: { md: 200 } }}>
            {t('Confirm area', 'এলাকা নিশ্চিত করুন')}
          </Button>
        </Stack>
      </Box>
    </Dialog>
  );
}
