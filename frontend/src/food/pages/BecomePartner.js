import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Box, Typography, TextField, Button, Card, Stack, Grid, Alert, MenuItem, Chip,
} from '@mui/material';
import StorefrontRoundedIcon from '@mui/icons-material/StorefrontRounded';
import CheckCircleRoundedIcon from '@mui/icons-material/CheckCircleRounded';
import { motion } from 'framer-motion';
import useApi from '../../hooks/APIHandler';
import { useFoodLocation } from '../context/FoodLocationContext';

const rise = { initial: { opacity: 0, y: 14 }, animate: { opacity: 1, y: 0 } };

// Bilingual throughout: the people this page is for — shop owners in
// Bancharampur — are far likelier to read Bangla than English, and this is the
// one page where losing them costs the platform a partner.
const T = {
  title: { en: 'Become a Partner', bn: 'পার্টনার হোন' },
  lead: {
    en: 'List your restaurant on Fabrything Food and start taking orders from your area.',
    bn: 'আপনার রেস্তোরাঁ ফেব্রিথিং ফুডে যুক্ত করুন এবং আপনার এলাকা থেকে অর্ডার নেওয়া শুরু করুন।',
  },
  benefits: {
    en: ['No setup fee', 'You control your menu and prices', 'Riders and delivery handled for you'],
    bn: ['কোনো সেটআপ ফি নেই', 'মেনু ও দাম আপনার নিয়ন্ত্রণে', 'রাইডার ও ডেলিভারি আমাদের দায়িত্বে'],
  },
  restaurant: { en: 'Restaurant name', bn: 'রেস্তোরাঁর নাম' },
  restaurantBn: { en: 'Restaurant name in Bangla (optional)', bn: 'রেস্তোরাঁর নাম (বাংলায়)' },
  owner: { en: 'Your name', bn: 'আপনার নাম' },
  phone: { en: 'Phone number', bn: 'মোবাইল নম্বর' },
  email: { en: 'Email', bn: 'ইমেইল' },
  password: { en: 'Choose a password', bn: 'একটি পাসওয়ার্ড দিন' },
  address: { en: 'Restaurant address', bn: 'রেস্তোরাঁর ঠিকানা' },
  cuisine: { en: 'Type of food (e.g. Bengali, Fast Food)', bn: 'খাবারের ধরন (যেমন বাঙালি, ফাস্ট ফুড)' },
  zone: { en: 'Which area are you in?', bn: 'আপনি কোন এলাকায়?' },
  submit: { en: 'Submit application', bn: 'আবেদন জমা দিন' },
  submitting: { en: 'Submitting…', bn: 'জমা হচ্ছে…' },
  doneTitle: { en: 'Application received 🎉', bn: 'আবেদন জমা হয়েছে 🎉' },
  doneBody: {
    en: 'We will review it shortly. Meanwhile you can sign in and start building your menu — customers will see you as soon as you are approved.',
    bn: 'আমরা শীঘ্রই এটি পর্যালোচনা করব। এর মধ্যে আপনি সাইন ইন করে আপনার মেনু তৈরি শুরু করতে পারেন — অনুমোদনের সাথে সাথেই গ্রাহকরা আপনাকে দেখতে পাবেন।',
  },
  goPanel: { en: 'Open my restaurant panel', bn: 'আমার রেস্তোরাঁ প্যানেল খুলুন' },
};

export default function BecomePartner() {
  const { lang, zones } = useFoodLocation() || {};
  const t = (key) => T[key][lang === 'bn' ? 'bn' : 'en'];
  const { callApi, loading } = useApi();
  const navigate = useNavigate();
  const [form, setForm] = useState({
    name: '', name_bn: '', owner_name: '', phone: '', email: '', password: '',
    address: '', cuisine_type: '', zone_id: '',
  });
  // Field-keyed, because the server answers with `field_errors` and a message
  // under the wrong input is worse than no message at all.
  const [errors, setErrors] = useState({});
  const [done, setDone] = useState(null);

  const set = (k) => (e) => setForm((f) => ({ ...f, [k]: e.target.value }));

  const submit = async () => {
    setErrors({});
    const body = { ...form, zone_ids: form.zone_id ? [form.zone_id] : [] };
    // rawError, or callApi returns null on the 400 and the form has nothing to
    // show — the "silent empty state hiding a real error" trap.
    const res = await callApi({ url: 'food/partner/apply/', method: 'POST', body,
      silent: true, rawError: true });
    if (res?.status === 201) { setDone(res.data.data); return; }
    const fieldErrors = res?.data?.field_errors;
    if (fieldErrors) {
      setErrors(Object.fromEntries(
        Object.entries(fieldErrors).map(([k, v]) => [k, Array.isArray(v) ? v[0] : String(v)])));
    } else {
      setErrors({ _: res?.data?.errors?.[0] || res?.data?.message || 'Something went wrong.' });
    }
  };

  if (done) {
    // The application is worth something immediately: the owner is already
    // signed in and can build a menu while they wait for approval.
    localStorage.setItem('token', done.access);
    return (
      <Box sx={{ maxWidth: 560, mx: 'auto', textAlign: 'center', py: 6 }}>
        <CheckCircleRoundedIcon color="success" sx={{ fontSize: 64, mb: 2 }} />
        <Typography variant="h4" sx={{ mb: 1 }}>{t('doneTitle')}</Typography>
        <Typography color="text.secondary" sx={{ mb: 3 }}>{t('doneBody')}</Typography>
        <Button variant="contained" size="large" sx={{ borderRadius: 999 }}
          onClick={() => navigate('/vendor')}>
          {t('goPanel')}
        </Button>
      </Box>
    );
  }

  return (
    <Box sx={{ maxWidth: 720, mx: 'auto' }}>
      <Box component={motion.div} {...rise} sx={{ textAlign: 'center', mb: 3 }}>
        <StorefrontRoundedIcon color="primary" sx={{ fontSize: 48 }} />
        <Typography variant="h4" sx={{ mt: 1 }}>{t('title')}</Typography>
        <Typography color="text.secondary" sx={{ mt: 1 }}>{t('lead')}</Typography>
        <Stack direction="row" spacing={1} justifyContent="center" sx={{ mt: 2, flexWrap: 'wrap', gap: 1 }}>
          {T.benefits[lang === 'bn' ? 'bn' : 'en'].map((b) => (
            <Chip key={b} label={b} variant="outlined" sx={{ fontWeight: 700 }} />
          ))}
        </Stack>
      </Box>

      <Card component={motion.div} {...rise} transition={{ delay: 0.08 }} sx={{ p: { xs: 2, sm: 3 } }}>
        {errors._ && <Alert severity="error" sx={{ mb: 2 }}>{errors._}</Alert>}
        <Grid container spacing={2}>
          <Grid item xs={12} sm={6}>
            <TextField label={t('restaurant')} value={form.name} onChange={set('name')} fullWidth
              required error={!!errors.name} helperText={errors.name} />
          </Grid>
          <Grid item xs={12} sm={6}>
            <TextField label={t('restaurantBn')} value={form.name_bn} onChange={set('name_bn')} fullWidth />
          </Grid>
          <Grid item xs={12} sm={6}>
            <TextField label={t('owner')} value={form.owner_name} onChange={set('owner_name')} fullWidth
              required error={!!errors.owner_name} helperText={errors.owner_name} />
          </Grid>
          <Grid item xs={12} sm={6}>
            <TextField label={t('phone')} value={form.phone} onChange={set('phone')} fullWidth
              required error={!!errors.phone} helperText={errors.phone} />
          </Grid>
          <Grid item xs={12} sm={6}>
            <TextField label={t('email')} type="email" value={form.email} onChange={set('email')} fullWidth
              required error={!!errors.email} helperText={errors.email} />
          </Grid>
          <Grid item xs={12} sm={6}>
            <TextField label={t('password')} type="password" value={form.password} onChange={set('password')}
              fullWidth required error={!!errors.password} helperText={errors.password} />
          </Grid>
          <Grid item xs={12}>
            <TextField label={t('address')} value={form.address} onChange={set('address')} fullWidth
              multiline rows={2} error={!!errors.address} helperText={errors.address} />
          </Grid>
          <Grid item xs={12} sm={6}>
            <TextField label={t('cuisine')} value={form.cuisine_type} onChange={set('cuisine_type')} fullWidth />
          </Grid>
          <Grid item xs={12} sm={6}>
            <TextField select label={t('zone')} value={form.zone_id} onChange={set('zone_id')} fullWidth>
              {(zones || []).map((z) => (
                <MenuItem key={z.id} value={z.id}>{z.display_name || z.name}</MenuItem>
              ))}
            </TextField>
          </Grid>
        </Grid>

        <Button
          fullWidth variant="contained" size="large" onClick={submit} disabled={loading}
          sx={{ mt: 3, py: 1.5, borderRadius: 999 }}
        >
          {loading ? t('submitting') : t('submit')}
        </Button>
      </Card>
    </Box>
  );
}
