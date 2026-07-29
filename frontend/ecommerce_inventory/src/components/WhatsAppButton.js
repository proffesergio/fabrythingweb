import React, { useEffect, useState } from 'react';
import { Fab, Tooltip } from '@mui/material';
import WhatsAppIcon from '@mui/icons-material/WhatsApp';
import useApi from '../hooks/APIHandler';

// Floating WhatsApp chat link (https://wa.me/<number>), shared by the
// storefront and the food-delivery frontend -- the owner asked for it
// site-wide except admin/vendor/rider panels, which don't render this
// component at all.
//
// Dormant by default, same pattern as MessengerButton: renders nothing until
// the owner sets `whatsapp_chat_number` on the StoreConfiguration singleton
// (Django admin -> Core -> Store configurations), read from the same public
// `store/config/` endpoint both frontends already call for Messenger. That
// keeps this safe to ship ahead of / independent of the owner changing the
// number -- no broken link, no empty floating circle.
//
// `bottom` is left to the caller: each layout has its own floating furniture
// (storefront: mobile BottomNavigation + MessengerButton; food: the phone tab
// bar + the sticky "view bag" bar) that this button must clear rather than
// cover, so neither layout can share one hardcoded offset.
export default function WhatsAppButton({ bottom, prefilledMessage }) {
    const [number, setNumber] = useState('');
    const { callApi } = useApi();

    useEffect(() => {
        let mounted = true;
        callApi({ url: 'store/config/' }).then(res => {
            const n = res?.data?.data?.whatsapp_chat_number;
            if (mounted && n) setNumber(n);
        });
        return () => { mounted = false; };
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, []);

    if (!number) return null;

    const href = `https://wa.me/${number}${prefilledMessage ? `?text=${encodeURIComponent(prefilledMessage)}` : ''}`;

    return (
        <Tooltip title="Chat with us on WhatsApp">
            <Fab
                component="a"
                href={href}
                target="_blank"
                rel="noopener noreferrer"
                aria-label="Chat with us on WhatsApp"
                color="success"
                sx={{
                    position: 'fixed',
                    right: { xs: 16, md: 24 },
                    bottom: bottom ?? { xs: 16, md: 24 },
                    zIndex: (theme) => theme.zIndex.speedDial,
                    minWidth: 44,
                    minHeight: 44,
                }}
            >
                <WhatsAppIcon />
            </Fab>
        </Tooltip>
    );
}
