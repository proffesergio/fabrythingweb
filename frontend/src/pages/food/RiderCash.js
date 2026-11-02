import { useEffect, useState, useCallback } from "react";
import {
    Box, Typography, Button, Table, TableBody, TableCell, TableHead, TableRow, Paper,
    TableContainer, Chip, Dialog, DialogTitle, DialogContent, DialogActions, TextField,
    Stack, Alert, Card,
} from "@mui/material";
import PaymentsIcon from "@mui/icons-material/Payments";
import { toast } from "react-toastify";
import useApi from "../../hooks/APIHandler";

// The operational answer to "who is holding the platform's money, and can I
// clear them so they keep getting cash orders". A rider over the ceiling stops
// being offered COD work (services_dispatch), so recording a deposit here is
// what puts them back in the pool — this screen is load-bearing for dispatch,
// not just reporting.
export default function RiderCash() {
    const { callApi } = useApi();
    const [data, setData] = useState(null);
    const [loadError, setLoadError] = useState("");
    const [depositing, setDepositing] = useState(null);   // the rider row
    const [amount, setAmount] = useState("");
    const [note, setNote] = useState("");

    const load = useCallback(async () => {
        const res = await callApi({ url: "food/admin/rider-cash/", method: "GET", rawError: true });
        if (res?.status === 200) { setData(res.data.data); setLoadError(""); }
        else {
            setData(null);
            setLoadError(res?.data?.message
                || "Could not load rider cash. Check that database migrations have been applied.");
        }
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, []);
    useEffect(() => { load(); }, [load]);

    const openDeposit = (rider) => { setDepositing(rider); setAmount(rider.cash_in_hand); setNote(""); };

    const submit = async () => {
        const res = await callApi({
            url: `food/admin/rider-cash/${depositing.rider_id}/deposit/`, method: "POST",
            body: { amount, note }, rawError: true,
        });
        if (res?.status === 200) {
            toast.success("Deposit recorded");
            setDepositing(null); load();
        } else {
            toast.error(res?.data?.errors?.[0] || res?.data?.message || "Could not record deposit");
        }
    };

    const riders = data?.riders || [];

    return (
        <Box sx={{ width: "100%" }}>
            <Stack direction="row" alignItems="center" spacing={1} sx={{ mb: 2 }}>
                <PaymentsIcon color="primary" />
                <Typography variant="h5">Rider cash</Typography>
            </Stack>

            {loadError && <Alert severity="error" sx={{ mb: 2 }}>{loadError}</Alert>}

            {data && (
                <Stack direction="row" spacing={2} sx={{ mb: 2, flexWrap: "wrap" }}>
                    <Card sx={{ p: 2, minWidth: 200 }}>
                        <Typography variant="caption" color="text.secondary">Outstanding across all riders</Typography>
                        <Typography variant="h5" sx={{ fontWeight: 800 }}>৳{data.total_outstanding}</Typography>
                    </Card>
                    <Card sx={{ p: 2, minWidth: 200 }}>
                        <Typography variant="caption" color="text.secondary">Cash ceiling per rider</Typography>
                        <Typography variant="h5" sx={{ fontWeight: 800 }}>৳{data.ceiling}</Typography>
                    </Card>
                </Stack>
            )}

            {data && riders.length === 0 && (
                <Alert severity="info">No riders yet. Riders holding COD cash will appear here.</Alert>
            )}

            {riders.length > 0 && (
                <TableContainer component={Paper}>
                    <Table size="small">
                        <TableHead>
                            <TableRow>
                                <TableCell>Rider</TableCell>
                                <TableCell align="right">Collected</TableCell>
                                <TableCell align="right">Deposited</TableCell>
                                <TableCell align="right">In hand</TableCell>
                                <TableCell align="center">Status</TableCell>
                                <TableCell align="right">Action</TableCell>
                            </TableRow>
                        </TableHead>
                        <TableBody>
                            {riders.map((r) => (
                                <TableRow key={r.rider_id} hover>
                                    <TableCell>{r.rider_name}</TableCell>
                                    <TableCell align="right">৳{r.collected}</TableCell>
                                    <TableCell align="right">৳{r.deposited}</TableCell>
                                    <TableCell align="right" sx={{ fontWeight: 800 }}>৳{r.cash_in_hand}</TableCell>
                                    <TableCell align="center">
                                        {r.over_ceiling
                                            ? <Chip size="small" color="error" label="Over limit — no cash orders" />
                                            : Number(r.cash_in_hand) > 0
                                                ? <Chip size="small" color="warning" variant="outlined" label="Holding cash" />
                                                : <Chip size="small" color="success" variant="outlined" label="Clear" />}
                                    </TableCell>
                                    <TableCell align="right">
                                        <Button size="small" variant="contained" disabled={Number(r.cash_in_hand) <= 0}
                                            onClick={() => openDeposit(r)}>
                                            Record deposit
                                        </Button>
                                    </TableCell>
                                </TableRow>
                            ))}
                        </TableBody>
                    </Table>
                </TableContainer>
            )}

            <Dialog open={!!depositing} onClose={() => setDepositing(null)} fullWidth maxWidth="xs">
                <DialogTitle>Deposit from {depositing?.rider_name}</DialogTitle>
                <DialogContent>
                    <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                        Holding ৳{depositing?.cash_in_hand}. Recording the deposit clears the
                        oldest COD orders it covers and lets them take cash orders again.
                    </Typography>
                    <TextField label="Amount ৳" fullWidth value={amount} sx={{ mb: 2 }}
                        onChange={(e) => setAmount(e.target.value)} autoFocus />
                    <TextField label="Note (optional)" fullWidth value={note}
                        onChange={(e) => setNote(e.target.value)} />
                </DialogContent>
                <DialogActions>
                    <Button onClick={() => setDepositing(null)}>Cancel</Button>
                    <Button variant="contained" onClick={submit}>Record</Button>
                </DialogActions>
            </Dialog>
        </Box>
    );
}
