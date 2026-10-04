import { useCallback, useEffect, useState } from 'react';
import {
  Alert, Box, Button, Chip, CircularProgress, Paper, Stack, Table, TableHead,
  TableRow, TableCell, TableBody, TextField, Typography,
} from '@mui/material';
import SendIcon from '@mui/icons-material/Send';
import { toast } from 'react-toastify';
import useApi from '../../../hooks/APIHandler';

// Breaking-news push console: subscriber count, compose + send, campaign
// history. Without FCM_SERVER_KEY on the backend, sends are recorded as
// skipped (never crash) — the status card says so explicitly.
export default function PushManager() {
  const { callApi } = useApi();
  const [info, setInfo] = useState({ count: 0, configured: false });
  const [campaigns, setCampaigns] = useState([]);
  const [loading, setLoading] = useState(true);
  const [title, setTitle] = useState('');
  const [body, setBody] = useState('');
  const [url, setUrl] = useState('');
  const [sending, setSending] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    const [d, c] = await Promise.all([
      callApi({ url: 'store/nobleseek/admin/push/devices/', silent: true, timeout: 25000 }),
      callApi({ url: 'store/nobleseek/admin/push/campaigns/', silent: true, timeout: 25000 }),
    ]);
    if (d?.status === 200) setInfo(d.data?.data ?? d.data ?? { count: 0, configured: false });
    if (c?.status === 200) setCampaigns(c.data?.data?.results || c.data?.data || []);
    setLoading(false);
  }, [callApi]);

  useEffect(() => { load(); }, [load]);

  const send = async () => {
    if (!title.trim() || !body.trim()) { toast.error('শিরোনাম + বার্তা দিন'); return; }
    if (!window.confirm(`${info.count} জনের কাছে পাঠাবেন?`)) return;
    setSending(true);
    const r = await callApi({
      url: 'store/nobleseek/admin/push/send/', method: 'POST',
      body: { title: title.trim(), body: body.trim(), url: url.trim() },
    });
    setSending(false);
    if (r?.status === 200) {
      const d = r.data?.data ?? {};
      toast.success(`পাঠানো: ${d.sent}, ব্যর্থ: ${d.failed}, স্কিপ: ${d.skipped}`);
      setTitle(''); setBody(''); setUrl('');
      load();
    }
  };

  return (
    <Box>
      <Paper sx={{ p: 2, mb: 2 }}>
        <Stack direction="row" spacing={1.5} alignItems="center" flexWrap="wrap">
          <Typography variant="subtitle1" fontWeight={800}>পুশ নোটিফিকেশন</Typography>
          <Chip size="small" label={`${info.count} গ্রাহক`} color="info" />
          <Chip
            size="small" label={info.configured ? 'FCM সক্রিয়' : 'FCM কী নেই — শুধু রেকর্ড হবে'}
            color={info.configured ? 'success' : 'warning'}
          />
        </Stack>
        {!info.configured && (
          <Alert severity="warning" sx={{ mt: 1.5 }}>
            ব্যাকএন্ডে <code>FCM_SERVER_KEY</code> নেই — পাঠানো বার্তা স্কিপ হিসেবে রেকর্ড হবে।
            Firebase Console → Project settings → Cloud Messaging থেকে কী নিয়ে Render Environment-এ বসান।
          </Alert>
        )}
      </Paper>
      <Paper sx={{ p: 2, mb: 2 }}>
        <Typography variant="subtitle1" fontWeight={800} gutterBottom>নতুন বার্তা</Typography>
        <Stack spacing={1.5}>
          <TextField size="small" fullWidth label="শিরোনাম" value={title} onChange={(e) => setTitle(e.target.value)} inputProps={{ maxLength: 120 }} />
          <TextField size="small" fullWidth multiline rows={2} label="বার্তা" value={body} onChange={(e) => setBody(e.target.value)} inputProps={{ maxLength: 300 }} />
          <TextField size="small" fullWidth label="লিংক (ঐচ্ছিক, খবরের URL)" value={url} onChange={(e) => setUrl(e.target.value)} placeholder="https://fabrything.com/nobleseek/…" />
          <Box><Button variant="contained" startIcon={<SendIcon />} disabled={sending || info.count === 0} onClick={send}>
            {sending ? 'পাঠানো হচ্ছে…' : `পাঠান (${info.count})`}
          </Button></Box>
        </Stack>
      </Paper>
      <Paper sx={{ p: 2 }}>
        <Typography variant="subtitle1" fontWeight={800} gutterBottom>ইতিহাস</Typography>
        {loading ? <Box sx={{ display: 'flex', justifyContent: 'center', py: 3 }}><CircularProgress /></Box> : (
          <Table size="small">
            <TableHead><TableRow><TableCell>শিরোনাম</TableCell><TableCell>লক্ষ্য</TableCell><TableCell>পাঠানো</TableCell><TableCell>ব্যর্থ</TableCell><TableCell>স্কিপ</TableCell><TableCell>কখন</TableCell></TableRow></TableHead>
            <TableBody>
              {campaigns.map((c) => (
                <TableRow key={c.id} hover>
                  <TableCell><Typography variant="body2" fontWeight={700}>{c.title}</Typography>
                    <Typography variant="caption" color="text.secondary">{c.note}</Typography></TableCell>
                  <TableCell>{c.audience}</TableCell><TableCell>{c.sent}</TableCell>
                  <TableCell>{c.failed}</TableCell><TableCell>{c.skipped}</TableCell>
                  <TableCell><Typography variant="caption">{c.created_at ? new Date(c.created_at).toLocaleString('bn-BD') : ''}</Typography></TableCell>
                </TableRow>
              ))}
              {!campaigns.length && <TableRow><TableCell colSpan={6} align="center">এখনো কিছু পাঠানো হয়নি।</TableCell></TableRow>}
            </TableBody>
          </Table>
        )}
      </Paper>
    </Box>
  );
}
