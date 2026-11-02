import { useEffect, useState, useCallback, Fragment } from "react";
import {
    Box, Typography, Tabs, Tab, Table, TableBody, TableCell, TableHead, TableRow, Paper,
    TableContainer, Chip, Stack, Pagination, Card, CardContent, Grid, Button, Checkbox,
    Collapse, IconButton, Alert, Tooltip, Divider,
} from "@mui/material";
import PaidIcon from "@mui/icons-material/Paid";
import ExpandMoreIcon from "@mui/icons-material/ExpandMore";
import ExpandLessIcon from "@mui/icons-material/ExpandLess";
import { toast } from "react-toastify";
import useApi from "../../hooks/APIHandler";

// The four money movements on a delivered order. Order matters — this is the
// sequence cash actually travels in.
const LEGS = [
    { key: "customer_payment", label: "Customer paid", short: "Customer",
      help: "The customer's money is in hand (COD cash collected, or mobile payment confirmed)." },
    { key: "rider_cash", label: "Rider handed cash over", short: "Cash in",
      help: "The rider turned in the COD cash they collected on this order." },
    { key: "rider_payout", label: "Rider paid", short: "Rider paid",
      help: "We paid the rider their base pay plus tip for this delivery." },
    { key: "restaurant_payout", label: "Restaurant paid", short: "Restaurant paid",
      help: "We paid the restaurant their share, after platform commission." },
];

const STATUS_COLOR = { SETTLED: "success", PENDING: "warning", NA: "default" };
const STATUS_LABEL = { SETTLED: "Paid", PENDING: "Pending", NA: "—" };

const taka = (v) => `৳${Number(v || 0).toLocaleString("en-BD", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;

function SummaryCard({ label, value, hint, color }) {
    return (
        <Card variant="outlined" sx={{ height: "100%" }}>
            <CardContent>
                <Typography variant="caption" color="text.secondary">{label}</Typography>
                <Typography variant="h6" fontWeight={800} color={color}>{value}</Typography>
                {hint && <Typography variant="caption" color="text.secondary">{hint}</Typography>}
            </CardContent>
        </Card>
    );
}

function MoneyRow({ label, value, bold, color }) {
    return (
        <Stack direction="row" justifyContent="space-between">
            <Typography variant="body2" color={bold ? "text.primary" : "text.secondary"} fontWeight={bold ? 700 : 400}>
                {label}
            </Typography>
            <Typography variant="body2" fontWeight={bold ? 800 : 600} color={color}>{value}</Typography>
        </Stack>
    );
}

export default function FoodPayments() {
    const { callApi } = useApi();
    const [rows, setRows] = useState([]);
    const [summary, setSummary] = useState(null);
    const [legTab, setLegTab] = useState("");        // "" = all
    const [page, setPage] = useState(1);
    const [totalPages, setTotalPages] = useState(1);
    const [expanded, setExpanded] = useState(null);
    const [selected, setSelected] = useState([]);
    const [error, setError] = useState("");

    const load = useCallback(async () => {
        const params = { page };
        // Each tab shows the orders still pending on that one leg.
        if (legTab) { params.leg = legTab; params.status = "PENDING"; }

        const res = await callApi({ url: "food/admin/settlements/", method: "GET", params, rawError: true });
        if (res?.status === 200) {
            setRows(res.data.data.data || []);
            setTotalPages(res.data.data.totalPages || 1);
            setError("");
        } else {
            setRows([]);
            setError(res?.data?.message || "Could not load settlements. Check that migrations have been applied.");
        }

        const sres = await callApi({ url: "food/admin/settlements/summary/", method: "GET", rawError: true });
        if (sres?.status === 200) setSummary(sres.data.data);
    }, [legTab, page]); // eslint-disable-line react-hooks/exhaustive-deps

    useEffect(() => { load(); }, [load]);
    useEffect(() => { setSelected([]); }, [legTab, page]);

    const settle = async (id, leg, settled) => {
        const res = await callApi({
            url: `food/admin/settlements/${id}/leg/`,
            method: "POST", body: { leg, settled }, rawError: true,
        });
        if (res?.status === 200) { toast.success(settled ? "Marked paid" : "Reverted to pending"); load(); }
        else toast.error(res?.data?.message || "Could not update");
    };

    const settleBulk = async () => {
        if (!legTab || selected.length === 0) return;
        const res = await callApi({
            url: "food/admin/settlements/bulk/",
            method: "POST", body: { ids: selected, leg: legTab, settled: true }, rawError: true,
        });
        if (res?.status === 200) {
            toast.success(`${res.data.data.updated} settled`);
            setSelected([]);
            load();
        } else toast.error(res?.data?.message || "Could not update");
    };

    const toggleSel = (id) =>
        setSelected((s) => (s.includes(id) ? s.filter((x) => x !== id) : [...s, id]));

    const out = summary?.outstanding || {};

    return (
        <Box>
            <Stack direction="row" spacing={1} alignItems="center" sx={{ mb: 2 }}>
                <PaidIcon color="primary" />
                <Typography variant="h5" fontWeight={800}>Payments &amp; settlements</Typography>
            </Stack>

            {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}

            {summary && (
                <Grid container spacing={2} sx={{ mb: 3 }}>
                    <Grid item xs={12} sm={6} md={3}>
                        <SummaryCard label="Platform revenue" value={taka(summary.platform_revenue)}
                                     hint={`${summary.orders} delivered order(s)`} color="success.main" />
                    </Grid>
                    <Grid item xs={12} sm={6} md={3}>
                        <SummaryCard label="Cash to collect" value={taka(out.rider_cash)}
                                     hint={`${summary.counts?.rider_cash || 0} with riders`} color="warning.main" />
                    </Grid>
                    <Grid item xs={12} sm={6} md={3}>
                        <SummaryCard label="Owed to riders" value={taka(out.rider_payout)}
                                     hint={`${summary.counts?.rider_payout || 0} unpaid`} color="error.main" />
                    </Grid>
                    <Grid item xs={12} sm={6} md={3}>
                        <SummaryCard label="Owed to restaurants" value={taka(out.restaurant_payout)}
                                     hint={`${summary.counts?.restaurant_payout || 0} unpaid`} color="error.main" />
                    </Grid>
                </Grid>
            )}

            <Tabs value={legTab} onChange={(_, v) => { setPage(1); setLegTab(v); }}
                  variant="scrollable" scrollButtons="auto" sx={{ mb: 2 }}>
                <Tab label="All delivered" value="" />
                {LEGS.map((l) => (
                    <Tab
                        key={l.key}
                        value={l.key}
                        label={`${l.label} — pending${summary ? ` (${summary.counts?.[l.key] ?? 0})` : ""}`}
                    />
                ))}
            </Tabs>

            {legTab && selected.length > 0 && (
                <Stack direction="row" spacing={1} alignItems="center" sx={{ mb: 2 }}>
                    <Button variant="contained" onClick={settleBulk}>
                        Mark {selected.length} as {LEGS.find((l) => l.key === legTab)?.label.toLowerCase()}
                    </Button>
                    <Button onClick={() => setSelected([])}>Clear</Button>
                </Stack>
            )}

            <TableContainer component={Paper}>
                <Table size="small">
                    <TableHead><TableRow>
                        {legTab && <TableCell padding="checkbox" />}
                        <TableCell />
                        <TableCell>Order</TableCell>
                        <TableCell>Restaurant</TableCell>
                        <TableCell>Delivered by</TableCell>
                        <TableCell align="right">Order total</TableCell>
                        {LEGS.map((l) => (
                            <TableCell key={l.key} align="center">
                                <Tooltip title={l.help}><span>{l.short}</span></Tooltip>
                            </TableCell>
                        ))}
                    </TableRow></TableHead>
                    <TableBody>
                        {rows.length === 0 && !error && (
                            <TableRow>
                                <TableCell colSpan={legTab ? 10 : 9} align="center" sx={{ py: 4 }}>
                                    <Typography color="text.secondary">
                                        Nothing here. Settlements are created when an order is marked delivered.
                                    </Typography>
                                </TableCell>
                            </TableRow>
                        )}
                        {rows.map((s) => (
                            <Fragment key={s.id}>
                                <TableRow hover>
                                    {legTab && (
                                        <TableCell padding="checkbox">
                                            <Checkbox size="small" checked={selected.includes(s.id)}
                                                      onChange={() => toggleSel(s.id)} />
                                        </TableCell>
                                    )}
                                    <TableCell>
                                        <IconButton size="small"
                                                    onClick={() => setExpanded(expanded === s.id ? null : s.id)}>
                                            {expanded === s.id ? <ExpandLessIcon fontSize="small" /> : <ExpandMoreIcon fontSize="small" />}
                                        </IconButton>
                                    </TableCell>
                                    <TableCell>
                                        <Typography variant="body2" fontWeight={700}>{s.order_code}</Typography>
                                        <Typography variant="caption" color="text.secondary">
                                            {s.delivered_at ? new Date(s.delivered_at).toLocaleString() : "—"} · {s.payment_method}
                                        </Typography>
                                    </TableCell>
                                    <TableCell>{s.restaurant_name}</TableCell>
                                    <TableCell>
                                        {s.rider_name || <Chip size="small" label="Unassigned" variant="outlined" />}
                                    </TableCell>
                                    <TableCell align="right">
                                        <Typography fontWeight={700}>{taka(s.order_total)}</Typography>
                                    </TableCell>
                                    {LEGS.map((l) => {
                                        const status = s[`${l.key}_status`];
                                        return (
                                            <TableCell key={l.key} align="center">
                                                <Chip
                                                    size="small"
                                                    label={STATUS_LABEL[status] || status}
                                                    color={STATUS_COLOR[status] || "default"}
                                                    variant={status === "NA" ? "outlined" : "filled"}
                                                    // An NA leg has no money in it — nothing to toggle.
                                                    onClick={status === "NA" ? undefined
                                                        : () => settle(s.id, l.key, status !== "SETTLED")}
                                                    sx={{ cursor: status === "NA" ? "default" : "pointer" }}
                                                />
                                            </TableCell>
                                        );
                                    })}
                                </TableRow>
                                <TableRow>
                                    <TableCell colSpan={legTab ? 10 : 9} sx={{ py: 0, border: 0 }}>
                                        <Collapse in={expanded === s.id} timeout="auto" unmountOnExit>
                                            <Box sx={{ py: 2, px: 1 }}>
                                                <Grid container spacing={3}>
                                                    <Grid item xs={12} md={4}>
                                                        <Typography variant="subtitle2" fontWeight={800} gutterBottom>
                                                            What the customer paid
                                                        </Typography>
                                                        <MoneyRow label="Food (after discount)" value={taka(s.food_net)} />
                                                        <MoneyRow label="Delivery fee" value={taka(s.delivery_fee)} />
                                                        <MoneyRow label="Tip" value={taka(s.tip)} />
                                                        <Divider sx={{ my: 1 }} />
                                                        <MoneyRow label="Order total" value={taka(s.order_total)} bold />
                                                    </Grid>
                                                    <Grid item xs={12} md={4}>
                                                        <Typography variant="subtitle2" fontWeight={800} gutterBottom>
                                                            Who gets what
                                                        </Typography>
                                                        <MoneyRow label={`Restaurant (after ${s.commission_rate}% commission)`}
                                                                  value={taka(s.restaurant_payout)} />
                                                        <MoneyRow label={`Rider (${taka(s.rider_base_pay)} + ${taka(s.tip)} tip)`}
                                                                  value={taka(s.rider_payout)} />
                                                        <MoneyRow label="Platform commission" value={taka(s.commission_amount)} />
                                                        <Divider sx={{ my: 1 }} />
                                                        <MoneyRow label="Platform revenue" value={taka(s.platform_revenue)}
                                                                  bold color="success.main" />
                                                    </Grid>
                                                    <Grid item xs={12} md={4}>
                                                        <Typography variant="subtitle2" fontWeight={800} gutterBottom>
                                                            Settlement
                                                        </Typography>
                                                        <Stack spacing={1}>
                                                            {LEGS.map((l) => {
                                                                const status = s[`${l.key}_status`];
                                                                const at = s[`${l.key}_at`];
                                                                return (
                                                                    <Stack key={l.key} direction="row"
                                                                           justifyContent="space-between" alignItems="center">
                                                                        <Box>
                                                                            <Typography variant="body2">{l.label}</Typography>
                                                                            {at && (
                                                                                <Typography variant="caption" color="text.secondary">
                                                                                    {new Date(at).toLocaleString()}
                                                                                </Typography>
                                                                            )}
                                                                        </Box>
                                                                        {status === "NA" ? (
                                                                            <Chip size="small" label="N/A" variant="outlined" />
                                                                        ) : (
                                                                            <Button
                                                                                size="small"
                                                                                variant={status === "SETTLED" ? "outlined" : "contained"}
                                                                                color={status === "SETTLED" ? "inherit" : "primary"}
                                                                                onClick={() => settle(s.id, l.key, status !== "SETTLED")}
                                                                            >
                                                                                {status === "SETTLED" ? "Undo" : "Mark paid"}
                                                                            </Button>
                                                                        )}
                                                                    </Stack>
                                                                );
                                                            })}
                                                        </Stack>
                                                    </Grid>
                                                </Grid>
                                            </Box>
                                        </Collapse>
                                    </TableCell>
                                </TableRow>
                            </Fragment>
                        ))}
                    </TableBody>
                </Table>
            </TableContainer>

            {totalPages > 1 && (
                <Stack alignItems="center" sx={{ mt: 2 }}>
                    <Pagination count={totalPages} page={page} onChange={(_, p) => setPage(p)} color="primary" />
                </Stack>
            )}
        </Box>
    );
}
