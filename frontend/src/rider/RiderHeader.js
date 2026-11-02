import { Box, Card, Stack, Avatar, Typography, Switch, FormControlLabel } from "@mui/material";

// Profile strip + the Online switch that drives the heartbeat. Bilingual, as
// riders here read Bangla more comfortably than English.
export default function RiderHeader({ me, online, onToggle, locationError }) {
    return (
        <Card sx={{ p: 2.5, mb: 2 }}>
            <Stack direction="row" alignItems="center" spacing={2}>
                <Avatar sx={{ bgcolor: "#E8452B", width: 48, height: 48 }}>{(me.name || "?")[0]}</Avatar>
                <Box sx={{ flexGrow: 1 }}>
                    <Typography fontWeight={800}>{me.name}</Typography>
                    <Typography variant="caption" color="text.secondary">
                        {me.rider_code} · {me.total_deliveries} deliveries · ৳{me.total_earnings} earned
                    </Typography>
                </Box>
                <FormControlLabel
                    labelPlacement="top"
                    control={<Switch checked={online} onChange={(e) => onToggle(e.target.checked)} />}
                    label={<Typography variant="caption">{online ? "Online / অনলাইন" : "Offline / অফলাইন"}</Typography>}
                />
            </Stack>
            <Typography variant="caption" color="text.secondary" display="block" sx={{ mt: 1 }}>
                Location is shared only while you are online · আপনি অনলাইনে থাকলেই কেবল অবস্থান শেয়ার হয়
            </Typography>
            {online && locationError && (
                <Typography variant="caption" color="error" display="block">{locationError}</Typography>
            )}
        </Card>
    );
}
