import { useCallback, useEffect, useState } from 'react';
import {
  Alert, Box, Button, Chip, CircularProgress, IconButton, LinearProgress,
  Paper, Stack, TextField, Typography,
} from '@mui/material';
import AddIcon from '@mui/icons-material/Add';
import DeleteIcon from '@mui/icons-material/Delete';
import { toast } from 'react-toastify';
import useApi from '../../../hooks/APIHandler';

// Reader polls: builder (question + up to 6 options), live results bars,
// activate/deactivate, delete. Voting itself lives on the portal.
export default function PollsManager() {
  const { callApi } = useApi();
  const [polls, setPolls] = useState([]);
  const [loading, setLoading] = useState(true);
  const [failed, setFailed] = useState(false);
  const [question, setQuestion] = useState('');
  const [options, setOptions] = useState(['', '']);
  const [creating, setCreating] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    setFailed(false);
    const r = await callApi({ url: 'store/nobleseek/admin/polls/', silent: true, timeout: 25000 });
    if (r?.status === 200) setPolls(r.data?.data ?? r.data ?? []);
    else setFailed(true);
    setLoading(false);
  }, [callApi]);

  useEffect(() => { load(); }, [load]);

  const create = async () => {
    const opts = options.map((o) => o.trim()).filter(Boolean);
    if (!question.trim() || opts.length < 2) { toast.error('প্রশ্ন + কমপক্ষে ২টি অপশন দিন'); return; }
    setCreating(true);
    const r = await callApi({
      url: 'store/nobleseek/admin/polls/', method: 'POST',
      body: { question: question.trim(), options: opts },
    });
    setCreating(false);
    if (r?.status === 201) {
      toast.success('জরিপ তৈরি হয়েছে');
      setQuestion(''); setOptions(['', '']);
      load();
    }
  };

  const toggle = async (p) => {
    await callApi({ url: `store/nobleseek/admin/polls/${p.id}/`, method: 'PATCH', body: { is_active: !p.is_active }, silent: true });
    load();
  };

  const remove = async (p) => {
    if (!window.confirm(`“${p.question}” মুছবেন? ভোটগুলোও যাবে।`)) return;
    await callApi({ url: `store/nobleseek/admin/polls/${p.id}/`, method: 'DELETE' });
    load();
  };

  return (
    <Box>
      <Paper sx={{ p: 2, mb: 2 }}>
        <Typography variant="subtitle1" fontWeight={800} gutterBottom>নতুন জরিপ</Typography>
        <Stack spacing={1.5}>
          <TextField size="small" fullWidth label="প্রশ্ন" value={question} onChange={(e) => setQuestion(e.target.value)} inputProps={{ maxLength: 255 }} />
          {options.map((o, i) => (
            <TextField
              key={i} size="small" fullWidth label={`অপশন ${i + 1}`} value={o}
              onChange={(e) => setOptions((prev) => prev.map((x, j) => (j === i ? e.target.value : x)))}
            />
          ))}
          <Box sx={{ display: 'flex', gap: 1 }}>
            {options.length < 6 && <Button size="small" startIcon={<AddIcon />} onClick={() => setOptions((p) => [...p, ''])}>অপশন যোগ</Button>}
            <Box sx={{ flex: 1 }} />
            <Button variant="contained" size="small" disabled={creating} onClick={create}>{creating ? '…' : 'তৈরি করুন'}</Button>
          </Box>
        </Stack>
      </Paper>
      {loading ? <Box sx={{ display: 'flex', justifyContent: 'center', py: 4 }}><CircularProgress /></Box>
        : failed ? (
          <Alert severity="warning" action={<Button size="small" onClick={load}>পুনরায়</Button>}>লোড হয়নি।</Alert>
        ) : polls.map((p) => {
          const max = Math.max(1, ...p.options.map((o) => o.votes));
          return (
            <Paper key={p.id} sx={{ p: 2, mb: 1.5 }}>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                <Typography fontWeight={800} sx={{ flex: 1 }}>{p.question}</Typography>
                <Chip size="small" label={p.is_active ? 'সক্রিয়' : 'বন্ধ'} color={p.is_active ? 'success' : 'default'} />
                <Typography variant="caption" color="text.secondary">{p.total} ভোট</Typography>
                <Button size="small" onClick={() => toggle(p)}>{p.is_active ? 'বন্ধ করুন' : 'চালু করুন'}</Button>
                <IconButton size="small" onClick={() => remove(p)}><DeleteIcon fontSize="small" /></IconButton>
              </Box>
              {p.options.map((o) => (
                <Box key={o.id} sx={{ display: 'flex', alignItems: 'center', gap: 1, mt: 1 }}>
                  <Typography variant="body2" sx={{ minWidth: 140 }}>{o.text}</Typography>
                  <LinearProgress variant="determinate" value={(o.votes / max) * 100} sx={{ flex: 1, height: 8, borderRadius: 4 }} />
                  <Typography variant="caption" sx={{ minWidth: 70, textAlign: 'right' }}>{o.votes} ({o.pct}%)</Typography>
                </Box>
              ))}
            </Paper>
          );
        })}
    </Box>
  );
}
