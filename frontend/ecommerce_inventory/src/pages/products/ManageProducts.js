import { useState, useEffect, useCallback, useMemo } from "react";
import { useNavigate } from "react-router-dom";
import {
    Box, Breadcrumbs, Button, Chip, IconButton, LinearProgress, Table, TableBody, TableCell,
    TableContainer, TableHead, TableRow, Paper, TextField, Typography, Stack, Avatar,
    InputAdornment, Pagination, Tooltip, Dialog, DialogContent, Divider, MenuItem, Switch,
    CircularProgress,
} from "@mui/material";
import Add from "@mui/icons-material/Add";
import Edit from "@mui/icons-material/Edit";
import SaveIcon from "@mui/icons-material/Save";
import UndoIcon from "@mui/icons-material/Undo";
import SearchIcon from "@mui/icons-material/Search";
import SyncIcon from "@mui/icons-material/Sync";
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

    const isDirty = (product) => {
        const d = edits[product.id];
        if (!d) return false;
        const priceChanged = Number(d.initial_selling_price) !== product.initial_selling_price;
        const draftDiscount = d.discount_price === "" ? null : Number(d.discount_price);
        const discountChanged = draftDiscount !== (product.discount_price ?? null);
        const stockEditable = (product.variant_count ?? 0) <= 1;
        const stockChanged = stockEditable && Number(d.stock_quantity) !== (product.total_stock ?? 0);
        return priceChanged || discountChanged || stockChanged;
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
                total_stock: totalStock,
                variant_count: data.variants?.length ?? product.variant_count,
            });
            setEdits((prev) => ({
                ...prev,
                [product.id]: {
                    initial_selling_price: String(data.initial_selling_price),
                    discount_price: data.discount_price === null ? "" : String(data.discount_price),
                    stock_quantity: String(totalStock),
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

    return (
        <Box sx={{ width: "100%" }}>
            {!onProductSelected && (
                <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 2 }}>
                    <Breadcrumbs>
                        <Typography variant="body2" sx={{ cursor: "pointer" }} onClick={() => navigate("/admin")}>Home</Typography>
                        <Typography variant="body2">Products</Typography>
                    </Breadcrumbs>
                    <Stack direction="row" spacing={1}>
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
                            <TableCell>Product</TableCell>
                            <TableCell>Category</TableCell>
                            <TableCell align="right">Price</TableCell>
                            <TableCell align="right">Discount</TableCell>
                            <TableCell align="right">Stock</TableCell>
                            <TableCell align="center">Available</TableCell>
                            <TableCell align="right">Actions</TableCell>
                        </TableRow>
                    </TableHead>
                    <TableBody>
                        {products.length === 0 && !loading && (
                            <TableRow><TableCell colSpan={7} align="center">No products found</TableCell></TableRow>
                        )}
                        {products.map((p) => {
                            const draft = edits[p.id] || draftFromProduct(p);
                            const saving = !!savingIds[p.id];
                            const dirty = !onProductSelected && isDirty(p);
                            const errors = rowErrors[p.id] || {};
                            const stockEditable = (p.variant_count ?? 0) <= 1;

                            return (
                                <TableRow key={p.id} hover selected={dirty}>
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
        </Box>
    );
};

export default ManageProducts;
