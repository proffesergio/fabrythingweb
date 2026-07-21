import { useEffect, useRef, useState } from "react";
import {
    Card, Stack, Box, Typography, Chip, Divider, Button, Alert, List, ListItem, ListItemText,
} from "@mui/material";
import CallIcon from "@mui/icons-material/Call";
import NavigationIcon from "@mui/icons-material/Navigation";
import DeliveryMap from "./DeliveryMap";
import { haversineKm, bearingDeg } from "./geo";

const NEXT = {
    OUT_FOR_DELIVERY: ["DELIVERED", "Mark delivered / ডেলিভারি সম্পন্ন"],
    PREPARING: ["OUT_FOR_DELIVERY", "Picked up / নিয়েছি"],
    CONFIRMED: ["OUT_FOR_DELIVERY", "Picked up / নিয়েছি"],
};

const num = (v) => (v === null || v === undefined || v === "" ? null : Number(v));
const point = (lat, lng) => (num(lat) === null || num(lng) === null ? null : { lat: num(lat), lng: num(lng) });

// Three consecutive growing distances is a real wrong-turn signal; one or two is
// just GPS noise or riding around a building.
const AWAY_STREAK_LIMIT = 3;

export default function DeliveryCard({ order, riderPosition, onAdvance }) {
    const pickup = point(order.pickup_lat, order.pickup_lng);
    const dropoff = point(order.delivery_lat, order.delivery_lng);
    // Before pickup the rider rides to the restaurant; after, to the customer.
    const leg = order.status === "OUT_FOR_DELIVERY" ? "DROPOFF" : "PICKUP";
    const target = leg === "PICKUP" ? pickup : dropoff;

    const distanceKm = riderPosition && target ? haversineKm(riderPosition, target) : null;
    const heading = riderPosition && target ? bearingDeg(riderPosition, target) : null;

    const [movingAway, setMovingAway] = useState(false);
    const lastDistance = useRef(null);
    const awayStreak = useRef(0);

    useEffect(() => {
        if (distanceKm === null) return;
        if (lastDistance.current !== null) {
            if (distanceKm > lastDistance.current) awayStreak.current += 1;
            else awayStreak.current = 0;
            setMovingAway(awayStreak.current >= AWAY_STREAK_LIMIT);
        }
        lastDistance.current = distanceKm;
    }, [distanceKm]);

    const next = NEXT[order.status];
    const cash = Number(order.cash_to_collect || 0);
    const mapsUrl = target
        ? `https://www.google.com/maps/dir/?api=1&destination=${target.lat},${target.lng}&travelmode=driving`
        : "https://www.google.com/maps";

    return (
        <Card sx={{ p: 2, mb: 1.5 }}>
            <Stack direction="row" justifyContent="space-between" alignItems="center">
                <Box>
                    <Typography fontWeight={800}>{order.order_code}</Typography>
                    <Typography variant="body2" color="text.secondary">
                        {order.restaurant_name} → {order.guest_name}
                    </Typography>
                </Box>
                <Chip size="small" label={order.status.replace(/_/g, " ")} />
            </Stack>

            {cash > 0 && (
                <Chip size="small" color="warning" sx={{ mt: 1 }}
                    label={`Collect ৳${order.cash_to_collect} cash`} />
            )}

            <Divider sx={{ my: 1 }} />
            <Typography variant="caption" color="text.secondary">
                {leg === "PICKUP" ? "Pick up from / নিতে হবে" : "Deliver to / পৌঁছে দিন"}
            </Typography>
            <Typography variant="body2">
                {leg === "PICKUP" ? order.restaurant_address : order.delivery_address}
            </Typography>

            <List dense sx={{ py: 0 }}>
                {order.items?.map((it) => (
                    <ListItem key={it.id} disableGutters sx={{ py: 0.25 }}>
                        <ListItemText
                            primary={`${it.quantity} × ${it.item_name}`}
                            secondary={(it.selected_options || []).map((o) => o.name).join(", ") || null}
                        />
                        <Typography variant="body2">৳{it.line_total}</Typography>
                    </ListItem>
                ))}
            </List>

            {order.notes && <Alert severity="info" sx={{ py: 0, mb: 1 }}>{order.notes}</Alert>}

            <DeliveryMap riderPosition={riderPosition} pickup={pickup} dropoff={dropoff} leg={leg} />

            {distanceKm !== null && (
                <Stack direction="row" alignItems="center" spacing={1} sx={{ mb: 1 }}>
                    <NavigationIcon sx={{ transform: `rotate(${heading}deg)`, color: "#E8452B" }} />
                    <Typography variant="body2" fontWeight={700}>
                        {distanceKm.toFixed(2)} km to {leg === "PICKUP" ? "pickup" : "drop-off"}
                    </Typography>
                </Stack>
            )}
            {movingAway && (
                <Alert severity="warning" sx={{ mb: 1 }}>
                    You're moving away from the {leg === "PICKUP" ? "restaurant" : "drop-off"} · আপনি দূরে সরে যাচ্ছেন
                </Alert>
            )}

            <Stack direction="row" spacing={1} sx={{ mb: 1 }}>
                <Button size="small" component="a" href={`tel:${order.guest_phone}`}
                    startIcon={<CallIcon />} variant="outlined" fullWidth>
                    Call customer
                </Button>
                <Button size="small" component="a" href={`tel:${order.restaurant_phone}`}
                    startIcon={<CallIcon />} variant="outlined" fullWidth>
                    Call restaurant
                </Button>
            </Stack>
            <Button size="small" component="a" href={mapsUrl} target="_blank" rel="noreferrer"
                fullWidth sx={{ mb: 1 }}>
                Open in Google Maps
            </Button>

            {next && (
                <Button fullWidth variant="contained" onClick={() => onAdvance(order.id, next[0])}>
                    {next[1]}
                </Button>
            )}
        </Card>
    );
}
