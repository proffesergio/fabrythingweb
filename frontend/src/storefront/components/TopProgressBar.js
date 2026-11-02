import React, { useEffect, useState } from 'react';
import { Box, LinearProgress, Typography } from '@mui/material';

// A thin indeterminate bar pinned to the top of the viewport while a page is
// fetching, plus a plain-language explanation once the wait stops looking
// normal.
//
// Skeletons alone were not enough on this site: Render's free tier can take
// ~50s to cold start, and a screen of motionless grey blocks for that long
// reads as broken rather than loading. The bar gives continuous motion, and
// after SLOW_AFTER_MS the copy says why the wait is happening instead of
// leaving the customer to guess.
const SLOW_AFTER_MS = 4000;

export default function TopProgressBar({ loading, label = 'Loading…' }) {
    const [slow, setSlow] = useState(false);

    useEffect(() => {
        if (!loading) {
            setSlow(false);
            return undefined;
        }
        const timer = setTimeout(() => setSlow(true), SLOW_AFTER_MS);
        return () => clearTimeout(timer);
    }, [loading]);

    if (!loading) return null;

    return (
        <Box
            role="progressbar"
            aria-label={label}
            aria-busy="true"
            sx={{
                position: 'fixed', top: 0, left: 0, right: 0,
                zIndex: (t) => t.zIndex.appBar + 2,
            }}
        >
            <LinearProgress color="secondary" sx={{ height: 3 }} />
            {slow && (
                <Box
                    sx={{
                        mx: 'auto', mt: 1, px: 2, py: 0.75, width: 'fit-content', maxWidth: '92%',
                        borderRadius: 999, bgcolor: 'rgba(15,23,42,0.92)', color: '#fff',
                        boxShadow: 3,
                    }}
                >
                    <Typography variant="caption">
                        Still loading — our server is waking up. This takes a few seconds.
                    </Typography>
                </Box>
            )}
        </Box>
    );
}
