import { useCallback, useEffect, useState } from "react";
import {
    Alert, Box, Button, Chip, Dialog, DialogActions, DialogContent, DialogTitle,
    IconButton, Stack, Switch, Table, TableBody, TableCell, TableContainer,
    TableHead, TableRow, Paper, TextField, Typography, Tooltip,
} from "@mui/material";
import { Add, Delete, Save } from "@mui/icons-material";
import { toast } from "react-toastify";
import useApi from "../../hooks/APIHandler";

/**
 * Village editor for one delivery zone (union).
 *
 * Villages carry both an English `name` and a Bangla `name_bn`. Customers see
 * `name_bn` when it is filled and the English name otherwise, so a blank Bangla
 * field is a visible gap in the customer address picker — it's flagged here.
 *
 * Edits made here survive deploys: seed_bancharampur is create-only and never
 * overwrites an existing row (food/tests/test_seed_preserves_edits.py).
 */
export default function ZoneVillagesDialog({ zone, open, onClose, onChanged }) {
    const { callApi } = useApi();
    const [villages, setVillages] = useState([]);
    const [draft, setDraft] = useState({ name: "", name_bn: "" });
    const [edits, setEdits] = useState({});   // id -> { name, name_bn }
    const [error, setError] = useState("");

    const load = useCallback(async () => {
        if (!zone) return;
        const res = await callApi({
            url: "food/admin/villages/", method: "GET",
            params: { zone: zone.id }, rawError: true,
        });
        if (res?.status === 200) {
            setVillages(res.data?.data || []);
            setEdits({});
            setError("");
        } else {
            setVillages([]);
            setError(res?.data?.message || "Could not load villages.");
        }
    }, [zone]); // eslint-disable-line react-hooks/exhaustive-deps

    useEffect(() => { if (open) load(); }, [open, load]);

    const add = async () => {
        if (!draft.name.trim()) { toast.error("English name is required"); return; }
        const res = await callApi({
            url: "food/admin/villages/", method: "POST",
            body: { zone: zone.id, name: draft.name.trim(), name_bn: draft.name_bn.trim(), is_active: true },
            rawError: true,
        });
        if (res?.status === 201) {
            toast.success("Village added");
            setDraft({ name: "", name_bn: "" });
            load();
            onChanged?.();
        } else {
            const errs = res?.data?.errors;
            toast.error(Array.isArray(errs) ? errs.join(" ") : "Could not add village");
        }
    };

    const save = async (v) => {
        const patch = edits[v.id];
        if (!patch) return;
        const res = await callApi({
            url: `food/admin/villages/${v.id}/`, method: "PATCH", body: patch, rawError: true,
        });
        if (res?.status === 200) {
            toast.success("Saved");
            setEdits((e) => { const n = { ...e }; delete n[v.id]; return n; });
            load();
        } else toast.error("Could not save");
    };

    const toggleActive = async (v) => {
        await callApi({
            url: `food/admin/villages/${v.id}/`, method: "PATCH",
            body: { is_active: !v.is_active },
        });
        load();
    };

    const remove = async (v) => {
        // Villages are referenced by past orders via SET_NULL, so deleting one
        // does not destroy order history — but it does disappear from the
        // customer picker. Deactivating is usually what you want.
        if (!window.confirm(`Delete "${v.name}"? Deactivating it instead keeps it out of the customer picker without removing it.`)) return;
        await callApi({ url: `food/admin/villages/${v.id}/`, method: "DELETE" });
        load();
        onChanged?.();
    };

    const edit = (id, field) => (e) =>
        setEdits((s) => ({ ...s, [id]: { ...(s[id] || {}), [field]: e.target.value } }));

    const valueOf = (v, field) => (edits[v.id]?.[field] ?? v[field] ?? "");
    const missingBn = villages.filter((v) => !v.name_bn).length;

    return (
        <Dialog open={open} onClose={onClose} maxWidth="md" fullWidth>
            <DialogTitle>
                Villages in {zone?.name}
                {zone?.name_bn && (
                    <Typography component="span" color="text.secondary"> · {zone.name_bn}</Typography>
                )}
            </DialogTitle>
            <DialogContent>
                {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}
                {missingBn > 0 && (
                    <Alert severity="warning" sx={{ mb: 2 }}>
                        {missingBn === 1
                            ? "1 village has no Bangla name"
                            : `${missingBn} villages have no Bangla name`} — customers will see the
                        English name for those.
                    </Alert>
                )}

                <Stack direction={{ xs: "column", sm: "row" }} spacing={1} sx={{ mb: 2 }}>
                    <TextField
                        size="small" label="New village (English)" value={draft.name}
                        onChange={(e) => setDraft({ ...draft, name: e.target.value })} fullWidth
                    />
                    <TextField
                        size="small" label="নতুন গ্রাম (বাংলা)" value={draft.name_bn}
                        onChange={(e) => setDraft({ ...draft, name_bn: e.target.value })} fullWidth
                    />
                    <Button variant="contained" startIcon={<Add />} onClick={add} sx={{ flexShrink: 0 }}>
                        Add
                    </Button>
                </Stack>

                <TableContainer component={Paper} variant="outlined">
                    <Table size="small">
                        <TableHead>
                            <TableRow>
                                <TableCell>English name</TableCell>
                                <TableCell>বাংলা নাম</TableCell>
                                <TableCell align="center">Shown to customer</TableCell>
                                <TableCell align="center">Active</TableCell>
                                <TableCell align="right">Actions</TableCell>
                            </TableRow>
                        </TableHead>
                        <TableBody>
                            {villages.length === 0 && (
                                <TableRow>
                                    <TableCell colSpan={5} align="center">No villages in this union yet</TableCell>
                                </TableRow>
                            )}
                            {villages.map((v) => (
                                <TableRow key={v.id} hover>
                                    <TableCell>
                                        <TextField variant="standard" fullWidth
                                                   value={valueOf(v, "name")} onChange={edit(v.id, "name")} />
                                    </TableCell>
                                    <TableCell>
                                        <TextField variant="standard" fullWidth placeholder="বাংলা নাম লিখুন"
                                                   value={valueOf(v, "name_bn")} onChange={edit(v.id, "name_bn")} />
                                    </TableCell>
                                    <TableCell align="center">
                                        <Chip size="small" variant="outlined"
                                              label={valueOf(v, "name_bn") || valueOf(v, "name")} />
                                    </TableCell>
                                    <TableCell align="center">
                                        <Switch size="small" checked={!!v.is_active} onChange={() => toggleActive(v)} />
                                    </TableCell>
                                    <TableCell align="right">
                                        <Tooltip title="Save changes">
                                            <span>
                                                <IconButton size="small" color="primary"
                                                            disabled={!edits[v.id]} onClick={() => save(v)}>
                                                    <Save fontSize="small" />
                                                </IconButton>
                                            </span>
                                        </Tooltip>
                                        <IconButton size="small" color="error" onClick={() => remove(v)}>
                                            <Delete fontSize="small" />
                                        </IconButton>
                                    </TableCell>
                                </TableRow>
                            ))}
                        </TableBody>
                    </Table>
                </TableContainer>
                <Box sx={{ mt: 1 }}>
                    <Typography variant="caption" color="text.secondary">
                        {villages.length} village{villages.length === 1 ? "" : "s"}. Edits here are permanent —
                        deploys never overwrite them.
                    </Typography>
                </Box>
            </DialogContent>
            <DialogActions>
                <Button onClick={onClose}>Done</Button>
            </DialogActions>
        </Dialog>
    );
}
