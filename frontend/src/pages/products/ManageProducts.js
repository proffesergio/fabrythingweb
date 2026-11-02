import { useState, useEffect, useCallback, useMemo } from "react";
import { useNavigate } from "react-router-dom";
import {
    Box, Breadcrumbs, Button, Checkbox, Chip, FormControlLabel, IconButton, LinearProgress, Table, TableBody, TableCell,
    TableContainer, TableHead, TableRow, Paper, TextField, Typography, Stack, Avatar,
    InputAdornment, Pagination, Tooltip, Dialog, DialogContent, DialogActions, DialogTitle,
    Divider, MenuItem, Switch, CircularProgress, Alert,
} from "@mui/material";
import Add from "@mui/icons-material/Add";
import Edit from "@mui/icons-material/Edit";
import SaveIcon from "@mui/icons-material/Save";
import UndoIcon from "@mui/icons-material/Undo";
import SearchIcon from "@mui/icons-material/Search";
import SyncIcon from "@mui/icons-material/Sync";
import LocalShippingIcon from "@mui/icons-material/LocalShipping";
import RateReviewOutlinedIcon from "@mui/icons-material/RateReviewOutlined";
import HelpOutlineIcon from "@mui/icons-material/HelpOutline";
import { toast } from "react-toastify";
import useApi from "../../hooks/APIHandler";
import ManageReviews from "./ManageReview";
import ManageQuestions from "./ManageQuestions";

const firstImage = (img) => (Array.isArray(img) ? img[0] : img) || "";
const cleanCategory = (c) => (typeof c === "string" ? c : "");

// The category list endpoint returns a nested tree (children under
// children); flatten it into an indented, ordered list for the filter
// dropdown -- products sit in leaf categories, so parents alone aren't
// enough to filter by.
const flattenCategories = (nodes, depth = 0) => {
    let out = [];
    for (const n of nodes || []) {
        out.push({ id: n.id, slug: n.slug, name: n.name, depth });
        if (n.children?.length) out = out.concat(flattenCategories(n.children, depth + 1));
    }
    return out;
};

const draftFromProduct = (p) => ({
    initial_selling_price: String(p.initial_selling_price ?? ""),
    discount_price: p.discount_price === null || p.discount_price === undefined ? "" : String(p.discount_price),
    stock_quantity: String(p.total_stock ?? 0),
    // null/undefined -- no per-product override, falls back to the store's
    // flat rate -- must render as blank, the same as discount_price's "no
    // discount" state, not as "0" (0 is a real, distinct "ships free" value).
    shipping_fee: p.shipping_fee === null || p.shipping_fee === undefined ? "" : String(p.shipping_fee),
    // Explicit "free shipping promo" flag -- distinct from shipping_fee: 0.
    // See docs/SHIPPING_FEES.md. Always a real boolean, never blank.
    free_shipping: !!p.free_shipping,
    saved: true, // no unsaved changes yet
});

const ManageProducts = ({ onProductSelected }) => {
    const { callApi, loading } = useApi();
    const navigate = useNavigate();
    const [products, setProducts] = useState([]);
    const [search, setSearch] = useState("");
    const [debounced, setDebounced] = useState("");
    const [page, setPage] = useState(1);
    const [totalPages, setTotalPages] = useState(1);
    const [reviewsFor, setReviewsFor] = useState(null);
    const [questionsFor, setQuestionsFor] = useState(null);
    const [syncing, setSyncing] = useState(false);

    const [categories, setCategories] = useState([]);
    const [categoryFilter, setCategoryFilter] = useState("");

    // Inline quick-edit state, keyed by product id.
    const [edits, setEdits] = useState({});
    const [rowErrors, setRowErrors] = useState({});
    const [savingIds, setSavingIds] = useState({});

    // Bulk shipping-fee state: checkboxes select rows on the current page
    // ("individual" products); with none checked, the dialog falls back to
    // the active category filter ("all" products in that category/subtree).
    const [selectedIds, setSelectedIds] = useState(new Set());
    const [bulkOpen, setBulkOpen] = useState(false);
    const [bulkFee, setBulkFee] = useState("");
    // "" = don't change the promo flag; "true"/"false" = set it explicitly.
    // A tri-state select, not a checkbox, because a bulk selection can mix
    // products that are already promo'd and ones that aren't -- there's no
    // single "current" state to show a checkbox against.
    const [bulkFreeShipping, setBulkFreeShipping] = useState("");
    const [bulkSaving, setBulkSaving] = useState(false);
    const [bulkCategoryCount, setBulkCategoryCount] = useState(null);
    const [bulkCategoryCountLoading, setBulkCategoryCountLoading] = useState(false);

    const flatCategories = useMemo(() => flattenCategories(categories), [categories]);

    useEffect(() => {
        const t = setTimeout(() => { setPage(1); setDebounced(search); }, 600);
        return () => clearTimeout(t);
    }, [search]);

    const getCategories = useCallback(async () => {
        const res = await callApi({ url: "products/categories/", method: "GET" });
        if (res?.status === 200) {
            setCategories(res.data.data.data || []);
        }
    }, []); // eslint-disable-line react-hooks/exhaustive-deps
    useEffect(() => { getCategories(); }, [getCategories]);

    const getProducts = useCallback(async () => {
        const res = await callApi({
            url: "products/", method: "GET",
            params: { page, pageSize: 12, search: debounced, ordering: "-id", category: categoryFilter || undefined },
        });
        if (res?.status === 200) {
            const list = res.data.data.data || [];
            setProducts(list);
            setTotalPages(res.data.data.totalPages || 1);
            // Reset quick-edit drafts to match the freshly-fetched values so a
            // refetch never leaves a stale unsaved draft sitting on screen.
            const nextEdits = {};
            list.forEach((p) => { nextEdits[p.id] = draftFromProduct(p); });
            setEdits(nextEdits);
            setRowErrors({});
            // A refetched page's rows are not the same rows that were
            // selected before -- never carry a stale selection across pages.
            setSelectedIds(new Set());
        }
    }, [page, debounced, categoryFilter]); // eslint-disable-line react-hooks/exhaustive-deps

    useEffect(() => { getProducts(); }, [getProducts]);

    const handleSyncPrices = async () => {
        setSyncing(true);
        const res = await callApi({
            url: "products/admin/sync-prices/", method: "POST", rawError: true, silent: true,
        });
        setSyncing(false);
        if (res?.status === 200) {
            const n = res.data.data.changes?.length ?? 0;
            toast.success(`Price sync complete — ${n} product${n === 1 ? "" : "s"} updated.`);
            getProducts();
        } else {
            toast.error(res?.data?.message || "Price sync failed");
        }
    };

    const setDraftField = (productId, field, value) => {
        setEdits((prev) => ({
            ...prev,
            [productId]: { ...prev[productId], [field]: value, saved: false },
        }));
    };

    const revertDraft = (product) => {
        setEdits((prev) => ({ ...prev, [product.id]: draftFromProduct(product) }));
        setRowErrors((prev) => ({ ...prev, [product.id]: {} }));
    };

    // product.shipping_fee can come back as a string ("250.00", from a plain
    // DecimalField) -- always compare as Number so "250.00" and 250 don't
    // register as a spurious diff.
    const currentShippingFee = (product) =>
        product.shipping_fee === null || product.shipping_fee === undefined
            ? null : Number(product.shipping_fee);

    const isDirty = (product) => {
        const d = edits[product.id];
        if (!d) return false;
        const priceChanged = Number(d.initial_selling_price) !== product.initial_selling_price;
        const draftDiscount = d.discount_price === "" ? null : Number(d.discount_price);
        const discountChanged = draftDiscount !== (product.discount_price ?? null);
        const stockEditable = (product.variant_count ?? 0) <= 1;
        const stockChanged = stockEditable && Number(d.stock_quantity) !== (product.total_stock ?? 0);
        const draftShippingFee = d.shipping_fee === "" ? null : Number(d.shipping_fee);
        const shippingChanged = draftShippingFee !== currentShippingFee(product);
        const freeShippingChanged = !!d.free_shipping !== !!product.free_shipping;
        return priceChanged || discountChanged || stockChanged || shippingChanged || freeShippingChanged;
    };

    // Applies a server-confirmed product onto local state, keeping the table
    // from ever showing a value that was not actually saved.
    const applyServerProduct = (productId, patch) => {
        setProducts((prev) => prev.map((p) => (p.id === productId ? { ...p, ...patch } : p)));
    };

    const handleSaveRow = async (product) => {
        const draft = edits[product.id];
        if (!draft) return;
        const body = {};
        if (Number(draft.initial_selling_price) !== product.initial_selling_price) {
            body.initial_selling_price = Number(draft.initial_selling_price);
        }
        const draftDiscount = draft.discount_price === "" ? null : Number(draft.discount_price);
        if (draftDiscount !== (product.discount_price ?? null)) {
            body.discount_price = draftDiscount;
        }
        const stockEditable = (product.variant_count ?? 0) <= 1;
        if (stockEditable && Number(draft.stock_quantity) !== (product.total_stock ?? 0)) {
            body.stock_quantity = Number(draft.stock_quantity);
        }
        const draftShippingFee = draft.shipping_fee === "" ? null : Number(draft.shipping_fee);
        if (draftShippingFee !== currentShippingFee(product)) {
            body.shipping_fee = draftShippingFee;
        }
        if (!!draft.free_shipping !== !!product.free_shipping) {
            body.free_shipping = !!draft.free_shipping;
        }
        if (Object.keys(body).length === 0) return;

        setSavingIds((prev) => ({ ...prev, [product.id]: true }));
        setRowErrors((prev) => ({ ...prev, [product.id]: {} }));

        // rawError: without it callApi returns null on the 400 this endpoint
        // sends for a bad price/discount, and the row would silently look
        // saved even though nothing changed on the server.
        const res = await callApi({
            url: `products/admin/${product.id}/quick-update/`, method: "PATCH", body,
            rawError: true, silent: true,
        });

        setSavingIds((prev) => { const n = { ...prev }; delete n[product.id]; return n; });

        if (res?.status === 200) {
            const data = res.data.data;
            const totalStock = (data.variants || []).reduce((sum, v) => sum + (v.stock_quantity || 0), 0);
            applyServerProduct(product.id, {
                initial_selling_price: data.initial_selling_price,
                discount_price: data.discount_price,
                status: data.status,
                shipping_fee: data.shipping_fee,
                free_shipping: !!data.free_shipping,
                total_stock: totalStock,
                variant_count: data.variants?.length ?? product.variant_count,
            });
            setEdits((prev) => ({
                ...prev,
                [product.id]: {
                    initial_selling_price: String(data.initial_selling_price),
                    discount_price: data.discount_price === null ? "" : String(data.discount_price),
                    stock_quantity: String(totalStock),
                    shipping_fee: data.shipping_fee === null || data.shipping_fee === undefined ? "" : String(data.shipping_fee),
                    free_shipping: !!data.free_shipping,
                    saved: true,
                },
            }));
            toast.success("Product updated");
        } else {
            const fieldErrors = res?.data?.field_errors || {};
            setRowErrors((prev) => ({ ...prev, [product.id]: fieldErrors }));
            const message = res?.data?.message || "Could not save changes";
            toast.error(message);
        }
    };

    const handleToggleAvailability = async (product) => {
        const nextStatus = product.status === "ACTIVE" ? "INACTIVE" : "ACTIVE";
        setSavingIds((prev) => ({ ...prev, [product.id]: true }));
        const res = await callApi({
            url: `products/admin/${product.id}/quick-update/`, method: "PATCH",
            body: { status: nextStatus }, rawError: true, silent: true,
        });
        setSavingIds((prev) => { const n = { ...prev }; delete n[product.id]; return n; });
        if (res?.status === 200) {
            applyServerProduct(product.id, { status: res.data.data.status });
            toast.success(`${product.name} is now ${res.data.data.status === "ACTIVE" ? "available" : "unavailable"}`);
        } else {
            // Leave product.status untouched -- the Switch reflects committed
            // state, so on failure it simply stays where it was.
            toast.error(res?.data?.message || "Could not update availability");
        }
    };

    // --- Bulk shipping fee (apply to selected rows, or a whole category) ---

    const toggleSelectRow = (id) => {
        setSelectedIds((prev) => {
            const next = new Set(prev);
            if (next.has(id)) next.delete(id); else next.add(id);
            return next;
        });
    };

    const allOnPageSelected = products.length > 0 && products.every((p) => selectedIds.has(p.id));
    const toggleSelectAllOnPage = () => {
        setSelectedIds((prev) => {
            if (allOnPageSelected) return new Set();
            return new Set(products.map((p) => p.id));
        });
    };

    const selectedCategoryName = useMemo(() => {
        const found = flatCategories.find((c) => String(c.id) === String(categoryFilter));
        return found?.name || "";
    }, [flatCategories, categoryFilter]);

    const openBulkDialog = async () => {
        setBulkFee("");
        setBulkFreeShipping("");
        setBulkOpen(true);
        setBulkCategoryCount(null);
        // Only need a fresh count when the dialog will actually target the
        // category (no rows checked) -- the count must ignore the search box
        // (the bulk endpoint itself only understands product_ids/category,
        // not free-text search), so it's fetched fresh rather than reused
        // from the on-screen (possibly search-narrowed) totalPages state.
        if (selectedIds.size === 0 && categoryFilter) {
            setBulkCategoryCountLoading(true);
            const res = await callApi({
                url: "products/", method: "GET",
                params: { category: categoryFilter, pageSize: 1, page: 1 },
            });
            setBulkCategoryCountLoading(false);
            if (res?.status === 200) {
                setBulkCategoryCount(res.data.data.totalItems ?? null);
            }
        }
    };

    const bulkScope = selectedIds.size > 0 ? "selection" : (categoryFilter ? "category" : null);

    const handleBulkApply = async () => {
        if (!bulkScope) return;
        const body = { shipping_fee: bulkFee === "" ? null : Number(bulkFee) };
        if (bulkFreeShipping !== "") {
            body.free_shipping = bulkFreeShipping === "true";
        }
        if (bulkScope === "selection") {
            body.product_ids = Array.from(selectedIds);
        } else {
            body.category = categoryFilter;
        }

        setBulkSaving(true);
        // rawError: same reason as every other admin write here -- without
        // it a 400 (e.g. a negative fee, or a batch over the server's cap)
        // would come back as null and this would toast a fake success.
        const res = await callApi({
            url: "products/admin/shipping-fee/bulk/", method: "POST", body,
            rawError: true, silent: true,
        });
        setBulkSaving(false);

        if (res?.status === 200) {
            const updated = res.data.data.updated;
            toast.success(`Shipping fee updated on ${updated} product${updated === 1 ? "" : "s"}`);
            setBulkOpen(false);
            setSelectedIds(new Set());
            getProducts();
        } else {
            const fieldErrors = res?.data?.field_errors || {};
            const firstError = Object.values(fieldErrors)[0]?.[0];
            toast.error(firstError || res?.data?.message || "Could not apply the bulk shipping fee");
        }
    };

    return (
        <Box sx={{ width: "100%" }}>
            {!onProductSelected && (
                <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 2 }}>
                    <Breadcrumbs>
                        <Typography variant="body2" sx={{ cursor: "pointer" }} onClick={() => navigate("/admin")}>Home</Typography>
                        <Typography variant="body2">Products</Typography>
                    </Breadcrumbs>
                    <Stack direction="row" spacing={1}>
                        <Button
                            variant="outlined" startIcon={<LocalShippingIcon />}
                            disabled={selectedIds.size === 0 && !categoryFilter}
                            onClick={openBulkDialog}
                        >
                            Bulk shipping fee
                        </Button>
                        <Button variant="outlined" startIcon={<SyncIcon />} disabled={syncing} onClick={handleSyncPrices}>
                            {syncing ? "Syncing…" : "Sync prices"}
                        </Button>
                        <Button variant="contained" startIcon={<Add />} onClick={() => navigate("/admin/form/product")}>
                            Add Product
                        </Button>
                    </Stack>
                </Stack>
            )}

            <Stack direction={{ xs: "column", sm: "row" }} spacing={2} sx={{ mb: 2 }}>
                <TextField
                    size="small" fullWidth placeholder="Search products…" value={search}
                    onChange={(e) => setSearch(e.target.value)}
                    InputProps={{ startAdornment: <InputAdornment position="start"><SearchIcon /></InputAdornment> }}
                />
                <TextField
                    select size="small" label="Category" value={categoryFilter}
                    onChange={(e) => { setPage(1); setCategoryFilter(e.target.value); }}
                    sx={{ minWidth: 220 }}
                >
                    <MenuItem value="">All categories</MenuItem>
                    {flatCategories.map((c) => (
                        <MenuItem key={c.id} value={c.id}>
                            {"  ".repeat(c.depth)}{c.depth > 0 ? "— " : ""}{c.name}
                        </MenuItem>
                    ))}
                </TextField>
            </Stack>

            {loading && <LinearProgress sx={{ mb: 1 }} />}
            <TableContainer component={Paper}>
                <Table>
                    <TableHead>
                        <TableRow>
                            {!onProductSelected && (
                                <TableCell padding="checkbox">
                                    <Tooltip title="Select all on this page, to bulk-apply a shipping fee">
                                        <Checkbox
                                            size="small"
                                            checked={allOnPageSelected}
                                            indeterminate={selectedIds.size > 0 && !allOnPageSelected}
                                            onChange={toggleSelectAllOnPage}
                                        />
                                    </Tooltip>
                                </TableCell>
                            )}
                            <TableCell>Product</TableCell>
                            <TableCell>Category</TableCell>
                            <TableCell align="right">Price</TableCell>
                            <TableCell align="right">Discount</TableCell>
                            <TableCell align="right">Shipping</TableCell>
                            <TableCell align="right">Stock</TableCell>
                            <TableCell align="center">Available</TableCell>
                            <TableCell align="right">Actions</TableCell>
                        </TableRow>
                    </TableHead>
                    <TableBody>
                        {products.length === 0 && !loading && (
                            <TableRow><TableCell colSpan={onProductSelected ? 8 : 9} align="center">No products found</TableCell></TableRow>
                        )}
                        {products.map((p) => {
                            const draft = edits[p.id] || draftFromProduct(p);
                            const saving = !!savingIds[p.id];
                            const dirty = !onProductSelected && isDirty(p);
                            const errors = rowErrors[p.id] || {};
                            const stockEditable = (p.variant_count ?? 0) <= 1;

                            return (
                                <TableRow key={p.id} hover selected={dirty}>
                                    {!onProductSelected && (
                                        <TableCell padding="checkbox">
                                            <Checkbox
                                                size="small"
                                                checked={selectedIds.has(p.id)}
                                                onChange={() => toggleSelectRow(p.id)}
                                                inputProps={{ "aria-label": `Select ${p.name}` }}
                                            />
                                        </TableCell>
                                    )}
                                    <TableCell>
                                        <Stack direction="row" spacing={1.5} alignItems="center">
                                            <Avatar variant="rounded" src={firstImage(p.image)} sx={{ width: 44, height: 44 }}>
                                                {(p.name || "?").charAt(0)}
                                            </Avatar>
                                            <Box>
                                                <Typography variant="body2" fontWeight={600}>{p.name}</Typography>
                                                <Typography variant="caption" color="text.secondary">{p.brand || p.sku}</Typography>
                                            </Box>
                                        </Stack>
                                    </TableCell>
                                    <TableCell><Typography variant="body2">{cleanCategory(p.category_id)}</Typography></TableCell>

                                    {onProductSelected ? (
                                        <>
                                            <TableCell align="right">
                                                <Typography variant="body2" fontWeight={700}>৳{p.initial_selling_price}</Typography>
                                            </TableCell>
                                            <TableCell align="right">
                                                <Typography variant="body2" color="text.secondary">{p.discount_price ? `৳${p.discount_price}` : "—"}</Typography>
                                            </TableCell>
                                            <TableCell align="right">
                                                {p.free_shipping ? (
                                                    <Chip size="small" color="success" label="Free" />
                                                ) : (
                                                    <Typography variant="body2" color="text.secondary">
                                                        {p.shipping_fee !== null && p.shipping_fee !== undefined ? `৳${p.shipping_fee}` : "store rate"}
                                                    </Typography>
                                                )}
                                            </TableCell>
                                            <TableCell align="right">{p.total_stock ?? "—"}</TableCell>
                                            <TableCell align="center">
                                                <Chip size="small" label={p.status} color={p.status === "ACTIVE" ? "success" : "default"} />
                                            </TableCell>
                                        </>
                                    ) : (
                                        <>
                                            <TableCell align="right">
                                                <TextField
                                                    size="small" type="number" disabled={saving} value={draft.initial_selling_price}
                                                    onChange={(e) => setDraftField(p.id, "initial_selling_price", e.target.value)}
                                                    error={!!errors.initial_selling_price}
                                                    helperText={errors.initial_selling_price?.[0]}
                                                    InputProps={{ startAdornment: <InputAdornment position="start">৳</InputAdornment> }}
                                                    sx={{ width: 120 }}
                                                />
                                            </TableCell>
                                            <TableCell align="right">
                                                <TextField
                                                    size="small" type="number" disabled={saving} value={draft.discount_price}
                                                    onChange={(e) => setDraftField(p.id, "discount_price", e.target.value)}
                                                    error={!!errors.discount_price}
                                                    helperText={errors.discount_price?.[0]}
                                                    placeholder="none"
                                                    InputProps={{ startAdornment: <InputAdornment position="start">৳</InputAdornment> }}
                                                    sx={{ width: 120 }}
                                                />
                                            </TableCell>
                                            <TableCell align="right">
                                                <TextField
                                                    size="small" type="number" disabled={saving || draft.free_shipping} value={draft.shipping_fee}
                                                    onChange={(e) => setDraftField(p.id, "shipping_fee", e.target.value)}
                                                    error={!!errors.shipping_fee}
                                                    helperText={errors.shipping_fee?.[0]}
                                                    placeholder="store rate"
                                                    InputProps={{ startAdornment: <InputAdornment position="start">৳</InputAdornment> }}
                                                    sx={{ width: 120 }}
                                                />
                                                <Tooltip title="Free-shipping promo -- waives this product's shipping outright, distinct from a 0 fee (docs/SHIPPING_FEES.md)">
                                                    <FormControlLabel
                                                        sx={{ mr: 0, mt: 0.25 }}
                                                        control={
                                                            <Checkbox
                                                                size="small" disabled={saving} checked={!!draft.free_shipping}
                                                                onChange={(e) => setDraftField(p.id, "free_shipping", e.target.checked)}
                                                                inputProps={{ "aria-label": `Free shipping for ${p.name}` }}
                                                            />
                                                        }
                                                        label={<Typography variant="caption">Free shipping</Typography>}
                                                    />
                                                </Tooltip>
                                            </TableCell>
                                            <TableCell align="right">
                                                {stockEditable ? (
                                                    <TextField
                                                        size="small" type="number" disabled={saving} value={draft.stock_quantity}
                                                        onChange={(e) => setDraftField(p.id, "stock_quantity", e.target.value)}
                                                        error={!!errors.stock_quantity}
                                                        helperText={errors.stock_quantity?.[0]}
                                                        sx={{ width: 90 }}
                                                    />
                                                ) : (
                                                    <Tooltip title="Multiple sizes/variants — edit stock per variant from the product's edit page">
                                                        <Typography variant="body2">{p.total_stock ?? 0} ({p.variant_count})</Typography>
                                                    </Tooltip>
                                                )}
                                            </TableCell>
                                            <TableCell align="center">
                                                <Tooltip title={p.status === "ACTIVE" ? "Active — click to deactivate" : "Inactive — click to activate"}>
                                                    <span>
                                                        <Switch
                                                            size="small" color="success" checked={p.status === "ACTIVE"}
                                                            disabled={saving}
                                                            onChange={() => handleToggleAvailability(p)}
                                                            inputProps={{ "aria-label": `Toggle availability for ${p.name}` }}
                                                        />
                                                    </span>
                                                </Tooltip>
                                            </TableCell>
                                        </>
                                    )}

                                    <TableCell align="right">
                                        {onProductSelected ? (
                                            <Button size="small" variant="contained" startIcon={<Add />} onClick={() => onProductSelected(p)}>Select</Button>
                                        ) : (
                                            <Stack direction="row" justifyContent="flex-end" alignItems="center">
                                                {saving && <CircularProgress size={16} sx={{ mx: 0.5 }} />}
                                                {!saving && dirty && (
                                                    <>
                                                        <Tooltip title="Save changes">
                                                            <IconButton size="small" color="primary" onClick={() => handleSaveRow(p)} aria-label={`Save ${p.name}`}>
                                                                <SaveIcon fontSize="small" />
                                                            </IconButton>
                                                        </Tooltip>
                                                        <Tooltip title="Discard changes">
                                                            <IconButton size="small" onClick={() => revertDraft(p)} aria-label={`Undo ${p.name}`}>
                                                                <UndoIcon fontSize="small" />
                                                            </IconButton>
                                                        </Tooltip>
                                                    </>
                                                )}
                                                <Tooltip title="Edit"><IconButton size="small" onClick={() => navigate(`/admin/form/product/${p.id}`)}><Edit fontSize="small" color="primary" /></IconButton></Tooltip>
                                                <Tooltip title="Reviews"><IconButton size="small" onClick={() => { setReviewsFor(p.id); setQuestionsFor(null); }}><RateReviewOutlinedIcon fontSize="small" /></IconButton></Tooltip>
                                                <Tooltip title="Questions"><IconButton size="small" onClick={() => { setQuestionsFor(p.id); setReviewsFor(null); }}><HelpOutlineIcon fontSize="small" /></IconButton></Tooltip>
                                            </Stack>
                                        )}
                                    </TableCell>
                                </TableRow>
                            );
                        })}
                    </TableBody>
                </Table>
            </TableContainer>

            {totalPages > 1 && (
                <Stack alignItems="center" sx={{ mt: 2 }}>
                    <Pagination count={totalPages} page={page} onChange={(_, p) => setPage(p)} color="primary" />
                </Stack>
            )}

            <Dialog maxWidth="lg" fullWidth open={!!reviewsFor} onClose={() => setReviewsFor(null)}>
                <DialogContent><ManageReviews product_id={reviewsFor} /><Divider /></DialogContent>
            </Dialog>
            <Dialog maxWidth="lg" fullWidth open={!!questionsFor} onClose={() => setQuestionsFor(null)}>
                <DialogContent><ManageQuestions product_id={questionsFor} /></DialogContent>
            </Dialog>

            <Dialog maxWidth="xs" fullWidth open={bulkOpen} onClose={() => !bulkSaving && setBulkOpen(false)}>
                <DialogTitle>Bulk shipping fee</DialogTitle>
                <DialogContent>
                    {bulkScope === "selection" && (
                        <Alert severity="info" sx={{ mb: 2 }}>
                            This will set the shipping fee on <strong>{selectedIds.size}</strong> selected
                            product{selectedIds.size === 1 ? "" : "s"}.
                        </Alert>
                    )}
                    {bulkScope === "category" && (
                        <Alert severity="info" sx={{ mb: 2 }}>
                            {bulkCategoryCountLoading ? (
                                "Counting matching products…"
                            ) : (
                                <>
                                    This will set the shipping fee on{" "}
                                    <strong>{bulkCategoryCount ?? "all"}</strong> product
                                    {bulkCategoryCount === 1 ? "" : "s"} in{" "}
                                    <strong>{selectedCategoryName || "the selected category"}</strong>{" "}
                                    (its full subtree, ignoring the search box).
                                </>
                            )}
                        </Alert>
                    )}
                    {!bulkScope && (
                        <Alert severity="warning" sx={{ mb: 2 }}>
                            Check some products, or pick a category filter, before applying a bulk fee.
                        </Alert>
                    )}
                    <TextField
                        fullWidth size="small" type="number" label="Shipping fee"
                        value={bulkFee} onChange={(e) => setBulkFee(e.target.value)}
                        placeholder="leave blank to use the store rate"
                        InputProps={{ startAdornment: <InputAdornment position="start">৳</InputAdornment> }}
                        disabled={bulkSaving}
                        helperText="Leave blank to reset to the store's flat rate; 0 means free delivery."
                    />
                    <TextField
                        select fullWidth size="small" label="Free shipping promo" sx={{ mt: 2 }}
                        value={bulkFreeShipping} onChange={(e) => setBulkFreeShipping(e.target.value)}
                        disabled={bulkSaving}
                        helperText="A mixed selection has no single current value, so this only changes what you pick here."
                    >
                        <MenuItem value="">Don't change</MenuItem>
                        <MenuItem value="true">Mark as free-shipping promo</MenuItem>
                        <MenuItem value="false">Remove free-shipping promo</MenuItem>
                    </TextField>
                </DialogContent>
                <DialogActions>
                    <Button onClick={() => setBulkOpen(false)} disabled={bulkSaving}>Cancel</Button>
                    <Button
                        variant="contained" onClick={handleBulkApply}
                        disabled={!bulkScope || bulkSaving || bulkCategoryCountLoading}
                    >
                        {bulkSaving ? "Applying…" : "Apply"}
                    </Button>
                </DialogActions>
            </Dialog>
        </Box>
    );
};

export default ManageProducts;
