import { useCallback, useEffect, useState } from 'react';
import {
  Alert, Box, Button, Dialog, DialogTitle, DialogContent, DialogActions,
  Paper, Switch, Table, TableHead, TableRow, TableCell, TableBody,
  TextField, Typography, IconButton, CircularProgress, FormControlLabel,
} from '@mui/material';
import EditIcon from '@mui/icons-material/Edit';
import VisibilityIcon from '@mui/icons-material/Visibility';
import useApi from '../../../hooks/APIHandler';

const EMPTY = { slug: '', title: '', intro: '', body_html: '', is_active: true };

// Trust/info pages editor — what readers see at /nobleseek/about etc.
// The portal falls back to built-in copy when the API is unreachable, so
// edits here upgrade live pages without a redeploy.
export default function PagesManager() {
  const { callApi } = useApi();
  const [pages, setPages] = useState([]);
  const [loading, setLoading] = useState(true);
  const [failed, setFailed] = useState(false);
  const [open, setOpen] = useState(false);
  const [form, setForm] = useState(EMPTY);
  const [saving, setSaving] = useState(false);
  const isEdit = !!form.slug && pages.some((p) => p.slug === form.slug && form._edit);

  const load = useCallback(async () => {
    setLoading(true);
    setFailed(false);
    const r = await callApi({ url: 'store/nobleseek/admin/pages/', silent: true, timeout: 25000 });
    if (r?.status === 200) setPages(r.data?.data ?? r.data ?? []);
    else setFailed(true);
    setLoading(false);
  }, [callApi]);

  useEffect(() => { load(); }, [load]);

  const openEdit = (p) => { setForm({ ...EMPTY, ...p, _edit: true }); setOpen(true); };

  const save = async () => {
    if (!form.slug.trim() || !form.title.trim() || !form.body_html.trim()) return;
    setSaving(true);
    const payload = {
      slug: form.slug.trim().toLowerCase(), title: form.title.trim(),
      intro: form.intro, body_html: form.body_html, is_active: !!form.is_active,
    };
    const r = await callApi({
      url: form._edit ? `store/nobleseek/admin/pages/${payload.slug}/` : 'store/nobleseek/admin/pages/',
      method: form._edit ? 'PATCH' : 'POST', body: payload, silent: true,
    });
    setSaving(false);
    if (r?.status === 200 || r?.status === 201) { setOpen(false); load(); }
  };

  return (
    <Paper sx={{ p: 2 }}>
      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 2 }}>
        <Typography variant="subtitle1" fontWeight={800}>পেজ ({pages.length})</Typography>
        <Box sx={{ flex: 1 }} />
        <Button size="small" variant="contained" onClick={() => { setForm({ ...EMPTY, _edit: false }); setOpen(true); }}>
          নতুন পেজ
        </Button>
      </Box>
      {loading ? <Box sx={{ display: 'flex', justifyContent: 'center', py: 4 }}><CircularProgress /></Box>
        : failed ? (
          <Alert severity="warning" action={<Button size="small" onClick={load}>পুনরায়</Button>}>পেজ লোড হয়নি।</Alert>
        ) : (
          <Table size="small">
            <TableHead><TableRow><TableCell>স্লাগ</TableCell><TableCell>শিরোনাম</TableCell><TableCell>সক্রিয়</TableCell><TableCell align="right">অ্যাকশন</TableCell></TableRow></TableHead>
            <TableBody>
              {pages.map((p) => (
                <TableRow key={p.slug} hover>
                  <TableCell><Typography variant="body2" fontWeight={700}>/{p.slug}</Typography></TableCell>
                  <TableCell>{p.title}</TableCell>
                  <TableCell>{p.is_active ? '✓' : '—'}</TableCell>
                  <TableCell align="right" sx={{ whiteSpace: 'nowrap' }}>
                    <IconButton size="small" component="a" href={`/nobleseek/${p.slug}`} target="_blank"><VisibilityIcon fontSize="small" /></IconButton>
                    <IconButton size="small" onClick={() => openEdit(p)}><EditIcon fontSize="small" /></IconButton>
                  </TableCell>
                </TableRow>
              ))}
              {!pages.length && <TableRow><TableCell colSpan={4} align="center">কোনো পেজ নেই।</TableCell></TableRow>}
            </TableBody>
          </Table>
        )}
      <Dialog open={open} onClose={() => setOpen(false)} maxWidth="md" fullWidth>
        <DialogTitle>{form._edit ? 'পেজ সম্পাদনা' : 'নতুন পেজ'}</DialogTitle>
        <DialogContent dividers>
          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1.75 }}>
            <Box sx={{ display: 'flex', gap: 1.5 }}>
              <TextField size="small" label="স্লাগ" value={form.slug} disabled={!!form._edit}
                onChange={(e) => setForm({ ...form, slug: e.target.value })} sx={{ minWidth: 180 }}
                helperText={form.slug ? `/nobleseek/${form.slug}` : ''} />
              <TextField size="small" fullWidth label="শিরোনাম" value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} />
            </Box>
            <TextField size="small" fullWidth label="ভূমিকা (ঐচ্ছিক)" value={form.intro} onChange={(e) => setForm({ ...form, intro: e.target.value })} />
            <TextField fullWidth multiline rows={10} label="মূল লেখা (HTML: <p> <ul> <strong>)" value={form.body_html} onChange={(e) => setForm({ ...form, body_html: e.target.value })} />
            <FormControlLabel control={<Switch size="small" checked={!!form.is_active} onChange={(e) => setForm({ ...form, is_active: e.target.checked })} />} label="সক্রিয় (পোর্টালে দেখাবে)" />
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setOpen(false)}>বাতিল</Button>
          <Button variant="contained" disabled={saving} onClick={save}>{saving ? '…' : 'সংরক্ষণ'}</Button>
        </DialogActions>
      </Dialog>
    </Paper>
  );
}
