import { useCallback, useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
    Alert, Autocomplete, Avatar, Box, Breadcrumbs, Button, Card, Checkbox, Chip,
    Grid, LinearProgress, MenuItem, Stack, TextField, Tooltip, Typography,
} from "@mui/material";
import CloudDownloadOutlined from "@mui/icons-material/CloudDownloadOutlined";
import CheckCircleIcon from "@mui/icons-material/CheckCircle";
import ErrorIcon from "@mui/icons-material/Error";
import BlockIcon from "@mui/icons-material/Block";
import useApi from "../../hooks/APIHandler";

// Arogga is out of scope for this tool -- no parser exists for it yet and it
// belongs to the separate pharmacy phase. Shown disabled rather than omitted
// so the admin knows it's coming, not missing.
const SOURCES = [
    { value: "potakait", label: "Potakait.com" },
    { value: "canvasit", label: "Canvasit.com.bd" },
    { value: "fabrilife", label: "Fabrilife.com" },
    { value: "arogga", label: "Arogga.com", disabled: true, note: "coming with the pharmacy phase" },
];

// Starting suggestions for the category dropdown, mirroring
// catalog.services_scrape_import's OPENCART_CATEGORY_PATHS /
// FABRILIFE_CATEGORY_PATHS on the backend -- used only to pre-populate the
// picker before the first search; the browse response's own `categories`
// list (returned by the server, which owns the authoritative copy) replaces
// this the moment a search comes back. potakait/canvasit paths here are
// VERIFIED against the live sites (2026-07-28 -- real requests, not
// guesses); only computer-hardware categories are verified today (note
// "router" is singular on both -- "routers" 404s). Phones/gadgets aren't
// browsable by category on either OpenCart site yet -- on canvasit, use
// search instead (it works); potakait has no working search endpoint at all.
const FALLBACK_CATEGORIES = {
    potakait: [
        { path: "laptops", label: "Laptops" },
        { path: "gaming-pc", label: "Gaming PCs" },
        { path: "monitors", label: "Monitors" },
        { path: "processors", label: "Processors" },
        { path: "keyboards", label: "Keyboards" },
        { path: "printers", label: "Printers" },
        { path: "router", label: "Routers" },
    ],
    canvasit: [
        { path: "laptop", label: "Laptops" },
        { path: "desktop-pc", label: "Desktops" },
        { path: "monitor", label: "Monitors" },
        { path: "processor", label: "Processors" },
        { path: "keyboard", label: "Keyboards" },
        { path: "printer", label: "Printers" },
        { path: "router", label: "Routers" },
    ],
    fabrilife: [
        { path: "men-tshirts", label: "Men's T-shirts" },
        { path: "men-polos", label: "Men's Polos" },
        { path: "women-kurti-tops", label: "Women's Kurti & Tops" },
    ],
};

// Which sources have a working free-text search -- must match
// catalog.services_scrape_import.SOURCE_SEARCH_SUPPORTED on the backend.
// potakait.com's search is JS/API-driven with no working URL we could find
// (verified live: every plausible search route 404s), so the search box is
// hidden for it rather than shipped as a silent zero-result trap.
const SEARCH_SUPPORTED = { potakait: false, canvasit: true, fabrilife: true };

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

const ImportProducts = () => {
    const { callApi, loading } = useApi();
    const navigate = useNavigate();

    const [source, setSource] = useState("potakait");
    const [categoryPath, setCategoryPath] = useState("");
    const [query, setQuery] = useState("");
    const [candidates, setCandidates] = useState([]);
    const [sourceCategories, setSourceCategories] = useState(FALLBACK_CATEGORIES.potakait);
    const [browsed, setBrowsed] = useState(false);
    const [browseError, setBrowseError] = useState("");
    // Zero-vs-unreachable bookkeeping from the last browse response, so an
    // empty result grid can say *why* it's empty instead of always reading
    // "no products found" -- see catalog.services_scrape_import.browse_
    // candidates on the backend for the full reasoning.
    const [browseMeta, setBrowseMeta] = useState({ listingProductCount: 0, fetchFailures: 0 });

    const searchSupported = SEARCH_SUPPORTED[source] !== false;

    const [selected, setSelected] = useState(new Set());
    const [ourCategories, setOurCategories] = useState([]);
    const [targetCategory, setTargetCategory] = useState("");

    const [importing, setImporting] = useState(false);
    const [results, setResults] = useState(null);

    const flatOurCategories = useMemo(() => flattenCategories(ourCategories), [ourCategories]);

    useEffect(() => {
        setSourceCategories(FALLBACK_CATEGORIES[source] || []);
        setCategoryPath("");
        setQuery("");
        setCandidates([]);
        setSelected(new Set());
        setResults(null);
        setBrowsed(false);
        setBrowseError("");
    }, [source]);

    useEffect(() => {
        (async () => {
            const res = await callApi({ url: "products/categories/", method: "GET" });
            if (res?.status === 200) setOurCategories(res.data.data.data || []);
        })();
    }, []); // eslint-disable-line react-hooks/exhaustive-deps

    const handleBrowse = useCallback(async () => {
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
            params: { source, category: categoryPath || undefined, q: trimmedQuery || undefined },
        });
        if (res?.status === 200) {
            const data = res.data.data;
            setCandidates(data.candidates || []);
            if (data.categories?.length) setSourceCategories(data.categories);
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
            const fieldErrors = res?.data?.field_errors || {};
            const fieldMessage = Object.values(fieldErrors)[0]?.[0];
            setBrowseError(fieldMessage || res?.data?.message || "Could not fetch that listing.");
        }
    }, [source, categoryPath, query, searchSupported]); // eslint-disable-line react-hooks/exhaustive-deps

    const toggleSelected = (url) => {
        setSelected((prev) => {
            const next = new Set(prev);
            if (next.has(url)) next.delete(url); else next.add(url);
            return next;
        });
    };

    const IMPORT_CAP = 12;

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
        } else {
            // Surface honestly -- callApi returns null on non-2xx without
            // rawError, and this screen has burned people before on a fake
            // "success" state. Show whatever the server actually said.
            setResults([{ source_url: "", status: "failed", reason: res?.data?.message || "Import request failed" }]);
        }
    };

    return (
        <Box sx={{ width: "100%" }}>
            <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 2 }}>
                <Breadcrumbs>
                    <Typography variant="body2" sx={{ cursor: "pointer" }} onClick={() => navigate("/admin")}>Home</Typography>
                    <Typography variant="body2" sx={{ cursor: "pointer" }} onClick={() => navigate("/admin/manage/product")}>Products</Typography>
                    <Typography variant="body2">Import</Typography>
                </Breadcrumbs>
            </Stack>

            <Card variant="outlined" sx={{ p: 2, mb: 2 }}>
                <Grid container spacing={2} alignItems="center">
                    <Grid item xs={12} sm={3}>
                        <TextField
                            select fullWidth size="small" label="Source" value={source}
                            onChange={(e) => setSource(e.target.value)}
                        >
                            {SOURCES.map((s) => (
                                <MenuItem key={s.value} value={s.value} disabled={s.disabled}>
                                    {s.label}{s.disabled ? ` — ${s.note}` : ""}
                                </MenuItem>
                            ))}
                        </TextField>
                    </Grid>
                    <Grid item xs={12} sm={3}>
                        <Autocomplete
                            size="small"
                            options={sourceCategories}
                            getOptionLabel={(o) => (typeof o === "string" ? o : o.label || o.path)}
                            value={sourceCategories.find((c) => c.path === categoryPath) || null}
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
                            disabled={loading} onClick={handleBrowse}
                        >
                            {loading ? "Fetching…" : "Fetch latest"}
                        </Button>
                    </Grid>
                </Grid>
                {browseError && <Alert severity="warning" sx={{ mt: 2 }}>{browseError}</Alert>}
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
                                    <Stack direction="row" spacing={1} alignItems="flex-start">
                                        <Checkbox
                                            checked={selected.has(c.source_url)}
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
                                    {c.already_have && (
                                        <Chip size="small" label="Already in store" sx={{ mt: 1 }} />
                                    )}
                                </Card>
                            </Grid>
                        ))}
                    </Grid>

                    <Card variant="outlined" sx={{ p: 2, mb: 2 }}>
                        <Grid container spacing={2} alignItems="center">
                            <Grid item xs={12} sm={4}>
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
        </Box>
    );
};

export default ImportProducts;
