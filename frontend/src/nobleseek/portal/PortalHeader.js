import React, { useEffect, useState } from 'react';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';
import { Box, Container, IconButton, Drawer, List, ListItemButton, ListItemText, Divider, InputBase, Paper } from '@mui/material';
import { Search as SearchIcon, Menu as MenuIcon, Close as CloseIcon, Facebook, Twitter, YouTube, FlashOn } from '@mui/icons-material';
import { fetchBreaking, fetchNewsCategories, PORTAL_SECTIONS } from '../api';
import { todayLine } from '../bn';

export const NS_ACCENT = '#F2631F'; // brand orange (SEEK + magnifier)
export const NS_NAVY = '#101244'; // brand navy (NOBLE + globe)
export const NS_INK = '#141414';

// ── Logo ────────────────────────────────────────────────────────────────
// Source: /nobleseek_logo.png (uploaded stacked lockup, kept as-is).
// Derived web assets (transparent, via tools/make_ns_logo.py):
//   /nobleseek-logo-wide.png  horizontal lockup — masthead + drawer
//   /nobleseek-logo-white.png white silhouette — dark footer only
//   /nobleseek-mark.png       square globe+lens badge — favicon, shop pill
export function MastheadLogo({ height = 48, light = false }) {
  const [stage, setStage] = useState(0);
  const src = [light ? '/nobleseek-logo-white.png' : '/nobleseek-logo-wide.png', '/nobleseek_logo.png'][Math.min(stage, 1)];
  if (stage >= 2) {
    return (
      <Box sx={{ display: 'flex', alignItems: 'center' }} className="ns-sans">
        <Box sx={{ fontWeight: 900, fontSize: height * 0.5, lineHeight: 1, letterSpacing: 1 }}>
          <span style={{ color: light ? '#ffffff' : NS_NAVY }}>NOBLE</span>
          <span style={{ color: NS_ACCENT }}>SEEK</span>
        </Box>
      </Box>
    );
  }
  return (
    <Box
      component="img"
      src={src}
      alt="নোবেলসিক — NobleSeek"
      onError={() => setStage((s) => s + 1)}
      sx={{ height, width: 'auto', display: 'block' }}
    />
  );
}

// ── Top utility strip ───────────────────────────────────────────────────
function TopUtilityBar() {
  return (
    <Box sx={{ bgcolor: NS_NAVY, color: 'rgba(255,255,255,0.85)', fontSize: 12.5 }}>
      <Container maxWidth="lg" sx={{ display: 'flex', alignItems: 'center', gap: 2, py: 0.7 }}>
        <Box className="ns-sans">{todayLine()}</Box>
        <Box sx={{ flex: 1 }} />
        <Box sx={{ display: { xs: 'none', sm: 'flex' }, gap: 2, alignItems: 'center' }} className="ns-sans">
          <Link to="/nobleseek" style={{ color: 'inherit', textDecoration: 'none' }}>সর্বশেষ</Link>
          <Link to="/nobleseek?category=opinion" style={{ color: 'inherit', textDecoration: 'none' }}>মতামত</Link>
          <Link to="/nobleseek/about" style={{ color: 'inherit', textDecoration: 'none' }}>আমাদের সম্পর্কে</Link>
          <Link to="/nobleseek/contact" style={{ color: 'inherit', textDecoration: 'none' }}>যোগাযোগ</Link>
        </Box>
        <Box sx={{ display: 'flex', gap: 0.25 }}>
          <IconButton component="a" href="https://www.facebook.com/" target="_blank" rel="noreferrer" size="small" sx={{ color: 'inherit' }} aria-label="Facebook"><Facebook fontSize="small" /></IconButton>
          <IconButton component="a" href="https://x.com/" target="_blank" rel="noreferrer" size="small" sx={{ color: 'inherit' }} aria-label="X"><Twitter fontSize="small" /></IconButton>
          <IconButton component="a" href="https://www.youtube.com/" target="_blank" rel="noreferrer" size="small" sx={{ color: 'inherit' }} aria-label="YouTube"><YouTube fontSize="small" /></IconButton>
        </Box>
      </Container>
    </Box>
  );
}

// ── Breaking ticker ─────────────────────────────────────────────────────
function BreakingTicker() {
  const [items, setItems] = useState([]);
  useEffect(() => { fetchBreaking(8).then(setItems).catch(() => {}); }, []);
  if (!items.length) return null;
  const loop = [...items, ...items];
  return (
    <Box sx={{ bgcolor: '#fff1f1', borderBottom: '1px solid #f3c1c1' }}>
      <Container maxWidth="lg" sx={{ display: 'flex', alignItems: 'stretch', gap: 0 }}>
        <Box sx={{ bgcolor: NS_ACCENT, color: 'white', display: 'flex', alignItems: 'center', gap: 0.5, px: 1.5, py: 0.8, fontWeight: 800, fontSize: 13, flexShrink: 0 }} className="ns-sans">
          <FlashOn fontSize="small" /> ব্রেকিং
        </Box>
        <Box sx={{ overflow: 'hidden', flex: 1, display: 'flex', alignItems: 'center' }}>
          <Box className="ns-ticker-track ns-sans" sx={{ fontSize: 13.5 }}>
            {loop.map((a, i) => (
              <Link key={`${a.id || a.slug}-${i}`} to={`/nobleseek/${a.slug}`} style={{ color: NS_INK, textDecoration: 'none', padding: '0 28px 0 8px' }}>
                <span style={{ color: NS_ACCENT, marginRight: 6 }}>●</span>{a.headline_bn || a.headline}
              </Link>
            ))}
          </Box>
        </Box>
      </Container>
    </Box>
  );
}

// ── Sticky section nav ──────────────────────────────────────────────────
function CategoryNav() {
  const [params] = useSearchParams();
  const navigate = useNavigate();
  const [cats, setCats] = useState([]);
  const [drawer, setDrawer] = useState(false);
  const [searchOpen, setSearchOpen] = useState(false);
  const [q, setQ] = useState('');
  const active = params.get('category') || '';

  useEffect(() => {
    fetchNewsCategories().then((c) => { if (Array.isArray(c) && c.length) setCats(c); }).catch(() => {});
  }, []);

  const sections = (cats.length ? cats : PORTAL_SECTIONS).filter((c) => c.slug && (c.is_active !== false));

  const submitSearch = (e) => {
    e?.preventDefault();
    setSearchOpen(false);
    setDrawer(false);
    navigate(q.trim() ? `/nobleseek?search=${encodeURIComponent(q.trim())}` : '/nobleseek');
  };

  return (
    <>
      <Box sx={{ position: 'sticky', top: 0, zIndex: 500, bgcolor: 'white', borderBottom: '2px solid ' + NS_INK }}>
        <Container maxWidth="lg" sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
          <IconButton size="small" onClick={() => setDrawer(true)} aria-label="মেনু" sx={{ flexShrink: 0 }}><MenuIcon /></IconButton>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.25, overflowX: 'auto', flex: 1, py: 0.5, '&::-webkit-scrollbar': { display: 'none' }, scrollbarWidth: 'none' }} className="ns-sans">
            <Box
              component={Link} to="/nobleseek"
              sx={{ px: 1.5, py: 1, fontSize: 14.5, fontWeight: 700, whiteSpace: 'nowrap', textDecoration: 'none', color: !active && !params.get('search') ? NS_ACCENT : NS_INK, borderBottom: !active && !params.get('search') ? `3px solid ${NS_ACCENT}` : '3px solid transparent' }}
            >সর্বশেষ</Box>
            {sections.map((c) => (
              <Box
                key={c.slug} component={Link} to={`/nobleseek?category=${c.slug}`}
                sx={{ px: 1.5, py: 1, fontSize: 14.5, fontWeight: active === c.slug ? 800 : 500, whiteSpace: 'nowrap', textDecoration: 'none', color: active === c.slug ? NS_ACCENT : NS_INK, borderBottom: active === c.slug ? `3px solid ${NS_ACCENT}` : '3px solid transparent', '&:hover': { color: NS_ACCENT } }}
              >{c.name}</Box>
            ))}
          </Box>
          <IconButton size="small" onClick={() => setSearchOpen((v) => !v)} aria-label="খুঁজুন" sx={{ flexShrink: 0 }}><SearchIcon /></IconButton>
        </Container>
        {searchOpen && (
          <Box sx={{ borderTop: '1px solid #eee', bgcolor: '#fafafa' }}>
            <Container maxWidth="lg" sx={{ py: 1 }}>
              <Paper component="form" onSubmit={submitSearch} sx={{ display: 'flex', alignItems: 'center', px: 1.5, py: 0.25, boxShadow: 'none', border: '1px solid #ddd' }}>
                <SearchIcon sx={{ color: '#999', mr: 1 }} />
                <InputBase autoFocus fullWidth placeholder="খবর খুঁজুন…" value={q} onChange={(e) => setQ(e.target.value)} className="ns-sans" sx={{ fontSize: 15 }} />
                <IconButton size="small" onClick={() => setSearchOpen(false)} aria-label="বন্ধ"><CloseIcon fontSize="small" /></IconButton>
              </Paper>
            </Container>
          </Box>
        )}
      </Box>

      <Drawer anchor="left" open={drawer} onClose={() => setDrawer(false)}>
        <Box sx={{ width: 300, py: 1 }} className="ns-sans">
          <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', px: 2, pb: 1 }}>
            <MastheadLogo height={36} />
            <IconButton size="small" onClick={() => setDrawer(false)} aria-label="বন্ধ"><CloseIcon /></IconButton>
          </Box>
          <Divider />
          <List dense>
            <ListItemButton component={Link} to="/nobleseek" onClick={() => setDrawer(false)}>
              <ListItemText primary="সর্বশেষ" primaryTypographyProps={{ fontWeight: 700 }} />
            </ListItemButton>
            {sections.map((c) => (
              <ListItemButton key={c.slug} component={Link} to={`/nobleseek?category=${c.slug}`} onClick={() => setDrawer(false)}>
                <ListItemText primary={c.name} />
              </ListItemButton>
            ))}
          </List>
          <Divider />
          <List dense>
            {[['আমাদের সম্পর্কে', '/nobleseek/about'], ['যোগাযোগ', '/nobleseek/contact'], ['গোপনীয়তা নীতি', '/nobleseek/privacy'], ['ডিসক্লেইমার', '/nobleseek/disclaimer'], ['সম্পাদকীয় নীতি', '/nobleseek/ethics']].map(([label, to]) => (
              <ListItemButton key={to} component={Link} to={to} onClick={() => setDrawer(false)}>
                <ListItemText primary={label} primaryTypographyProps={{ fontSize: 13.5, color: '#555' }} />
              </ListItemButton>
            ))}
          </List>
        </Box>
      </Drawer>
    </>
  );
}

export default function PortalHeader() {
  return (
    <>
      <TopUtilityBar />
      <Box sx={{ bgcolor: 'white' }}>
        <Container maxWidth="lg" sx={{ display: 'flex', alignItems: 'center', justifyContent: 'center', py: { xs: 1.5, md: 2.25 }, position: 'relative' }}>
          <Box sx={{ display: { xs: 'none', md: 'block' }, position: 'absolute', left: 24, fontSize: 12.5, color: '#6b7280' }} className="ns-sans">{todayLine()}</Box>
          <Link to="/nobleseek" style={{ textDecoration: 'none' }} aria-label="নোবেলসিক হোম">
            <MastheadLogo height={54} />
          </Link>
        </Container>
      </Box>
      <CategoryNav />
      <BreakingTicker />
    </>
  );
}
