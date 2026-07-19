import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
    Box, Grid, Card, CardContent, Typography, LinearProgress, Chip, Stack, Avatar, Button,
    Table, TableBody, TableCell, TableHead, TableRow, Divider,
} from "@mui/material";
import ReceiptLongIcon from "@mui/icons-material/ReceiptLong";
import PaidIcon from "@mui/icons-material/Paid";
import StorefrontIcon from "@mui/icons-material/Storefront";
import PendingActionsIcon from "@mui/icons-material/PendingActions";
import {
    ResponsiveContainer, AreaChart, Area, XAxis, YAxis, Tooltip, CartesianGrid,
    PieChart, Pie, Cell,
} from "recharts";
import useApi from "../../hooks/APIHandler";

const PIE_COLORS = ["#6366F1", "#10B981", "#F59E0B", "#EF4444", "#0EA5E9", "#94A3B8"];
const STATUS_COLORS = { DELIVERED: "success", CANCELLED: "error", PLACED: "warning", OUT_FOR_DELIVERY: "info" };

function StatTile({ icon, label, value, accent }) {
    return (
        <Card sx={{ height: "100%" }}>
            <CardContent>
                <Stack direction="row" alignItems="center" spacing={2}>
                    <Avatar variant="rounded" sx={{ bgcolor: accent, width: 48, height: 48 }}>{icon}</Avatar>
                    <Box>
                        <Typography variant="h5" fontWeight={800}>{value}</Typography>
                        <Typography variant="body2" color="text.secondary">{label}</Typography>
                    </Box>
                </Stack>
            </CardContent>
        </Card>
    );
}

export default function FoodDashboard() {
    const { callApi, loading } = useApi();
    const [d, setD] = useState(null);
    const navigate = useNavigate();

    useEffect(() => {
        (async () => {
            const res = await callApi({ url: "food/admin/dashboard/", method: "GET" });
            if (res?.status === 200) setD(res.data.data);
        })();
    }, []); // eslint-disable-line react-hooks/exhaustive-deps

    if (loading && !d) return <LinearProgress />;
    if (!d) return null;

    const pieData = Object.entries(d.status_distribution || {})
        .filter(([, v]) => v > 0)
        .map(([name, value]) => ({ name, value }));

    return (
        <Box>
            <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 2 }}>
                <Typography variant="h5" fontWeight={800}>Food Dashboard</Typography>
                {d.restaurants.pending > 0 && (
                    <Button size="small" variant="outlined" color="warning"
                        onClick={() => navigate("/admin/manage/food/restaurants")}>
                        {d.restaurants.pending} pending approval{d.restaurants.pending > 1 ? "s" : ""}
                    </Button>
                )}
            </Stack>

            <Grid container spacing={2} sx={{ mb: 1 }}>
                <Grid item xs={12} sm={6} md={3}>
                    <StatTile icon={<ReceiptLongIcon />} accent="#6366F1" label="Orders (total)" value={d.orders.total} />
                </Grid>
                <Grid item xs={12} sm={6} md={3}>
                    <StatTile icon={<ReceiptLongIcon />} accent="#0EA5E9" label="Orders today" value={d.orders.today} />
                </Grid>
                <Grid item xs={12} sm={6} md={3}>
                    <StatTile icon={<PaidIcon />} accent="#10B981" label="Revenue (month)" value={`৳${d.revenue.this_month}`} />
                </Grid>
                <Grid item xs={12} sm={6} md={3}>
                    <StatTile icon={<StorefrontIcon />} accent="#F59E0B" label="Active restaurants" value={d.restaurants.active} />
                </Grid>
            </Grid>

            <Grid container spacing={2} sx={{ mt: 0 }}>
                <Grid item xs={12} md={8}>
                    <Card>
                        <CardContent>
                            <Typography variant="subtitle1" fontWeight={700} gutterBottom>Revenue — last 14 days</Typography>
                            <Box sx={{ width: "100%", height: 260 }}>
                                <ResponsiveContainer width="100%" height="100%">
                                    <AreaChart data={d.revenue_trend}>
                                        <defs>
                                            <linearGradient id="rev" x1="0" y1="0" x2="0" y2="1">
                                                <stop offset="5%" stopColor="#6366F1" stopOpacity={0.5} />
                                                <stop offset="95%" stopColor="#6366F1" stopOpacity={0} />
                                            </linearGradient>
                                        </defs>
                                        <CartesianGrid strokeDasharray="3 3" opacity={0.2} />
                                        <XAxis dataKey="date" tick={{ fontSize: 11 }} />
                                        <YAxis tick={{ fontSize: 11 }} />
                                        <Tooltip />
                                        <Area type="monotone" dataKey="total" stroke="#6366F1" fill="url(#rev)" />
                                    </AreaChart>
                                </ResponsiveContainer>
                            </Box>
                        </CardContent>
                    </Card>
                </Grid>
                <Grid item xs={12} md={4}>
                    <Card sx={{ height: "100%" }}>
                        <CardContent>
                            <Typography variant="subtitle1" fontWeight={700} gutterBottom>Order status</Typography>
                            <Box sx={{ width: "100%", height: 220 }}>
                                <ResponsiveContainer width="100%" height="100%">
                                    <PieChart>
                                        <Pie data={pieData} dataKey="value" nameKey="name" innerRadius={45} outerRadius={80}>
                                            {pieData.map((_, i) => <Cell key={i} fill={PIE_COLORS[i % PIE_COLORS.length]} />)}
                                        </Pie>
                                        <Tooltip />
                                    </PieChart>
                                </ResponsiveContainer>
                            </Box>
                            <Stack spacing={0.5}>
                                {pieData.map((s, i) => (
                                    <Stack key={s.name} direction="row" justifyContent="space-between">
                                        <Typography variant="caption" sx={{ color: PIE_COLORS[i % PIE_COLORS.length] }}>{s.name}</Typography>
                                        <Typography variant="caption">{s.value}</Typography>
                                    </Stack>
                                ))}
                            </Stack>
                        </CardContent>
                    </Card>
                </Grid>
            </Grid>

            <Grid container spacing={2} sx={{ mt: 0 }}>
                <Grid item xs={12} md={7}>
                    <Card>
                        <CardContent>
                            <Typography variant="subtitle1" fontWeight={700} gutterBottom>Recent orders</Typography>
                            <Table size="small">
                                <TableHead>
                                    <TableRow>
                                        <TableCell>Code</TableCell><TableCell>Restaurant</TableCell>
                                        <TableCell>Total</TableCell><TableCell>Status</TableCell>
                                    </TableRow>
                                </TableHead>
                                <TableBody>
                                    {(d.recent_orders || []).map((o) => (
                                        <TableRow key={o.id} hover sx={{ cursor: "pointer" }}
                                            onClick={() => navigate("/admin/manage/food/orders")}>
                                            <TableCell>{o.order_code}</TableCell>
                                            <TableCell>{o.restaurant_name}</TableCell>
                                            <TableCell>৳{o.total}</TableCell>
                                            <TableCell><Chip size="small" label={o.status} color={STATUS_COLORS[o.status] || "default"} /></TableCell>
                                        </TableRow>
                                    ))}
                                </TableBody>
                            </Table>
                        </CardContent>
                    </Card>
                </Grid>
                <Grid item xs={12} md={5}>
                    <Card>
                        <CardContent>
                            <Typography variant="subtitle1" fontWeight={700} gutterBottom>Top restaurants</Typography>
                            {(d.top_restaurants || []).map((r, i) => (
                                <Box key={r.name}>
                                    <Stack direction="row" justifyContent="space-between" sx={{ py: 1 }}>
                                        <Typography variant="body2">{r.name}</Typography>
                                        <Typography variant="body2" color="text.secondary">৳{r.revenue} · {r.orders} orders</Typography>
                                    </Stack>
                                    {i < d.top_restaurants.length - 1 && <Divider />}
                                </Box>
                            ))}
                            {(!d.top_restaurants || d.top_restaurants.length === 0) && (
                                <Typography variant="body2" color="text.secondary">No orders yet.</Typography>
                            )}
                        </CardContent>
                    </Card>
                </Grid>
            </Grid>
        </Box>
    );
}
