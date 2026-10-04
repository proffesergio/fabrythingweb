import { useCallback, useEffect, useState } from 'react';
import { Alert, Box, Button, Chip, CircularProgress, Paper, Typography } from '@mui/material';
import useApi from '../../../hooks/APIHandler';

// Tag cloud from real usage counts — click drills into the articles tab.
export default function TagsManager({ onDrillTag }) {
  const { callApi } = useApi();
  const [tags, setTags] = useState([]);
  const [loading, setLoading] = useState(true);
  const [failed, setFailed] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    setFailed(false);
    const r = await callApi({ url: 'store/nobleseek/admin/tags/', silent: true, timeout: 25000 });
    if (r?.status === 200) setTags(r.data?.data ?? r.data ?? []);
    else setFailed(true);
    setLoading(false);
  }, [callApi]);

  useEffect(() => { load(); }, [load]);

  const max = Math.max(1, ...tags.map((t) => t.count));

  return (
    <Paper sx={{ p: 2 }}>
      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 2 }}>
        <Typography variant="subtitle1" fontWeight={800}>ট্যাগ ({tags.length})</Typography>
        <Box sx={{ flex: 1 }} />
        <Button size="small" onClick={load} disabled={loading}>রিলোড</Button>
      </Box>
      {loading ? <Box sx={{ display: 'flex', justifyContent: 'center', py: 4 }}><CircularProgress /></Box>
        : failed ? (
          <Alert severity="warning" action={<Button size="small" onClick={load}>পুনরায়</Button>}>
            ট্যাগ লোড হয়নি।
          </Alert>
        ) : !tags.length ? (
          <Typography variant="body2" color="text.secondary" sx={{ py: 3, textAlign: 'center' }}>
            কোনো ট্যাগ নেই — প্রতিবেদনে ট্যাগ যোগ করুন।
          </Typography>
        ) : (
          <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap' }}>
            {tags.map((t) => (
              <Chip
                key={t.tag} clickable onClick={() => onDrillTag && onDrillTag(t.tag)}
                label={`#${t.tag} · ${t.count}`}
                color={t.count >= max * 0.7 ? 'primary' : 'default'}
                variant={t.count >= max * 0.7 ? 'filled' : 'outlined'}
              />
            ))}
          </Box>
        )}
    </Paper>
  );
}
