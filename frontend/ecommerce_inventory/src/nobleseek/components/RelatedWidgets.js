import React, { useEffect, useState } from 'react';
import { Box, Grid, Typography, Skeleton } from '@mui/material';
import { Link } from 'react-router-dom';
import axios from 'axios';
import config from '../../utils/config';
import { fetchRelated } from '../api';
import NewsCard from './NewsCard';
import useCachedApi from '../../hooks/useCachedApi';

export function RelatedNews({ slug }) {
  const [items, setItems] = useState([]);
  useEffect(() => {
    if (!slug) return;
    fetchRelated(slug).then(setItems).catch(() => {});
  }, [slug]);
  if (!items.length) return null;
  return (
    <Box sx={{ mt: 5 }}>
      <Typography variant="h6" fontWeight={800} gutterBottom>Related stories</Typography>
      <Grid container spacing={2}>
        {items.map((a) => (
          <Grid item xs={12} sm={6} md={3} key={a.id || a.slug}>
            <NewsCard article={a} />
          </Grid>
        ))}
      </Grid>
    </Box>
  );
}

// Shop funnel: news readers -> product clicks. Reuses store products API.
// If the editor linked explicit product ids, resolve those; otherwise fall
// back to the latest store products so the funnel box never renders empty.
export function RelatedProducts({ productIds }) {
  const ids = Array.isArray(productIds) ? productIds.filter(Number.isFinite).slice(0, 4) : [];
  const { data } = useCachedApi('store/products/', { params: {}, enabled: ids.length === 0 });
  const [manual, setManual] = useState([]);
  useEffect(() => {
    if (!ids.length) return undefined;
    let live = true;
    Promise.all(ids.map((id) =>
      axios.get(`${config.API_URL}store/products/${id}/`)
        .then((r) => r?.data?.data ?? r?.data)
        .catch(() => null)
    )).then((rows) => {
      if (live) setManual(rows.filter(Boolean));
    });
    return () => { live = false; };
  }, [ids.join(',')]);
  const fallback = (data?.results || data || []).slice(0, 4);
  const list = ids.length ? manual : fallback;
  if (!list.length) return null;
  return (
    <Box sx={{ mt: 5, p: 2, border: '1px solid', borderColor: 'divider', borderRadius: 3, bgcolor: 'background.paper' }}>
      <Typography variant="subtitle1" fontWeight={800} gutterBottom>Shop this story on Fabrything</Typography>
      <Grid container spacing={1.5}>
        {list.map((p) => (
          <Grid item xs={6} md={3} key={p.id || p.slug}>
            <Box component={Link} to={`/product/${p.slug}`} sx={{ textDecoration: 'none', color: 'inherit' }}>
              {p.image && <Box component="img" src={Array.isArray(p.image) ? p.image[0] : p.image} alt={p.name} loading="lazy" sx={{ width: '100%', height: 110, objectFit: 'cover', borderRadius: 2 }} />}
              <Typography variant="body2" fontWeight={700} sx={{ mt: 0.5, display: '-webkit-box', WebkitLineClamp: 1, WebkitBoxOrient: 'vertical', overflow: 'hidden' }}>{p.name}</Typography>
              <Typography variant="caption" color="secondary.main" fontWeight={800}>৳{p.discount_price || p.selling_price || p.price}</Typography>
            </Box>
          </Grid>
        ))}
      </Grid>
    </Box>
  );
}

export function SidebarAds({ render }) { return <>{render?.()}</>; }
export { Skeleton };
