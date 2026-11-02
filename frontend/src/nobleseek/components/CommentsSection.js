import React, { useEffect, useState } from 'react';
import { Box, Button, LinearProgress, TextField, Typography } from '@mui/material';
import { fetchComments, flagComment, postComment } from '../api';

// On-site reader discussion: approved comments only, post-then-review flow,
// per-comment reporting. Lives under the article body, above FB comments.
export default function CommentsSection({ articleId }) {
  const [items, setItems] = useState([]);
  const [name, setName] = useState('');
  const [text, setText] = useState('');
  const [sending, setSending] = useState(false);
  const [note, setNote] = useState('');

  const load = async () => {
    if (!articleId) return;
    try { setItems(await fetchComments(articleId)); } catch { /* keep old list */ }
  };
  useEffect(() => { load(); }, [articleId]); // eslint-disable-line react-hooks/exhaustive-deps

  const submit = async () => {
    if (name.trim().length < 2 || text.trim().length < 2 || sending) return;
    setSending(true);
    try {
      await postComment(articleId, name.trim(), text.trim());
      setText('');
      setNote('মন্তব্য পেয়েছি — যাচাইয়ের পর প্রকাশ হবে।');
      load();
    } catch {
      setNote('পাঠানো যায়নি — আবার চেষ্টা করুন।');
    }
    setSending(false);
  };

  const report = async (id) => {
    try { await flagComment(id); } catch { /* best effort */ }
  };

  return (
    <Box sx={{ mt: 4 }}>
      <Typography variant="h6" fontWeight={800} className="ns-serif" gutterBottom>
        মন্তব্য ({items.length})
      </Typography>
      {items.map((c) => (
        <Box key={c.id} sx={{ py: 1.5, borderBottom: '1px solid #eee' }}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <Typography variant="body2" fontWeight={800} className="ns-sans">{c.name}</Typography>
            <Typography variant="caption" color="text.secondary" className="ns-sans">
              {c.created_at ? new Date(c.created_at).toLocaleString('bn-BD') : ''}
            </Typography>
            <Box sx={{ flex: 1 }} />
            <Button size="small" sx={{ minWidth: 0, color: '#999' }} onClick={() => report(c.id)}>
              রিপোর্ট
            </Button>
          </Box>
          <Typography variant="body2" className="ns-sans" sx={{ mt: 0.25 }}>{c.text}</Typography>
        </Box>
      ))}
      {!items.length && (
        <Typography variant="body2" color="text.secondary" className="ns-sans" sx={{ mb: 2 }}>
          এখনো কোনো মন্তব্য নেই — প্রথম মন্তব্য করুন।
        </Typography>
      )}
      <Box sx={{ mt: 2, p: 2, border: '1px solid #e5e5e5', borderRadius: 2 }}>
        <Typography variant="body2" fontWeight={800} className="ns-sans" gutterBottom>মন্তব্য লিখুন</Typography>
        <TextField size="small" fullWidth label="আপনার নাম" value={name} onChange={(e) => setName(e.target.value)} sx={{ mb: 1.5 }} inputProps={{ maxLength: 80 }} />
        <TextField size="small" fullWidth multiline rows={3} label="মন্তব্য" value={text} onChange={(e) => setText(e.target.value)} inputProps={{ maxLength: 500 }} />
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mt: 1.5 }}>
          <Button variant="contained" size="small" disabled={sending} onClick={submit} className="ns-sans">
            {sending ? '…' : 'পাঠান'}
          </Button>
          {note && <Typography variant="caption" color="text.secondary" className="ns-sans">{note}</Typography>}
        </Box>
      </Box>
    </Box>
  );
}
