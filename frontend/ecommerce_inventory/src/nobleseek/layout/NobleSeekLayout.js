import React from 'react';
import { Outlet, Link, useNavigate } from 'react-router-dom';
import { AppBar, Toolbar, Box, Container, Typography, Button, Divider, IconButton } from '@mui/material';
import { Facebook, ArrowBack } from '@mui/icons-material';
import BrandLogo from '../../components/BrandLogo';

// Lightweight NobleSeek shell — NO cart/Redux/MegaMenu/chat widgets, so
// FB-clicked readers get first paint fast. Dedicated footer as requested.
export default function NobleSeekLayout() {
  const navigate = useNavigate();
  return (
    <Box sx={{ minHeight: '100vh', display: 'flex', flexDirection: 'column', bgcolor: '#f8fafc' }}>
      <Box sx={{ bgcolor: '#0f172a', color: 'white', py: 0.5, textAlign: 'center', fontSize: 12 }}>
        NobleSeek by Fabrything — Google Trends ভিত্তিক প্রতিদিনের খবর
      </Box>
      <AppBar position="sticky" elevation={1} sx={{ bgcolor: 'white', color: '#0f172a' }}>
        <Toolbar sx={{ gap: 1.5 }}>
          <IconButton size="small" onClick={() => navigate(-1)} aria-label="Back"><ArrowBack /></IconButton>
          <Box component={Link} to="/nobleseek" sx={{ display: 'flex', alignItems: 'center', textDecoration: 'none', color: 'inherit' }}>
            <BrandLogo brand="fabrything" variant="horizontal" mode="light" height={24} />
            <Typography variant="h6" fontWeight={900} sx={{ ml: 1 }}>NobleSeek</Typography>
          </Box>
          <Box sx={{ flex: 1 }} />
          <Button component={Link} to="/nobleseek" size="small">Latest</Button>
          <Button component={Link} to="/shop" size="small" variant="contained" color="secondary">Shop</Button>
          <IconButton component="a" href="https://www.facebook.com/" target="_blank" rel="noreferrer" size="small" aria-label="NobleSeek Facebook"><Facebook /></IconButton>
        </Toolbar>
      </AppBar>
      <Box sx={{ flex: 1 }}>
        <Outlet />
      </Box>
      <Box sx={{ bgcolor: '#0f172a', color: 'rgba(255,255,255,0.75)', mt: 6, pt: 5, pb: 3 }}>
        <Container maxWidth="lg">
          <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 4, justifyContent: 'space-between' }}>
            <Box sx={{ maxWidth: 340 }}>
              <Typography variant="h6" fontWeight={900} sx={{ color: 'white' }}>NobleSeek</Typography>
              <Typography variant="body2" sx={{ mt: 1 }}>
                Trends-driven Bangla news desk by Fabrything. Viral headlines from Google Trends,
                human-written 800+ word reports, 1 verified image per story.
              </Typography>
              <Typography variant="caption" sx={{ display: 'block', mt: 1 }}>
                Traffic partner: NobleSeek Facebook page → fabrything.com/nobleseek
              </Typography>
            </Box>
            <Box>
              <Typography variant="subtitle2" fontWeight={800} sx={{ color: 'white' }}>Sections</Typography>
              {['bangladesh', 'world', 'sports', 'tech', 'entertainment'].map((s) => (
                <Typography key={s} component={Link} to={`/nobleseek?category=${s}`} variant="body2" sx={{ display: 'block', color: 'inherit', textDecoration: 'none', textTransform: 'capitalize' }}>{s}</Typography>
              ))}
            </Box>
            <Box>
              <Typography variant="subtitle2" fontWeight={800} sx={{ color: 'white' }}>Trust (AdSense)</Typography>
              {[
                ['About NobleSeek', '/nobleseek/about'],
                ['Contact', '/nobleseek/contact'],
                ['Privacy', '/nobleseek/privacy'],
                ['Disclaimer', '/nobleseek/disclaimer'],
                ['Editorial Ethics', '/nobleseek/ethics'],
                ['Fabrything Shop', '/shop'],
              ].map(([label, to]) => (
                <Typography key={to} component={Link} to={to} variant="body2" sx={{ display: 'block', color: 'inherit', textDecoration: 'none' }}>{label}</Typography>
              ))}
            </Box>
          </Box>
          <Divider sx={{ my: 2, borderColor: 'rgba(255,255,255,0.12)' }} />
          <Typography variant="caption">© 2026 NobleSeek by Fabrything • support@fabrything.com • Dhaka, Bangladesh</Typography>
        </Container>
      </Box>
    </Box>
  );
}
