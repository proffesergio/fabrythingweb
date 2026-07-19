import { useEffect, useState, useCallback } from "react";
import { useParams, useNavigate } from "react-router-dom";
import {
    Box, Card, CardContent, Typography, Grid, TextField, Button, Stack, Divider, Chip,
    Checkbox, FormControlLabel, LinearProgress, Breadcrumbs,
} from "@mui/material";
import { toast } from "react-toastify";
import useApi from "../../hooks/APIHandler";

const WEEKDAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];
const PROFILE_FIELDS = [
    ["name", "Name"], ["cuisine_type", "Cuisine"], ["phone", "Phone"], ["address", "Address"],
    ["commission_percentage", "Commission %"], ["base_delivery_fee", "Delivery fee"],
    ["min_order_amount", "Min order"], ["avg_prep_minutes", "Avg prep (min)"],
];

export default function RestaurantDetailAdmin() {
    const { id } = useParams();
    const navigate = useNavigate();
    const { callApi, loading } = useApi();
    const [r, setR] = useState(null);
    const [zones, setZones] = useState([]);
    const [assigned, setAssigned] = useState({}); // zoneId -> fee
    const [hours, setHours] = useState(
        WEEKDAYS.map((_, i) => ({ weekday: i, open_time: "09:00", close_time: "22:00", is_closed: false }))
    );

    const load = useCallback(async () => {
        const [detail, zoneRes] = await Promise.all([
            callApi({ url: `food/admin/restaurants/${id}/`, method: "GET" }),
            callApi({ url: "food/zones/", method: "GET" }),
        ]);
        if (detail?.status === 200) {
            setR(detail.data.data);
            if (detail.data.data.hours?.length) {
                const map = {};
                detail.data.data.hours.forEach((h) => { map[h.weekday] = h; });
                setHours(WEEKDAYS.map((_, i) => map[i] || { weekday: i, open_time: "09:00", close_time: "22:00", is_closed: false }));
            }
            const a = {};
            (detail.data.data.zones || []).forEach((z) => { a[z.id] = z.delivery_fee ?? ""; });
            setAssigned(a);
        }
        setZones(zoneRes?.data?.data || []);
    }, [id]); // eslint-disable-line react-hooks/exhaustive-deps

    useEffect(() => { load(); }, [load]);

    const saveProfile = async () => {
        const body = {};
        PROFILE_FIELDS.forEach(([k]) => { body[k] = r[k]; });
        const res = await callApi({ url: `food/admin/restaurants/${id}/`, method: "PATCH", body });
        if (res?.data) toast.success("Profile saved");
    };

    const saveHours = async () => {
        const res = await callApi({ url: `food/admin/restaurants/${id}/hours/`, method: "PUT", body: { hours } });
        if (res?.status === 200) toast.success("Hours saved");
    };

    const toggleZone = async (zone, checked) => {
        if (checked) {
            await callApi({ url: `food/admin/restaurants/${id}/zones/`, method: "POST", body: { zone_id: zone.id, delivery_fee: assigned[zone.id] || null } });
            setAssigned((a) => ({ ...a, [zone.id]: a[zone.id] ?? "" }));
        } else {
            await callApi({ url: `food/admin/restaurants/${id}/zones/`, method: "DELETE", body: { zone_id: zone.id } });
            setAssigned((a) => { const n = { ...a }; delete n[zone.id]; return n; });
        }
        toast.success("Zones updated");
    };

    const setHour = (i, k, v) => setHours((hs) => hs.map((h, idx) => (idx === i ? { ...h, [k]: v } : h)));

    if (loading && !r) return <LinearProgress />;
    if (!r) return null;

    return (
        <Box>
            <Breadcrumbs sx={{ mb: 2 }}>
                <Typography variant="body2" sx={{ cursor: "pointer" }} onClick={() => navigate("/admin/manage/food/restaurants")}>Restaurants</Typography>
                <Typography variant="body2">{r.name}</Typography>
            </Breadcrumbs>
            <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 2 }}>
                <Typography variant="h5" fontWeight={800}>{r.name} <Chip size="small" label={r.status} sx={{ ml: 1 }} /></Typography>
                <Button variant="outlined" onClick={() => navigate("/admin/manage/food/menu")}>Manage menu</Button>
            </Stack>

            <Grid container spacing={2}>
                <Grid item xs={12} md={6}>
                    <Card><CardContent>
                        <Typography variant="subtitle1" fontWeight={700} gutterBottom>Profile</Typography>
                        <Grid container spacing={2}>
                            {PROFILE_FIELDS.map(([k, label]) => (
                                <Grid item xs={12} sm={6} key={k}>
                                    <TextField label={label} fullWidth size="small" value={r[k] ?? ""}
                                        onChange={(e) => setR((prev) => ({ ...prev, [k]: e.target.value }))} />
                                </Grid>
                            ))}
                        </Grid>
                        <Button variant="contained" sx={{ mt: 2 }} onClick={saveProfile}>Save profile</Button>
                    </CardContent></Card>
                </Grid>

                <Grid item xs={12} md={6}>
                    <Card sx={{ mb: 2 }}><CardContent>
                        <Typography variant="subtitle1" fontWeight={700} gutterBottom>Opening hours</Typography>
                        {hours.map((h, i) => (
                            <Stack key={i} direction="row" spacing={1} alignItems="center" sx={{ mb: 1 }}>
                                <Typography sx={{ width: 40 }}>{WEEKDAYS[i]}</Typography>
                                <TextField size="small" type="time" value={h.open_time} onChange={(e) => setHour(i, "open_time", e.target.value)} />
                                <TextField size="small" type="time" value={h.close_time} onChange={(e) => setHour(i, "close_time", e.target.value)} />
                                <FormControlLabel control={<Checkbox checked={h.is_closed} onChange={(e) => setHour(i, "is_closed", e.target.checked)} />} label="Closed" />
                            </Stack>
                        ))}
                        <Button variant="contained" sx={{ mt: 1 }} onClick={saveHours}>Save hours</Button>
                    </CardContent></Card>

                    <Card><CardContent>
                        <Typography variant="subtitle1" fontWeight={700} gutterBottom>Delivery zones</Typography>
                        {zones.length === 0 && <Typography variant="body2" color="text.secondary">No zones defined.</Typography>}
                        {zones.map((z) => (
                            <Stack key={z.id} direction="row" alignItems="center" spacing={1} sx={{ mb: 1 }}>
                                <FormControlLabel
                                    control={<Checkbox checked={z.id in assigned} onChange={(e) => toggleZone(z, e.target.checked)} />}
                                    label={z.name} sx={{ flex: 1 }}
                                />
                                {z.id in assigned && (
                                    <TextField size="small" label="Fee override" type="number" value={assigned[z.id] ?? ""}
                                        onChange={(e) => setAssigned((a) => ({ ...a, [z.id]: e.target.value }))}
                                        onBlur={() => toggleZone(z, true)} sx={{ width: 130 }} />
                                )}
                            </Stack>
                        ))}
                    </CardContent></Card>
                </Grid>
            </Grid>
            <Divider sx={{ my: 2 }} />
        </Box>
    );
}
