import { useEffect, useState, useCallback } from "react";
import {
    Dialog, DialogTitle, DialogContent, DialogActions, Box, Card, Stack, TextField,
    Button, IconButton, Typography, Switch, FormControlLabel, Chip, Divider, MenuItem,
} from "@mui/material";
import AddIcon from "@mui/icons-material/Add";
import DeleteIcon from "@mui/icons-material/DeleteOutline";
import { toast } from "react-toastify";
import useApi from "../../hooks/APIHandler";
import FoodLoader from "./FoodLoader";

// Full modifier/add-on editor for a menu item: groups (Size, Add-ons…) each with
// required/optional + a max-choices rule, and named options with price deltas.
export default function ItemOptionsDialog({ open, item, onClose }) {
    const { callApi } = useApi();
    const [groups, setGroups] = useState([]);
    const [loading, setLoading] = useState(false);
    const [newGroup, setNewGroup] = useState({ name: "", is_required: false, max_select: 1 });
    const [optInputs, setOptInputs] = useState({}); // groupId -> {name, price_delta}

    const load = useCallback(async () => {
        if (!item) return;
        setLoading(true);
        try {
            const res = await callApi({ url: "food/admin/option-groups/", method: "GET", params: { item: item.id } });
            const gs = res?.data?.data || [];
            const withOpts = await Promise.all(gs.map(async (g) => {
                const o = await callApi({ url: "food/admin/options/", method: "GET", params: { group: g.id } });
                return { ...g, options: o?.data?.data || [] };
            }));
            setGroups(withOpts);
        } finally { setLoading(false); }
    }, [item]); // eslint-disable-line react-hooks/exhaustive-deps

    useEffect(() => { if (open) load(); }, [open, load]);

    const createGroup = async () => {
        if (!newGroup.name.trim()) return;
        const res = await callApi({ url: "food/admin/option-groups/", method: "POST", body: {
            item: item.id, name: newGroup.name, is_required: newGroup.is_required,
            min_select: newGroup.is_required ? 1 : 0, max_select: Number(newGroup.max_select) || 1,
        } });
        if (res?.status === 201) { toast.success("Modifier group added"); setNewGroup({ name: "", is_required: false, max_select: 1 }); load(); }
    };
    const deleteGroup = async (id) => { await callApi({ url: `food/admin/option-groups/${id}/`, method: "DELETE" }); load(); };
    const addOption = async (gid) => {
        const inp = optInputs[gid] || {};
        if (!inp.name?.trim()) return;
        const res = await callApi({ url: "food/admin/options/", method: "POST", body: { group: gid, name: inp.name, price_delta: inp.price_delta || "0.00" } });
        if (res?.status === 201) { setOptInputs((s) => ({ ...s, [gid]: { name: "", price_delta: "" } })); load(); }
    };
    const deleteOption = async (oid) => { await callApi({ url: `food/admin/options/${oid}/`, method: "DELETE" }); load(); };
    const setInp = (gid, k, v) => setOptInputs((s) => ({ ...s, [gid]: { ...s[gid], [k]: v } }));

    return (
        <Dialog open={open} onClose={onClose} fullWidth maxWidth="sm">
            <DialogTitle>Modifiers — {item?.name}</DialogTitle>
            <DialogContent dividers>
                {loading ? <FoodLoader label="Loading modifiers…" emoji="🧂" /> : (
                    <>
                        {groups.length === 0 && (
                            <Typography color="text.secondary" sx={{ mb: 2 }}>
                                No modifier groups yet — add one below (e.g. “Size” or “Add-ons”).
                            </Typography>
                        )}
                        {groups.map((g) => (
                            <Card key={g.id} variant="outlined" sx={{ p: 2, mb: 2, borderRadius: 3 }}>
                                <Stack direction="row" justifyContent="space-between" alignItems="center">
                                    <Box>
                                        <Typography fontWeight={800}>{g.name}</Typography>
                                        <Typography variant="caption" color="text.secondary">
                                            {g.is_required ? "Required" : "Optional"} · choose up to {g.max_select}
                                        </Typography>
                                    </Box>
                                    <IconButton size="small" color="error" onClick={() => deleteGroup(g.id)}><DeleteIcon /></IconButton>
                                </Stack>
                                <Divider sx={{ my: 1 }} />
                                {g.options.map((o) => (
                                    <Stack key={o.id} direction="row" alignItems="center" justifyContent="space-between" sx={{ py: 0.5 }}>
                                        <Typography variant="body2">{o.name}</Typography>
                                        <Stack direction="row" spacing={1} alignItems="center">
                                            <Chip size="small" label={`+৳${o.price_delta}`} />
                                            <IconButton size="small" color="error" onClick={() => deleteOption(o.id)}><DeleteIcon fontSize="small" /></IconButton>
                                        </Stack>
                                    </Stack>
                                ))}
                                <Stack direction="row" spacing={1} sx={{ mt: 1 }}>
                                    <TextField size="small" label="Option (e.g. Large)" value={optInputs[g.id]?.name || ""} onChange={(e) => setInp(g.id, "name", e.target.value)} />
                                    <TextField size="small" label="+ ৳" type="number" sx={{ width: 110 }} value={optInputs[g.id]?.price_delta || ""} onChange={(e) => setInp(g.id, "price_delta", e.target.value)} />
                                    <Button startIcon={<AddIcon />} onClick={() => addOption(g.id)}>Add</Button>
                                </Stack>
                            </Card>
                        ))}

                        <Card variant="outlined" sx={{ p: 2, borderRadius: 3, bgcolor: "rgba(244,166,42,0.07)" }}>
                            <Typography variant="subtitle2" sx={{ mb: 1 }}>New modifier group</Typography>
                            <Stack direction={{ xs: "column", sm: "row" }} spacing={1} alignItems={{ sm: "center" }}>
                                <TextField size="small" label="Group name" value={newGroup.name} onChange={(e) => setNewGroup({ ...newGroup, name: e.target.value })} />
                                <TextField size="small" select label="Max" sx={{ width: 100 }} value={newGroup.max_select} onChange={(e) => setNewGroup({ ...newGroup, max_select: e.target.value })}>
                                    {[1, 2, 3, 4, 5].map((n) => <MenuItem key={n} value={n}>{n}</MenuItem>)}
                                </TextField>
                                <FormControlLabel control={<Switch checked={newGroup.is_required} onChange={(e) => setNewGroup({ ...newGroup, is_required: e.target.checked })} />} label="Required" />
                                <Button variant="contained" startIcon={<AddIcon />} onClick={createGroup}>Add group</Button>
                            </Stack>
                        </Card>
                    </>
                )}
            </DialogContent>
            <DialogActions><Button onClick={onClose}>Done</Button></DialogActions>
        </Dialog>
    );
}
