import { useEffect, useState, useCallback } from 'react';
import { IconButton, Badge, Menu, Box, Typography, Divider } from '@mui/material';
import NotificationsNoneRoundedIcon from '@mui/icons-material/NotificationsNoneRounded';
import useApi from '../../hooks/APIHandler';
import { isSignedIn } from '../../utils/authToken';

export default function NotificationsBell() {
  const { callApi } = useApi();
  const [data, setData] = useState({ unread: 0, items: [] });
  const [anchor, setAnchor] = useState(null);
  // isSignedIn, not a raw localStorage read: an expired token used to keep this
  // bell mounted and polling `food/notifications/` every 30s, producing a 401
  // in the console twice a minute for a visitor who was not really signed in.
  const loggedIn = isSignedIn();

  const load = useCallback(async () => {
    const r = await callApi({ url: 'food/notifications/', method: 'GET', silent: true });
    if (r?.status === 200) setData(r.data.data);
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    if (!loggedIn) return undefined;
    load();
    const t = setInterval(load, 30000);
    return () => clearInterval(t);
  }, [loggedIn, load]);

  if (!loggedIn) return null;

  const open = (e) => {
    setAnchor(e.currentTarget);
    if (data.unread) callApi({ url: 'food/notifications/', method: 'POST', silent: true }).then(load);
  };

  return (
    <>
      <IconButton onClick={open} sx={{ color: 'text.primary' }}>
        <Badge badgeContent={data.unread} color="primary"><NotificationsNoneRoundedIcon /></Badge>
      </IconButton>
      <Menu anchorEl={anchor} open={!!anchor} onClose={() => setAnchor(null)}
        PaperProps={{ sx: { width: 320, maxHeight: 420, borderRadius: 3 } }}>
        <Typography sx={{ px: 2, py: 1, fontWeight: 800 }}>Notifications</Typography>
        <Divider />
        {data.items.length === 0 && <Typography sx={{ px: 2, py: 2 }} color="text.secondary">You're all caught up 🎉</Typography>}
        {data.items.map((n) => (
          <Box key={n.id} sx={{ px: 2, py: 1.2 }}>
            <Typography variant="body2" fontWeight={700}>{n.title}</Typography>
            <Typography variant="caption" color="text.secondary">{n.body}</Typography>
            <Divider sx={{ mt: 1 }} />
          </Box>
        ))}
      </Menu>
    </>
  );
}
