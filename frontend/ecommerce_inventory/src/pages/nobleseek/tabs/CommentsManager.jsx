import { useCallback, useEffect, useState } from 'react';
import {
  Alert, Box, Button, Chip, CircularProgress, Paper, Stack, Table, TableHead,
  TableRow, TableCell, TableBody, TextField, Typography, IconButton, MenuItem,
} from '@mui/material';
import CheckIcon from '@mui/icons-material/Check';
import CloseIcon from '@mui/icons-material/Close';
import DeleteIcon from '@mui/icons-material/Delete';
import { toast } from 'react-toastify';
import useApi from '../../../hooks/APIHandler';

const STATUS = ['', 'PENDING', 'APPROVED', 'REJECTED'];
const STATUS_BN = { '': 'সব', PENDING: 'অপেক্ষমাণ', APPROVED: 'অনুমোদিত', REJECTED: 'বাতিল' };

// On-site comment moderation: approve/reject/delete, flagged-first ordering
// comes from the backend. New comments arrive PENDING — nothing public
// until approved here.
export default function CommentsManager() {
  const { callApi } = useApi();
  const [rows, setRows] = useState([]);
  const [status, setStatus] = useState('PENDING');
  const [loading, setLoading] = useState(true);
  const [failed, setFailed] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    setFailed(false);
    const r = await callApi({
      url: 'store/nobleseek/admin/comments/',
      params: status ? { status } : {}, silent: true, timeout: 25000,
    });
    if (r?.status === 200) setRows(r.data?.data?.results || r.data?.data || []);
    else setFailed(true);
    setLoading(false);
  }, [callApi, status]);

  useEffect(() => { load(); }, [load]);

  const decide = async (id, next) => {
    const r = await callApi({
      url: `store/nobleseek/admin/comments/${id}/`, method: 'PATCH',
      body: { status: next }, silent: true,
    });
    if (r?.status === 200) { toast.success(next === 'APPROVED' ? 'অনুমোদিত' : 'বাতিল হয়েছে'); load(); }
    else toast.error('ব্যর্থ হয়েছে');
  };

  const remove = async (id) => {
    if (!window.confirm('মন্তব্যটি মুছবেন?')) return;
    await callApi({ url: `store/nobleseek/admin/comments/${id}/`, method: 'DELETE' });
    load();
  };

  return (
    <Paper sx={{ p: 2 }}>
      <Stack direction="row" spacing={1.5} sx={{ mb: 2 }} alignItems="center">
        <Typography variant="subtitle1" fontWeight={800}>মন্তব্য</Typography>
        <TextField size="small" select value={status} onChange={(e) => setStatus(e.target.value)} sx={{ minWidth: 140 }}>
          {STATUS.map((s) => <MenuItem key={s} value={s}>{STATUS_BN[s]}</MenuItem>)}
        </TextField>
        <Box sx={{ flex: 1 }} />
        <Button size="small" onClick={load} disabled={loading}>রিলোড</Button>
      </Stack>
      {loading ? <Box sx={{ display: 'flex', justifyContent: 'center', py: 4 }}><CircularProgress /></Box>
        : failed ? (
          <Alert severity="warning" action={<Button size="small" onClick={load}>পুনরায়</Button>}>লোড হয়নি।</Alert>
        ) : (
          <Table size="small">
            <TableHead><TableRow><TableCell>মন্তব্য</TableCell><TableCell>স্ট্যাটাস</TableCell><TableCell>ফ্ল্যাগ</TableCell><TableCell align="right">অ্যাকশন</TableCell></TableRow></TableHead>
            <TableBody>
              {rows.map((c) => (
                <TableRow key={c.id} hover>
                  <TableCell sx={{ maxWidth: 480 }}>
                    <Typography variant="body2" fontWeight={700}>{c.name}</Typography>
                    <Typography variant="body2" color="text.secondary">{c.text}</Typography>
                    <Typography variant="caption" color="text.secondary">
                      article #{c.article} • {c.created_at ? new Date(c.created_at).toLocaleString('bn-BD') : ''}
                    </Typography>
                  </TableCell>
                  <TableCell>
                    <Chip size="small" label={STATUS_BN[c.status] || c.status}
                      color={c.status === 'APPROVED' ? 'success' : c.status === 'REJECTED' ? 'default' : 'warning'} />
                  </TableCell>
                  <TableCell>{c.flags > 0 ? `🚩${c.flags}` : '—'}</TableCell>
                  <TableCell align="right" sx={{ whiteSpace: 'nowrap' }}>
                    {c.status !== 'APPROVED' && (
                      <IconButton size="small" color="success" onClick={() => decide(c.id, 'APPROVED')}><CheckIcon fontSize="small" /></IconButton>
                    )}
                    {c.status !== 'REJECTED' && (
                      <IconButton size="small" color="warning" onClick={() => decide(c.id, 'REJECTED')}><CloseIcon fontSize="small" /></IconButton>
                    )}
                    <IconButton size="small" onClick={() => remove(c.id)}><DeleteIcon fontSize="small" /></IconButton>
                  </TableCell>
                </TableRow>
              ))}
              {!rows.length && <TableRow><TableCell colSpan={4} align="center">এই তালিকায় কিছু নেই।</TableCell></TableRow>}
            </TableBody>
          </Table>
        )}
    </Paper>
  );
}
