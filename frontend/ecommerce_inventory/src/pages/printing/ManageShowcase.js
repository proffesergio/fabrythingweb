import { useEffect, useState, useCallback } from "react";
import {
    Box, Typography, Table, TableBody, TableCell, TableHead, TableRow, Paper,
    TableContainer, Chip, LinearProgress, Button, IconButton, TextField, Stack,
    Switch, MenuItem, Card,
} from "@mui/material";
import DeleteIcon from "@mui/icons-material/Delete";
import EditIcon from "@mui/icons-material/Edit";
import axios from "axios";
import { toast } from "react-toastify";
import useApi from "../../hooks/APIHandler";
import config from "../../utils/config";
import { getToken } from "../../utils/authToken";
import { PRESS_STRIP, PRESS_BADGES, categoryTitle } from "../../storefront/pages/printing/pressCategories";

// Design showcase manager: upload design files in any print format
// (pdf/ai/psd/eps/tiff/png/jpeg), assign a category, badge, BDT price and
// Top-Pick flag. Everything here renders on the storefront's
// ColorLifePrint-style catalog instantly — no deploy.
const GARMENT_CATS = [
    { key: "apparel", title: "Apparel (t-shirt flow)" },
    { key: "headwear-bags", title: "Headwear & bags" },
    { key: "drinkware", title: "Drinkware" },
    { key: "office", title: "Office & stationery" },
    { key: "accessories-tech", title: "Accessories & tech" },
];
const ALL_CATS = [...PRESS_STRIP, ...GARMENT_CATS];
const ACCEPTED = ".pdf,.ai,.psd,.eps,.tiff,.tif,.png,.jpg,.jpeg,.svg,.webp";

const EMPTY = {
    name: "", category: "business-cards", note: "", description: "",
    image: "", file_url: "", file_type: "", badge: "", price_bdt: "",
    is_top_pick: true, press_product: "", is_active: true, display_order: 0,
};

export default function ManageShowcase() {
    const { callApi } = useApi();
    const [items, setItems] = useState([]);
    const [products, setProducts] = useState([]);
    const [form, setForm] = useState(EMPTY);
    const [editingId, setEditingId] = useState(null);
    const [uploadPct, setUploadPct] = useState(null);
    const [uploadKind, setUploadKind] = useState("");

    const fetchItems = useCallback(async () => {
        const res = await callApi({ url: "print/admin/showcase/", rawError: true, silent: true });
        if (res?.status === 200) setItems(res.data.data);
    }, []); // eslint-disable-line react-hooks/exhaustive-deps

    const fetchProducts = useCallback(async () => {
        const res = await callApi({ url: "print/press/products/", rawError: true, silent: true });
        if (res?.status === 200) setProducts(res.data.data);
    }, []); // eslint-disable-line react-hooks/exhaustive-deps

    useEffect(() => { fetchItems(); fetchProducts(); }, [fetchItems, fetchProducts]);

    const uploadFile = async (file, kind) => {
        if (!file) return;
        setUploadKind(kind);
        setUploadPct(0);
        const fd = new FormData();
        fd.append("file", file);
        try {
            const res = await axios.request({
                url: `${config.API_URL}print/admin/showcase/upload/`,
                method: "POST", data: fd,
                headers: { Authorization: getToken() ? `Bearer ${getToken()}` : "" },
                onUploadProgress: (e) => setUploadPct(e.total ? Math.round((e.loaded / e.total) * 100) : 50),
            });
            const d = res?.data?.data;
            if (d?.file_url) {
                if (kind === "thumbnail" || d.is_image) {
                    setForm((f) => ({ ...f, image: d.file_url }));
                }
                if (kind === "design") {
                    setForm((f) => ({ ...f, file_url: d.file_url, file_type: d.file_type }));
                    if (d.is_image && !form.image) setForm((f) => ({ ...f, image: d.file_url }));
                }
                toast.success(`${file.name} uploaded`);
            }
        } catch (err) {
            toast.error(err?.response?.data?.data || `Could not upload ${file.name}`);
        } finally {
            setUploadPct(null);
        }
    };

    const save = async () => {
        if (!form.name.trim()) { toast.error("Name is required"); return; }
        const body = {
            ...form,
            price_bdt: form.price_bdt === "" ? null : form.price_bdt,
            press_product: form.press_product === "" ? null : form.press_product,
        };
        const url = editingId ? `print/admin/showcase/${editingId}/` : "print/admin/showcase/";
        const method = editingId ? "PATCH" : "POST";
        const res = await callApi({ url, method, body, rawError: true });
        if (res?.status === 200 || res?.status === 201) {
            toast.success(editingId ? "Design updated" : "Design added to showcase");
            setForm(EMPTY);
            setEditingId(null);
            fetchItems();
        } else {
            toast.error(res?.data?.message || JSON.stringify(res?.data?.data || "Could not save"));
        }
    };

    const startEdit = (it) => {
        setEditingId(it.id);
        setForm({
            name: it.name || "", category: it.category || "business-cards",
            note: it.note || "", description: it.description || "",
            image: it.image || "", file_url: it.file_url || "", file_type: it.file_type || "",
            badge: it.badge || "", price_bdt: it.price_bdt ?? "",
            is_top_pick: !!it.is_top_pick, press_product: it.press_product || "",
            is_active: it.is_active !== false, display_order: it.display_order || 0,
        });
        window.scrollTo({ top: 0, behavior: "smooth" });
    };

    const toggle = async (it, patch) => {
        const res = await callApi({ url: `print/admin/showcase/${it.id}/`, method: "PATCH", body: patch, rawError: true });
        if (res?.status === 200) fetchItems(); else toast.error("Could not update");
    };

    const remove = async (id) => {
        if (!window.confirm("Remove this design from the showcase?")) return;
        const res = await callApi({ url: `print/admin/showcase/${id}/`, method: "DELETE", rawError: true });
        if (res?.status === 200) { toast.success("Removed"); fetchItems(); } else toast.error("Could not delete");
    };

    return (
        <Box>
            <Typography variant="h5" fontWeight={800} sx={{ mb: 1 }}>Design Showcase</Typography>
            <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                Upload design files (PDF, AI, PSD, EPS, TIFF, PNG, JPEG) per category — they appear
                on the storefront catalog with badges, prices and Top-Pick placement.
            </Typography>

            <Card variant="outlined" sx={{ p: 2, mb: 3 }}>
                <Typography variant="subtitle1" fontWeight={800} sx={{ mb: 2 }}>
                    {editingId ? `Editing #${editingId}` : "Add a design"}
                </Typography>
                <Stack spacing={1.5}>
                    <Stack direction="row" spacing={1} sx={{ flexWrap: "wrap" }}>
                        <TextField size="small" label="Design name" value={form.name}
                            onChange={(e) => setForm({ ...form, name: e.target.value })} sx={{ minWidth: 220 }} />
                        <TextField size="small" select label="Category" value={form.category}
                            onChange={(e) => setForm({ ...form, category: e.target.value })} sx={{ minWidth: 220 }}>
                            {ALL_CATS.map((c) => <MenuItem key={c.key} value={c.key}>{c.title}</MenuItem>)}
                        </TextField>
                        <TextField size="small" select label="Badge" value={form.badge}
                            onChange={(e) => setForm({ ...form, badge: e.target.value })} sx={{ minWidth: 120 }}>
                            {PRESS_BADGES.map((b) => <MenuItem key={b} value={b}>{b || "None"}</MenuItem>)}
                        </TextField>
                        <TextField size="small" label="Price ৳ (blank = on quote)" value={form.price_bdt}
                            onChange={(e) => setForm({ ...form, price_bdt: e.target.value })} sx={{ width: 170 }} />
                    </Stack>
                    <Stack direction="row" spacing={1} sx={{ flexWrap: "wrap" }}>
                        <TextField size="small" label="Short note" value={form.note}
                            onChange={(e) => setForm({ ...form, note: e.target.value })} sx={{ minWidth: 220 }} />
                        <TextField size="small" select label="Orderable press product" value={form.press_product}
                            onChange={(e) => setForm({ ...form, press_product: e.target.value })} sx={{ minWidth: 220 }}>
                            <MenuItem value="">None (quote only)</MenuItem>
                            {products.map((p) => <MenuItem key={p.id} value={p.id}>{p.name}</MenuItem>)}
                        </TextField>
                        <TextField size="small" type="number" label="Order" value={form.display_order}
                            onChange={(e) => setForm({ ...form, display_order: e.target.value })} sx={{ width: 100 }} />
                    </Stack>
                    <TextField size="small" fullWidth multiline minRows={2} label="Description" value={form.description}
                        onChange={(e) => setForm({ ...form, description: e.target.value })} />
                    <Stack direction="row" spacing={1} alignItems="center" sx={{ flexWrap: "wrap" }}>
                        <Button variant="outlined" component="label">
                            Upload design file
                            <input type="file" hidden accept={ACCEPTED}
                                onChange={(e) => { uploadFile(e.target.files?.[0], "design"); e.target.value = ""; }} />
                        </Button>
                        <Button variant="outlined" component="label">
                            Upload thumbnail
                            <input type="file" hidden accept="image/*"
                                onChange={(e) => { uploadFile(e.target.files?.[0], "thumbnail"); e.target.value = ""; }} />
                        </Button>
                        {form.file_url && <Chip size="small" label={`${form.file_type || "file"} attached`} color="success" />}
                        {form.image && (
                            <Box component="img" src={form.image} alt="preview"
                                sx={{ width: 64, height: 64, objectFit: "cover", borderRadius: 1, border: "1px solid", borderColor: "divider" }} />
                        )}
                    </Stack>
                    {uploadPct != null && (
                        <Box>
                            <LinearProgress variant="determinate" value={uploadPct} sx={{ height: 8, borderRadius: 4 }} />
                            <Typography variant="caption">Uploading {uploadKind}… {uploadPct}%</Typography>
                        </Box>
                    )}
                    <Stack direction="row" spacing={2} alignItems="center">
                        <Stack direction="row" spacing={0.5} alignItems="center">
                            <Switch size="small" checked={form.is_top_pick}
                                onChange={(e) => setForm({ ...form, is_top_pick: e.target.checked })} />
                            <Typography variant="body2">Top Pick</Typography>
                        </Stack>
                        <Stack direction="row" spacing={0.5} alignItems="center">
                            <Switch size="small" checked={form.is_active}
                                onChange={(e) => setForm({ ...form, is_active: e.target.checked })} />
                            <Typography variant="body2">Active</Typography>
                        </Stack>
                        <Box sx={{ flex: 1 }} />
                        {editingId && <Button onClick={() => { setForm(EMPTY); setEditingId(null); }}>Cancel</Button>}
                        <Button variant="contained" onClick={save}>{editingId ? "Save changes" : "Add design"}</Button>
                    </Stack>
                </Stack>
            </Card>

            <TableContainer component={Paper}>
                <Table size="small">
                    <TableHead>
                        <TableRow>
                            <TableCell>Preview</TableCell><TableCell>Design</TableCell><TableCell>Category</TableCell>
                            <TableCell>Badge</TableCell><TableCell>Price</TableCell>
                            <TableCell>Top</TableCell><TableCell>Active</TableCell><TableCell />
                        </TableRow>
                    </TableHead>
                    <TableBody>
                        {items.length === 0 && (
                            <TableRow><TableCell colSpan={8} align="center">No showcase designs yet</TableCell></TableRow>
                        )}
                        {items.map((it) => (
                            <TableRow key={it.id}>
                                <TableCell>
                                    {it.image ? (
                                        <Box component="img" src={it.image} alt=""
                                            sx={{ width: 48, height: 48, objectFit: "cover", borderRadius: 1 }} />
                                    ) : (
                                        <Chip size="small" label={it.file_type?.toUpperCase() || "—"} variant="outlined" />
                                    )}
                                </TableCell>
                                <TableCell>
                                    <strong>{it.name}</strong>
                                    {it.press_product_name && (
                                        <Typography variant="caption" display="block" color="text.secondary">
                                            → {it.press_product_name}
                                        </Typography>
                                    )}
                                </TableCell>
                                <TableCell>{categoryTitle(it.category)}</TableCell>
                                <TableCell>{it.badge ? <Chip size="small" label={it.badge} color="error" /> : "—"}</TableCell>
                                <TableCell>{it.price_bdt != null ? `৳${Number(it.price_bdt).toLocaleString("en-US")}` : "quote"}</TableCell>
                                <TableCell>
                                    <Switch size="small" checked={!!it.is_top_pick}
                                        onChange={(e) => toggle(it, { is_top_pick: e.target.checked })} />
                                </TableCell>
                                <TableCell>
                                    <Switch size="small" checked={it.is_active !== false}
                                        onChange={(e) => toggle(it, { is_active: e.target.checked })} />
                                </TableCell>
                                <TableCell>
                                    <IconButton size="small" onClick={() => startEdit(it)}><EditIcon fontSize="small" /></IconButton>
                                    <IconButton size="small" onClick={() => remove(it.id)}><DeleteIcon fontSize="small" /></IconButton>
                                </TableCell>
                            </TableRow>
                        ))}
                    </TableBody>
                </Table>
            </TableContainer>
        </Box>
    );
}
