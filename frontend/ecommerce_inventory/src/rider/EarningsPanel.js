import { Card, Stack, Box, Typography, Divider, List, ListItem, ListItemText } from "@mui/material";

const Stat = ({ label, value, color }) => (
    <Box sx={{ flex: 1, textAlign: "center" }}>
        <Typography variant="h6" fontWeight={800} color={color}>৳{value}</Typography>
        <Typography variant="caption" color="text.secondary">{label}</Typography>
    </Box>
);

export default function EarningsPanel({ earnings }) {
    if (!earnings) return null;
    return (
        <Card sx={{ p: 2, mb: 2 }}>
            <Stack direction="row" divider={<Divider orientation="vertical" flexItem />}>
                <Stat label="Today / আজ" value={earnings.today} />
                <Stat label="Lifetime / মোট" value={earnings.lifetime} />
                <Stat label="Cash to hand in" value={earnings.cash_to_collect} color="warning.main" />
            </Stack>
            {earnings.history?.length > 0 && (
                <>
                    <Divider sx={{ my: 1.5 }} />
                    <Typography variant="caption" color="text.secondary">Completed deliveries</Typography>
                    <List dense>
                        {earnings.history.map((h) => (
                            <ListItem key={`${h.order_code}-${h.delivered_at}`} disableGutters>
                                <ListItemText
                                    primary={h.order_code}
                                    secondary={new Date(h.delivered_at).toLocaleString()}
                                />
                                <Typography fontWeight={700}>৳{h.payout}</Typography>
                            </ListItem>
                        ))}
                    </List>
                </>
            )}
        </Card>
    );
}
