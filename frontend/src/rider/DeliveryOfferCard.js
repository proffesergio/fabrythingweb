import { useEffect, useRef, useState } from "react";
import { Card, Stack, Typography, Chip, Button, LinearProgress } from "@mui/material";
import TwoWheelerIcon from "@mui/icons-material/TwoWheeler";
import PlaceIcon from "@mui/icons-material/Place";
import PaymentsIcon from "@mui/icons-material/Payments";
import { motion } from "framer-motion";

// The offer TTL the server issues (services_dispatch.OFFER_TTL_SECONDS). The bar
// is cosmetic — the server is the authority on whether an offer is still live,
// and Accept returns 409 if it lapsed — so a small drift here is harmless.
const TTL = 60;

// An incoming delivery offer with a live countdown. The whole point of the offer
// model over silent assignment: the rider chooses, and can see what they are
// choosing (distance, pay, cash to carry) before they commit.
export default function DeliveryOfferCard({ offer, onAccept, onDecline, busy }) {
    const [left, setLeft] = useState(offer.seconds_left ?? TTL);
    // Reset when a *different* offer arrives, not on every poll of the same one.
    const offerId = offer.offer_id;
    const startedAt = useRef(Date.now());
    useEffect(() => {
        startedAt.current = Date.now();
        setLeft(offer.seconds_left ?? TTL);
    }, [offerId]); // eslint-disable-line react-hooks/exhaustive-deps

    useEffect(() => {
        const base = offer.seconds_left ?? TTL;
        const t = setInterval(() => {
            const elapsed = Math.floor((Date.now() - startedAt.current) / 1000);
            setLeft(Math.max(0, base - elapsed));
        }, 500);
        return () => clearInterval(t);
    }, [offerId]); // eslint-disable-line react-hooks/exhaustive-deps

    const isCash = (offer.payment_method || "COD").toUpperCase() === "COD";

    return (
        <Card
            component={motion.div}
            initial={{ opacity: 0, y: -12, scale: 0.98 }} animate={{ opacity: 1, y: 0, scale: 1 }}
            sx={{ p: 2.5, mb: 2, border: "2px solid #E8452B", borderRadius: 3,
                  boxShadow: "0 10px 30px rgba(232,69,43,0.25)" }}
        >
            <Stack direction="row" alignItems="center" spacing={1} sx={{ mb: 1 }}>
                <TwoWheelerIcon sx={{ color: "#E8452B" }} />
                <Typography sx={{ fontWeight: 900, flexGrow: 1 }}>
                    New delivery offer / নতুন ডেলিভারি
                </Typography>
                <Chip size="small" color={left <= 15 ? "error" : "default"}
                    label={`${left}s`} sx={{ fontWeight: 800 }} />
            </Stack>

            {/* Time is running out to answer — the bar makes that unmissable. */}
            <LinearProgress variant="determinate" value={(left / TTL) * 100}
                color={left <= 15 ? "error" : "primary"}
                sx={{ mb: 2, height: 6, borderRadius: 3 }} />

            <Stack spacing={0.75} sx={{ mb: 2 }}>
                <Stack direction="row" spacing={1} alignItems="center">
                    <PlaceIcon fontSize="small" color="action" />
                    <Typography sx={{ fontWeight: 700 }}>{offer.restaurant_name}</Typography>
                    {offer.distance_km && (
                        <Chip size="small" variant="outlined" label={`${offer.distance_km} km`} />
                    )}
                </Stack>
                <Typography variant="body2" color="text.secondary" sx={{ pl: 3.5 }}>
                    → {offer.delivery_address}
                </Typography>
                <Stack direction="row" spacing={1} alignItems="center" sx={{ mt: 0.5 }}>
                    <PaymentsIcon fontSize="small" color="action" />
                    <Typography variant="body2">
                        You earn <b>৳{offer.rider_pay}</b>
                    </Typography>
                    {isCash && (
                        <Chip size="small" color="warning" variant="outlined"
                            label={`Collect ৳${offer.total} cash`} />
                    )}
                </Stack>
            </Stack>

            <Stack direction="row" spacing={1.5}>
                <Button fullWidth variant="outlined" color="inherit" disabled={busy}
                    onClick={() => onDecline(offer)} sx={{ borderRadius: 999 }}>
                    Decline / না
                </Button>
                <Button fullWidth variant="contained" disabled={busy || left <= 0}
                    onClick={() => onAccept(offer)}
                    sx={{ borderRadius: 999, fontWeight: 800 }}>
                    {left <= 0 ? "Expired" : "Accept / নিচ্ছি"}
                </Button>
            </Stack>
        </Card>
    );
}
