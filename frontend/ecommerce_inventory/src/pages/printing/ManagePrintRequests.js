import { useEffect, useState, useCallback } from "react";
import {
    Box, Typography, Tabs, Tab, Table, TableBody, TableCell, TableHead, TableRow, Paper,
    TableContainer, Chip, LinearProgress, Drawer, Stack, Divider, Button, IconButton,
    TextField, Alert,
} from "@mui/material";
import CloseIcon from "@mui/icons-material/Close";
import { toast } from "react-toastify";
import useApi from "../../hooks/APIHandler";

const STATUS_COLORS = {
    SUBMITTED: "default", IN_DESIGN: "info", PROOF_READY: "warning",
    REVISION_REQUESTED: "warning", APPROVED: "success", IN_PRODUCTION: "secondary",
    READY: "primary", COMPLETED: "success", CANCELLED: "error",
};
const STATUS_TABS = ["", "SUBMITTED", "IN_DESIGN", "PROOF_READY", "REVISION_REQUESTED", "APPROVED", "IN_PRODUCTION", "READY", "COMPLETED", "CANCELLED"];

// Next legal production step from each status -- mirrors
// PrintRequest.ALLOWED_TRANSITIONS on the backend, which is the real
// enforcement; this is just what the "Advance" button offers.
const NEXT_STATUS = {
    APPROVED: "IN_PRODUCTION", IN_PRODUCTION: "READY", READY: "COMPLETED",
};

export default function ManagePrintRequests() {
    const { callApi, loading } = useApi();
    const [requests, setRequests] = useState([]);
    const [status, setStatus] = useState("");
    const [detail, setDetail] = useState(null);
    const [exportData, setExportData] = useState(null);

    const [proofUnit, setProofUnit] = useState({ image: "", note: "" });
    const [priceForm, setPriceForm] = useState({ unit_price: "", total_price: "" });
    const [notesDraft, setNotesDraft] = useState("");

    const fetchRequests = useCallback(async (st) => {
        const params = {};
        if (st) params.status = st;
        const res = await callApi({ url: "print/admin/requests/", method: "GET", params, rawError: true });
        if (res?.status === 200) setRequests(res.data.data);
        else toast.error("Could not load print requests.");
    }, []); // eslint-disable-line react-hooks/exhaustive-deps

    useEffect(() => { fetchRequests(status); }, [status, fetchRequests]);

    const openDetail = async (id) => {
        const res = await callApi({ url: `print/admin/requests/${id}/`, method: "GET", rawError: true });
        if (res?.status === 200) {
            setDetail(res.data.data);
            setNotesDraft(res.data.data.staff_notes || "");
            setExportData(null);
        } else {
            toast.error("Could not load this request.");
        }
    };

    const attachProofByUrl = async () => {
        if (!proofUnit.image.trim()) { toast.error("Paste an image URL (upload it via /api/uploads/ first) or use file upload."); return; }
        const res = await callApi({
            url: `print/admin/requests/${detail.id}/proofs/`, method: "POST",
            body: { image: proofUnit.image.trim(), note: proofUnit.note }, rawError: true,
        });
        if (res?.status === 201) {
            toast.success("Proof attached");
            setProofUnit({ image: "", note: "" });
            openDetail(detail.id);
            fetchRequests(status);
        } else {
            toast.error(res?.data?.message || "Could not attach proof");
        }
    };

    const attachProofByFile = async (file) => {
        if (!file) return;
        const fd = new FormData();
        fd.append("image", file);
        if (proofUnit.note) fd.append("note", proofUnit.note);
        const res = await callApi({
            url: `print/admin/requests/${detail.id}/proofs/`, method: "POST", body: fd,
            header: { "Content-Type": "multipart/form-data" }, rawError: true,
        });
        if (res?.status === 201) {
            toast.success("Proof attached");
            setProofUnit({ image: "", note: "" });
            openDetail(detail.id);
            fetchRequests(status);
        } else {
            toast.error(res?.data?.message || "Could not attach proof");
        }
    };

    const setPrice = async () => {
        if (!priceForm.unit_price) { toast.error("Unit price is required"); return; }
        const res = await callApi({
            url: `print/admin/requests/${detail.id}/price/`, method: "POST",
            body: { unit_price: priceForm.unit_price, total_price: priceForm.total_price || undefined },
            rawError: true,
        });
        if (res?.status === 200) {
            toast.success("Price updated");
            openDetail(detail.id);
            fetchRequests(status);
        } else {
            toast.error(res?.data?.message || "Could not update price");
        }
    };

    const advanceStatus = async (newStatus) => {
        const res = await callApi({
            url: `print/admin/requests/${detail.id}/status/`, method: "POST", body: { status: newStatus }, rawError: true,
        });
        if (res?.status === 200) {
            toast.success(`Status: ${newStatus}`);
            openDetail(detail.id);
            fetchRequests(status);
        } else {
            toast.error(res?.data?.message || "Illegal status transition");
        }
    };

    const saveNotes = async () => {
        const res = await callApi({
            url: `print/admin/requests/${detail.id}/`, method: "PATCH", body: { staff_notes: notesDraft }, rawError: true,
        });
        if (res?.status === 200) toast.success("Notes saved");
    };

    const loadExport = async () => {
        const res = await callApi({ url: `print/admin/requests/${detail.id}/export/`, method: "GET", rawError: true });
        if (res?.status === 200) setExportData(res.data.data);
    };

    return (
        <Box>
            <Typography variant="h5" fontWeight={800} sx={{ mb: 2 }}>Custom Print Requests</Typography>
            <Tabs value={status} onChange={(_, v) => setStatus(v)} variant="scrollable" sx={{ mb: 2 }}>
                {STATUS_TABS.map((s) => <Tab key={s || "all"} label={s ? s.replace(/_/g, " ") : "All"} value={s} />)}
            </Tabs>
            {loading && <LinearProgress />}
            <TableContainer component={Paper}>
                <Table>
                    <TableHead>
                        <TableRow>
                            <TableCell>ID</TableCell><TableCell>Customer</TableCell>
                            <TableCell>Garment</TableCell><TableCell>Qty</TableCell><TableCell>Status</TableCell>
                        </TableRow>
                    </TableHead>
                    <TableBody>
                        {requests.length === 0 && !loading && (
                            <TableRow><TableCell colSpan={5} align="center">No requests</TableCell></TableRow>
                        )}
                        {requests.map((r) => (
                            <TableRow key={r.id} hover sx={{ cursor: "pointer" }} onClick={() => openDetail(r.id)}>
                                <TableCell>#{r.id}</TableCell>
                                <TableCell>{r.customer_username || r.customer_email}</TableCell>
                                <TableCell>{r.product_name || r.preset_name || "--"}</TableCell>
                                <TableCell>{r.quantity}</TableCell>
                                <TableCell><Chip size="small" label={r.status} color={STATUS_COLORS[r.status] || "default"} /></TableCell>
                            </TableRow>
                        ))}
                    </TableBody>
                </Table>
            </TableContainer>

            <Drawer anchor="right" open={!!detail} onClose={() => setDetail(null)}
                PaperProps={{ sx: { width: { xs: "100%", sm: 480 }, p: 3 } }}>
                {detail && (
                    <Box>
                        <Stack direction="row" justifyContent="space-between" alignItems="center">
                            <Typography variant="h6">Request #{detail.id}</Typography>
                            <IconButton onClick={() => setDetail(null)}><CloseIcon /></IconButton>
                        </Stack>
                        <Chip size="small" sx={{ my: 1 }} label={detail.status} color={STATUS_COLORS[detail.status] || "default"} />
                        <Typography variant="body2" color="text.secondary">
                            {detail.customer_username || detail.customer_email}
                        </Typography>
                        <Divider sx={{ my: 2 }} />

                        <Typography variant="subtitle2">Brief</Typography>
                        <Typography variant="body2" sx={{ whiteSpace: "pre-wrap", mb: 2 }}>{detail.brief}</Typography>
                        <Typography variant="body2" color="text.secondary">
                            {detail.product_name || detail.preset_name || "--"} · {detail.color} · {detail.size} · Qty {detail.quantity}
                        </Typography>

                        {detail.reference_images?.length > 0 && (
                            <Box sx={{ display: "flex", gap: 1, flexWrap: "wrap", my: 1 }}>
                                {detail.reference_images.map((url) => (
                                    <Box key={url} component="img" src={url} alt="Reference"
                                        sx={{ width: 70, height: 70, objectFit: "cover", borderRadius: 1 }} />
                                ))}
                            </Box>
                        )}

                        {detail.roster_lines?.length > 0 && (
                            <>
                                <Divider sx={{ my: 2 }} />
                                <Typography variant="subtitle2" sx={{ mb: 1 }}>Roster</Typography>
                                {detail.roster_lines.map((l) => (
                                    <Typography key={l.id} variant="body2">
                                        {l.player_name} {l.number ? `#${l.number}` : ""} — {l.size} &times;{l.quantity}
                                    </Typography>
                                ))}
                            </>
                        )}

                        <Divider sx={{ my: 2 }} />
                        <Typography variant="subtitle2" sx={{ mb: 1 }}>Price</Typography>
                        {detail.agreed_unit_price != null ? (
                            <Alert severity="success" sx={{ mb: 1 }}>
                                Locked in: ৳{detail.agreed_unit_price} / item, total ৳{detail.agreed_total_price}
                            </Alert>
                        ) : (
                            <Stack direction="row" spacing={1} sx={{ mb: 1 }}>
                                <TextField size="small" label="Unit price" value={priceForm.unit_price}
                                    onChange={(e) => setPriceForm({ ...priceForm, unit_price: e.target.value })} />
                                <TextField size="small" label="Total (optional)" value={priceForm.total_price}
                                    onChange={(e) => setPriceForm({ ...priceForm, total_price: e.target.value })} />
                                <Button variant="contained" onClick={setPrice}>Set price</Button>
                            </Stack>
                        )}

                        <Divider sx={{ my: 2 }} />
                        <Typography variant="subtitle2" sx={{ mb: 1 }}>Proofs ({detail.proofs?.length || 0})</Typography>
                        {detail.proofs?.map((p) => (
                            <Box key={p.id} sx={{ mb: 1.5 }}>
                                <Typography variant="body2">
                                    v{p.version} — <Chip size="small" label={p.decision} />
                                </Typography>
                                {p.customer_feedback && (
                                    <Typography variant="caption" color="text.secondary">Feedback: {p.customer_feedback}</Typography>
                                )}
                            </Box>
                        ))}
                        {["SUBMITTED", "IN_DESIGN", "REVISION_REQUESTED"].includes(detail.status) && (
                            <Box sx={{ mb: 2 }}>
                                <Stack spacing={1}>
                                    <TextField size="small" label="Image URL (or upload below)" value={proofUnit.image}
                                        onChange={(e) => setProofUnit({ ...proofUnit, image: e.target.value })} />
                                    <TextField size="small" label="Note" value={proofUnit.note}
                                        onChange={(e) => setProofUnit({ ...proofUnit, note: e.target.value })} />
                                    <Stack direction="row" spacing={1}>
                                        <Button variant="contained" onClick={attachProofByUrl}>Attach via URL</Button>
                                        <Button variant="outlined" component="label">
                                            Upload file
                                            <input type="file" hidden accept="image/*"
                                                onChange={(e) => attachProofByFile(e.target.files?.[0])} />
                                        </Button>
                                    </Stack>
                                </Stack>
                            </Box>
                        )}

                        {NEXT_STATUS[detail.status] && (
                            <>
                                <Divider sx={{ my: 2 }} />
                                <Button variant="contained" onClick={() => advanceStatus(NEXT_STATUS[detail.status])}>
                                    Advance to {NEXT_STATUS[detail.status].replace(/_/g, " ")}
                                </Button>
                            </>
                        )}
                        {!["COMPLETED", "CANCELLED"].includes(detail.status) && (
                            <Button color="error" sx={{ mt: 1, display: "block" }} onClick={() => advanceStatus("CANCELLED")}>
                                Cancel request
                            </Button>
                        )}

                        <Divider sx={{ my: 2 }} />
                        <Typography variant="subtitle2" sx={{ mb: 1 }}>Staff notes</Typography>
                        <TextField fullWidth multiline minRows={2} size="small" value={notesDraft}
                            onChange={(e) => setNotesDraft(e.target.value)} sx={{ mb: 1 }} />
                        <Button size="small" onClick={saveNotes}>Save notes</Button>

                        <Divider sx={{ my: 2 }} />
                        <Button size="small" onClick={loadExport}>Load print-ready export data</Button>
                        {exportData && (
                            <Box component="pre" sx={{
                                mt: 1, p: 1.5, bgcolor: "action.hover", borderRadius: 1,
                                fontSize: 12, overflowX: "auto", whiteSpace: "pre-wrap",
                            }}>
                                {JSON.stringify(exportData, null, 2)}
                            </Box>
                        )}
                    </Box>
                )}
            </Drawer>
        </Box>
    );
}
