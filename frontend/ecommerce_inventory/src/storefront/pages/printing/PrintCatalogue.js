import React from 'react';
import { Box, Chip, Divider, Grid, Paper, Typography } from '@mui/material';
import { PRINT_CATEGORIES, PRINT_TERMS } from './catalogue';

/**
 * Showcase of what we can print, shown above the request form so a client can
 * see the range before writing a brief. Nothing here is individually
 * purchasable — every item goes through the same brief → proof → approval
 * flow, which is where fabric, colour, quantity and price are settled.
 */
export default function PrintCatalogue() {
    return (
        <Box sx={{ mb: 4 }}>
            <Typography variant="h6" fontWeight={700} gutterBottom>
                What we can print for you
            </Typography>
            <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                Anything below can be branded with your logo, artwork or team details. Pick what you
                have in mind and describe it in the request form — you do not need a design ready.
            </Typography>

            {/* Stated up front so nobody writes a brief for 5 pieces and is
                disappointed at the quote. */}
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

            <Grid container spacing={2}>
                {PRINT_CATEGORIES.map((cat) => (
                    <Grid item xs={12} md={6} key={cat.key}>
                        <Paper variant="outlined" sx={{ p: 2, height: '100%' }}>
                            <Typography variant="subtitle1" fontWeight={700}>{cat.title}</Typography>
                            <Typography variant="body2" color="text.secondary" sx={{ mb: 1.5 }}>
                                {cat.blurb}
                            </Typography>
                            <Divider sx={{ mb: 1.5 }} />
                            <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.75 }}>
                                {cat.items.map((item) => (
                                    <Chip
                                        key={item.name}
                                        label={item.name}
                                        title={item.note || undefined}
                                        size="small"
                                        variant="outlined"
                                    />
                                ))}
                            </Box>
                        </Paper>
                    </Grid>
                ))}
            </Grid>
        </Box>
    );
}
