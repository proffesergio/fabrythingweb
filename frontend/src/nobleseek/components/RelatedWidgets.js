import React, { useEffect, useState } from 'react';
import { Box, Grid, Typography } from '@mui/material';
import { fetchRelated } from '../api';
import { SecondaryCard, SectionHeader } from './NewsCards';

export function RelatedNews({ slug }) {
  const [items, setItems] = useState([]);
  useEffect(() => {
    if (!slug) return;
    fetchRelated(slug).then(setItems).catch(() => {});
  }, [slug]);
  if (!items.length) return null;
  return (
    <Box sx={{ mt: 5 }}>
      <SectionHeader title="আরও পড়ুন" />
      <Grid container spacing={2.5}>
        {items.map((a) => (
          <Grid item xs={12} sm={6} md={3} key={a.id || a.slug}>
            <SecondaryCard article={a} />
          </Grid>
        ))}
      </Grid>
    </Box>
  );
}

// Shop-funnel product box removed: NobleSeek is a standalone news portal.
// (The shop→news funnel lives on the shop side: NobleSeekStrip on HomePage.)
export function RelatedProducts() { return null; }
