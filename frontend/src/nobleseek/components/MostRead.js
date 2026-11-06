import React, { useEffect, useId, useState } from 'react';
import { Box, Typography, Tabs, Tab } from '@mui/material';
import { Link } from 'react-router-dom';
import { fetchPopular, fetchSection } from '../api';
import { TextOnlyItem } from './NewsCards';
import { NS_ACCENT } from '../portal/PortalHeader';

// Each tab keeps its own API ordering; empty latest never substitutes popularity.
export default function MostRead({ latest = [] }) {
  const [tab, setTab] = useState(0);
  const [popular, setPopular] = useState([]);
  const [loading, setLoading] = useState(true);
  const id = useId();
  useEffect(() => {
    let live = true;
    fetchPopular(5).then((items) => { if (live) setPopular(Array.isArray(items) ? items : []); })
      .catch(() => {}).finally(() => { if (live) setLoading(false); });
    return () => { live = false; };
  }, []);
  const items = (tab === 0 ? latest : popular).slice(0, 5);
  return (
    <Box sx={{ borderTop: '3px solid #00141A', bgcolor: '#FEFEFE', minWidth: 0 }}>
      <Tabs aria-label="সংবাদ তালিকা" value={tab} onChange={(_, value) => setTab(value)} variant="fullWidth" sx={{ bgcolor: '#00141A', '& .MuiTab-root': { color: '#c6ced8', fontWeight: 700, fontSize: 16, minWidth: 0, px: 1 }, '& .Mui-selected': { color: '#fff !important' }, '& .MuiTabs-indicator': { backgroundColor: '#fff' } }}>
        {['সর্বশেষ', 'সর্বাধিক পঠিত'].map((label, index) => <Tab key={label} id={`${id}-tab-${index}`} aria-controls={`${id}-panel-${index}`} label={label} className="ns-sans" />)}
      </Tabs>
      <Box role="tabpanel" id={`${id}-panel-${tab}`} aria-labelledby={`${id}-tab-${tab}`} sx={{ px: 1, pt: 1 }}>
        {items.map((article, index) => <TextOnlyItem key={article.id || article.slug} article={article} rank={index + 1} />)}
        {!items.length && <Typography role="status" className="ns-sans" sx={{ py: 3, color: '#475467' }}>{tab === 1 && loading ? 'লোড হচ্ছে…' : 'কোনো খবর পাওয়া যায়নি'}</Typography>}
      </Box>
    </Box>
  );
}

export function FacebookFollow() {
  return (
    <Box sx={{ bgcolor: '#F5F8FA', border: '1px solid #E8E8E8', p: 3, textAlign: 'center' }}>
      <Typography className="ns-serif" sx={{ color: '#040D33', fontSize: 18, fontWeight: 700, mb: 2 }}>সত্যের পথে, সবসময়</Typography>
      <Box component="a" href="https://www.facebook.com/nobleseek" target="_blank" rel="noopener noreferrer" className="ns-sans" sx={{ display: 'block', bgcolor: '#1877F2', color: '#fff', py: 1.25, px: 2, fontWeight: 700, textDecoration: 'none', '&:hover': { bgcolor: '#166FE5' } }}>ফেসবুকে আমাদের অনুসরণ করুন</Box>
    </Box>
  );
}

// Homepage opinion column: মতামত section picks + link.
export function OpinionBox() {
  const [items, setItems] = useState([]);
  useEffect(() => {
    fetchSection('opinion', 3).then(setItems).catch(() => {});
  }, []);
  if (!items.length) return null;
  return (
    <Box sx={{ border: '1px solid #e8e8e8', borderRadius: 2, bgcolor: '#fffdf5', p: 2, height: '100%' }}>
      <Typography variant="subtitle1" fontWeight={900} className="ns-serif" sx={{ mb: 0.5 }}>
        মতামত
      </Typography>
      <Typography variant="caption" color="text.secondary" className="ns-sans">বিশ্লেষণ ও সম্পাদকীয়</Typography>
      <Box sx={{ mt: 1 }}>
        {items.map((a) => (
          <Box key={a.id || a.slug} component={Link} to={`/nobleseek/${a.slug}`} sx={{ display: 'block', textDecoration: 'none', color: 'inherit', py: 1, borderTop: '1px solid #f0e8d8' }}>
            <Typography variant="body2" fontWeight={700} className="ns-serif ns-clamp-3" sx={{ lineHeight: 1.6 }}>
              {a.headline_bn || a.headline}
            </Typography>
          </Box>
        ))}
      </Box>
      <Typography component={Link} to="/nobleseek?category=opinion" variant="body2" fontWeight={800} sx={{ color: NS_ACCENT, textDecoration: 'none' }} className="ns-sans">
        সব মতামত →
      </Typography>
    </Box>
  );
}
