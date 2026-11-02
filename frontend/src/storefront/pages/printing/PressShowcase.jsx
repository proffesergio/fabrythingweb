import React, { useEffect, useMemo, useState } from 'react';
import {
  Alert, Box, Button, Card, Chip, Dialog, DialogContent, DialogTitle,
  IconButton, Stack, TextField, Typography,
} from '@mui/material';
import { Close, Search, Star, StarBorder } from '@mui/icons-material';
import useApi from '../../../hooks/APIHandler';
import { PRESS_NAV, PRESS_STRIP, categoryTitle, readWishlist, toggleWishlist } from './pressCategories';

// ColorLifePrint-style storefront: top category nav, "Products Categories"
// strip, "Top Picks" grid with HOT badges, BDT prices and wishlist stars.
// Fed by GET print/showcase/ — admin uploads (any print format + thumbnail)
// appear here automatically, grouped by category.
export function ShowcaseImage({ item, height = 150, rounded = 2 }) {
  if (item?.image) {
    return (
      <Box
        component="img" src={item.image} alt={item.name} loading="lazy"
        sx={{ width: '100%', height, objectFit: 'cover', borderRadius: rounded, bgcolor: 'action.hover' }}
      />
    );
  }
  return (
    <Box
      sx={{
        width: '100%', height, borderRadius: rounded, bgcolor: 'action.hover',
        display: 'flex', alignItems: 'center', justifyContent: 'center', p: 1.5,
      }}
    >
      <Typography variant="subtitle2" align="center" sx={{ fontWeight: 700, color: 'text.secondary', lineHeight: 1.3 }}>
        {item?.name}
      </Typography>
    </Box>
  );
}

export function BadgePill({ badge }) {
  if (!badge) return null;
  const color = badge === 'HOT' ? '#e53935' : badge === 'OFFER' ? '#e53935' : '#2e7d32';
  return (
    <Chip
      size="small" label={badge}
      sx={{ position: 'absolute', top: 8, left: 8, bgcolor: color, color: '#fff', fontWeight: 800, fontSize: 11, height: 22 }}
    />
  );
}

export default function PressShowcase({ onOrder }) {
  const { callApi } = useApi();
  const [items, setItems] = useState([]);
  const [activeCategory, setActiveCategory] = useState('');
  const [query, setQuery] = useState('');
  const [wishlist, setWishlist] = useState(() => readWishlist());
  const [detail, setDetail] = useState(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      const res = await callApi({ url: 'print/showcase/', silent: true });
      if (!cancelled && res?.data?.data) setItems(res.data.data);
    })();
    return () => { cancelled = true; };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Press-catalogue items only — the garment (t-shirt) showcase keeps its own
  // component and flow untouched.
  const pressItems = useMemo(
    () => items.filter((it) => PRESS_STRIP.some((c) => c.key === it.category)),
    [items],
  );

  const tileImage = (key) => (pressItems.find((it) => it.category === key && it.image) || {}).image;

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    return pressItems.filter((it) => {
      if (activeCategory && it.category !== activeCategory) return false;
      if (q && !`${it.name} ${it.note} ${categoryTitle(it.category)}`.toLowerCase().includes(q)) return false;
      return true;
    });
  }, [pressItems, activeCategory, query]);

  const topPicks = useMemo(
    () => filtered.filter((it) => it.is_top_pick || !activeCategory),
    [filtered, activeCategory],
  );

  const pickNav = (category) => setActiveCategory((c) => (c === category ? '' : category || ''));

  return (
    <Box sx={{ mb: 4 }}>
      {/* ── Top category nav ── */}
      <Box
        sx={{
          display: 'flex', gap: 2.5, overflowX: 'auto', py: 1.25, px: 2, mb: 3, mx: -2,
          bgcolor: '#e9eefb', '&::-webkit-scrollbar': { display: 'none' }, scrollbarWidth: 'none',
        }}
      >
        {PRESS_NAV.map((n) => (
          <Box
            key={n.label} onClick={() => n.category && pickNav(n.category)}
            sx={{
              position: 'relative', whiteSpace: 'nowrap', cursor: n.category ? 'pointer' : 'default',
              fontSize: '0.85rem', fontWeight: activeCategory === n.category ? 800 : 600,
              color: activeCategory === n.category ? 'primary.main' : 'text.primary',
              '&:hover': n.category ? { color: 'primary.main' } : {},
              pt: n.badge ? 1 : 0,
            }}
          >
            {n.label} {n.category ? '⌄' : ''}
            {n.badge && (
              <Chip
                size="small" label={n.badge}
                sx={{
                  position: 'absolute', top: -8, right: -14, height: 16, fontSize: 9, fontWeight: 800,
                  bgcolor: n.badge === 'FREE' ? '#4caf50' : '#e53935', color: '#fff',
                }}
              />
            )}
          </Box>
        ))}
      </Box>

      <Typography variant="h5" fontWeight={800} sx={{ mb: 2 }}>Products Categories</Typography>

      {/* ── Category strip ── */}
      <Card variant="outlined" sx={{ p: 2, mb: 4, borderRadius: 3 }}>
        <Box sx={{ display: 'flex', gap: 2.5, overflowX: 'auto', pb: 1 }}>
          {PRESS_STRIP.map((c) => {
            const img = tileImage(c.key);
            const on = activeCategory === c.key;
            return (
              <Box
                key={c.key} onClick={() => pickNav(c.key)}
                sx={{ minWidth: 110, maxWidth: 110, cursor: 'pointer', textAlign: 'center' }}
              >
                <Box
                  sx={{
                    width: 110, height: 110, borderRadius: 3, overflow: 'hidden',
                    border: on ? '2px solid' : '1px solid', borderColor: on ? 'primary.main' : 'divider',
                    bgcolor: 'action.hover', display: 'flex', alignItems: 'center', justifyContent: 'center',
                  }}
                >
                  {img ? (
                    <Box component="img" src={img} alt={c.title} loading="lazy"
                      sx={{ width: '100%', height: '100%', objectFit: 'cover' }} />
                  ) : (
                    <Typography variant="caption" fontWeight={700} color="text.secondary" sx={{ px: 1 }}>
                      {c.title}
                    </Typography>
                  )}
                </Box>
                <Typography variant="caption" fontWeight={on ? 800 : 600} color={on ? 'primary.main' : 'text.primary'}
                  sx={{ display: 'block', mt: 0.75, lineHeight: 1.25 }}>
                  {c.title}
                </Typography>
              </Box>
            );
          })}
        </Box>
      </Card>

      {/* ── Top Picks header ── */}
      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5, mb: 2, flexWrap: 'wrap' }}>
        <Typography variant="h5" fontWeight={800}>
          {activeCategory ? categoryTitle(activeCategory) : 'Top Picks'}
        </Typography>
        <Box sx={{ flex: 1 }} />
        <TextField
          size="small" placeholder="Search designs…" value={query} onChange={(e) => setQuery(e.target.value)}
          InputProps={{ startAdornment: <Search fontSize="small" sx={{ mr: 0.5, color: 'text.secondary' }} /> }}
          sx={{ width: 200 }}
        />
        {activeCategory && (
          <Button size="small" onClick={() => setActiveCategory('')}>Clear filter</Button>
        )}
        <Button
          size="small" variant="contained" onClick={() => setActiveCategory('')}
          sx={{ borderRadius: 5, bgcolor: '#e9eefb', color: 'primary.main', boxShadow: 'none', fontWeight: 700 }}
        >
          All Products ＞
        </Button>
      </Box>

      {filtered.length === 0 ? (
        <Alert severity="info">
          No designs in this category yet — upload them from the admin (Printing Press → Design Showcase).
        </Alert>
      ) : (
        <Box
          sx={{
            display: 'grid', gap: 2,
            gridTemplateColumns: { xs: 'repeat(2, 1fr)', sm: 'repeat(3, 1fr)', md: 'repeat(4, 1fr)', lg: 'repeat(5, 1fr)' },
          }}
        >
          {topPicks.map((it) => {
            const wished = wishlist.has(it.id);
            return (
              <Card
                key={it.id} variant="outlined"
                sx={{ borderRadius: 3, overflow: 'hidden', cursor: 'pointer', '&:hover': { boxShadow: 3 } }}
                onClick={() => setDetail(it)}
              >
                <Box sx={{ position: 'relative' }}>
                  <ShowcaseImage item={it} height={150} rounded={0} />
                  <BadgePill badge={it.badge} />
                </Box>
                <Box sx={{ p: 1.5 }}>
                  <Box sx={{ display: 'flex', alignItems: 'flex-start', gap: 0.5 }}>
                    <Typography variant="body2" fontWeight={700} sx={{ flex: 1, lineHeight: 1.3 }}>
                      {it.name}
                    </Typography>
                    <IconButton
                      size="small" sx={{ p: 0.25 }}
                      onClick={(e) => { e.stopPropagation(); setWishlist(toggleWishlist(it.id)); }}
                      aria-label="wishlist"
                    >
                      {wished ? <Star fontSize="small" color="warning" /> : <StarBorder fontSize="small" sx={{ color: 'text.disabled' }} />}
                    </IconButton>
                  </Box>
                  <Typography variant="caption" color="text.secondary" display="block">
                    {categoryTitle(it.category)}
                  </Typography>
                  <Typography variant="body2" fontWeight={800} color="primary.main" sx={{ mt: 0.5 }}>
                    {it.price_bdt != null ? `৳${Number(it.price_bdt).toLocaleString('en-US')}` : 'Price on quote'}
                  </Typography>
                </Box>
              </Card>
            );
          })}
        </Box>
      )}

      {/* ── Design detail ── */}
      <Dialog open={!!detail} onClose={() => setDetail(null)} maxWidth="sm" fullWidth>
        {detail && (
          <>
            <DialogTitle sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
              <Typography variant="h6" fontWeight={800} sx={{ flex: 1 }}>{detail.name}</Typography>
              <IconButton size="small" onClick={() => setDetail(null)}><Close /></IconButton>
            </DialogTitle>
            <DialogContent>
              <Box sx={{ position: 'relative', mb: 2 }}>
                <ShowcaseImage item={detail} height={240} />
                <BadgePill badge={detail.badge} />
              </Box>
              <Stack direction="row" spacing={1} sx={{ mb: 1 }}>
                <Chip size="small" label={categoryTitle(detail.category)} />
                {detail.file_type && <Chip size="small" variant="outlined" label={detail.file_type.toUpperCase()} />}
                {detail.price_bdt != null && (
                  <Chip size="small" color="primary" label={`৳${Number(detail.price_bdt).toLocaleString('en-US')}`} />
                )}
              </Stack>
              {(detail.description || detail.note) && (
                <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                  {detail.description || detail.note}
                </Typography>
              )}
              {detail.file_url && (
                <Button size="small" href={detail.file_url} target="_blank" rel="noreferrer" sx={{ mb: 2 }}>
                  Download design file ({detail.file_type || 'file'})
                </Button>
              )}
              <Button
                variant="contained" fullWidth size="large"
                onClick={() => { setDetail(null); onOrder && onOrder(detail.press_product, detail); }}
              >
                Order this design
              </Button>
              <Typography variant="caption" color="text.secondary" display="block" sx={{ mt: 1, textAlign: 'center' }}>
                Instant price calculator, artwork upload and bKash / Nagad / Rocket checkout below.
              </Typography>
            </DialogContent>
          </>
        )}
      </Dialog>
    </Box>
  );
}
