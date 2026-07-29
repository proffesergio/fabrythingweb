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

// Curated starting suggestions for the category dropdown, mirroring
// catalog.services_scrape_import's OPENCART_CATEGORY_PATHS /
// FABRILIFE_CATEGORY_PATHS on the backend -- used only to pre-populate the
// picker before the first search; the browse response's own `categories`
// list (returned by the server, which owns the authoritative copy) replaces
// this the moment a search comes back.
const FALLBACK_CATEGORIES = {
    potakait: [
        { path: "smart-phone", label: "Smartphones" },
        { path: "tablet-pc", label: "Tablets" },
        { path: "laptop", label: "Laptops" },
        { path: "smart-watch", label: "Smart Watches" },
        { path: "earphone-headphone", label: "Earbuds & Headphones" },
        { path: "power-bank", label: "Power Banks & Chargers" },
    ],
    canvasit: [
        { path: "smart-phone", label: "Smartphones" },
        { path: "tablet-pc", label: "Tablets" },
        { path: "laptop", label: "Laptops" },
        { path: "smart-watch", label: "Smart Watches" },
        { path: "earphone-headphone", label: "Earbuds & Headphones" },
        { path: "power-bank", label: "Power Banks & Chargers" },
    ],
    fabrilife: [
        { path: "men-tshirts", label: "Men's T-shirts" },
        { path: "men-polos", label: "Men's Polos" },
        { path: "women-kurti-tops", label: "Women's Kurti & Tops" },
    ],
};

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

    const [selected, setSelected] = useState(new Set());
    const [ourCategories, setOurCategories] = useState([]);
    const [targetCategory, setTargetCategory] = useState("");

    const [importing, setImporting] = useState(false);
    const [results, setResults] = useState(null);

    const flatOurCategories = useMemo(() => flattenCategories(ourCategories), [ourCategories]);

    useEffect(() => {
        setSourceCategories(FALLBACK_CATEGORIES[source] || []);
        setCategoryPath("");
        setCandidates([]);
        setSelected(new Set());
        setResults(null);
        setBrowsed(false);
    }, [source]);

    useEffect(() => {
        (async () => {
            const res = await callApi({ url: "products/categories/", method: "GET" });
            if (res?.status === 200) setOurCategories(res.data.data.data || []);
        })();
    }, []); // eslint-disable-line react-hooks/exhaustive-deps

    const handleBrowse = useCallback(async () => {
        if (!categoryPath && !query.trim()) {
            setBrowseError("Pick a category or type a search term first.");
            return;
        }
        setBrowseError("");
        setResults(null);
        const res = await callApi({
            url: "products/admin/import/browse/", method: "GET", rawError: true,
            params: { source, category: categoryPath || undefined, q: query.trim() || undefined },
        });
        if (res?.status === 200) {
            const data = res.data.data;
            setCandidates(data.candidates || []);
            if (data.categories?.length) setSourceCategories(data.categories);
            setSelected(new Set());
            setBrowsed(true);
        } else {
            setCandidates([]);
            setBrowsed(true);
            setBrowseError(res?.data?.message || "Could not fetch that listing.");
        }
    }, [source, categoryPath, query]); // eslint-disable-line react-hooks/exhaustive-deps

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
                        <TextField
                            fullWidth size="small" label="...or search term"
                            value={query} onChange={(e) => setQuery(e.target.value)}
                            placeholder="e.g. hoodie"
                        />
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
                <Alert severity="info" sx={{ mb: 2 }}>No products found for that category/search.</Alert>
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
