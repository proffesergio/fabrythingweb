import { useState } from 'react';
import { Box, Button, Dialog, DialogTitle, DialogContent, DialogActions, IconButton, Menu, MenuItem, TextField, Tooltip, Typography } from '@mui/material';
import ShareIcon from '@mui/icons-material/Share';
import LinkIcon from '@mui/icons-material/Link';
import FacebookIcon from '@mui/icons-material/Facebook';
import { toast } from 'react-toastify';
import useApi from '../../hooks/APIHandler';
import { articleShareUrl, nativeShareOrCopy, shareLinks } from '../../nobleseek/share';

// Per-article share center: FB / X / WhatsApp / Telegram / copy / native
// sheet, plus "mark as posted" which stamps fb_post_url (traffic proof).
export default function ShareMenu({ article }) {
  const { callApi } = useApi();
  const [anchor, setAnchor] = useState(null);
  const [fbOpen, setFbOpen] = useState(false);
  const [fbUrl, setFbUrl] = useState(article?.fb_post_url || '');
  if (!article) return null;

  const url = articleShareUrl(article.slug);
  const title = article.headline_bn || article.headline;
  const links = shareLinks(url, title);

  const copy = async () => {
    const r = await nativeShareOrCopy({ title, text: title, url });
    if (r === 'copied') toast.success('লিংক কপি হয়েছে');
    else if (r === 'failed') toast.error('শেয়ার করা যায়নি');
    setAnchor(null);
  };

  const markPosted = async () => {
    if (!fbUrl.trim()) { toast.error('FB পোস্ট URL দিন'); return; }
    const r = await callApi({
      url: `store/nobleseek/admin/articles/${article.id}/`,
      method: 'PATCH', body: { fb_post_url: fbUrl.trim() }, silent: true,
    });
    if (r?.status === 200) {
      toast.success('FB পোস্ট হিসেবে চিহ্নিত');
      setFbOpen(false); setAnchor(null);
    } else toast.error('সংরক্ষণ ব্যর্থ');
  };

  const open = (href) => {
    window.open(href, '_blank', 'noopener,width=640,height=560');
    setAnchor(null);
  };

  return (
    <>
      <Tooltip title="শেয়ার">
        <IconButton size="small" onClick={(e) => setAnchor(e.currentTarget)}>
          <ShareIcon fontSize="small" />
        </IconButton>
      </Tooltip>
      <Menu anchorEl={anchor} open={Boolean(anchor)} onClose={() => setAnchor(null)}>
        <MenuItem onClick={() => open(links.facebook)}><FacebookIcon fontSize="small" sx={{ mr: 1 }} /> Facebook</MenuItem>
        <MenuItem onClick={() => open(links.x)}><Typography sx={{ mr: 1, fontWeight: 900 }}>𝕏</Typography> X (Twitter)</MenuItem>
        <MenuItem onClick={() => open(links.whatsapp)}><Typography sx={{ mr: 1 }}>💬</Typography> WhatsApp</MenuItem>
        <MenuItem onClick={() => open(links.telegram)}><Typography sx={{ mr: 1 }}>✈️</Typography> Telegram</MenuItem>
        <MenuItem onClick={copy}><LinkIcon fontSize="small" sx={{ mr: 1 }} /> কপি / শেয়ার</MenuItem>
        <MenuItem onClick={() => { setFbUrl(article.fb_post_url || ''); setFbOpen(true); }}>
          <Typography sx={{ mr: 1 }}>📌</Typography> FB পোস্ট হিসেবে চিহ্নিত
        </MenuItem>
      </Menu>
      <Dialog open={fbOpen} onClose={() => setFbOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle>FB ট্রাফিক প্রমাণ</DialogTitle>
        <DialogContent>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 1.5 }}>
            NobleSeek ফেসবুক পেজে পোস্ট করে সেই পোস্টের URL এখানে বসান — কোন খবর থেকে ট্রাফিক এলো তার প্রমাণ থাকে।
          </Typography>
          <TextField fullWidth size="small" label="Facebook পোস্ট URL" value={fbUrl} onChange={(e) => setFbUrl(e.target.value)} placeholder="https://www.facebook.com/…/posts/…" />
          <Box sx={{ mt: 1.5, p: 1.5, bgcolor: '#f8fafc', borderRadius: 1 }}>
            <Typography variant="caption" color="text.secondary">শেয়ার লিংক (পোস্টে ব্যবহার করুন)</Typography>
            <Typography variant="body2" sx={{ wordBreak: 'break-all' }}>{url}</Typography>
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setFbOpen(false)}>বাতিল</Button>
          <Button variant="contained" onClick={markPosted}>সংরক্ষণ</Button>
        </DialogActions>
      </Dialog>
    </>
  );
}
