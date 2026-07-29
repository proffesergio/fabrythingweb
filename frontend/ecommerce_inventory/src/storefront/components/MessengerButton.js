import React, { useEffect, useState } from 'react';
import { Fab, Tooltip } from '@mui/material';
import { Chat as ChatIcon } from '@mui/icons-material';
import useApi from '../../hooks/APIHandler';

// Floating deep link to the store's Facebook Page Messenger thread
// (https://m.me/<page id or username>). Meta discontinued the embeddable
// Customer Chat Plugin (fb-customerchat / MessengerExtensions) in 2024, so
// this is a plain new-tab link rather than an in-page widget — see
// docs/MESSENGER_SETUP.md.
//
// Dormant by default: renders nothing until the owner sets
// `messenger_page_id` on the StoreConfiguration singleton (Django admin ->
// Core -> Store configurations). That keeps this safe to ship ahead of the
// owner wiring up their Page — no broken link, no empty floating circle.
//
// `ref=website_floating_button` is appended to the link so Messenger passes
// it through to the page inbox/webhook, the supported way to attribute a
// conversation's origin (see docs/MESSENGER_SETUP.md for exactly what that
// does and does not make visible in Meta Business Suite).
export default function MessengerButton() {
    const [pageId, setPageId] = useState('');
    const { callApi } = useApi();

    useEffect(() => {
        let mounted = true;
        callApi({ url: 'store/config/' }).then(res => {
            const id = res?.data?.data?.messenger_page_id;
            if (mounted && id) setPageId(id);
        });
        return () => { mounted = false; };
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, []);

    if (!pageId) return null;

    const href = `https://m.me/${encodeURIComponent(pageId)}?ref=website_floating_button`;

    return (
        <Tooltip title="Message us on Facebook">
            <Fab
                component="a"
                href={href}
                target="_blank"
                rel="noopener noreferrer"
                aria-label="Message us on Facebook Messenger"
                color="primary"
                sx={{
                    position: 'fixed',
                    right: { xs: 16, md: 24 },
                    // Clears the mobile BottomNavigation — 56px tall, fixed
                    // at bottom:0 with zIndex 1200 (StorefrontLayout.js) —
                    // with room to spare. Desktop has no bottom nav, so a
                    // small inset is enough there.
                    bottom: { xs: 'calc(56px + 16px)', md: 24 },
                    zIndex: (theme) => theme.zIndex.speedDial,
                    minWidth: 44,
                    minHeight: 44,
                }}
            >
                <ChatIcon />
            </Fab>
        </Tooltip>
    );
}
