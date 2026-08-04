import React, { useEffect, useState } from 'react';
import { Box, Card, CardContent, Grid, Paper, Typography } from '@mui/material';
import useApi from '../../../hooks/APIHandler';
import { PRINT_CATEGORIES, PRINT_IMAGES, PRINT_TERMS } from './catalogue';

/**
 * Visual showcase of what we can print, shown above the request form so a
 * client sees the range before writing a brief.
 *
 * Nothing here is individually purchasable — every item routes into the same
 * brief -> proof -> approval flow, where fabric, colour, quantity and price
 * are settled.
 *
 * Items render a photo when one is mapped in PRINT_IMAGES, otherwise a
 * typographic tile. The fallback is a deliberate design, not a placeholder:
 * see the note in catalogue.js about not lifting a competitor's product
 * photography.
 */
export default function PrintCatalogue() {
    const { callApi } = useApi();
    const [uploaded, setUploaded] = useState([]);

    // Items the owner has uploaded in the admin take precedence: they are his
    // own photography, so they can carry real pictures. The static list in
    // catalogue.js remains the fallback so the page is never empty before he
    // has uploaded anything.
    useEffect(() => {
        let cancelled = false;
        (async () => {
            const res = await callApi({ url: 'print/showcase/', rawError: true });
            if (!cancelled && res?.status === 200) setUploaded(res.data?.data || []);
        })();
        return () => { cancelled = true; };
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, []);

    const groups = uploaded.length
        ? PRINT_CATEGORIES.map((cat) => ({
            ...cat,
            items: uploaded
                .filter((u) => u.category === cat.key)
                .map((u) => ({ name: u.name, note: u.note, image: u.image })),
        })).filter((cat) => cat.items.length)
        : PRINT_CATEGORIES;

    return (
        <Box sx={{ mb: 5 }}>
            <Typography variant="h6" fontWeight={700} gutterBottom>
                What we can print for you
            </Typography>
            <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                Anything below can be branded with your logo, artwork or team details. Pick what you
                have in mind and describe it in the form — you do not need a design ready.
            </Typography>

            <Paper variant="outlined" sx={{ p: 2, mb: 3, bgcolor: 'action.hover' }}>
                <Grid container spacing={2}>
                    <Grid item xs={12} sm={4}>
                        <Typography variant="caption" color="text.secondary">Minimum order</Typography>
                        <Typography variant="body2" fontWeight={600}>{PRINT_TERMS.minimumOrder}</Typography>
                    </Grid>
                    <Grid item xs={12} sm={4}>
                        <Typography variant="caption" color="text.secondary">Turnaround</Typography>
                        <Typography variant="body2" fontWeight={600}>{PRINT_TERMS.turnaround}</Typography>
                    </Grid>
                    <Grid item xs={12} sm={4}>
                        <Typography variant="caption" color="text.secondary">Artwork</Typography>
                        <Typography variant="body2" fontWeight={600}>{PRINT_TERMS.artwork}</Typography>
                    </Grid>
                </Grid>
            </Paper>

            {groups.map((cat) => (
                <Box key={cat.key} sx={{ mb: 4 }}>
                    <Typography variant="subtitle1" fontWeight={700}>{cat.title}</Typography>
                    <Typography variant="body2" color="text.secondary" sx={{ mb: 1.5 }}>
                        {cat.blurb}
                    </Typography>

                    <Grid container spacing={2}>
                        {cat.items.map((item) => (
                            <Grid item xs={6} sm={4} md={3} lg={2} key={item.name}>
                                <PrintItemCard item={item} />
                            </Grid>
                        ))}
                    </Grid>
                </Box>
            ))}
        </Box>
    );
}

function PrintItemCard({ item }) {
    // An uploaded item carries its own image; the static list falls back to
    // the PRINT_IMAGES map, then to a typographic tile.
    const image = item.image || PRINT_IMAGES[item.name];
    return (
        <Card variant="outlined" sx={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
            <Box
                sx={{
                    // Fixed 1:1 tile keeps the grid even whether the item has a
                    // photo or the typographic fallback.
                    aspectRatio: '1 / 1',
                    display: 'flex', alignItems: 'center', justifyContent: 'center',
                    p: 1.5, boxSizing: 'border-box',
                    bgcolor: image ? '#fff' : 'action.hover',
                }}
            >
                {image ? (
                    <Box
                        component="img"
                        src={image}
                        alt={item.name}
                        loading="lazy"
                        sx={{ maxWidth: '100%', maxHeight: '100%', objectFit: 'contain' }}
                    />
                ) : (
                    <Typography
                        variant="subtitle2"
                        align="center"
                        sx={{ fontWeight: 700, color: 'text.secondary', lineHeight: 1.25 }}
                    >
                        {item.name}
                    </Typography>
                )}
            </Box>
            <CardContent sx={{ p: 1.25, '&:last-child': { pb: 1.25 } }}>
                <Typography variant="body2" fontWeight={600} noWrap title={item.name}>
                    {item.name}
                </Typography>
                {item.note ? (
                    <Typography variant="caption" color="text.secondary" sx={{ display: 'block' }}>
                        {item.note}
                    </Typography>
                ) : null}
            </CardContent>
        </Card>
    );
}
