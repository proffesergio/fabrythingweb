import { useCallback, useEffect, useMemo, useState } from "react";
import {
    Alert, Autocomplete, Avatar, Box, Breadcrumbs, Button, Card, Checkbox, Chip,
    CircularProgress, Dialog, DialogActions, DialogContent, DialogTitle, Divider,
    FormControlLabel, Grid, IconButton, LinearProgress, MenuItem, Paper, Stack,
    Switch, Tab, Table, TableBody, TableCell, TableHead, TableRow, Tabs, TextField,
    Typography,
} from "@mui/material";
import { useNavigate } from "react-router-dom";
import CloudDownloadOutlined from "@mui/icons-material/CloudDownloadOutlined";
import StorefrontIcon from "@mui/icons-material/Storefront";
import ArrowUpwardIcon from "@mui/icons-material/ArrowUpward";
import ArrowDownwardIcon from "@mui/icons-material/ArrowDownward";
import DeleteIcon from "@mui/icons-material/Delete";
import EditIcon from "@mui/icons-material/Edit";
import { toast } from "react-toastify";
import useApi from "../../hooks/APIHandler";

const flattenCategories = (nodes, depth = 0) => {
    let out = [];
    for (const n of nodes || []) {
        out.push({ id: n.id, slug: n.slug, name: n.name, depth });
        if (n.children?.length) out = out.concat(flattenCategories(n.children, depth + 1));
    }
    return out;
};

const firstImage = (images) => (Array.isArray(images) ? images[0] : "") || "";
const firstFieldError = (fieldErrors) => Object.values(fieldErrors || {})[0]?.[0];

const BULK_ADD_CAP = 12;

const EMPTY_EDIT_FORM = {
    id: null,
    title: "", brand: "", image: "", original_price: "", current_price: "",
    commission_amount: "", link_type: "CART", manual_short_link: "",
    is_active: true, starts_at: "", ends_at: "", show_in_sidebar: false,
    show_on_deals_page: false, show_in_category_grid: false, grid_category_ids: [],
};

// Same ISO <-> datetime-local conversion ManageBanners.js already uses.
function toLocalInputValue(iso) {
    if (!iso) return "";
    const d = new Date(iso);
    if (Number.isNaN(d.getTime())) return "";
    const pad = (n) => String(n).padStart(2, "0");
    return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

export default function ManageAffiliateProducts() {
    const { callApi, loading } = useApi();
    const navigate = useNavigate();
    const [tab, setTab] = useState(0);

    // ---- Our taxonomy, for grid_categories tagging ----
    const [ourCategories, setOurCategories] = useState([]);
    const flatOurCategories = useMemo(() => flattenCategories(ourCategories), [ourCategories]);

    useEffect(() => {
        (async () => {
            const res = await callApi({ url: "products/categories/", method: "GET" });
            if (res?.status === 200) setOurCategories(res.data.data.data || []);
        })();
    }, []); // eslint-disable-line react-hooks/exhaustive-deps

    // ---- Search Rokomari tab ----
    const [query, setQuery] = useState("");
    const [categoryPath, setCategoryPath] = useState("");
    const [candidates, setCandidates] = useState([]);
    const [browsed, setBrowsed] = useState(false);
    const [browseError, setBrowseError] = useState("");
    const [selected, setSelected] = useState(new Set());
    const [addingLinkType, setAddingLinkType] = useState("CART");
    const [adding, setAdding] = useState(false);
    const [addResults, setAddResults] = useState(null);

    const handleSearch = useCallback(async () => {
        const trimmed = query.trim();
        if (!trimmed && !categoryPath) {
            setBrowseError("Type a search term or a Rokomari category path.");
            return;
        }
        setBrowseError("");
        setAddResults(null);
        const res = await callApi({
            url: "store/admin/affiliate/search/", method: "GET", rawError: true,
            params: { q: trimmed || undefined, category: categoryPath || undefined },
        });
        if (res?.status === 200) {
            setCandidates(res.data.data.candidates || []);
            setSelected(new Set());
            setBrowsed(true);
        } else {
            setCandidates([]);
            setBrowsed(true);
            setBrowseError(firstFieldError(res?.data?.field_errors) || res?.data?.message || "Search failed.");
        }
    }, [query, categoryPath]); // eslint-disable-line react-hooks/exhaustive-deps

    const toggleSelected = (url) => {
        setSelected((prev) => {
            const next = new Set(prev);
            if (next.has(url)) next.delete(url); else next.add(url);
            return next;
        });
    };

    const handleBulkAdd = async () => {
        if (selected.size === 0) return;
        setAdding(true);
        setAddResults(null);
        const chosen = candidates.filter((c) => selected.has(c.source_url)).map((c) => ({
            source_url: c.source_url, remote_product_id: c.remote_product_id,
            name: c.name, price: c.price, discount_price: c.discount_price,
            images: c.images, link_type: addingLinkType,
        }));
        const res = await callApi({
            url: "store/admin/affiliate/bulk-add/", method: "POST", rawError: true,
            body: { candidates: chosen },
        });
        setAdding(false);
        if (res?.status === 200) {
            setAddResults(res.data.data);
            setSelected(new Set());
            toast.success(`${res.data.data.created.length} product(s) added`);
            loadProducts();
        } else {
            toast.error(firstFieldError(res?.data?.field_errors) || res?.data?.message || "Bulk-add failed");
        }
    };

    // ---- Manage tab ----
    const [products, setProducts] = useState([]);
    const [manageLoading, setManageLoading] = useState(true);
    const [manageError, setManageError] = useState("");
    const [dialogOpen, setDialogOpen] = useState(false);
    const [form, setForm] = useState(EMPTY_EDIT_FORM);
    const [saving, setSaving] = useState(false);
    const [fieldErrors, setFieldErrors] = useState({});

    const loadProducts = useCallback(async () => {
        setManageLoading(true);
        const res = await callApi({ url: "store/admin/affiliate/", rawError: true });
        if (res?.status === 200) {
            setProducts(res.data.data || []);
            setManageError("");
        } else {
            setManageError(res?.data?.message || "Could not load affiliate products.");
        }
        setManageLoading(false);
    }, []); // eslint-disable-line react-hooks/exhaustive-deps

    useEffect(() => { loadProducts(); }, [loadProducts]);

    const openEdit = (p) => {
        setForm({
            ...EMPTY_EDIT_FORM,
            ...p,
            grid_category_ids: p.grid_category_ids || [],
            starts_at: toLocalInputValue(p.starts_at),
            ends_at: toLocalInputValue(p.ends_at),
        });
        setFieldErrors({});
        setDialogOpen(true);
    };

    const save = async () => {
        setSaving(true);
        setFieldErrors({});
        const payload = {
            title: form.title, brand: form.brand, image: form.image,
            original_price: form.original_price || null, current_price: form.current_price || null,
            commission_amount: form.commission_amount || null, link_type: form.link_type,
            manual_short_link: form.manual_short_link, is_active: form.is_active,
            starts_at: form.starts_at || null, ends_at: form.ends_at || null,
            show_in_sidebar: form.show_in_sidebar, show_on_deals_page: form.show_on_deals_page,
            show_in_category_grid: form.show_in_category_grid, grid_category_ids: form.grid_category_ids,
        };
        const res = await callApi({
            url: `store/admin/affiliate/${form.id}/`, method: "PATCH", body: payload, rawError: true,
        });
        setSaving(false);
        if (res?.status === 200) {
            toast.success("Affiliate product updated");
            setDialogOpen(false);
            loadProducts();
        } else if (res?.data?.field_errors) {
            setFieldErrors(res.data.field_errors);
            toast.error("Please fix the highlighted fields");
        } else {
            toast.error(res?.data?.message || "Could not save");
        }
    };

    const remove = async (p) => {
        if (!window.confirm(`Delete "${p.title}"?`)) return;
        const res = await callApi({ url: `store/admin/affiliate/${p.id}/`, method: "DELETE", rawError: true });
        if (res?.status === 200) { toast.success("Deleted"); loadProducts(); }
        else toast.error(res?.data?.message || "Could not delete");
    };

    const move = async (index, direction) => {
        const next = [...products];
        const swapWith = index + direction;
        if (swapWith < 0 || swapWith >= next.length) return;
        [next[index], next[swapWith]] = [next[swapWith], next[index]];
        setProducts(next); // optimistic
        const res = await callApi({
            url: "store/admin/affiliate/reorder/", method: "POST",
            body: { order: next.map((p) => p.id) }, rawError: true,
        });
        if (res?.status === 200) setProducts(res.data.data || next);
        else { toast.error("Could not reorder — reloading"); loadProducts(); }
    };

    return (
        <Box sx={{ width: "100%" }}>
            <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 2 }}>
                <Breadcrumbs>
                    <Typography variant="body2" sx={{ cursor: "pointer" }} onClick={() => navigate("/admin")}>Home</Typography>
                    <Typography variant="body2">Affiliate Products</Typography>
                </Breadcrumbs>
            </Stack>

            <Stack direction="row" spacing={1} alignItems="center" sx={{ mb: 1 }}>
                <StorefrontIcon color="primary" />
                <Typography variant="h5" fontWeight={800}>Rokomari Affiliate Products</Typography>
            </Stack>

            <Tabs value={tab} onChange={(_, v) => setTab(v)} sx={{ mb: 2 }}>
                <Tab label="Search & Add" />
                <Tab label="Manage" />
            </Tabs>

            {tab === 0 && (
                <>
                    <Card variant="outlined" sx={{ p: 2, mb: 2 }}>
                        <Grid container spacing={2} alignItems="center">
                            <Grid item xs={12} sm={5}>
                                <TextField
                                    fullWidth size="small" label="Search Rokomari"
                                    value={query} onChange={(e) => setQuery(e.target.value)}
                                    placeholder="e.g. perfume"
                                />
                            </Grid>
                            <Grid item xs={12} sm={4}>
                                <TextField
                                    fullWidth size="small" label="...or a Rokomari category path"
                                    value={categoryPath} onChange={(e) => setCategoryPath(e.target.value)}
                                    placeholder="product/category/2618/perfume"
                                />
                            </Grid>
                            <Grid item xs={12} sm={3}>
                                <Button
                                    fullWidth variant="contained" startIcon={<CloudDownloadOutlined />}
                                    disabled={loading} onClick={handleSearch}
                                >
                                    {loading ? "Searching…" : "Search"}
                                </Button>
                            </Grid>
                        </Grid>
                        {browseError && <Alert severity="warning" sx={{ mt: 2 }}>{browseError}</Alert>}
                    </Card>

                    {loading && <LinearProgress sx={{ mb: 2 }} />}

                    {browsed && candidates.length === 0 && !browseError && (
                        <Alert severity="info" sx={{ mb: 2 }}>No products found for that search/category.</Alert>
                    )}

                    {candidates.length > 0 && (
                        <>
                            <Grid container spacing={2} sx={{ mb: 2 }}>
                                {candidates.map((c) => (
                                    <Grid item xs={12} sm={6} md={4} lg={3} key={c.source_url}>
                                        <Card
                                            variant="outlined"
                                            sx={{
                                                p: 1.5, height: "100%", cursor: c.remote_product_id ? "pointer" : "not-allowed",
                                                borderColor: selected.has(c.source_url) ? "primary.main" : undefined,
                                                borderWidth: selected.has(c.source_url) ? 2 : 1,
                                                opacity: c.already_have ? 0.7 : 1,
                                            }}
                                            onClick={() => c.remote_product_id && toggleSelected(c.source_url)}
                                        >
                                            <Stack direction="row" spacing={1} alignItems="flex-start">
                                                <Checkbox
                                                    checked={selected.has(c.source_url)}
                                                    disabled={!c.remote_product_id}
                                                    onChange={() => toggleSelected(c.source_url)}
                                                    onClick={(e) => e.stopPropagation()}
                                                    sx={{ p: 0 }}
                                                />
                                                <Avatar variant="rounded" src={firstImage(c.images)} sx={{ width: 56, height: 56 }}>
                                                    {(c.name || "?").charAt(0)}
                                                </Avatar>
                                            </Stack>
                                            <Typography variant="body2" fontWeight={600} sx={{ mt: 1 }} noWrap title={c.name}>
                                                {c.name}
                                            </Typography>
                                            <Stack direction="row" spacing={1} alignItems="center" sx={{ mt: 0.5 }}>
                                                <Typography variant="body2" fontWeight={700}>
                                                    ৳{c.discount_price ?? c.price}
                                                </Typography>
                                                {c.discount_price != null && (
                                                    <Typography variant="caption" sx={{ textDecoration: "line-through" }} color="text.secondary">
                                                        ৳{c.price}
                                                    </Typography>
                                                )}
                                            </Stack>
                                            {c.already_have && <Chip size="small" label="Already in main catalog" sx={{ mt: 1 }} />}
                                            {!c.remote_product_id && (
                                                <Chip size="small" color="warning" label="Could not determine product id" sx={{ mt: 1 }} />
                                            )}
                                        </Card>
                                    </Grid>
                                ))}
                            </Grid>

                            <Card variant="outlined" sx={{ p: 2 }}>
                                <Grid container spacing={2} alignItems="center">
                                    <Grid item xs={12} sm={4}>
                                        <Typography variant="body2">
                                            {selected.size} selected (cap {BULK_ADD_CAP} per request)
                                        </Typography>
                                    </Grid>
                                    <Grid item xs={12} sm={4}>
                                        <TextField
                                            select fullWidth size="small" label="Link type for these"
                                            value={addingLinkType} onChange={(e) => setAddingLinkType(e.target.value)}
                                        >
                                            <MenuItem value="CART">Cart link (quick-cart)</MenuItem>
                                            <MenuItem value="PRODUCT">Product page link</MenuItem>
                                        </TextField>
                                    </Grid>
                                    <Grid item xs={12} sm={4}>
                                        <Button
                                            fullWidth variant="contained" color="primary"
                                            disabled={adding || selected.size === 0 || selected.size > BULK_ADD_CAP}
                                            onClick={handleBulkAdd}
                                        >
                                            {adding ? "Adding…" : `Add ${selected.size || ""} selected`}
                                        </Button>
                                    </Grid>
                                </Grid>
                                {selected.size > BULK_ADD_CAP && (
                                    <Alert severity="warning" sx={{ mt: 2 }}>
                                        Bulk-add is capped at {BULK_ADD_CAP} products per request. Deselect some and run again.
                                    </Alert>
                                )}
                                {adding && <LinearProgress sx={{ mt: 2 }} />}
                            </Card>
                        </>
                    )}

                    {addResults && (
                        <Card variant="outlined" sx={{ p: 2, mt: 2 }}>
                            <Typography variant="subtitle1" sx={{ mb: 1 }}>
                                Added {addResults.created.length} of {addResults.total}
                            </Typography>
                            {addResults.skipped.length > 0 && (
                                <Stack spacing={0.5}>
                                    {addResults.skipped.map((s, i) => (
                                        <Typography key={i} variant="caption" color="text.secondary">
                                            Skipped {s.source_url}: {s.reason}
                                        </Typography>
                                    ))}
                                </Stack>
                            )}
                        </Card>
                    )}
                </>
            )}

            {tab === 1 && (
                <Box>
                    {manageError && <Alert severity="error" sx={{ mb: 2 }}>{manageError}</Alert>}
                    <Paper>
                        <Table size="small">
                            <TableHead>
                                <TableRow>
                                    <TableCell>Order</TableCell>
                                    <TableCell>Product</TableCell>
                                    <TableCell>Price</TableCell>
                                    <TableCell>Link type</TableCell>
                                    <TableCell>Placement</TableCell>
                                    <TableCell align="right">Clicks</TableCell>
                                    <TableCell>Status</TableCell>
                                    <TableCell align="right">Actions</TableCell>
                                </TableRow>
                            </TableHead>
                            <TableBody>
                                {manageLoading && (
                                    <TableRow><TableCell colSpan={8} align="center"><CircularProgress size={24} sx={{ my: 2 }} /></TableCell></TableRow>
                                )}
                                {!manageLoading && products.length === 0 && !manageError && (
                                    <TableRow><TableCell colSpan={8} align="center">
                                        <Typography variant="body2" color="text.secondary" sx={{ py: 3 }}>
                                            No affiliate products yet — search Rokomari and add some.
                                        </Typography>
                                    </TableCell></TableRow>
                                )}
                                {products.map((p, i) => (
                                    <TableRow key={p.id}>
                                        <TableCell>
                                            <Stack direction="row" alignItems="center">
                                                <IconButton size="small" disabled={i === 0} onClick={() => move(i, -1)} aria-label="Move up">
                                                    <ArrowUpwardIcon fontSize="small" />
                                                </IconButton>
                                                <IconButton size="small" disabled={i === products.length - 1} onClick={() => move(i, 1)} aria-label="Move down">
                                                    <ArrowDownwardIcon fontSize="small" />
                                                </IconButton>
                                            </Stack>
                                        </TableCell>
                                        <TableCell>
                                            <Stack direction="row" spacing={1} alignItems="center">
                                                {p.image && <Avatar variant="rounded" src={p.image} sx={{ width: 32, height: 32 }} />}
                                                <Box>
                                                    <Typography variant="body2" fontWeight={600} noWrap sx={{ maxWidth: 220 }}>{p.title}</Typography>
                                                    <Typography variant="caption" color="text.secondary">{p.brand}</Typography>
                                                </Box>
                                            </Stack>
                                        </TableCell>
                                        <TableCell>
                                            <Typography variant="body2">৳{p.current_price ?? "—"}</Typography>
                                        </TableCell>
                                        <TableCell><Chip size="small" label={p.link_type} /></TableCell>
                                        <TableCell>
                                            <Stack direction="row" spacing={0.5} flexWrap="wrap">
                                                {p.show_in_sidebar && <Chip size="small" label="Sidebar" />}
                                                {p.show_on_deals_page && <Chip size="small" label="Deals" />}
                                                {p.show_in_category_grid && <Chip size="small" label="Category grid" />}
                                            </Stack>
                                        </TableCell>
                                        <TableCell align="right">{p.click_count}</TableCell>
                                        <TableCell>
                                            <Chip size="small" color={p.is_active ? "success" : "default"} label={p.is_active ? "Active" : "Inactive"} />
                                        </TableCell>
                                        <TableCell align="right">
                                            <IconButton size="small" onClick={() => openEdit(p)} aria-label="Edit"><EditIcon fontSize="small" /></IconButton>
                                            <IconButton size="small" color="error" onClick={() => remove(p)} aria-label="Delete"><DeleteIcon fontSize="small" /></IconButton>
                                        </TableCell>
                                    </TableRow>
                                ))}
                            </TableBody>
                        </Table>
                    </Paper>
                </Box>
            )}

            <Dialog open={dialogOpen} onClose={() => setDialogOpen(false)} maxWidth="sm" fullWidth>
                <DialogTitle>Edit Affiliate Product</DialogTitle>
                <DialogContent>
                    <Stack spacing={2} sx={{ mt: 1 }}>
                        <TextField
                            label="Title" fullWidth value={form.title}
                            onChange={(e) => setForm({ ...form, title: e.target.value })}
                            error={!!fieldErrors.title} helperText={fieldErrors.title?.[0]}
                        />
                        <TextField
                            label="Brand" fullWidth value={form.brand}
                            onChange={(e) => setForm({ ...form, brand: e.target.value })}
                        />
                        <Stack direction="row" spacing={2}>
                            <TextField
                                label="Original price" fullWidth value={form.original_price}
                                onChange={(e) => setForm({ ...form, original_price: e.target.value })}
                            />
                            <TextField
                                label="Current price" fullWidth value={form.current_price}
                                onChange={(e) => setForm({ ...form, current_price: e.target.value })}
                            />
                        </Stack>
                        <TextField
                            label="Commission amount (optional)" fullWidth value={form.commission_amount}
                            onChange={(e) => setForm({ ...form, commission_amount: e.target.value })}
                        />
                        <TextField
                            select label="Link type" fullWidth value={form.link_type}
                            onChange={(e) => setForm({ ...form, link_type: e.target.value })}
                        >
                            <MenuItem value="CART">Cart link (quick-cart)</MenuItem>
                            <MenuItem value="PRODUCT">Product page link</MenuItem>
                        </TextField>
                        <TextField
                            label="Manual short link override (optional — pasted rkmri.co link wins over the constructed URL)"
                            fullWidth value={form.manual_short_link}
                            onChange={(e) => setForm({ ...form, manual_short_link: e.target.value })}
                            placeholder="https://rkmri.co/…"
                            error={!!fieldErrors.manual_short_link} helperText={fieldErrors.manual_short_link?.[0]}
                        />
                        <Divider />
                        <Typography variant="subtitle2">Placement</Typography>
                        <Stack direction="row" spacing={2} flexWrap="wrap">
                            <FormControlLabel
                                control={<Switch checked={!!form.show_in_sidebar}
                                    onChange={(e) => setForm({ ...form, show_in_sidebar: e.target.checked })} />}
                                label="Sidebar / section widget"
                            />
                            <FormControlLabel
                                control={<Switch checked={!!form.show_on_deals_page}
                                    onChange={(e) => setForm({ ...form, show_on_deals_page: e.target.checked })} />}
                                label="Deals page"
                            />
                            <FormControlLabel
                                control={<Switch checked={!!form.show_in_category_grid}
                                    onChange={(e) => setForm({ ...form, show_in_category_grid: e.target.checked })} />}
                                label="Category grid"
                            />
                        </Stack>
                        <Autocomplete
                            multiple
                            disabled={!form.show_in_category_grid}
                            options={flatOurCategories}
                            getOptionLabel={(c) => c.name}
                            isOptionEqualToValue={(a, b) => a.id === b.id}
                            value={flatOurCategories.filter((c) => form.grid_category_ids.includes(c.id))}
                            onChange={(_, values) => setForm({ ...form, grid_category_ids: values.map((v) => v.id) })}
                            renderInput={(params) => (
                                <TextField {...params} label="Which categories to inject into" placeholder="Choose categories…" />
                            )}
                        />
                        <Divider />
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
                            control={<Switch checked={!!form.is_active}
                                onChange={(e) => setForm({ ...form, is_active: e.target.checked })} />}
                            label="Active"
                        />
                    </Stack>
                </DialogContent>
                <DialogActions>
                    <Button onClick={() => setDialogOpen(false)}>Cancel</Button>
                    <Button variant="contained" disabled={saving} onClick={save}>
                        {saving ? <CircularProgress size={20} /> : "Save"}
                    </Button>
                </DialogActions>
            </Dialog>
        </Box>
    );
}
