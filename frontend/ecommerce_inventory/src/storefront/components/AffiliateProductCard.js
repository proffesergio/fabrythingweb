import React from 'react';
import { Box, Button, Card, Chip, Stack, Typography } from '@mui/material';
import OpenInNewIcon from '@mui/icons-material/OpenInNew';

/**
 * Shared card for one AffiliateProduct (storefront.serializers_affiliate.
 * AffiliateProductPublicSerializer's shape) -- used by AffiliateWidget,
 * DealsPage and the category-grid injection in ProductCatalog, so the badge/
 * link rules never drift between the three surfaces.
 *
 * The owner chose clear labelling over a subtler design: every affiliate
 * item is badged "via <Program>" and opens in a new tab with
 * rel="noopener noreferrer" -- a shopper must never be surprised to land on
 * another site. The href is `go_url`, OUR OWN redirect endpoint
 * (/api/store/affiliate/<id>/go/), never a link built client-side -- that
 * endpoint is what increments click_count and resolves the current
 * constructed/overridden target server-side.
 */
export default function AffiliateProductCard({ item, dense = false }) {
    if (!item) return null;
    const hasDiscount = item.current_price != null
        && item.original_price != null
        && String(item.original_price) !== String(item.current_price);

    return (
        <Card
            variant="outlined"
            sx={{ p: 1.5, height: '100%', display: 'flex', flexDirection: 'column', position: 'relative' }}
        >
            <Chip
                label={`via ${item.program_label || item.program}`}
                size="small"
                color="secondary"
                sx={{ position: 'absolute', top: 8, left: 8, fontWeight: 700, zIndex: 1 }}
            />
            <Box
                component="img"
                src={item.image || ''}
                alt={item.title}
                sx={{
                    width: '100%', height: dense ? 110 : 160, objectFit: 'contain',
                    borderRadius: 1, bgcolor: 'background.default', mb: 1,
                }}
            />
            <Typography variant="body2" fontWeight={600} noWrap title={item.title}>
                {item.title}
            </Typography>
            {item.brand && (
                <Typography variant="caption" color="text.secondary" noWrap>{item.brand}</Typography>
            )}
            <Stack direction="row" spacing={1} alignItems="center" sx={{ mt: 0.5, mb: 1 }}>
                {item.current_price != null && (
                    <Typography variant="body2" fontWeight={700}>৳{item.current_price}</Typography>
                )}
                {hasDiscount && (
                    <Typography variant="caption" sx={{ textDecoration: 'line-through' }} color="text.secondary">
                        ৳{item.original_price}
                    </Typography>
                )}
            </Stack>
            <Button
                component="a"
                href={item.go_url}
                target="_blank"
                rel="noopener noreferrer"
                fullWidth
                variant="contained"
                size="small"
                endIcon={<OpenInNewIcon fontSize="small" />}
                sx={{ mt: 'auto' }}
            >
                Shop Now
            </Button>
        </Card>
    );
}
