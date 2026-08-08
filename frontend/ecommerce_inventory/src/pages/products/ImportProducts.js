import { useCallback, useEffect, useMemo, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import {
    Alert, Autocomplete, Avatar, Box, Breadcrumbs, Button, Card, Checkbox, Chip,
    Dialog, DialogActions, DialogContent, DialogTitle, Divider, FormControlLabel,
    Grid, IconButton, LinearProgress, MenuItem, Stack, Switch, Tab, Table, TableBody,
    TableCell, TableContainer, TableHead, TableRow, Tabs, TextField, Tooltip, Typography,
} from "@mui/material";
import CloudDownloadOutlined from "@mui/icons-material/CloudDownloadOutlined";
import CheckCircleIcon from "@mui/icons-material/CheckCircle";
import ErrorIcon from "@mui/icons-material/Error";
import BlockIcon from "@mui/icons-material/Block";
import AddIcon from "@mui/icons-material/Add";
import EditIcon from "@mui/icons-material/Edit";
import DeleteIcon from "@mui/icons-material/Delete";
import RefreshIcon from "@mui/icons-material/Refresh";
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

const STATUS_META = {
    imported: { label: "Imported", color: "success", icon: <CheckCircleIcon fontSize="small" /> },
    skipped_exists: { label: "Already in store", color: "default", icon: <BlockIcon fontSize="small" /> },
    failed: { label: "Failed", color: "error", icon: <ErrorIcon fontSize="small" /> },
};

const RUN_STATUS_META = {
    RUNNING: { label: "Running", color: "info" },
    COMPLETED: { label: "Completed", color: "success" },
    FAILED: { label: "Failed", color: "error" },
};

const ADAPTER_OPTIONS = [
    { value: "", label: "No adapter yet" },
    { value: "opencart", label: "OpenCart (potakait/canvasit)" },
    { value: "fabrilife", label: "Fabrilife (Algolia)" },
];

const EMPTY_SOURCE_FORM = {
    name: "", slug: "", base_url: "", adapter_key: "",
    supports_search: false, is_enabled: false, sets_source_url: false, notes: "",
};

const EMPTY_CATEGORY_FORM = { source_path: "", label: "", our_category_slug: "" };

const firstFieldError = (fieldErrors) => Object.values(fieldErrors || {})[0]?.[0];

const ImportProducts = () => {
    const { callApi, loading } = useApi();
    const navigate = useNavigate();

    const [tab, setTab] = useState(0);

    // ---- Sources: fetched from the API (catalog.models.ImportSource), not a
    // hardcoded list -- this is what lets the owner add/disable a source
    // without a code change. See ImportSourceController on the backend. ----
    const [sources, setSources] = useState([]);
    const [sourcesError, setSourcesError] = useState("");

    const loadSources = useCallback(async () => {
        const res = await callApi({ url: "products/admin/import/sources/", method: "GET", rawError: true });
        if (res?.status === 200) {
            const list = res.data.data || [];
            setSources(list);
            setSourcesError("");
            return list;
        }
        setSourcesError(res?.data?.message || "Could not load import sources.");
        return [];
    }, []); // eslint-disable-line react-hooks/exhaustive-deps

    // A per-source route (/manage/import/fabrilife) pins the picker to that
    // source and hides the selector — the sidebar entry has already made the
    // choice, and leaving a dropdown that can silently switch away from it is
    // how you end up importing Arogga medicine into a sports category.
    const { sourceSlug } = useParams();
    const [source, setSource] = useState(sourceSlug || "");
    useEffect(() => {
        // Navigating straight from "Import from Fabrilife" to "Import from
        // Arogga" remounts nothing, so the state has to follow the route.
        if (sourceSlug) setSource(sourceSlug);
    }, [sourceSlug]);
    const [categoryPath, setCategoryPath] = useState("");
    const [query, setQuery] = useState("");
    const [candidates, setCandidates] = useState([]);
    // The API's own category list for the selected source (from
    // ImportSourceCategory) -- a live browse response can extend/replace it
    // (see handleBrowse), but the server is always the source of truth, never
    // a frontend fallback dict.
    const [browseCategories, setBrowseCategories] = useState(null);
    const [browsed, setBrowsed] = useState(false);
    const [browseError, setBrowseError] = useState("");
    // Zero-vs-unreachable bookkeeping from the last browse response, so an
    // empty result grid can say *why* it's empty instead of always reading
    // "no products found" -- see catalog.services_scrape_import.browse_
    // candidates on the backend for the full reasoning.
    const [browseMeta, setBrowseMeta] = useState({ listingProductCount: 0, fetchFailures: 0 });

    const activeSource = useMemo(() => sources.find((s) => s.slug === source) || null, [sources, source]);
    const searchSupported = !!activeSource?.supports_search;
    // Only the medicine adapter reports a prescription flag; for every other
    // source the field is absent and the Rx chips must not be rendered.
    const isMedicineSource = activeSource?.adapter_key === "arogga";
    // A listing page carries name/price/image for the whole category in ONE
    // request but cannot say whether an item needs a prescription -- that
    // marker only exists on the product page. Checking this fetches each
    // product (≈1s each, rate-limited) to find out. Default ON for a medicine
    // source: importing medicines without knowing their Rx status is the one
    // mistake that matters here.
    const [withRxStatus, setWithRxStatus] = useState(true);
    const sourceCategoriesFromApi = useMemo(() => (
        (activeSource?.categories || []).map((c) => (
            { path: c.source_path, label: c.label || c.source_path, our_category: c.our_category_slug }
        ))
    ), [activeSource]);
    const displayedCategories = browseCategories || sourceCategoriesFromApi;

    const [selected, setSelected] = useState(new Set());
    const [ourCategories, setOurCategories] = useState([]);
    const [targetCategory, setTargetCategory] = useState("");

    const [importing, setImporting] = useState(false);
    const [results, setResults] = useState(null);

    const flatOurCategories = useMemo(() => flattenCategories(ourCategories), [ourCategories]);

    // Bootstrap: source list + our own taxonomy, once.
    useEffect(() => {
        (async () => {
            const list = await loadSources();
            const firstEnabled = list.find((s) => s.is_enabled);
            if (firstEnabled) setSource(firstEnabled.slug);
        })();
    }, [loadSources]);

    useEffect(() => {
        (async () => {
            const res = await callApi({ url: "products/categories/", method: "GET" });
            if (res?.status === 200) setOurCategories(res.data.data.data || []);
        })();
    }, []); // eslint-disable-line react-hooks/exhaustive-deps

    useEffect(() => {
        setCategoryPath("");
        setQuery("");
        setCandidates([]);
        setSelected(new Set());
        setResults(null);
        setBrowsed(false);
        setBrowseError("");
        setBrowseCategories(null);
    }, [source]);

    const handleBrowse = useCallback(async () => {
        if (!activeSource) {
            setBrowseError("Pick a source first.");
            return;
        }
        const trimmedQuery = searchSupported ? query.trim() : "";
        if (!categoryPath && !trimmedQuery) {
            setBrowseError(searchSupported
                ? "Pick a category or type a search term first."
                : "Pick a category first — search isn't available for this source.");
            return;
        }
        setBrowseError("");
        setResults(null);
        const res = await callApi({
            url: "products/admin/import/browse/", method: "GET", rawError: true,
            params: {
                source, category: categoryPath || undefined, q: trimmedQuery || undefined,
                // The backend defaults detail=true; only a medicine source is
                // given the choice, and only there does it change the answer.
                detail: isMedicineSource ? String(withRxStatus) : undefined,
            },
        });
        if (res?.status === 200) {
            const data = res.data.data;
            setCandidates(data.candidates || []);
            if (data.categories?.length) setBrowseCategories(data.categories);
            setBrowseMeta({
                listingProductCount: data.listing_product_count ?? 0,
                fetchFailures: data.fetch_failures ?? 0,
            });
            setSelected(new Set());
            setBrowsed(true);
        } else {
            setCandidates([]);
            setBrowseMeta({ listingProductCount: 0, fetchFailures: 0 });
            setBrowsed(true);
            // Field-specific errors (e.g. `q` for an unsupported search) land
            // in field_errors -- fall back to the flat message otherwise.
            const fieldMessage = firstFieldError(res?.data?.field_errors);
            setBrowseError(fieldMessage || res?.data?.message || "Could not fetch that listing.");
        }
    }, [source, activeSource, categoryPath, query, searchSupported, isMedicineSource, withRxStatus]); // eslint-disable-line react-hooks/exhaustive-deps

    const toggleSelected = (url) => {
        setSelected((prev) => {
            const next = new Set(prev);
            if (next.has(url)) next.delete(url); else next.add(url);
            return next;
        });
    };

    const IMPORT_CAP = 12;

    // What the owner is about to import, medicine-wise. Counted from the
    // candidates actually ticked, not the whole page.
    const selectedCandidates = useMemo(
        () => candidates.filter((c) => selected.has(c.source_url)),
        [candidates, selected],
    );
    const selectedRxCount = selectedCandidates.filter((c) => c.requires_prescription === true).length;
    const selectedUnknownRxCount = isMedicineSource
        ? selectedCandidates.filter((c) => c.requires_prescription === null).length
        : 0;

    const handleImport = async () => {
        if (selected.size === 0 || !targetCategory) return;
        setImporting(true);
        setResults(null);
        const res = await callApi({
            url: "products/admin/import/", method: "POST", rawError: true,
            body: { source, source_urls: Array.from(selected), category_id: targetCategory },
        });
        setImporting(false);
        if (res?.status === 200) {
            setResults(res.data.data.results || []);
            // Candidates that just got imported/skipped can drop out of the
            // pending selection so a re-run of the button can't re-import them.
            setSelected(new Set());
            loadSources(); // last_synced_at just moved -- refresh the picker/management view
        } else {
            // Surface honestly -- callApi returns null on non-2xx without
            // rawError, and this screen has burned people before on a fake
            // "success" state. Show whatever the server actually said.
            const fieldMessage = firstFieldError(res?.data?.field_errors);
            setResults([{ source_url: "", status: "failed", reason: fieldMessage || res?.data?.message || "Import request failed" }]);
        }
    };

    // ---- Manage Sources tab: add/edit sources and their category mappings ----
    const [sourceDialogOpen, setSourceDialogOpen] = useState(false);
    const [editingSourceId, setEditingSourceId] = useState(null);
    const [sourceForm, setSourceForm] = useState(EMPTY_SOURCE_FORM);
    const [sourceFormErrors, setSourceFormErrors] = useState({});
    const [savingSource, setSavingSource] = useState(false);

    const openAddSource = () => {
        setEditingSourceId(null);
        setSourceForm(EMPTY_SOURCE_FORM);
        setSourceFormErrors({});
        setSourceDialogOpen(true);
    };
    const openEditSource = (s) => {
        setEditingSourceId(s.id);
        setSourceForm({
            name: s.name, slug: s.slug, base_url: s.base_url || "", adapter_key: s.adapter_key || "",
            supports_search: !!s.supports_search, is_enabled: !!s.is_enabled,
            sets_source_url: !!s.sets_source_url, notes: s.notes || "",
        });
        setSourceFormErrors({});
        setSourceDialogOpen(true);
    };

    const saveSource = async () => {
        setSavingSource(true);
        const isEdit = editingSourceId != null;
        const res = await callApi({
            url: isEdit ? `products/admin/import/sources/${editingSourceId}/` : "products/admin/import/sources/",
            method: isEdit ? "PATCH" : "POST",
            body: sourceForm, rawError: true,
        });
        setSavingSource(false);
        if (res?.status === 200 || res?.status === 201) {
            setSourceDialogOpen(false);
            await loadSources();
        } else {
            setSourceFormErrors(res?.data?.field_errors || {});
        }
    };

    const toggleSourceEnabled = async (s) => {
        const res = await callApi({
            url: `products/admin/import/sources/${s.id}/`, method: "PATCH",
            body: { is_enabled: !s.is_enabled }, rawError: true,
        });
        if (res?.status === 200) {
            await loadSources();
        } else {
            setSourcesError(firstFieldError(res?.data?.field_errors) || res?.data?.message || "Could not update source.");
        }
    };

    const [categoryDialogOpen, setCategoryDialogOpen] = useState(false);
    const [categoryDialogSourceId, setCategoryDialogSourceId] = useState(null);
    const [editingCategoryId, setEditingCategoryId] = useState(null);
    const [categoryForm, setCategoryForm] = useState(EMPTY_CATEGORY_FORM);
    const [categoryFormErrors, setCategoryFormErrors] = useState({});
    const [savingCategory, setSavingCategory] = useState(false);

    const openAddCategory = (sourceId) => {
        setCategoryDialogSourceId(sourceId);
        setEditingCategoryId(null);
        setCategoryForm(EMPTY_CATEGORY_FORM);
        setCategoryFormErrors({});
        setCategoryDialogOpen(true);
    };
    const openEditCategory = (sourceId, cat) => {
        setCategoryDialogSourceId(sourceId);
        setEditingCategoryId(cat.id);
        setCategoryForm({ source_path: cat.source_path, label: cat.label || "", our_category_slug: cat.our_category_slug });
        setCategoryFormErrors({});
        setCategoryDialogOpen(true);
    };

    const saveCategory = async () => {
        setSavingCategory(true);
        const isEdit = editingCategoryId != null;
        const res = await callApi({
            url: isEdit
                ? `products/admin/import/source-categories/${editingCategoryId}/`
                : `products/admin/import/sources/${categoryDialogSourceId}/categories/`,
            method: isEdit ? "PATCH" : "POST",
            body: categoryForm, rawError: true,
        });
        setSavingCategory(false);
        if (res?.status === 200 || res?.status === 201) {
            setCategoryDialogOpen(false);
            await loadSources();
        } else {
            setCategoryFormErrors(res?.data?.field_errors || {});
        }
    };

    const removeCategory = async (catId) => {
        const res = await callApi({ url: `products/admin/import/source-categories/${catId}/`, method: "DELETE", rawError: true });
        if (res?.status === 200) await loadSources();
    };

    // ---- Sync History tab (ImportRun) ----
    const [runs, setRuns] = useState([]);
    const [runsLoading, setRunsLoading] = useState(false);
    const [runsSourceFilter, setRunsSourceFilter] = useState("");

    const loadRuns = useCallback(async () => {
        setRunsLoading(true);
        const res = await callApi({
            url: "products/admin/import/runs/", method: "GET", rawError: true,
            params: runsSourceFilter ? { source: runsSourceFilter } : {},
        });
        setRunsLoading(false);
        if (res?.status === 200) setRuns(res.data.data.data || []);
    }, [runsSourceFilter]); // eslint-disable-line react-hooks/exhaustive-deps

    useEffect(() => {
        if (tab === 2) loadRuns();
    }, [tab, loadRuns]);

    return (
        <Box sx={{ width: "100%" }}>
            <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 2 }}>
                <Breadcrumbs>
                    <Typography variant="body2" sx={{ cursor: "pointer" }} onClick={() => navigate("/admin")}>Home</Typography>
                    <Typography variant="body2" sx={{ cursor: "pointer" }} onClick={() => navigate("/admin/manage/product")}>Products</Typography>
                    <Typography variant="body2">Import</Typography>
                </Breadcrumbs>
            </Stack>

            <Tabs value={tab} onChange={(_, v) => setTab(v)} sx={{ mb: 2 }}>
                <Tab label="Import" />
                <Tab label="Manage Sources" />
                <Tab label="Sync History" />
            </Tabs>

            {tab === 0 && (
                <>
                    <Card variant="outlined" sx={{ p: 2, mb: 2 }}>
                        <Grid container spacing={2} alignItems="center">
                            <Grid item xs={12} sm={3}>
                                <TextField
                                    select fullWidth size="small" label="Source" value={source}
                                    onChange={(e) => setSource(e.target.value)}
                                    // Locked when the route named the source: the sidebar
                                    // entry already chose it, and a dropdown that can drift
                                    // away is how Arogga medicine lands in a sports category.
                                    disabled={!!sourceSlug}
                                    helperText={sourceSlug ? `Locked to ${activeSource?.name || sourceSlug}` : undefined}
                                >
                                    {sources.map((s) => (
                                        <MenuItem key={s.slug} value={s.slug} disabled={!s.is_enabled}>
                                            {s.name}{!s.is_enabled ? " — disabled" : ""}
                                        </MenuItem>
                                    ))}
                                </TextField>
                            </Grid>
                            <Grid item xs={12} sm={3}>
                                <Autocomplete
                                    size="small"
                                    options={displayedCategories}
                                    getOptionLabel={(o) => (typeof o === "string" ? o : o.label || o.path)}
                                    value={displayedCategories.find((c) => c.path === categoryPath) || null}
                                    onChange={(_, v) => setCategoryPath(v ? v.path : "")}
                                    renderInput={(params) => <TextField {...params} label="Category on site" />}
                                />
                            </Grid>
                            <Grid item xs={12} sm={3}>
                                {searchSupported ? (
                                    <TextField
                                        fullWidth size="small" label="...or search term"
                                        value={query} onChange={(e) => setQuery(e.target.value)}
                                        placeholder="e.g. hoodie"
                                    />
                                ) : (
                                    <TextField
                                        fullWidth size="small" label="Search" disabled value=""
                                        helperText="Not available for this source — browse by category instead."
                                    />
                                )}
                            </Grid>
                            <Grid item xs={12} sm={3}>
                                <Button
                                    fullWidth variant="contained" startIcon={<CloudDownloadOutlined />}
                                    disabled={loading || !activeSource} onClick={handleBrowse}
                                >
                                    {loading ? "Fetching…" : "Fetch latest"}
                                </Button>
                            </Grid>
                        </Grid>
                        {isMedicineSource && (
                            <FormControlLabel
                                sx={{ mt: 1 }}
                                control={
                                    <Checkbox
                                        checked={withRxStatus}
                                        onChange={(e) => setWithRxStatus(e.target.checked)}
                                    />
                                }
                                label={
                                    withRxStatus
                                        ? "Check prescription status (opens each product — slower, ~1s per item)"
                                        : "Fast listing only — prescription status will show as unknown"
                                }
                            />
                        )}
                        {activeSource?.notes && !activeSource.is_enabled && (
                            <Alert severity="info" sx={{ mt: 2 }}>{activeSource.notes}</Alert>
                        )}
                        {browseError && <Alert severity="warning" sx={{ mt: 2 }}>{browseError}</Alert>}
                        {sourcesError && <Alert severity="error" sx={{ mt: 2 }}>{sourcesError}</Alert>}
                    </Card>

                    {loading && <LinearProgress sx={{ mb: 2 }} />}

                    {browsed && candidates.length === 0 && !browseError && (
                        browseMeta.listingProductCount > 0 ? (
                            <Alert severity="warning" sx={{ mb: 2 }}>
                                Found {browseMeta.listingProductCount} product link{browseMeta.listingProductCount === 1 ? "" : "s"} on
                                the source site but couldn't fetch/read any of them — it may be down or
                                blocking us right now. Try again in a moment.
                            </Alert>
                        ) : (
                            <Alert severity="info" sx={{ mb: 2 }}>No products found for that category/search.</Alert>
                        )
                    )}

                    {candidates.length > 0 && (
                        <>
                            <Grid container spacing={2} sx={{ mb: 2 }}>
                                {candidates.map((c) => (
                                    <Grid item xs={12} sm={6} md={4} lg={3} key={c.source_url}>
                                        <Card
                                            variant="outlined"
                                            sx={{
                                                p: 1.5, height: "100%", cursor: "pointer",
                                                borderColor: selected.has(c.source_url) ? "primary.main" : undefined,
                                                borderWidth: selected.has(c.source_url) ? 2 : 1,
                                                opacity: c.already_have ? 0.7 : 1,
                                            }}
                                            onClick={() => toggleSelected(c.source_url)}
                                        >
                                            <Box sx={{ position: "relative", mb: 1 }}>
                                                <Box
                                                    sx={{
                                                        width: "100%", aspectRatio: "1 / 1", borderRadius: 2,
                                                        overflow: "hidden", bgcolor: "#fff",
                                                        display: "flex", alignItems: "center", justifyContent: "center",
                                                        border: "1px solid", borderColor: "divider",
                                                    }}
                                                >
                                                    {firstImage(c.images) ? (
                                                        <Box
                                                            component="img"
                                                            src={firstImage(c.images)}
                                                            alt={c.name || ""}
                                                            loading="lazy"
                                                            sx={{ width: "100%", height: "100%", objectFit: "contain" }}
                                                        />
                                                    ) : (
                                                        <Avatar variant="rounded" sx={{ width: 56, height: 56 }}>
                                                            {(c.name || "?").charAt(0)}
                                                        </Avatar>
                                                    )}
                                                </Box>
                                                <Checkbox
                                                    checked={selected.has(c.source_url)}
                                                    onChange={() => toggleSelected(c.source_url)}
                                                    onClick={(e) => e.stopPropagation()}
                                                    sx={{
                                                        position: "absolute", top: 4, left: 4, p: 0.5,
                                                        bgcolor: "background.paper", borderRadius: 1,
                                                        "&:hover": { bgcolor: "background.paper" },
                                                    }}
                                                />
                                            </Box>
                                            <Typography variant="body2" fontWeight={600} sx={{ mt: 1 }} noWrap title={c.name}>
                                                {c.name}
                                            </Typography>
                                            {/* Two prices, clearly separated: what the source
                                                charges, and what we would put on the shelf after
                                                catalog.pricing.apply_markup. Showing only the
                                                source price meant picking stock without seeing
                                                the sell price or the margin. */}
                                            <Stack spacing={0.25} sx={{ mt: 0.75 }}>
                                                <Stack direction="row" spacing={0.75} alignItems="baseline">
                                                    <Typography variant="body1" fontWeight={800} color="success.main">
                                                        ৳{c.selling_discount_price ?? c.selling_price ?? "—"}
                                                    </Typography>
                                                    {c.selling_discount_price != null && c.selling_price != null && (
                                                        <Typography variant="caption" sx={{ textDecoration: "line-through" }} color="text.secondary">
                                                            ৳{c.selling_price}
                                                        </Typography>
                                                    )}
                                                    <Typography variant="caption" color="text.secondary">our price</Typography>
                                                </Stack>
                                                <Typography variant="caption" color="text.secondary">
                                                    cost ৳{c.discount_price ?? c.price}
                                                    {c.selling_price != null && (c.discount_price ?? c.price) != null
                                                        ? ` · +৳${(Number(c.selling_discount_price ?? c.selling_price) - Number(c.discount_price ?? c.price)).toFixed(2)} margin`
                                                        : ""}
                                                </Typography>
                                            </Stack>
                                            <Stack direction="row" spacing={0.5} sx={{ mt: 1, flexWrap: "wrap", gap: 0.5 }}>
                                                {c.already_have && (
                                                    <Chip size="small" label="Already in store" />
                                                )}
                                                {/* Medicines. `true` = the source page says it needs a
                                                    prescription, so it will import blocked at checkout
                                                    until rx_sales_enabled is on. `null` = a listing-only
                                                    browse, which cannot know -- said plainly rather than
                                                    shown as over-the-counter. */}
                                                {c.requires_prescription === true && (
                                                    <Chip size="small" color="error" variant="outlined"
                                                          label="Prescription required" />
                                                )}
                                                {c.requires_prescription === null && isMedicineSource && (
                                                    <Chip size="small" variant="outlined"
                                                          label="Rx status unknown" />
                                                )}
                                            </Stack>
                                        </Card>
                                    </Grid>
                                ))}
                            </Grid>

                            {selectedRxCount > 0 && (
                                <Alert severity="warning" sx={{ mb: 2 }}>
                                    {selectedRxCount} of the {selected.size} selected item
                                    {selected.size === 1 ? " is" : "s are"} prescription-only. They will
                                    import, but stay blocked at checkout until prescription sales are
                                    switched on in Store Configuration — which needs a DGDA licence.
                                </Alert>
                            )}
                            {selectedUnknownRxCount > 0 && (
                                <Alert severity="info" sx={{ mb: 2 }}>
                                    Prescription status is unknown for {selectedUnknownRxCount} selected
                                    item{selectedUnknownRxCount === 1 ? "" : "s"} (fast listing browse).
                                    Tick “Check prescription status” and fetch again to find out before
                                    importing.
                                </Alert>
                            )}
                            <Card variant="outlined" sx={{ p: 2, mb: 2 }}>
                                <Grid container spacing={2} alignItems="center">
                                    <Grid item xs={12} sm={4}>
                                        <Stack direction="row" spacing={1} sx={{ mb: 1 }}>
                                            <Button
                                                size="small"
                                                onClick={() => setSelected(new Set(
                                                    candidates.filter((c) => !c.already_have)
                                                        .slice(0, IMPORT_CAP).map((c) => c.source_url)))}
                                            >
                                                Select new ({candidates.filter((c) => !c.already_have).length})
                                            </Button>
                                            <Button size="small" onClick={() => setSelected(new Set())}>
                                                Clear
                                            </Button>
                                        </Stack>
                                        <Typography variant="body2">
                                            {selected.size} selected (cap {IMPORT_CAP} per request — reference sites
                                            are rate-limited to 1 request/second, so a run takes roughly 1
                                            second per product)
                                        </Typography>
                                    </Grid>
                                    <Grid item xs={12} sm={4}>
                                        <TextField
                                            select fullWidth size="small" label="Import into category"
                                            value={targetCategory} onChange={(e) => setTargetCategory(e.target.value)}
                                        >
                                            <MenuItem value="">Choose a category…</MenuItem>
                                            {flatOurCategories.map((c) => (
                                                <MenuItem key={c.id} value={c.id}>
                                                    {"  ".repeat(c.depth)}{c.depth > 0 ? "— " : ""}{c.name}
                                                </MenuItem>
                                            ))}
                                        </TextField>
                                    </Grid>
                                    <Grid item xs={12} sm={4}>
                                        <Button
                                            fullWidth variant="contained" color="primary"
                                            disabled={importing || selected.size === 0 || selected.size > IMPORT_CAP || !targetCategory}
                                            onClick={handleImport}
                                        >
                                            {importing
                                                ? `Importing ${selected.size} product${selected.size === 1 ? "" : "s"}… this can take ~${selected.size}s`
                                                : `Import ${selected.size || ""} selected`}
                                        </Button>
                                    </Grid>
                                </Grid>
                                {selected.size > IMPORT_CAP && (
                                    <Alert severity="warning" sx={{ mt: 2 }}>
                                        Import is capped at {IMPORT_CAP} products per request. Deselect some and run again.
                                    </Alert>
                                )}
                                {importing && <LinearProgress sx={{ mt: 2 }} />}
                            </Card>
                        </>
                    )}

                    {results && (
                        <Card variant="outlined" sx={{ p: 2 }}>
                            <Typography variant="subtitle1" sx={{ mb: 1 }}>Import results</Typography>
                            <Stack spacing={1}>
                                {results.map((r, i) => {
                                    const meta = STATUS_META[r.status] || STATUS_META.failed;
                                    return (
                                        <Stack key={r.source_url || i} direction="row" spacing={1} alignItems="center">
                                            <Chip size="small" color={meta.color} icon={meta.icon} label={meta.label} />
                                            <Typography variant="body2" sx={{ flex: 1 }} noWrap>
                                                {r.name || r.source_url || "—"}
                                            </Typography>
                                            {r.reason && (
                                                <Tooltip title={r.reason}>
                                                    <Typography variant="caption" color="text.secondary" noWrap sx={{ maxWidth: 260 }}>
                                                        {r.reason}
                                                    </Typography>
                                                </Tooltip>
                                            )}
                                        </Stack>
                                    );
                                })}
                            </Stack>
                        </Card>
                    )}
                </>
            )}

            {tab === 1 && (
                <Box>
                    <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 2 }}>
                        <Typography variant="subtitle1">Import sources</Typography>
                        <Button variant="contained" startIcon={<AddIcon />} onClick={openAddSource}>Add source</Button>
                    </Stack>

                    {sourcesError && <Alert severity="error" sx={{ mb: 2 }}>{sourcesError}</Alert>}

                    <Stack spacing={2}>
                        {sources.map((s) => (
                            <Card key={s.id} variant="outlined" sx={{ p: 2 }}>
                                <Stack direction="row" justifyContent="space-between" alignItems="flex-start" flexWrap="wrap">
                                    <Box>
                                        <Stack direction="row" spacing={1} alignItems="center">
                                            <Typography variant="subtitle2">{s.name}</Typography>
                                            <Chip size="small" label={s.slug} />
                                            <Chip size="small" label={s.adapter_key || "no adapter"} color={s.adapter_key ? "default" : "warning"} />
                                            {s.supports_search && <Chip size="small" label="search" color="info" />}
                                            {s.sets_source_url && <Chip size="small" label="price-synced" color="secondary" />}
                                        </Stack>
                                        <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>{s.base_url}</Typography>
                                        {s.notes && <Typography variant="caption" color="text.secondary">{s.notes}</Typography>}
                                    </Box>
                                    <Stack direction="row" spacing={1} alignItems="center">
                                        <FormControlLabel
                                            control={<Switch checked={!!s.is_enabled} onChange={() => toggleSourceEnabled(s)} />}
                                            label={s.is_enabled ? "Enabled" : "Disabled"}
                                        />
                                        <IconButton size="small" onClick={() => openEditSource(s)} aria-label={`Edit ${s.name}`}>
                                            <EditIcon fontSize="small" />
                                        </IconButton>
                                    </Stack>
                                </Stack>

                                <Divider sx={{ my: 1.5 }} />

                                <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 1 }}>
                                    <Typography variant="body2" fontWeight={600}>Category mappings</Typography>
                                    <Button size="small" startIcon={<AddIcon />} onClick={() => openAddCategory(s.id)}>Add mapping</Button>
                                </Stack>
                                {(s.categories || []).length === 0 ? (
                                    <Typography variant="caption" color="text.secondary">No category mappings yet.</Typography>
                                ) : (
                                    <TableContainer>
                                        <Table size="small">
                                            <TableHead>
                                                <TableRow>
                                                    <TableCell>Source path</TableCell>
                                                    <TableCell>Label</TableCell>
                                                    <TableCell>Our category</TableCell>
                                                    <TableCell align="right">Actions</TableCell>
                                                </TableRow>
                                            </TableHead>
                                            <TableBody>
                                                {(s.categories || []).map((cat) => (
                                                    <TableRow key={cat.id}>
                                                        <TableCell>{cat.source_path}</TableCell>
                                                        <TableCell>{cat.label}</TableCell>
                                                        <TableCell>{cat.our_category_slug}</TableCell>
                                                        <TableCell align="right">
                                                            <IconButton size="small" onClick={() => openEditCategory(s.id, cat)} aria-label={`Edit ${cat.source_path}`}>
                                                                <EditIcon fontSize="small" />
                                                            </IconButton>
                                                            <IconButton size="small" onClick={() => removeCategory(cat.id)} aria-label={`Delete ${cat.source_path}`}>
                                                                <DeleteIcon fontSize="small" />
                                                            </IconButton>
                                                        </TableCell>
                                                    </TableRow>
                                                ))}
                                            </TableBody>
                                        </Table>
                                    </TableContainer>
                                )}
                            </Card>
                        ))}
                    </Stack>

                    <Dialog open={sourceDialogOpen} onClose={() => setSourceDialogOpen(false)} maxWidth="sm" fullWidth>
                        <DialogTitle>{editingSourceId ? "Edit source" : "Add source"}</DialogTitle>
                        <DialogContent>
                            <Stack spacing={2} sx={{ mt: 1 }}>
                                <TextField
                                    label="Name" value={sourceForm.name} fullWidth
                                    onChange={(e) => setSourceForm((f) => ({ ...f, name: e.target.value }))}
                                    error={!!sourceFormErrors.name} helperText={sourceFormErrors.name?.[0]}
                                />
                                <TextField
                                    label="Slug" value={sourceForm.slug} fullWidth
                                    onChange={(e) => setSourceForm((f) => ({ ...f, slug: e.target.value }))}
                                    disabled={!!editingSourceId}
                                    error={!!sourceFormErrors.slug} helperText={sourceFormErrors.slug?.[0]}
                                />
                                <TextField
                                    label="Base URL" value={sourceForm.base_url} fullWidth
                                    onChange={(e) => setSourceForm((f) => ({ ...f, base_url: e.target.value }))}
                                    error={!!sourceFormErrors.base_url} helperText={sourceFormErrors.base_url?.[0]}
                                />
                                <TextField
                                    select label="Adapter" value={sourceForm.adapter_key} fullWidth
                                    onChange={(e) => setSourceForm((f) => ({ ...f, adapter_key: e.target.value }))}
                                    error={!!sourceFormErrors.adapter_key} helperText={sourceFormErrors.adapter_key?.[0]}
                                >
                                    {ADAPTER_OPTIONS.map((o) => (
                                        <MenuItem key={o.value} value={o.value}>{o.label}</MenuItem>
                                    ))}
                                </TextField>
                                <FormControlLabel
                                    control={<Checkbox checked={sourceForm.supports_search}
                                        onChange={(e) => setSourceForm((f) => ({ ...f, supports_search: e.target.checked }))} />}
                                    label="Supports free-text search"
                                />
                                <FormControlLabel
                                    control={<Checkbox checked={sourceForm.sets_source_url}
                                        onChange={(e) => setSourceForm((f) => ({ ...f, sets_source_url: e.target.checked }))} />}
                                    label="Partner store (sets source_url — price-sync re-prices these)"
                                />
                                <FormControlLabel
                                    control={<Checkbox checked={sourceForm.is_enabled}
                                        onChange={(e) => setSourceForm((f) => ({ ...f, is_enabled: e.target.checked }))} />}
                                    label="Enabled"
                                />
                                {sourceFormErrors.is_enabled && (
                                    <Alert severity="warning">{sourceFormErrors.is_enabled[0]}</Alert>
                                )}
                                <TextField
                                    label="Notes" value={sourceForm.notes} fullWidth multiline minRows={2}
                                    onChange={(e) => setSourceForm((f) => ({ ...f, notes: e.target.value }))}
                                />
                            </Stack>
                        </DialogContent>
                        <DialogActions>
                            <Button onClick={() => setSourceDialogOpen(false)}>Cancel</Button>
                            <Button variant="contained" disabled={savingSource} onClick={saveSource}>
                                {savingSource ? "Saving…" : "Save"}
                            </Button>
                        </DialogActions>
                    </Dialog>

                    <Dialog open={categoryDialogOpen} onClose={() => setCategoryDialogOpen(false)} maxWidth="sm" fullWidth>
                        <DialogTitle>{editingCategoryId ? "Edit category mapping" : "Add category mapping"}</DialogTitle>
                        <DialogContent>
                            <Stack spacing={2} sx={{ mt: 1 }}>
                                <TextField
                                    label="Source path" value={categoryForm.source_path} fullWidth
                                    onChange={(e) => setCategoryForm((f) => ({ ...f, source_path: e.target.value }))}
                                    error={!!categoryFormErrors.source_path} helperText={categoryFormErrors.source_path?.[0]}
                                />
                                <TextField
                                    label="Label" value={categoryForm.label} fullWidth
                                    onChange={(e) => setCategoryForm((f) => ({ ...f, label: e.target.value }))}
                                    error={!!categoryFormErrors.label} helperText={categoryFormErrors.label?.[0]}
                                />
                                <TextField
                                    label="Our category slug" value={categoryForm.our_category_slug} fullWidth
                                    onChange={(e) => setCategoryForm((f) => ({ ...f, our_category_slug: e.target.value }))}
                                    error={!!categoryFormErrors.our_category_slug} helperText={categoryFormErrors.our_category_slug?.[0]}
                                />
                            </Stack>
                        </DialogContent>
                        <DialogActions>
                            <Button onClick={() => setCategoryDialogOpen(false)}>Cancel</Button>
                            <Button variant="contained" disabled={savingCategory} onClick={saveCategory}>
                                {savingCategory ? "Saving…" : "Save"}
                            </Button>
                        </DialogActions>
                    </Dialog>
                </Box>
            )}

            {tab === 2 && (
                <Box>
                    <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 2 }}>
                        <Typography variant="subtitle1">Sync history</Typography>
                        <Stack direction="row" spacing={1} alignItems="center">
                            <TextField
                                select size="small" label="Source" sx={{ minWidth: 180 }}
                                value={runsSourceFilter} onChange={(e) => setRunsSourceFilter(e.target.value)}
                            >
                                <MenuItem value="">All sources</MenuItem>
                                {sources.map((s) => <MenuItem key={s.slug} value={s.slug}>{s.name}</MenuItem>)}
                            </TextField>
                            <IconButton onClick={loadRuns} aria-label="Refresh"><RefreshIcon /></IconButton>
                        </Stack>
                    </Stack>

                    {runsLoading && <LinearProgress sx={{ mb: 2 }} />}

                    <TableContainer component={Card} variant="outlined">
                        <Table size="small">
                            <TableHead>
                                <TableRow>
                                    <TableCell>Source</TableCell>
                                    <TableCell>Status</TableCell>
                                    <TableCell>Started</TableCell>
                                    <TableCell align="right">Found</TableCell>
                                    <TableCell align="right">Imported</TableCell>
                                    <TableCell align="right">Skipped</TableCell>
                                    <TableCell align="right">Failed</TableCell>
                                    <TableCell>Triggered by</TableCell>
                                    <TableCell>Error</TableCell>
                                </TableRow>
                            </TableHead>
                            <TableBody>
                                {runs.length === 0 && !runsLoading && (
                                    <TableRow><TableCell colSpan={9} align="center">No import runs yet</TableCell></TableRow>
                                )}
                                {runs.map((r) => {
                                    const meta = RUN_STATUS_META[r.status] || RUN_STATUS_META.RUNNING;
                                    return (
                                        <TableRow key={r.id}>
                                            <TableCell>{r.source_name || r.source_slug}</TableCell>
                                            <TableCell><Chip size="small" color={meta.color} label={meta.label} /></TableCell>
                                            <TableCell>{r.started_at}</TableCell>
                                            <TableCell align="right">{r.found_count}</TableCell>
                                            <TableCell align="right">{r.imported_count}</TableCell>
                                            <TableCell align="right">{r.skipped_count}</TableCell>
                                            <TableCell align="right">{r.failed_count}</TableCell>
                                            <TableCell>{r.triggered_by || "—"}</TableCell>
                                            <TableCell>
                                                {r.error_summary ? (
                                                    <Tooltip title={r.error_summary}>
                                                        <Typography variant="caption" noWrap sx={{ maxWidth: 200, display: "block" }}>
                                                            {r.error_summary}
                                                        </Typography>
                                                    </Tooltip>
                                                ) : "—"}
                                            </TableCell>
                                        </TableRow>
                                    );
                                })}
                            </TableBody>
                        </Table>
                    </TableContainer>
                </Box>
            )}
        </Box>
    );
};

export default ImportProducts;
