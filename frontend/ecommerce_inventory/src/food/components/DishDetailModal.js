import { useEffect, useState } from 'react';
import { Box, Button, Chip, Dialog, DialogContent, IconButton, Stack, Typography } from '@mui/material';
import CloseRoundedIcon from '@mui/icons-material/CloseRounded';
import AddRoundedIcon from '@mui/icons-material/AddRounded';
import RemoveRoundedIcon from '@mui/icons-material/RemoveRounded';
import AccessTimeRoundedIcon from '@mui/icons-material/AccessTimeRounded';
import { FOOD } from '../theme';
import { dayName } from '../utils/hours';

const TAG_META = {
  spicy: { label: 'Spicy', bn: 'ঝাল', emoji: '🌶️' }, new: { label: 'New', bn: 'নতুন', emoji: '✨' },
  popular: { label: 'Popular', bn: 'জনপ্রিয়', emoji: '🔥' }, veg: { label: 'Veg', bn: 'ভেজ', emoji: '🌱' },
  bestseller: { label: 'Bestseller', bn: 'বেস্টসেলার', emoji: '⭐' },
};
const t = (en, bn, lang) => (lang === 'bn' ? bn : en);
const fmt = (v) => (v ? String(v).slice(0, 5) : '');

// Full dish story: photo, complete description, tags, spice/prep/availability,
// quantity + add. Choice-based customization still lives in ItemOptionModal —
// this sheet's button opens it (options) or adds directly (no options).
export default function DishDetailModal({ open, item, restaurantClosed, lang = 'en', onClose, onCustomize, onAdd }) {
  const [qty, setQty] = useState(1);
  useEffect(() => { if (open) setQty(1); }, [open, item && item.id]);

  if (!item) return null;
  const hasOptions = item.option_groups && item.option_groups.length > 0;
  const tags = (item.tags || []).filter((k) => TAG_META[k]);
  const price = Number(item.effective_price ?? item.price);
  const off = item.available_now === false || restaurantClosed;

  const primary = () => {
    if (off) return;
    if (hasOptions) onCustomize(item);
    else onAdd(qty);
  };

  return (
    <Dialog open={open} onClose={onClose} fullWidth maxWidth="sm" scroll="body">
      <Box sx={{ position: 'relative' }}>
        <Box sx={{ position: 'relative', pt: '56%' }}>
          <Box sx={{ position: 'absolute', inset: 0, background: item.image ? undefined : 'radial-gradient(120% 120% at 30% 0%, #FFE7C2, #F7B27A)' }}>
            {item.image
              ? <Box component="img" src={item.image} alt={item.display_name} sx={{ width: '100%', height: '100%', objectFit: 'cover' }} />
              : <Box sx={{ width: '100%', height: '100%', display: 'grid', placeItems: 'center', fontSize: 72 }}>🍽️</Box>}
          </Box>
          <IconButton onClick={onClose} aria-label="Close"
            sx={{ position: 'absolute', top: 8, right: 8, bgcolor: 'rgba(0,0,0,0.5)', color: '#fff', '&:hover': { bgcolor: 'rgba(0,0,0,0.65)' } }}>
            <CloseRoundedIcon />
          </IconButton>
          {item.discount_price && (
            <Chip size="small" label={`${t('Deal', 'অফার', lang)} · ৳${item.discount_price}`}
              sx={{ position: 'absolute', bottom: 10, left: 10, bgcolor: FOOD.turmeric, color: '#3A2A05', fontWeight: 800 }} />
          )}
        </Box>
        <DialogContent sx={{ pt: 2 }}>
          <Stack direction="row" spacing={1} alignItems="center" sx={{ mb: 0.5 }}>
            <Typography variant="h5" sx={{ fontWeight: 900, flex: 1 }}>{item.display_name}</Typography>
          </Stack>
          <Typography variant="h6" sx={{ fontWeight: 800, color: 'primary.main', mb: 1 }}>৳{price}</Typography>

          {tags.length > 0 && (
            <Stack direction="row" spacing={0.5} sx={{ mb: 1.5, flexWrap: 'wrap', gap: 0.5 }}>
              {tags.map((k) => (
                <Chip key={k} size="small" label={`${TAG_META[k].emoji} ${t(TAG_META[k].label, TAG_META[k].bn, lang)}`}
                  sx={{ bgcolor: 'rgba(244,166,42,0.16)', color: '#7a5310', fontWeight: 700 }} />
              ))}
              {item.is_veg && <Chip size="small" label={t('Veg', 'ভেজ', lang)} variant="outlined" color="success" />}
              {item.is_featured && <Chip size="small" label={t("Chef's pick", 'শেফের পছন্দ', lang)} variant="outlined" />}
            </Stack>
          )}

          {item.description ? (
            <Typography variant="body1" color="text.secondary" sx={{ mb: 2, lineHeight: 1.75 }}>{item.description}</Typography>
          ) : (
            <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
              {t('No description yet — ask the restaurant if you need details.', 'বিবরণ নেই — প্রয়োজনে রেস্তোরাঁকে জিজ্ঞেস করুন।', lang)}
            </Typography>
          )}

          <Stack spacing={0.75} sx={{ mb: 2 }}>
            {item.spice_level && (
              <Typography variant="body2">🌶️ {t('Spice', 'ঝাল', lang)}: <strong>{item.spice_level}</strong></Typography>
            )}
            {item.prep_minutes != null && (
              <Typography variant="body2">⏱️ {t('Ready in about', 'প্রস্তুত হতে প্রায়', lang)} <strong>{item.prep_minutes} {t('min', 'মিনিট', lang)}</strong></Typography>
            )}
            {item.available_from && (
              <Typography variant="body2" sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                <AccessTimeRoundedIcon fontSize="small" />
                {fmt(item.available_from)}–{fmt(item.available_to)}
                {(item.available_days || []).length > 0 && (
                  <> · {(item.available_days || []).map((d) => dayName(d, lang)).join(', ')}</>
                )}
              </Typography>
            )}
            {hasOptions && (
              <Typography variant="body2" color="text.secondary">
                ✨ {t(
                  `${item.option_groups.length} customization group(s) — choose on the next step.`,
                  `${item.option_groups.length}টি কাস্টমাইজেশন গ্রুপ — পরের ধাপে বেছে নিন।`, lang)}
              </Typography>
            )}
          </Stack>

          {off ? (
            <Button fullWidth disabled variant="contained" sx={{ borderRadius: 999, py: 1.25 }}>
              {restaurantClosed ? t('Restaurant closed', 'রেস্তোরাঁ বন্ধ', lang) : t('Unavailable now', 'এখন পাওয়া যাচ্ছে না', lang)}
            </Button>
          ) : (
            <Stack direction="row" spacing={1.5} alignItems="center">
              {!hasOptions && (
                <Stack direction="row" alignItems="center" sx={{ border: 1, borderColor: 'divider', borderRadius: 999, px: 0.5 }}>
                  <IconButton size="small" onClick={() => setQty((q) => Math.max(1, q - 1))} aria-label="Decrease"><RemoveRoundedIcon /></IconButton>
                  <Typography sx={{ minWidth: 28, textAlign: 'center', fontWeight: 800 }}>{qty}</Typography>
                  <IconButton size="small" onClick={() => setQty((q) => Math.min(20, q + 1))} aria-label="Increase"><AddRoundedIcon /></IconButton>
                </Stack>
              )}
              <Button fullWidth variant="contained" size="large" startIcon={<AddRoundedIcon />}
                onClick={primary} sx={{ borderRadius: 999, py: 1.25 }}>
                {hasOptions
                  ? t(`Customize · ৳${price}`, `কাস্টমাইজ · ৳${price}`, lang)
                  : t(`Add · ৳${price * qty}`, `যোগ করুন · ৳${price * qty}`, lang)}
              </Button>
            </Stack>
          )}
        </DialogContent>
      </Box>
    </Dialog>
  );
}
