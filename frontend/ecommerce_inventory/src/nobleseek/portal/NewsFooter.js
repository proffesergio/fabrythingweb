import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { Box, Container, Typography, Divider, IconButton } from '@mui/material';
import { Facebook, Twitter, YouTube } from '@mui/icons-material';
import { fetchNewsCategories, PORTAL_SECTIONS } from '../api';
import { MastheadLogo, NS_NAVY } from './PortalHeader';

const TRUST = [
  ['আমাদের সম্পর্কে', '/nobleseek/about'],
  ['যোগাযোগ', '/nobleseek/contact'],
  ['গোপনীয়তা নীতি', '/nobleseek/privacy'],
  ['ডিসক্লেইমার', '/nobleseek/disclaimer'],
  ['সম্পাদকীয় নীতি', '/nobleseek/ethics'],
];

export default function NewsFooter() {
  const [cats, setCats] = useState([]);
  useEffect(() => {
    fetchNewsCategories().then((c) => { if (Array.isArray(c) && c.length) setCats(c); }).catch(() => {});
  }, []);
  const sections = (cats.length ? cats : PORTAL_SECTIONS).filter((c) => c.slug && (c.is_active !== false));

  return (
    <Box sx={{ bgcolor: NS_NAVY, color: 'rgba(255,255,255,0.72)', mt: 7 }}>
      <Container maxWidth="lg" sx={{ py: 5 }}>
        <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 4, justifyContent: 'space-between' }}>
          <Box sx={{ maxWidth: 330 }}>
            <MastheadLogo height={46} light />
            <Typography variant="body2" sx={{ mt: 1.5, lineHeight: 1.8 }} className="ns-sans">
              দেশ-বিদেশের সর্বশেষ সংবাদ, বিশ্লেষণ ও মতামত — যাচাই করা তথ্য, দ্রুত পরিবেশন।
            </Typography>
            <Box sx={{ display: 'flex', gap: 0.5, mt: 1.5 }}>
              <IconButton component="a" href="https://www.facebook.com/" target="_blank" rel="noreferrer" size="small" sx={{ color: 'inherit', border: '1px solid rgba(255,255,255,0.25)' }} aria-label="Facebook"><Facebook fontSize="small" /></IconButton>
              <IconButton component="a" href="https://x.com/" target="_blank" rel="noreferrer" size="small" sx={{ color: 'inherit', border: '1px solid rgba(255,255,255,0.25)' }} aria-label="X"><Twitter fontSize="small" /></IconButton>
              <IconButton component="a" href="https://www.youtube.com/" target="_blank" rel="noreferrer" size="small" sx={{ color: 'inherit', border: '1px solid rgba(255,255,255,0.25)' }} aria-label="YouTube"><YouTube fontSize="small" /></IconButton>
            </Box>
          </Box>
          <Box>
            <Typography variant="subtitle2" fontWeight={800} sx={{ color: 'white', mb: 1.2 }} className="ns-sans">বিভাগসমূহ</Typography>
            {sections.slice(0, 8).map((c) => (
              <Typography key={c.slug} component={Link} to={`/nobleseek?category=${c.slug}`} variant="body2" sx={{ display: 'block', color: 'inherit', textDecoration: 'none', py: 0.3, '&:hover': { color: 'white' } }} className="ns-sans">{c.name}</Typography>
            ))}
          </Box>
          <Box>
            <Typography variant="subtitle2" fontWeight={800} sx={{ color: 'white', mb: 1.2 }} className="ns-sans">আরও পড়ুন</Typography>
            {sections.slice(8).map((c) => (
              <Typography key={c.slug} component={Link} to={`/nobleseek?category=${c.slug}`} variant="body2" sx={{ display: 'block', color: 'inherit', textDecoration: 'none', py: 0.3, '&:hover': { color: 'white' } }} className="ns-sans">{c.name}</Typography>
            ))}
            {TRUST.map(([label, to]) => (
              <Typography key={to} component={Link} to={to} variant="body2" sx={{ display: 'block', color: 'inherit', textDecoration: 'none', py: 0.3, '&:hover': { color: 'white' } }} className="ns-sans">{label}</Typography>
            ))}
          </Box>
          <Box sx={{ maxWidth: 260 }}>
            <Typography variant="subtitle2" fontWeight={800} sx={{ color: 'white', mb: 1.2 }} className="ns-sans">যোগাযোগ</Typography>
            <Typography variant="body2" className="ns-sans">নোবেলসিক নিউজরুম<br />ঢাকা, বাংলাদেশ</Typography>
            <Typography variant="body2" sx={{ mt: 1 }} className="ns-sans">support@fabrything.com<br />+880 1842-168117</Typography>
            <Typography variant="body2" sx={{ mt: 1.5 }} className="ns-sans">সম্পাদক: নোবেলসিক সম্পাদনা পর্ষদ</Typography>
          </Box>
        </Box>
        <Divider sx={{ my: 2.5, borderColor: 'rgba(255,255,255,0.12)' }} />
        <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1, justifyContent: 'space-between', alignItems: 'center' }}>
          <Typography variant="caption" className="ns-sans">© {new Date().getFullYear()} নোবেলসিক • সর্বস্বত্ব সংরক্ষিত</Typography>
          <Typography variant="caption" className="ns-sans">ভুল সংশোধন: support@fabrything.com — ২৪ ঘণ্টার মধ্যে আপডেট</Typography>
        </Box>
      </Container>
    </Box>
  );
}
