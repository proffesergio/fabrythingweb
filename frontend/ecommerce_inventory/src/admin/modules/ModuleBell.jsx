import React, { useCallback, useEffect, useState } from 'react';
import { Badge, Box, Divider, IconButton, Menu, MenuItem, Tooltip, Typography } from '@mui/material';
import { Notifications as NotificationsIcon } from '@mui/icons-material';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import config from '../../utils/config';
import { getToken } from '../../utils/authToken';
import { MODULES, NOTIFICATIONS_API } from './registry';

// Topbar bell fed by the notifications rollup: per-module pending counts
// with drill links into each module home. Silent and self-hiding — a failed
// rollup never blocks the shell.
export default function ModuleBell() {
  const navigate = useNavigate();
  const [anchor, setAnchor] = useState(null);
  const [data, setData] = useState(null);

  const load = useCallback(async () => {
    try {
      const token = getToken();
      const res = await axios.get(`${config.API_URL}${NOTIFICATIONS_API}`, {
        headers: token ? { Authorization: `Bearer ${token}` } : {},
        timeout: 15000,
      });
      const payload = res?.data?.data ?? res?.data ?? null;
      if (payload) setData(payload);
    } catch { /* bell stays quiet on failure */ }
  }, []);

  useEffect(() => { load(); }, [load]);

  const total = data?.total || 0;
  const rows = data ? [
    { id: 'shop', count: Object.values(data.shop || {}).reduce((a, b) => a + (b || 0), 0), to: MODULES.shop.home },
    { id: 'food', count: Object.values(data.food || {}).reduce((a, b) => a + (b || 0), 0), to: MODULES.food.home },
    { id: 'news', count: Object.values(data.news || {}).reduce((a, b) => a + (b || 0), 0), to: '/admin/manage/nobleseek' },
  ] : [];

  return (
    <>
      <Tooltip title="Notifications">
        <IconButton
          color="inherit" size="small" aria-label="notifications"
          onClick={(e) => { setAnchor(e.currentTarget); load(); }}
        >
          <Badge badgeContent={total} color="error" invisible={total === 0}>
            <NotificationsIcon />
          </Badge>
        </IconButton>
      </Tooltip>
      <Menu
        anchorEl={anchor} open={Boolean(anchor)} onClose={() => setAnchor(null)}
        PaperProps={{ sx: { minWidth: 260 } }}
      >
        {rows.length === 0 && (
          <MenuItem disabled><Typography variant="body2">No alerts right now.</Typography></MenuItem>
        )}
        {rows.map((r) => (
          <MenuItem
            key={r.id}
            onClick={() => { setAnchor(null); navigate(r.to); }}
          >
            <Box sx={{ width: 10, height: 10, borderRadius: '50%', bgcolor: MODULES[r.id].color, mr: 1.5 }} />
            <Typography variant="body2" sx={{ flex: 1 }}>{MODULES[r.id].label}</Typography>
            <Typography variant="body2" fontWeight={800} color={r.count ? 'error' : 'text.secondary'}>
              {r.count}
            </Typography>
          </MenuItem>
        ))}
        <Divider />
        <MenuItem onClick={() => { setAnchor(null); navigate('/admin/manage/analytics'); }}>
          <Typography variant="body2" color="text.secondary">Open Traffic & Analytics</Typography>
        </MenuItem>
      </Menu>
    </>
  );
}
