import React, { useEffect, useState } from 'react';
import { Box, Container, Grid, Typography, Button } from '@mui/material';
import { Link } from 'react-router-dom';
import { fetchLatestStrip } from '../api';
import NewsCard from '../components/NewsCard';

// Homepage funnel strip: latest 4 NobleSeek cards -> drives shop visitors to news (and back).
export default function NobleSeekStrip() {
  const [items, setItems] = useState([]);
  useEffect(() => { fetchLatestStrip().then(setItems).catch(() => {}); }, []);
  if (!items.length) return null;
  return (
    <Container maxWidth="lg" sx={{ mt: 4, mb: 2 }}>
      <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 1.5 }}>
        <Typography variant="h5" fontWeight={900}>
          NobleSeek <Typography component="span" variant="body2" color="text.secondary">— Trends News</Typography>
        </Typography>
        <Button component={Link} to="/nobleseek" size="small" variant="outlined">All news</Button>
      </Box>
      <Grid container spacing={2}>
        {items.slice(0, 4).map((a) => (
          <Grid item xs={12} sm={6} md={3} key={a.id || a.slug}>
            <NewsCard article={a} utm="homepage-strip" />
          </Grid>
        ))}
      </Grid>
    </Container>
  );
}
