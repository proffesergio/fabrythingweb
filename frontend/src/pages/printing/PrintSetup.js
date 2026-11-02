import { useEffect, useState, useCallback } from "react";
import {
    Box, Typography, Tabs, Tab, Table, TableBody, TableCell, TableHead, TableRow, Paper,
    TableContainer, Button, IconButton, TextField, Stack, Switch,
} from "@mui/material";
import DeleteIcon from "@mui/icons-material/Delete";
import { toast } from "react-toastify";
import useApi from "../../hooks/APIHandler";

const EMPTY_AREA = { name: "", price: "", is_active: true, display_order: 0 };
const EMPTY_PRESET = { name: "", base_price: "", is_active: true, display_order: 0 };

// Admin config for the custom-print catalog: which print locations exist and
// their price (PrintArea), which garments are offered for printing
// (PrintablePreset), and the quantity-tier bulk-discount ladder
// (PrintPricingConfig, a singleton) -- all editable here without a deploy.
export default function PrintSetup() {
    const { callApi } = useApi();
    const [tab, setTab] = useState(0);

    const [areas, setAreas] = useState([]);
    const [newArea, setNewArea] = useState(EMPTY_AREA);

    const [presets, setPresets] = useState([]);
    const [newPreset, setNewPreset] = useState(EMPTY_PRESET);

    const [tiers, setTiers] = useState([]);

    const fetchAreas = useCallback(async () => {
        const res = await callApi({ url: "print/admin/print-areas/", rawError: true });
        if (res?.status === 200) setAreas(res.data.data);
    }, []); // eslint-disable-line react-hooks/exhaustive-deps

    const fetchPresets = useCallback(async () => {
        const res = await callApi({ url: "print/admin/presets/", rawError: true });
        if (res?.status === 200) setPresets(res.data.data);
    }, []); // eslint-disable-line react-hooks/exhaustive-deps

    const fetchPricing = useCallback(async () => {
        const res = await callApi({ url: "print/admin/pricing/", rawError: true });
        if (res?.status === 200) setTiers(res.data.data.quantity_tiers || []);
    }, []); // eslint-disable-line react-hooks/exhaustive-deps

    useEffect(() => { fetchAreas(); fetchPresets(); fetchPricing(); }, [fetchAreas, fetchPresets, fetchPricing]);

    const addArea = async () => {
        if (!newArea.name.trim() || !newArea.price) { toast.error("Name and price are required"); return; }
        const res = await callApi({ url: "print/admin/print-areas/", method: "POST", body: newArea, rawError: true });
        if (res?.status === 201) { setNewArea(EMPTY_AREA); fetchAreas(); } else toast.error(res?.data?.message || "Could not add");
    };
    const updateArea = async (id, patch) => {
        const res = await callApi({ url: `print/admin/print-areas/${id}/`, method: "PATCH", body: patch, rawError: true });
        if (res?.status === 200) fetchAreas(); else toast.error("Could not update");
    };
    const deleteArea = async (id) => {
        const res = await callApi({ url: `print/admin/print-areas/${id}/`, method: "DELETE", rawError: true });
        if (res?.status === 200) fetchAreas(); else toast.error("Could not delete");
    };

    const addPreset = async () => {
        if (!newPreset.name.trim() || !newPreset.base_price) { toast.error("Name and base price are required"); return; }
        const res = await callApi({ url: "print/admin/presets/", method: "POST", body: newPreset, rawError: true });
        if (res?.status === 201) { setNewPreset(EMPTY_PRESET); fetchPresets(); } else toast.error(res?.data?.message || "Could not add");
    };
    const updatePreset = async (id, patch) => {
        const res = await callApi({ url: `print/admin/presets/${id}/`, method: "PATCH", body: patch, rawError: true });
        if (res?.status === 200) fetchPresets(); else toast.error("Could not update");
    };
    const deletePreset = async (id) => {
        const res = await callApi({ url: `print/admin/presets/${id}/`, method: "DELETE", rawError: true });
        if (res?.status === 200) fetchPresets(); else toast.error("Could not delete");
    };

    const addTier = () => setTiers((prev) => [...prev, { min_qty: 1, discount_percent: 0 }]);
    const updateTier = (idx, patch) => setTiers((prev) => prev.map((t, i) => (i === idx ? { ...t, ...patch } : t)));
    const removeTier = (idx) => setTiers((prev) => prev.filter((_, i) => i !== idx));
    const saveTiers = async () => {
        const res = await callApi({
            url: "print/admin/pricing/", method: "PUT",
            body: { quantity_tiers: tiers.map((t) => ({ min_qty: Number(t.min_qty), discount_percent: Number(t.discount_percent) })) },
            rawError: true,
        });
        if (res?.status === 200) toast.success("Pricing tiers saved"); else toast.error("Could not save tiers");
    };

    return (
        <Box>
            <Typography variant="h5" fontWeight={800} sx={{ mb: 2 }}>Custom Printing Setup</Typography>
            <Tabs value={tab} onChange={(_, v) => setTab(v)} sx={{ mb: 2 }}>
                <Tab label="Print Areas" />
                <Tab label="Garment Presets" />
                <Tab label="Quantity Discounts" />
            </Tabs>

            {tab === 0 && (
                <Box>
                    <TableContainer component={Paper} sx={{ mb: 2 }}>
                        <Table size="small">
                            <TableHead>
                                <TableRow><TableCell>Name</TableCell><TableCell>Price</TableCell><TableCell>Active</TableCell><TableCell /></TableRow>
                            </TableHead>
                            <TableBody>
                                {areas.map((a) => (
                                    <TableRow key={a.id}>
                                        <TableCell>{a.name}</TableCell>
                                        <TableCell>
                                            <TextField size="small" value={a.price}
                                                onChange={(e) => updateArea(a.id, { price: e.target.value })} sx={{ width: 100 }} />
                                        </TableCell>
                                        <TableCell>
                                            <Switch checked={a.is_active} onChange={(e) => updateArea(a.id, { is_active: e.target.checked })} />
                                        </TableCell>
                                        <TableCell>
                                            <IconButton size="small" onClick={() => deleteArea(a.id)}><DeleteIcon fontSize="small" /></IconButton>
                                        </TableCell>
                                    </TableRow>
                                ))}
                            </TableBody>
                        </Table>
                    </TableContainer>
                    <Stack direction="row" spacing={1}>
                        <TextField size="small" label="Name" value={newArea.name} onChange={(e) => setNewArea({ ...newArea, name: e.target.value })} />
                        <TextField size="small" label="Price" value={newArea.price} onChange={(e) => setNewArea({ ...newArea, price: e.target.value })} />
                        <Button variant="contained" onClick={addArea}>Add print area</Button>
                    </Stack>
                </Box>
            )}

            {tab === 1 && (
                <Box>
                    <TableContainer component={Paper} sx={{ mb: 2 }}>
                        <Table size="small">
                            <TableHead>
                                <TableRow><TableCell>Name</TableCell><TableCell>Base price</TableCell><TableCell>Active</TableCell><TableCell /></TableRow>
                            </TableHead>
                            <TableBody>
                                {presets.map((p) => (
                                    <TableRow key={p.id}>
                                        <TableCell>{p.name}</TableCell>
                                        <TableCell>
                                            <TextField size="small" value={p.base_price}
                                                onChange={(e) => updatePreset(p.id, { base_price: e.target.value })} sx={{ width: 100 }} />
                                        </TableCell>
                                        <TableCell>
                                            <Switch checked={p.is_active} onChange={(e) => updatePreset(p.id, { is_active: e.target.checked })} />
                                        </TableCell>
                                        <TableCell>
                                            <IconButton size="small" onClick={() => deletePreset(p.id)}><DeleteIcon fontSize="small" /></IconButton>
                                        </TableCell>
                                    </TableRow>
                                ))}
                            </TableBody>
                        </Table>
                    </TableContainer>
                    <Stack direction="row" spacing={1}>
                        <TextField size="small" label="Name" value={newPreset.name} onChange={(e) => setNewPreset({ ...newPreset, name: e.target.value })} />
                        <TextField size="small" label="Base price" value={newPreset.base_price} onChange={(e) => setNewPreset({ ...newPreset, base_price: e.target.value })} />
                        <Button variant="contained" onClick={addPreset}>Add preset</Button>
                    </Stack>
                </Box>
            )}

            {tab === 2 && (
                <Box>
                    <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                        The highest tier at or below the order quantity applies.
                    </Typography>
                    {tiers.map((t, idx) => (
                        <Stack key={idx} direction="row" spacing={1} alignItems="center" sx={{ mb: 1 }}>
                            <TextField size="small" type="number" label="Min qty" value={t.min_qty}
                                onChange={(e) => updateTier(idx, { min_qty: e.target.value })} sx={{ width: 120 }} />
                            <TextField size="small" type="number" label="Discount %" value={t.discount_percent}
                                onChange={(e) => updateTier(idx, { discount_percent: e.target.value })} sx={{ width: 130 }} />
                            <IconButton size="small" onClick={() => removeTier(idx)}><DeleteIcon fontSize="small" /></IconButton>
                        </Stack>
                    ))}
                    <Stack direction="row" spacing={1} sx={{ mt: 1 }}>
                        <Button onClick={addTier}>Add tier</Button>
                        <Button variant="contained" onClick={saveTiers}>Save</Button>
                    </Stack>
                </Box>
            )}
        </Box>
    );
}
