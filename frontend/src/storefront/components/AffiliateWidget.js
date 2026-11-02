import React, { useEffect, useRef, useState } from 'react';
import { Box, IconButton, Stack, Typography } from '@mui/material';
import ChevronLeftIcon from '@mui/icons-material/ChevronLeft';
import ChevronRightIcon from '@mui/icons-material/ChevronRight';
import StorefrontIcon from '@mui/icons-material/Storefront';
import useApi from '../../hooks/APIHandler';
import AffiliateProductCard from './AffiliateProductCard';

const ROTATE_MS = 5000;

function prefersReducedMotion() {
    return typeof window !== 'undefined' && typeof window.matchMedia === 'function'
        && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
}

/**
 * Rotating sidebar/section widget for affiliate products (GET
 * /api/store/partner-picks/?placement=sidebar, or a specific ?category=<slug>
 * when `category` is passed instead). One item is shown at a time and
 * auto-advances every ROTATE_MS -- but:
 *
 *   - the interval is torn down while the tab is hidden
 *     (document.visibilityState) and restarted when it becomes visible
 *     again, so a backgrounded tab doesn't burn cycles rotating something
 *     nobody can see;
 *   - it never starts at all under prefers-reduced-motion -- every item is
 *     rendered statically instead (manual prev/next arrows still work,
 *     since those are user-initiated, not autoplay);
 *   - the interval is always cleared on unmount.
 */
export default function AffiliateWidget({ placement = 'sidebar', category = null, title = 'Deals from Rokomari' }) {
    const { callApi } = useApi();
    const [items, setItems] = useState([]);
    const [index, setIndex] = useState(0);
    const intervalRef = useRef(null);

    useEffect(() => {
        let mounted = true;
        const params = category ? { category } : { placement };
        callApi({ url: 'store/partner-picks/', params }).then((res) => {
            if (mounted) setItems(res?.data?.data || []);
        });
        return () => { mounted = false; };
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [placement, category]);

    useEffect(() => {
        if (items.length <= 1 || prefersReducedMotion()) return undefined;

        const advance = () => setIndex((i) => (i + 1) % items.length);

        const start = () => {
            if (intervalRef.current) return;
            intervalRef.current = setInterval(advance, ROTATE_MS);
        };
        const stop = () => {
            if (intervalRef.current) {
                clearInterval(intervalRef.current);
                intervalRef.current = null;
            }
        };
        const onVisibilityChange = () => {
            if (document.visibilityState === 'visible') start(); else stop();
        };

        if (document.visibilityState === 'visible') start();
        document.addEventListener('visibilitychange', onVisibilityChange);

        return () => {
            stop();
            document.removeEventListener('visibilitychange', onVisibilityChange);
        };
    }, [items.length]);

    if (!items.length) return null;

    const reduced = prefersReducedMotion();
    const current = items[index % items.length];

    return (
        <Box sx={{ mb: 3 }}>
            <Stack direction="row" spacing={1} alignItems="center" sx={{ mb: 1.5 }}>
                <StorefrontIcon fontSize="small" color="secondary" />
                <Typography variant="subtitle2" fontWeight={700}>{title}</Typography>
            </Stack>

            {reduced ? (
                <Stack spacing={2}>
                    {items.map((item) => <AffiliateProductCard key={item.id} item={item} dense />)}
                </Stack>
            ) : (
                <Box sx={{ position: 'relative' }}>
                    <AffiliateProductCard item={current} dense />
                    {items.length > 1 && (
                        <Stack direction="row" justifyContent="center" spacing={0.5} sx={{ mt: 1 }}>
                            <IconButton
                                size="small"
                                aria-label="Previous deal"
                                onClick={() => setIndex((i) => (i - 1 + items.length) % items.length)}
                            >
                                <ChevronLeftIcon fontSize="small" />
                            </IconButton>
                            {items.map((item, i) => (
                                <Box
                                    key={item.id}
                                    sx={{
                                        width: 6, height: 6, borderRadius: '50%', alignSelf: 'center',
                                        bgcolor: i === index ? 'secondary.main' : 'action.disabled',
                                    }}
                                />
                            ))}
                            <IconButton
                                size="small"
                                aria-label="Next deal"
                                onClick={() => setIndex((i) => (i + 1) % items.length)}
                            >
                                <ChevronRightIcon fontSize="small" />
                            </IconButton>
                        </Stack>
                    )}
                </Box>
            )}
        </Box>
    );
}
