import React, { useEffect, useState } from 'react';
import {
    Box, Button, Dialog, DialogContent, DialogTitle, IconButton, Paper, Slide,
    Stack, Typography,
} from '@mui/material';
import { Close, IosShare, AddBoxOutlined, GetApp } from '@mui/icons-material';
import {
    INSTALL_DELAY_MS,
    isStandalone,
    needsManualIosInstructions,
    rememberDismissal,
    shouldOfferInstall,
    wasRecentlyDismissed,
} from '../../utils/pwa';

/**
 * "Install Fabrything" bar for mobile browsers.
 *
 * Deliberately delayed and dismissible: a banner that covers the shop on the
 * first paint costs more in bounced first impressions than it wins in
 * installs, and a dismissal is remembered for 30 days so it never nags.
 *
 * iOS never fires `beforeinstallprompt` — Safari only installs through the
 * Share sheet — so there the button opens step-by-step instructions instead of
 * a native prompt. Without that branch, half the mobile market would see
 * nothing at all.
 *
 * All of the "should this show?" logic lives in utils/pwa.js and is unit
 * tested; this component is the rendering.
 */
export default function InstallPrompt() {
    const [promptEvent, setPromptEvent] = useState(null);
    const [elapsed, setElapsed] = useState(0);
    const [dismissed, setDismissed] = useState(() => wasRecentlyDismissed());
    const [iosHelpOpen, setIosHelpOpen] = useState(false);
    const [installed, setInstalled] = useState(() => isStandalone());

    const iosManual = needsManualIosInstructions();

    useEffect(() => {
        const onPrompt = (e) => {
            // Chrome shows its own mini-infobar unless this is prevented; we
            // want to choose the moment ourselves.
            e.preventDefault();
            setPromptEvent(e);
        };
        const onInstalled = () => setInstalled(true);
        window.addEventListener('beforeinstallprompt', onPrompt);
        window.addEventListener('appinstalled', onInstalled);
        const timer = setTimeout(() => setElapsed(INSTALL_DELAY_MS), INSTALL_DELAY_MS);
        return () => {
            window.removeEventListener('beforeinstallprompt', onPrompt);
            window.removeEventListener('appinstalled', onInstalled);
            clearTimeout(timer);
        };
    }, []);

    const visible = shouldOfferInstall({
        promptEvent,
        iosManual,
        standalone: installed,
        dismissed,
        elapsedMs: elapsed,
    });

    const close = () => {
        rememberDismissal();
        setDismissed(true);
    };

    const install = async () => {
        if (iosManual) {
            setIosHelpOpen(true);
            return;
        }
        if (!promptEvent) return;
        promptEvent.prompt();
        try {
            await promptEvent.userChoice;
        } catch {
            /* the browser can reject an already-consumed prompt */
        }
        // A prompt event can only be used once, whichever way they answered.
        setPromptEvent(null);
        close();
    };

    return (
        <>
            <Slide direction="up" in={visible} mountOnEnter unmountOnExit>
                <Paper
                    elevation={8}
                    role="dialog"
                    aria-label="Install Fabrything"
                    sx={{
                        position: 'fixed', left: 8, right: 8, zIndex: (t) => t.zIndex.snackbar,
                        // Clear of the mobile bottom nav / iOS home indicator.
                        bottom: { xs: 'calc(8px + env(safe-area-inset-bottom))', md: 16 },
                        p: 1.5, borderRadius: 3,
                        display: { xs: 'flex', md: 'none' },
                        alignItems: 'center', gap: 1.5,
                    }}
                >
                    <Box
                        component="img"
                        src="/logo192.png"
                        alt=""
                        sx={{ width: 44, height: 44, borderRadius: 2, flexShrink: 0 }}
                    />
                    <Box sx={{ flex: 1, minWidth: 0 }}>
                        <Typography variant="subtitle2" fontWeight={700} noWrap>
                            Install Fabrything
                        </Typography>
                        <Typography variant="caption" color="text.secondary">
                            Faster shopping, straight from your home screen.
                        </Typography>
                    </Box>
                    <Button
                        variant="contained"
                        color="secondary"
                        size="small"
                        startIcon={<GetApp />}
                        onClick={install}
                        sx={{ flexShrink: 0 }}
                    >
                        Install
                    </Button>
                    <IconButton size="small" aria-label="Dismiss install prompt" onClick={close}>
                        <Close fontSize="small" />
                    </IconButton>
                </Paper>
            </Slide>

            <Dialog open={iosHelpOpen} onClose={() => setIosHelpOpen(false)} fullWidth maxWidth="xs">
                <DialogTitle sx={{ fontWeight: 700 }}>Add to Home Screen</DialogTitle>
                <DialogContent>
                    <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                        Safari installs apps from the Share menu.
                    </Typography>
                    <Stack spacing={2}>
                        <Stack direction="row" spacing={1.5} alignItems="center">
                            <IosShare color="secondary" />
                            <Typography variant="body2">
                                1. Tap the <strong>Share</strong> button in Safari&apos;s toolbar.
                            </Typography>
                        </Stack>
                        <Stack direction="row" spacing={1.5} alignItems="center">
                            <AddBoxOutlined color="secondary" />
                            <Typography variant="body2">
                                2. Choose <strong>Add to Home Screen</strong>.
                            </Typography>
                        </Stack>
                        <Typography variant="body2">
                            3. Tap <strong>Add</strong>. Fabrything will appear with your other apps.
                        </Typography>
                    </Stack>
                </DialogContent>
            </Dialog>
        </>
    );
}
