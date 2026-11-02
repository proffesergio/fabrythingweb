import { useEffect, useState, useCallback } from "react";
import {
    Box, Typography, Button, Table, TableBody, TableCell, TableHead, TableRow, Paper,
    TableContainer, Chip, Dialog, DialogTitle, DialogContent, DialogActions, TextField,
    Stack, Alert, Grid,
} from "@mui/material";
import StorefrontIcon from "@mui/icons-material/Storefront";
import { toast } from "react-toastify";
import useApi from "../../hooks/APIHandler";

// Approval is where the commission terms are agreed, so the dialog asks for
// them rather than letting a partner go live on defaults nobody discussed.
// These mirror the model defaults (food/models.py::Restaurant).
const DEFAULT_TERMS = { commission_percentage: "12.00", min_commission_amount: "25.00" };

export default function PartnerApplications() {
    const { callApi } = useApi();
    const [rows, setRows] = useState([]);
    const [loadError, setLoadError] = useState("");
    const [approving, setApproving] = useState(null);   // the restaurant row
    const [terms, setTerms] = useState(DEFAULT_TERMS);
    const [rejecting, setRejecting] = useState(null);
    const [reason, setReason] = useState("");

    const load = useCallback(async () => {
        // rawError, or a 500 renders as "no applications" and the real failure
        // is invisible — the silent-empty-state trap.
        const res = await callApi({ url: "food/admin/partner/applications/", method: "GET", rawError: true });
        if (res?.status === 200) { setRows(res?.data?.data || []); setLoadError(""); }
        else {
            setRows([]);
            setLoadError(res?.data?.message
                || "Could not load applications. Check that database migrations have been applied.");
        }
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, []);

    useEffect(() => { load(); }, [load]);

    const decide = async (restaurant, body) => {
        const res = await callApi({
            url: `food/admin/partner/${restaurant.id}/decision/`, method: "POST", body, rawError: true,
        });
        if (res?.status === 200) {
            toast.success(res.data.message);
            setApproving(null); setRejecting(null); setReason("");
            setTerms(DEFAULT_TERMS);
            load();
        } else {
            toast.error(res?.data?.message || "Could not record the decision.");
        }
    };

    return (
        <Box sx={{ width: "100%" }}>
            <Stack direction="row" alignItems="center" spacing={1} sx={{ mb: 2 }}>
                <StorefrontIcon color="primary" />
                <Typography variant="h5">Partner applications</Typography>
                <Chip label={rows.length} size="small" color={rows.length ? "primary" : "default"} />
            </Stack>

            {loadError && <Alert severity="error" sx={{ mb: 2 }}>{loadError}</Alert>}

            {!loadError && rows.length === 0 && (
                <Alert severity="info">
                    No applications waiting. New restaurants apply at <b>/food/partner</b> and appear
                    here for approval — they stay invisible to customers until you approve them.
                </Alert>
            )}

            {rows.length > 0 && (
                <TableContainer component={Paper}>
                    <Table size="small">
                        <TableHead>
                            <TableRow>
                                <TableCell>Restaurant</TableCell>
                                <TableCell>Owner</TableCell>
                                <TableCell>Contact</TableCell>
                                <TableCell>Area</TableCell>
                                <TableCell align="right">Decision</TableCell>
                            </TableRow>
                        </TableHead>
                        <TableBody>
                            {rows.map((r) => (
                                <TableRow key={r.id} hover>
                                    <TableCell>
                                        <Typography sx={{ fontWeight: 700 }}>{r.name}</Typography>
                                        <Typography variant="caption" color="text.secondary">
                                            {r.cuisine_type || "—"} · {r.address || "no address given"}
                                        </Typography>
                                    </TableCell>
                                    <TableCell>
                                        {r.owner_name || "—"}
                                        <Typography variant="caption" color="text.secondary" display="block">
                                            login: {r.owner_username}
                                        </Typography>
                                    </TableCell>
                                    <TableCell>
                                        {r.phone}
                                        <Typography variant="caption" color="text.secondary" display="block">
                                            {r.owner_email}
                                        </Typography>
                                    </TableCell>
                                    <TableCell>{r.pickup_lat ? "pin dropped" : "—"}</TableCell>
                                    <TableCell align="right">
                                        <Stack direction="row" spacing={1} justifyContent="flex-end">
                                            <Button size="small" variant="contained"
                                                onClick={() => { setApproving(r); setTerms(DEFAULT_TERMS); }}>
                                                Approve
                                            </Button>
                                            <Button size="small" color="inherit"
                                                onClick={() => setRejecting(r)}>
                                                Reject
                                            </Button>
                                        </Stack>
                                    </TableCell>
                                </TableRow>
                            ))}
                        </TableBody>
                    </Table>
                </TableContainer>
            )}

            <Dialog open={!!approving} onClose={() => setApproving(null)} fullWidth maxWidth="xs">
                <DialogTitle>Approve {approving?.name}</DialogTitle>
                <DialogContent>
                    <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                        The platform charges <b>whichever is higher</b> of these two on each order,
                        so small orders still cover a rider and large ones still scale.
                    </Typography>
                    <Grid container spacing={2}>
                        <Grid item xs={6}>
                            <TextField label="Commission %" fullWidth value={terms.commission_percentage}
                                onChange={(e) => setTerms((t) => ({ ...t, commission_percentage: e.target.value }))} />
                        </Grid>
                        <Grid item xs={6}>
                            <TextField label="Minimum ৳" fullWidth value={terms.min_commission_amount}
                                onChange={(e) => setTerms((t) => ({ ...t, min_commission_amount: e.target.value }))} />
                        </Grid>
                    </Grid>
                </DialogContent>
                <DialogActions>
                    <Button onClick={() => setApproving(null)}>Cancel</Button>
                    <Button variant="contained"
                        onClick={() => decide(approving, { decision: "approve", ...terms })}>
                        Approve and go live
                    </Button>
                </DialogActions>
            </Dialog>

            <Dialog open={!!rejecting} onClose={() => setRejecting(null)} fullWidth maxWidth="xs">
                <DialogTitle>Reject {rejecting?.name}</DialogTitle>
                <DialogContent>
                    <TextField label="Reason (optional)" fullWidth multiline rows={3} sx={{ mt: 1 }}
                        value={reason} onChange={(e) => setReason(e.target.value)} />
                    <Typography variant="caption" color="text.secondary">
                        The owner's login is kept so you can contact them and they can re-apply.
                    </Typography>
                </DialogContent>
                <DialogActions>
                    <Button onClick={() => setRejecting(null)}>Cancel</Button>
                    <Button color="error" variant="contained"
                        onClick={() => decide(rejecting, { decision: "reject", reason })}>
                        Reject
                    </Button>
                </DialogActions>
            </Dialog>
        </Box>
    );
}
