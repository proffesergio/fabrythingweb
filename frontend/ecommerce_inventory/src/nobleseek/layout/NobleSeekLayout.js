import React from 'react';
import { Outlet } from 'react-router-dom';
import { Box } from '@mui/material';
import NewsFonts from '../NewsFonts';
import PortalHeader from '../portal/PortalHeader';
import NewsFooter from '../portal/NewsFooter';

// Standalone NobleSeek news portal shell — no shop chrome (no cart, menus,
// chat, Fabrything branding). Typography + section nav mirror a classic
// Bangla newspaper front page.
export default function NobleSeekLayout() {
  return (
    <Box className="ns-sans" sx={{ minHeight: '100vh', display: 'flex', flexDirection: 'column', bgcolor: '#ffffff', color: '#141414' }}>
      <NewsFonts />
      <PortalHeader />
      <Box sx={{ flex: 1 }}>
        <Outlet />
      </Box>
      <NewsFooter />
    </Box>
  );
}
