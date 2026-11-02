import React, { useEffect, useState } from 'react';
import { Box, Container, Grid, Skeleton, Typography } from '@mui/material';
import LocalOfferIcon from '@mui/icons-material/LocalOffer';
import useApi from '../../hooks/APIHandler';
import ProductCard from '../components/ProductCard';

/** Dedicated Deals page -- every AffiliateProduct with show_on_deals_page=True,
 * active and inside its scheduling window (GET /api/store/partner-picks/?placement=deals).
 *
 * Renders through the SAME ProductCard the storefront uses for its own
 * products (image tile proportions, price/discount treatment, the mobile
 * card-height work) via ProductCard's `affiliate` prop, instead of a
 * separately-styled layout. The "via <Program>" partner badge and the
 * click-tracking redirect (/api/store/partner-picks/<id>/go/, opened in a new
 * tab with rel="noopener noreferrer") still apply -- see ProductCard.js.
 */

// Maps AffiliateProductPublicSerializer's shape onto the plain fields
// ProductCard already knows how to render (image as an array, discount vs
// list price) -- keeps ProductCard itself agnostic of the affiliate API shape.
function toProductShape(item) {
    const original = item.original_price != null ? Number(item.original_price) : null;
    const current = item.current_price != null ? Number(item.current_price) : null;
    const hasDiscount = original != null && current != null && original !== current;
    return {
        id: item.id,
        name: item.title,
        brand: item.brand,
        image: item.image ? [item.image] : [],
        initial_selling_price: hasDiscount ? original : (current ?? original),
        discount_price: hasDiscount ? current : null,
    };
}

export default function DealsPage() {
    const { callApi } = useApi();
    const [items, setItems] = useState(null); // null = loading

    useEffect(() => {
        let mounted = true;
        callApi({ url: 'store/partner-picks/', params: { placement: 'deals' } }).then((res) => {
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
                            <ProductCard
                                product={toProductShape(item)}
                                affiliate={{ goUrl: item.go_url, targetUrl: item.target_url, label: item.program_label || item.program }}
                            />
                        </Grid>
                    ))}
                </Grid>
            )}
        </Container>
    );
}
