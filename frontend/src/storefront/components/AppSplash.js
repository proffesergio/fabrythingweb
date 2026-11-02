import React, { useEffect, useState } from 'react';
import { Box, Fade } from '@mui/material';
import { isStandalone } from '../../utils/pwa';

// A PWA splash screen is static by specification — Android generates it from
// the manifest icon and background_color, and nothing can animate it. So the
// motion has to be an in-app overlay that takes over the moment React mounts,
// hiding the handover from the system splash.
//
// It runs ONLY in the installed app (display-mode: standalone). A shopper who
// just followed a link into the site in a browser tab gets no artificial delay
// — a splash on the web is a cost, not a feature.
const SPLASH_MS = 900;

export default function AppSplash() {
    // Decided once, at mount: if this is a browser tab the component never
    // renders anything at all and costs a single boolean.
    const [show, setShow] = useState(() => isStandalone());

    useEffect(() => {
        if (!show) return undefined;
        const timer = setTimeout(() => setShow(false), SPLASH_MS);
        return () => clearTimeout(timer);
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, []);

    if (!isStandalone()) return null;

    return (
        <Fade in={show} timeout={{ enter: 0, exit: 350 }} unmountOnExit>
            <Box
                aria-hidden="true"
                sx={{
                    position: 'fixed', inset: 0, zIndex: (t) => t.zIndex.modal + 10,
                    // Matches manifest background_color so the system splash
                    // hands over to this with no visible colour jump.
                    bgcolor: '#0F172A',
                    display: 'flex', flexDirection: 'column',
                    alignItems: 'center', justifyContent: 'center', gap: 3,
                    '@keyframes splashPop': {
                        '0%': { opacity: 0, transform: 'scale(0.82)' },
                        '60%': { opacity: 1, transform: 'scale(1.04)' },
                        '100%': { opacity: 1, transform: 'scale(1)' },
                    },
                    '@keyframes splashSweep': {
                        '0%': { transform: 'translateX(-100%)' },
                        '100%': { transform: 'translateX(100%)' },
                    },
                }}
            >
                <Box
                    component="img"
                    src="/logo192.png"
                    alt=""
                    sx={{
                        width: 108, height: 108, borderRadius: 4,
                        animation: 'splashPop 620ms cubic-bezier(0.34, 1.3, 0.64, 1) both',
                    }}
                />
                {/* A determinate-looking sweep rather than a spinner: the wait is
                    fixed and short, so a spinner would imply something is being
                    fetched and might stall. */}
                <Box sx={{ width: 132, height: 3, borderRadius: 2, bgcolor: 'rgba(255,255,255,0.14)', overflow: 'hidden' }}>
                    <Box
                        sx={{
                            width: '100%', height: '100%', bgcolor: '#E85D4A',
                            animation: 'splashSweep 900ms ease-in-out infinite',
                        }}
                    />
                </Box>
            </Box>
        </Fade>
    );
}
