import React, { useEffect, useState } from 'react';
import { Box, Typography, Tabs, Tab } from '@mui/material';
import { Link } from 'react-router-dom';
import { fetchPopular, fetchSection } from '../api';
import { HorizontalCard, TextOnlyItem } from './NewsCards';
import { NS_ACCENT } from '../portal/PortalHeader';

// Tabbed sidebar: সর্বাধিক পঠিত (by views) / সর্বশেষ.
export default function MostRead({ latest = [] }) {
  const [tab, setTab] = useState(0);
  const [popular, setPopular] = useState([]);

  useEffect(() => {
    fetchPopular(5).then(setPopular).catch(() => {});
  }, []);

  return (
    <Box sx={{ border: '1px solid #e8e8e8', borderRadius: 2, overflow: 'hidden', bgcolor: 'white' }}>
      <Tabs value={tab} onChange={(_, v) => setTab(v)} variant="fullWidth" sx={{ '& .MuiTab-root': { fontWeight: 800, fontSize: 14 }, '& .Mui-selected': { color: NS_ACCENT }, '& .MuiTabs-indicator': { backgroundColor: NS_ACCENT } }}>
        <Tab label="সর্বাধিক পঠিত" className="ns-sans" />
        <Tab label="সর্বশেষ" className="ns-sans" />
      </Tabs>
      <Box sx={{ px: 1.5, pb: 1 }}>
        {tab === 0
          ? popular.map((a, i) => <TextOnlyItem key={a.id || a.slug} article={a} rank={i + 1} />)
          : (latest.length ? latest : popular).slice(0, 5).map((a) => <HorizontalCard key={a.id || a.slug} article={a} thumb={88} />)}
        {!popular.length && tab === 0 && (
          <Typography variant="body2" color="text.secondary" sx={{ py: 2, textAlign: 'center' }} className="ns-sans">শীঘ্রই আসছে</Typography>
        )}
      </Box>
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
