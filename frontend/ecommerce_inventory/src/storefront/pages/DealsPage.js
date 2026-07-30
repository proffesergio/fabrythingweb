import React, { useEffect, useState } from 'react';
import { Box, Container, Grid, Skeleton, Typography } from '@mui/material';
import LocalOfferIcon from '@mui/icons-material/LocalOffer';
import useApi from '../../hooks/APIHandler';
import AffiliateProductCard from '../components/AffiliateProductCard';

/** Dedicated Deals page -- every AffiliateProduct with show_on_deals_page=True,
 * active and inside its scheduling window (GET /api/store/affiliate/?placement=deals).
 */
export default function DealsPage() {
    const { callApi } = useApi();
    const [items, setItems] = useState(null); // null = loading

    useEffect(() => {
        let mounted = true;
        callApi({ url: 'store/affiliate/', params: { placement: 'deals' } }).then((res) => {
            if (mounted) setItems(res?.data?.data || []);
        });
        return () => { mounted = false; };
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, []);

    return (
        <Container maxWidth="lg" sx={{ py: 4 }}>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
                <LocalOfferIcon color="secondary" />
                <Typography variant="h4" fontWeight={800}>Deals</Typography>
            </Box>
            <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
                Hand-picked partner deals -- these open on the partner's own site to complete your purchase.
            </Typography>

            {items === null && (
                <Grid container spacing={2}>
                    {[1, 2, 3, 4].map((i) => (
                        <Grid item xs={6} sm={4} md={3} key={i}>
                            <Skeleton variant="rectangular" height={260} sx={{ borderRadius: 2 }} />
                        </Grid>
                    ))}
                </Grid>
            )}

            {items !== null && items.length === 0 && (
                <Typography variant="body2" color="text.secondary" sx={{ py: 6, textAlign: 'center' }}>
                    No deals right now -- check back soon.
                </Typography>
            )}

            {items !== null && items.length > 0 && (
                <Grid container spacing={2}>
                    {items.map((item) => (
                        <Grid item xs={6} sm={4} md={3} key={item.id}>
                            <AffiliateProductCard item={item} />
                        </Grid>
                    ))}
                </Grid>
            )}
        </Container>
    );
}
