import { useState } from 'react';
import { Link as RouterLink, useNavigate } from 'react-router-dom';
import { Box, Button, Card, IconButton, Stack, TextField, Typography } from '@mui/material';
import ChevronRightRoundedIcon from '@mui/icons-material/ChevronRightRounded';
import DeleteOutlineRoundedIcon from '@mui/icons-material/DeleteOutlineRounded';
import { readGuestOrders, recordGuestOrder, removeGuestOrder } from '../utils/guestOrders';

// Guest order history: no account needed. Entries are written at checkout
// (and by manual tracking below), survive browser restarts via localStorage,
// and open the same code+phone track page signed-in users get.
export default function GuestOrdersPanel({ compact = false, signedIn = false }) {
  const navigate = useNavigate();
  const [entries, setEntries] = useState(() => readGuestOrders());
  const [code, setCode] = useState('');
  const [phone, setPhone] = useState('');

  const open = (entry) => {
    navigate(`/food/order/${entry.code}`, { state: { phone: entry.phone || undefined } });
  };
  const drop = (entryCode) => {
    removeGuestOrder(entryCode);
    setEntries(readGuestOrders());
  };
  const trackManual = () => {
    const c = code.trim();
    if (!c || !phone.trim()) return;
    recordGuestOrder({ code: c, phone: phone.trim() });
    setEntries(readGuestOrders());
    navigate(`/food/order/${c}`, { state: { phone: phone.trim() } });
  };

  return (
    <Box sx={compact ? {} : { maxWidth: 640, mx: 'auto' }}>
      {!compact && (
        <Typography variant="h6" sx={{ mb: 1.5, fontWeight: 900 }}>Guest orders</Typography>
      )}
      {entries.length === 0 && (
        <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
          No saved guest orders on this device yet — orders placed without an account appear here.
        </Typography>
      )}
      {entries.map((o) => (
        <Card key={o.code} sx={{ p: 2, mb: 1.5, display: 'flex', alignItems: 'center', gap: 1 }}>
          <Box
            onClick={() => open(o)} role="button" tabIndex={0}
            onKeyDown={(e) => { if (e.key === 'Enter') open(o); }}
            sx={{ flex: 1, minWidth: 0, cursor: 'pointer' }}
          >
            <Typography sx={{ fontWeight: 800 }} noWrap>{o.restaurant || 'Food order'}</Typography>
            <Typography variant="body2" color="text.secondary">
              {o.code}{o.total != null ? ` · ৳${o.total}` : ''}
              {o.at ? ` · ${new Date(o.at).toLocaleDateString()}` : ''}
            </Typography>
          </Box>
          <IconButton size="small" aria-label="Track" onClick={() => open(o)}>
            <ChevronRightRoundedIcon />
          </IconButton>
          <IconButton size="small" aria-label="Remove" onClick={() => drop(o.code)}>
            <DeleteOutlineRoundedIcon fontSize="small" />
          </IconButton>
        </Card>
      ))}
      <Card sx={{ p: 2 }}>
        <Typography variant="body2" fontWeight={800} sx={{ mb: 1 }}>Track another order</Typography>
        <Stack direction={{ xs: 'column', sm: 'row' }} spacing={1}>
          <TextField size="small" label="Order code" value={code} onChange={(e) => setCode(e.target.value)} fullWidth />
          <TextField size="small" label="Phone" value={phone} onChange={(e) => setPhone(e.target.value)} fullWidth />
          <Button variant="contained" onClick={trackManual} disabled={!code.trim() || !phone.trim()}>View</Button>
        </Stack>
        <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mt: 1 }}>
          On a new device or incognito? Enter the code + checkout phone — no account needed.
          {!signedIn && <> Or <RouterLink to="/auth/login">sign in</RouterLink> for account orders.</>}
        </Typography>
      </Card>
    </Box>
  );
}
