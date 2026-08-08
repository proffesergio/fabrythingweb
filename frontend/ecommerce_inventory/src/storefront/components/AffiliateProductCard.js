import React from 'react';
import { Box, Card, CardMedia, Chip, Stack, Typography } from '@mui/material';
import OpenInNewIcon from '@mui/icons-material/OpenInNew';

/**
 * Shared card for one AffiliateProduct (storefront.serializers_affiliate.
 * AffiliateProductPublicSerializer's shape) — used by AffiliateWidget,
 * DealsPage and the category-grid injection in ProductCatalog, so the badge
 * and link rules never drift between the three surfaces.
 *
 * Styled to match ProductCard: same white photo tile, same contain-fit and
 * hover zoom, same discount badge and price treatment. The one deliberate
 * difference is the "via <Program>" badge and the open-in-new-tab glyph — a
 * shopper must never be surprised to land on another site.
 *
 * THE WHOLE CARD IS THE LINK. Previously only a "Shop Now" button was
 * clickable, so tapping the image or the title — which is what people
 * actually do — did nothing.
 *
 * `href` is `target_url`, the affiliate destination itself, so the new tab
 * goes straight to Rokomari. It used to be `go_url` (our own /r/ endpoint):
 * that counts the click and resolves the target server-side, but it also put
 * fabrythingweb.onrender.com in front of the customer, and on the free tier a
 * cold start left them on a blank Render page for ~50s before the 302 fired.
 *
 * The click is still counted: `pingClick` fires a background beacon at
 * `go_url` from THIS page while the new tab navigates. Tracking is now
 * best-effort and the customer's click is not — which is the right way round.
 * If `target_url` is null (a program with no adapter and no manual override)
 * the card falls back to `go_url`, which resolves server-side.
 */

export function pingClick(goUrl) {
    if (!goUrl) return;
    try {
        // sendBeacon survives the page losing focus to the new tab and does not
        // delay navigation. Falls back to a detached fetch where unsupported.
        if (navigator.sendBeacon) {
            navigator.sendBeacon(goUrl);
            return;
        }
        fetch(goUrl, { method: 'GET', mode: 'no-cors', keepalive: true }).catch(() => {});
    } catch {
        // A blocked or failed tracker must never interfere with the click.
    }
}

export default function AffiliateProductCard({ item, dense = false }) {
    if (!item) return null;

    const hasDiscount = item.current_price != null
        && item.original_price != null
        && String(item.original_price) !== String(item.current_price);
    const discountPct = hasDiscount
        ? Math.round((1 - Number(item.current_price) / Number(item.original_price)) * 100)
        : 0;

    const href = item.target_url || item.go_url;

    return (
        <Card
            component="a"
            href={href}
            target="_blank"
            rel="noopener noreferrer sponsored"
            aria-label={`${item.title} — opens ${item.program_label || item.program} in a new tab`}
            onClick={() => pingClick(item.go_url)}
            onAuxClick={() => pingClick(item.go_url)}   // middle-click / open-in-new-tab
            sx={{
                height: '100%', display: 'flex', flexDirection: 'column',
                position: 'relative', textDecoration: 'none', color: 'inherit',
                borderRadius: 2, overflow: 'hidden',
                transition: 'transform 0.2s ease, box-shadow 0.2s ease',
                '&:hover': { transform: 'translateY(-4px)', boxShadow: 6 },
                '&:hover .aff-img': { transform: 'scale(1.05)' },
            }}
        >
            <Chip
                label={`via ${item.program_label || item.program}`}
                size="small"
                color="secondary"
                sx={{ position: 'absolute', top: 8, left: 8, fontWeight: 700, zIndex: 2 }}
            />
            {discountPct > 0 && (
                <Chip
                    label={`-${discountPct}%`}
                    size="small"
                    sx={{
                        position: 'absolute', top: 8, right: 8, zIndex: 2,
                        bgcolor: '#ff1744', color: '#fff', fontWeight: 700,
                    }}
                />
            )}

            {/* Same white tile as ProductCard: partner photos are shot on white,
                so the tile stays white in dark mode too — a dark tile would put
                an obvious white rectangle around every photo. */}
            <Box sx={{
                position: 'relative', overflow: 'hidden',
                aspectRatio: dense ? '1 / 1' : { xs: '1 / 1', md: '3/4' },
                bgcolor: '#fff', p: { xs: 1.5, md: 2 },
            }}>
                <CardMedia
                    component="img"
                    className="aff-img"
                    image={item.image || ''}
                    alt={item.title}
                    sx={{
                        width: '100%', height: '100%', objectFit: 'contain',
                        transition: 'transform 0.4s ease',
                    }}
                />
            </Box>

            <Box sx={{ p: 1.5, pt: 1.25, display: 'flex', flexDirection: 'column', flex: 1 }}>
                <Typography
                    variant="body2"
                    fontWeight={600}
                    title={item.title}
                    sx={{
                        display: '-webkit-box', WebkitLineClamp: 2, WebkitBoxOrient: 'vertical',
                        overflow: 'hidden', minHeight: '2.6em', lineHeight: 1.3,
                    }}
                >
                    {item.title}
                </Typography>
                {item.brand && (
                    <Typography variant="caption" color="text.secondary" noWrap sx={{ mt: 0.25 }}>
                        {item.brand}
                    </Typography>
                )}

                <Stack direction="row" spacing={1} alignItems="baseline" sx={{ mt: 'auto', pt: 1 }}>
                    {item.current_price != null && (
                        <Typography variant="subtitle1" fontWeight={800} color="secondary.main">
                            ৳{item.current_price}
                        </Typography>
                    )}
                    {hasDiscount && (
                        <Typography variant="caption" sx={{ textDecoration: 'line-through' }} color="text.secondary">
                            ৳{item.original_price}
                        </Typography>
                    )}
                </Stack>

                <Stack direction="row" spacing={0.5} alignItems="center" sx={{ mt: 0.75 }}>
                    <OpenInNewIcon sx={{ fontSize: 14, color: 'text.secondary' }} />
                    <Typography variant="caption" color="text.secondary">
                        Buy on {item.program_label || item.program}
                    </Typography>
                </Stack>
            </Box>
        </Card>
    );
}
