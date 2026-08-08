import { useCallback, useEffect, useState } from "react";
import {
    Box, Typography, Stack, Paper, Table, TableHead, TableRow, TableCell, TableBody,
    IconButton, Button, Dialog, DialogTitle, DialogContent, DialogActions, TextField,
    MenuItem, Switch, FormControlLabel, Chip, Autocomplete, Alert, CircularProgress,
} from "@mui/material";
import ViewCarouselIcon from "@mui/icons-material/ViewCarousel";
import AddIcon from "@mui/icons-material/Add";
import EditIcon from "@mui/icons-material/Edit";
import DeleteIcon from "@mui/icons-material/Delete";
import ArrowUpwardIcon from "@mui/icons-material/ArrowUpward";
import ArrowDownwardIcon from "@mui/icons-material/ArrowDownward";
import { toast } from "react-toastify";
import useApi from "../../hooks/APIHandler";

const ANIMATION_OPTIONS = [
    { value: "FADE_UP", label: "Fade up" },
    { value: "SLIDE_IN", label: "Slide in" },
    { value: "FLOAT", label: "Float / parallax" },
    { value: "ZOOM", label: "Zoom" },
];

const LAYOUT_OPTIONS = [
    { value: "PRODUCT", label: "Product cut-out beside text (animated)" },
    { value: "FULL_BLEED", label: "Full-width image (wide artwork)" },
];

const EMPTY_FORM = {
    id: null,
    layout: "PRODUCT",
    image: "",
    eyebrow: "",
    headline: "",
    subtext: "",
    animation_style: "FADE_UP",
    background: "#1a1a2e",
    cta_label: "Shop Now",
    cta_product: null,
    cta_product_name: null,
    cta_url: "",
    is_active: true,
    starts_at: "",
    ends_at: "",
};

// Backend datetimes come back as full ISO strings; <input type="datetime-local">
// wants "YYYY-MM-DDTHH:mm" with no timezone suffix.
function toLocalInputValue(iso) {
    if (!iso) return "";
    const d = new Date(iso);
    if (Number.isNaN(d.getTime())) return "";
    const pad = (n) => String(n).padStart(2, "0");
    return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

export default function ManageBanners() {
    const { callApi } = useApi();
    const [banners, setBanners] = useState([]);
    const [loading, setLoading] = useState(true);
    const [loadError, setLoadError] = useState("");
    const [dialogOpen, setDialogOpen] = useState(false);
    const [form, setForm] = useState(EMPTY_FORM);
    const [saving, setSaving] = useState(false);
    const [uploading, setUploading] = useState(false);
    const [fieldErrors, setFieldErrors] = useState({});
    const [productQuery, setProductQuery] = useState("");
    const [productOptions, setProductOptions] = useState([]);
    const [productSearching, setProductSearching] = useState(false);

    const loadBanners = useCallback(async () => {
        setLoading(true);
        const res = await callApi({ url: "store/admin/banners/", rawError: true });
        if (res?.status === 200) {
            setBanners(res.data.data || []);
            setLoadError("");
        } else {
            setLoadError(res?.data?.message || "Could not load banners.");
        }
        setLoading(false);
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, []);

    useEffect(() => { loadBanners(); }, [loadBanners]);

    // Debounced product search for the CTA picker.
    useEffect(() => {
        if (!productQuery.trim()) { setProductOptions([]); return undefined; }
        setProductSearching(true);
        const id = setTimeout(async () => {
            const res = await callApi({ url: "products/", params: { search: productQuery, pageSize: 10 } });
            setProductOptions(res?.data?.data?.data || []);
            setProductSearching(false);
        }, 350);
        return () => clearTimeout(id);
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [productQuery]);

    const openCreate = () => {
        setForm(EMPTY_FORM);
        setFieldErrors({});
        setDialogOpen(true);
    };

    const openEdit = (banner) => {
        setForm({
            ...EMPTY_FORM,
            ...banner,
            starts_at: toLocalInputValue(banner.starts_at),
            ends_at: toLocalInputValue(banner.ends_at),
        });
        setFieldErrors({});
        setDialogOpen(true);
    };

    const uploadImage = async (file) => {
        if (!file) return;
        setUploading(true);
        const body = new FormData();
        body.append("image", file);
        const res = await callApi({
            url: "uploads/", method: "POST", body,
            header: { "Content-Type": "multipart/form-data" }, rawError: true, silent: true,
        });
        setUploading(false);
        const url = res?.data?.urls?.[0];
        if (url) setForm((f) => ({ ...f, image: url }));
        else toast.error("Upload failed — try again");
    };

    const save = async () => {
        setSaving(true);
        setFieldErrors({});
        const payload = {
            layout: form.layout,
            image: form.image,
            eyebrow: form.eyebrow,
            headline: form.headline,
            subtext: form.subtext,
            animation_style: form.animation_style,
            background: form.background,
            cta_label: form.cta_label,
            cta_product: form.cta_product || null,
            cta_url: form.cta_url,
            is_active: form.is_active,
            starts_at: form.starts_at || null,
            ends_at: form.ends_at || null,
        };
        const res = form.id
            ? await callApi({ url: `store/admin/banners/${form.id}/`, method: "PATCH", body: payload, rawError: true })
            : await callApi({ url: "store/admin/banners/", method: "POST", body: payload, rawError: true });
        setSaving(false);
        if (res?.status === 200 || res?.status === 201) {
            toast.success(form.id ? "Banner updated" : "Banner created");
            setDialogOpen(false);
            loadBanners();
        } else if (res?.data?.field_errors) {
            setFieldErrors(res.data.field_errors);
            toast.error("Please fix the highlighted fields");
        } else {
            toast.error(res?.data?.message || "Could not save banner");
        }
    };

    const remove = async (banner) => {
        if (!window.confirm(`Delete banner "${banner.headline}"?`)) return;
        const res = await callApi({ url: `store/admin/banners/${banner.id}/`, method: "DELETE", rawError: true });
        if (res?.status === 200) {
            toast.success("Banner deleted");
            loadBanners();
        } else {
            toast.error(res?.data?.message || "Could not delete banner");
        }
    };

    const move = async (index, direction) => {
        const next = [...banners];
        const swapWith = index + direction;
        if (swapWith < 0 || swapWith >= next.length) return;
        [next[index], next[swapWith]] = [next[swapWith], next[index]];
        setBanners(next); // optimistic reorder
        const res = await callApi({
            url: "store/admin/banners/reorder/", method: "POST",
            body: { order: next.map((b) => b.id) }, rawError: true,
        });
        if (res?.status === 200) setBanners(res.data.data || next);
        else { toast.error("Could not reorder — reloading"); loadBanners(); }
    };

    return (
        <Box>
            <Stack direction="row" spacing={1} alignItems="center" justifyContent="space-between" sx={{ mb: 2 }}>
                <Stack direction="row" spacing={1} alignItems="center">
                    <ViewCarouselIcon color="primary" />
                    <Typography variant="h5" fontWeight={800}>Homepage Banners</Typography>
                </Stack>
                <Button variant="contained" startIcon={<AddIcon />} onClick={openCreate}>Add Banner</Button>
            </Stack>

            {loadError && <Alert severity="error" sx={{ mb: 2 }}>{loadError}</Alert>}

            <Paper>
                <Table>
                    <TableHead>
                        <TableRow>
                            <TableCell>Order</TableCell>
                            <TableCell>Preview</TableCell>
                            <TableCell>Headline</TableCell>
                            <TableCell>Animation</TableCell>
                            <TableCell>CTA</TableCell>
                            <TableCell>Status</TableCell>
                            <TableCell align="right">Actions</TableCell>
                        </TableRow>
                    </TableHead>
                    <TableBody>
                        {loading && (
                            <TableRow><TableCell colSpan={7} align="center"><CircularProgress size={24} sx={{ my: 2 }} /></TableCell></TableRow>
                        )}
                        {!loading && banners.length === 0 && !loadError && (
                            <TableRow><TableCell colSpan={7} align="center">
                                <Typography variant="body2" color="text.secondary" sx={{ py: 3 }}>
                                    No banners yet — add one to populate the homepage hero.
                                </Typography>
                            </TableCell></TableRow>
                        )}
                        {banners.map((b, i) => (
                            <TableRow key={b.id}>
                                <TableCell>
                                    <Stack direction="row" alignItems="center">
                                        <IconButton size="small" disabled={i === 0} onClick={() => move(i, -1)} aria-label="Move up">
                                            <ArrowUpwardIcon fontSize="small" />
                                        </IconButton>
                                        <IconButton size="small" disabled={i === banners.length - 1} onClick={() => move(i, 1)} aria-label="Move down">
                                            <ArrowDownwardIcon fontSize="small" />
                                        </IconButton>
                                    </Stack>
                                </TableCell>
                                <TableCell>
                                    {b.image && (
                                        <Box component="img" src={b.image} alt="" sx={{
                                            width: 64, height: 40, objectFit: "contain", borderRadius: 1,
                                            background: b.background || "#1a1a2e",
                                        }} />
                                    )}
                                </TableCell>
                                <TableCell>
                                    <Typography variant="body2" fontWeight={600}>{b.headline}</Typography>
                                    {b.eyebrow && <Typography variant="caption" color="text.secondary">{b.eyebrow}</Typography>}
                                </TableCell>
                                <TableCell>
                                    <Chip size="small" label={ANIMATION_OPTIONS.find((a) => a.value === b.animation_style)?.label || b.animation_style} />
                                </TableCell>
                                <TableCell>
                                    <Typography variant="caption">
                                        {b.cta_product_name ? `→ ${b.cta_product_name}` : (b.cta_url || "—")}
                                    </Typography>
                                </TableCell>
                                <TableCell>
                                    <Chip size="small" color={b.is_active ? "success" : "default"} label={b.is_active ? "Active" : "Inactive"} />
                                </TableCell>
                                <TableCell align="right">
                                    <IconButton size="small" onClick={() => openEdit(b)} aria-label="Edit"><EditIcon fontSize="small" /></IconButton>
                                    <IconButton size="small" color="error" onClick={() => remove(b)} aria-label="Delete"><DeleteIcon fontSize="small" /></IconButton>
                                </TableCell>
                            </TableRow>
                        ))}
                    </TableBody>
                </Table>
            </Paper>

            <Dialog open={dialogOpen} onClose={() => setDialogOpen(false)} maxWidth="sm" fullWidth>
                <DialogTitle>{form.id ? "Edit Banner" : "Add Banner"}</DialogTitle>
                <DialogContent>
                    <Stack spacing={2} sx={{ mt: 1 }}>
                        <Stack direction="row" spacing={2} alignItems="center">
                            {form.image && (
                                <Box component="img" src={form.image} alt="" sx={{
                                    width: 100, height: 60, objectFit: "contain", borderRadius: 1,
                                    background: form.background || "#1a1a2e",
                                }} />
                            )}
                            <Button component="label" variant="outlined" disabled={uploading}>
                                {uploading ? "Uploading…" : "Upload PNG"}
                                <input hidden type="file" accept="image/png,image/*"
                                    onChange={(e) => uploadImage(e.target.files?.[0])} />
                            </Button>
                        </Stack>
                        <TextField
                            label="Transparent PNG image URL" fullWidth value={form.image}
                            onChange={(e) => setForm({ ...form, image: e.target.value })}
                            error={!!fieldErrors.image} helperText={fieldErrors.image?.[0]}
                        />
                        <TextField
                            label="Eyebrow / badge (optional)" fullWidth value={form.eyebrow}
                            onChange={(e) => setForm({ ...form, eyebrow: e.target.value })}
                        />
                        <TextField
                            select label="Layout" fullWidth value={form.layout}
                            onChange={(e) => setForm({ ...form, layout: e.target.value })}
                            helperText={form.layout === "FULL_BLEED"
                                ? "The image fills the hero edge to edge and is shown whole. Use for a wide banner that already has its own wording."
                                : "A transparent product PNG is composited beside the headline and animated in."}
                            sx={{ mb: 2 }}
                        >
                            {LAYOUT_OPTIONS.map((l) => <MenuItem key={l.value} value={l.value}>{l.label}</MenuItem>)}
                        </TextField>
                        <TextField
                            label="Headline" fullWidth value={form.headline}
                            onChange={(e) => setForm({ ...form, headline: e.target.value })}
                            error={!!fieldErrors.headline}
                            helperText={fieldErrors.headline?.[0]
                                || (form.layout === "FULL_BLEED"
                                    ? "Optional — leave blank so nothing is drawn over the artwork."
                                    : "Optional.")}
                        />
                        <TextField
                            label="Subtext" fullWidth multiline minRows={2} value={form.subtext}
                            onChange={(e) => setForm({ ...form, subtext: e.target.value })}
                        />
                        <Stack direction="row" spacing={2}>
                            <TextField
                                select label="Animation" fullWidth value={form.animation_style}
                                onChange={(e) => setForm({ ...form, animation_style: e.target.value })}
                            >
                                {ANIMATION_OPTIONS.map((a) => <MenuItem key={a.value} value={a.value}>{a.label}</MenuItem>)}
                            </TextField>
                            <TextField
                                label="Background (colour or CSS gradient)" fullWidth value={form.background}
                                onChange={(e) => setForm({ ...form, background: e.target.value })}
                                placeholder="#1a1a2e or linear-gradient(...)"
                            />
                        </Stack>
                        <TextField
                            label="CTA button label" fullWidth value={form.cta_label}
                            onChange={(e) => setForm({ ...form, cta_label: e.target.value })}
                        />
                        <Autocomplete
                            options={productOptions}
                            loading={productSearching}
                            getOptionLabel={(p) => p.name || `Product #${p.id}`}
                            isOptionEqualToValue={(a, b) => a.id === b.id}
                            value={form.cta_product ? { id: form.cta_product, name: form.cta_product_name } : null}
                            onChange={(e, v) => setForm({ ...form, cta_product: v?.id || null, cta_product_name: v?.name || null })}
                            onInputChange={(e, v) => setProductQuery(v)}
                            renderInput={(params) => (
                                <TextField {...params} label="Link to product (optional)" placeholder="Search products…" />
                            )}
                        />
                        <TextField
                            label="Fallback URL (used if no product is linked)" fullWidth value={form.cta_url}
                            onChange={(e) => setForm({ ...form, cta_url: e.target.value })}
                            placeholder="/shop or https://…"
                        />
                        <Stack direction="row" spacing={2}>
                            <TextField
                                type="datetime-local" label="Starts at (optional)" fullWidth
                                InputLabelProps={{ shrink: true }} value={form.starts_at}
                                onChange={(e) => setForm({ ...form, starts_at: e.target.value })}
                            />
                            <TextField
                                type="datetime-local" label="Ends at (optional)" fullWidth
                                InputLabelProps={{ shrink: true }} value={form.ends_at}
                                onChange={(e) => setForm({ ...form, ends_at: e.target.value })}
                            />
                        </Stack>
                        <FormControlLabel
                            control={<Switch checked={!!form.is_active} onChange={(e) => setForm({ ...form, is_active: e.target.checked })} />}
                            label="Active"
                        />
                    </Stack>
                </DialogContent>
                <DialogActions>
                    <Button onClick={() => setDialogOpen(false)}>Cancel</Button>
                    <Button variant="contained" disabled={saving || !form.headline || !form.image} onClick={save}>
                        {saving ? <CircularProgress size={20} /> : "Save"}
                    </Button>
                </DialogActions>
            </Dialog>
        </Box>
    );
}
