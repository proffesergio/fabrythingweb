import React from 'react';
import { Box, Card, CardContent, Grid, Paper, Typography } from '@mui/material';
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

            {PRINT_CATEGORIES.map((cat) => (
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
    const image = PRINT_IMAGES[item.name];
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
