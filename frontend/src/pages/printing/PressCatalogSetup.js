import { useEffect, useState, useCallback } from "react";
import {
    Box, Typography, Tabs, Tab, Table, TableBody, TableCell, TableHead, TableRow, Paper,
    TableContainer, Button, IconButton, TextField, Stack, Switch, MenuItem, Divider,
} from "@mui/material";
import DeleteIcon from "@mui/icons-material/Delete";
import { toast } from "react-toastify";
import useApi from "../../hooks/APIHandler";

// Press catalog admin: products (+ sizes), paper stocks, finishing matrix,
// courier rates and the shop config (USD rate, margin, upload cap, fallback
// shipping matrix). All backend-driven — no deploys to retune pricing.
const PRODUCT_CATEGORIES = ["cards", "flyers", "banners", "office", "packaging", "corporate"];
const FINISHING_KINDS = ["SIDE", "LAMINATION", "FINISHING"];
const SHIPPING_ZONES = ["INSIDE_DHAKA_HOME", "HUB_PICKUP", "OUTSIDE_DHAKA"];

export default function PressCatalogSetup() {
    const { callApi } = useApi();
    const [tab, setTab] = useState(0);

    const [products, setProducts] = useState([]);
    const [newProduct, setNewProduct] = useState({ name: "", slug: "", category: "cards", base_setup_cost: "", per_sq_inch_rate: "" });
    const [sizes, setSizes] = useState([]);
    const [newSize, setNewSize] = useState({ product: "", name: "", width: "", height: "", unit: "in" });

    const [papers, setPapers] = useState([]);
    const [newPaper, setNewPaper] = useState({ name: "", gsm: "", multiplier: "1.0" });

    const [finishings, setFinishings] = useState([]);
    const [newFinishing, setNewFinishing] = useState({ kind: "FINISHING", name: "", price: "", per_unit: true });

    const [rates, setRates] = useState([]);
    const [newRate, setNewRate] = useState({ zone: "INSIDE_DHAKA_HOME", courier: "", base_fee: "", per_kg_fee: "" });

    const [shopConfig, setShopConfig] = useState(null);
    const [configDraft, setConfigDraft] = useState({ usd_rate: "", default_margin_factor: "", max_upload_mb: "" });

    const fetchAll = useCallback(async () => {
        const [p, s, pa, f, r, c] = await Promise.all([
            callApi({ url: "print/press/admin/products/", rawError: true, silent: true }),
            callApi({ url: "print/press/admin/sizes/", rawError: true, silent: true }),
            callApi({ url: "print/press/admin/paper/", rawError: true, silent: true }),
            callApi({ url: "print/press/admin/finishing/", rawError: true, silent: true }),
            callApi({ url: "print/press/admin/shipping/", rawError: true, silent: true }),
            callApi({ url: "print/press/admin/shop-config/", rawError: true, silent: true }),
        ]);
        if (p?.status === 200) setProducts(p.data.data);
        if (s?.status === 200) setSizes(s.data.data);
        if (pa?.status === 200) setPapers(pa.data.data);
        if (f?.status === 200) setFinishings(f.data.data);
        if (r?.status === 200) setRates(r.data.data);
        if (c?.status === 200) {
            setShopConfig(c.data.data);
            setConfigDraft({
                usd_rate: c.data.data.usd_rate, default_margin_factor: c.data.data.default_margin_factor,
                max_upload_mb: c.data.data.max_upload_mb,
            });
        }
    }, []); // eslint-disable-line react-hooks/exhaustive-deps

    useEffect(() => { fetchAll(); }, [fetchAll]);

    const create = async (url, body, okMsg) => {
        const res = await callApi({ url, method: "POST", body, rawError: true });
        if (res?.status === 201) { toast.success(okMsg); fetchAll(); return true; }
        toast.error(res?.data?.message || JSON.stringify(res?.data?.data || "Could not create"));
        return false;
    };
    const patch = async (url, body) => {
        const res = await callApi({ url, method: "PATCH", body, rawError: true });
        if (res?.status === 200) fetchAll(); else toast.error("Could not update");
    };
    const remove = async (url) => {
        const res = await callApi({ url, method: "DELETE", rawError: true });
        if (res?.status === 200) { toast.success("Deleted"); fetchAll(); } else toast.error("Could not delete");
    };

    const addProduct = () => {
        if (!newProduct.name.trim() || !newProduct.slug.trim()) { toast.error("Name and slug are required"); return; }
        create("print/press/admin/products/", { ...newProduct, is_active: true }, "Product created");
    };
    const saveConfig = async () => {
        const res = await callApi({ url: "print/press/admin/shop-config/", method: "PUT", body: configDraft, rawError: true });
        if (res?.status === 200) toast.success("Shop config saved"); else toast.error("Could not save config");
    };

    return (
        <Box>
            <Typography variant="h5" fontWeight={800} sx={{ mb: 2 }}>Press Catalog & Pricing</Typography>
            <Tabs value={tab} onChange={(_, v) => setTab(v)} variant="scrollable" sx={{ mb: 2 }}>
                <Tab label="Products & Sizes" />
                <Tab label="Paper Stocks" />
                <Tab label="Finishing" />
                <Tab label="Shipping Rates" />
                <Tab label="Shop Config" />
            </Tabs>

            {tab === 0 && (
                <Box>
                    <TableContainer component={Paper} sx={{ mb: 2 }}>
                        <Table size="small">
                            <TableHead>
                                <TableRow><TableCell>Product</TableCell><TableCell>Category</TableCell><TableCell>Setup</TableCell><TableCell>Rate/in²</TableCell><TableCell>Min qty</TableCell><TableCell>Active</TableCell><TableCell /></TableRow>
                            </TableHead>
                            <TableBody>
                                {products.map((p) => (
                                    <TableRow key={p.id}>
                                        <TableCell>{p.name}<Typography variant="caption" color="text.secondary" display="block">/{p.slug}</Typography></TableCell>
                                        <TableCell>{p.category}</TableCell>
                                        <TableCell>
                                            <TextField size="small" value={p.base_setup_cost} sx={{ width: 90 }}
                                                onChange={(e) => patch(`print/press/admin/products/${p.id}/`, { base_setup_cost: e.target.value })} />
                                        </TableCell>
                                        <TableCell>
                                            <TextField size="small" value={p.per_sq_inch_rate} sx={{ width: 90 }}
                                                onChange={(e) => patch(`print/press/admin/products/${p.id}/`, { per_sq_inch_rate: e.target.value })} />
                                        </TableCell>
                                        <TableCell>
                                            <TextField size="small" value={p.min_qty} sx={{ width: 70 }}
                                                onChange={(e) => patch(`print/press/admin/products/${p.id}/`, { min_qty: e.target.value })} />
                                        </TableCell>
                                        <TableCell>
                                            <Switch checked={p.is_active} onChange={(e) => patch(`print/press/admin/products/${p.id}/`, { is_active: e.target.checked })} />
                                        </TableCell>
                                        <TableCell>
                                            <IconButton size="small" onClick={() => remove(`print/press/admin/products/${p.id}/`)}><DeleteIcon fontSize="small" /></IconButton>
                                        </TableCell>
                                    </TableRow>
                                ))}
                            </TableBody>
                        </Table>
                    </TableContainer>
                    <Stack direction="row" spacing={1} sx={{ mb: 3, flexWrap: "wrap" }}>
                        <TextField size="small" label="Name" value={newProduct.name} onChange={(e) => setNewProduct({ ...newProduct, name: e.target.value })} />
                        <TextField size="small" label="slug" value={newProduct.slug} onChange={(e) => setNewProduct({ ...newProduct, slug: e.target.value })} />
                        <TextField size="small" select label="Category" value={newProduct.category} onChange={(e) => setNewProduct({ ...newProduct, category: e.target.value })} sx={{ minWidth: 130 }}>
                            {PRODUCT_CATEGORIES.map((c) => <MenuItem key={c} value={c}>{c}</MenuItem>)}
                        </TextField>
                        <TextField size="small" label="Setup ৳" value={newProduct.base_setup_cost} onChange={(e) => setNewProduct({ ...newProduct, base_setup_cost: e.target.value })} sx={{ width: 100 }} />
                        <TextField size="small" label="Rate/in²" value={newProduct.per_sq_inch_rate} onChange={(e) => setNewProduct({ ...newProduct, per_sq_inch_rate: e.target.value })} sx={{ width: 100 }} />
                        <Button variant="contained" onClick={addProduct}>Add product</Button>
                    </Stack>

                    <Divider sx={{ my: 2 }} />
                    <Typography variant="subtitle1" fontWeight={700} sx={{ mb: 1 }}>Size presets (A4, A5, 3.5"x2" …)</Typography>
                    <TableContainer component={Paper} sx={{ mb: 2 }}>
                        <Table size="small">
                            <TableHead>
                                <TableRow><TableCell>Product</TableCell><TableCell>Name</TableCell><TableCell>W × H</TableCell><TableCell>Unit</TableCell><TableCell /></TableRow>
                            </TableHead>
                            <TableBody>
                                {sizes.map((s) => (
                                    <TableRow key={s.id}>
                                        <TableCell>{products.find((p) => p.id === s.product)?.name || s.product}</TableCell>
                                        <TableCell>{s.name}</TableCell>
                                        <TableCell>{s.width} × {s.height}</TableCell>
                                        <TableCell>{s.unit}</TableCell>
                                        <TableCell>
                                            <IconButton size="small" onClick={() => remove(`print/press/admin/sizes/${s.id}/`)}><DeleteIcon fontSize="small" /></IconButton>
                                        </TableCell>
                                    </TableRow>
                                ))}
                            </TableBody>
                        </Table>
                    </TableContainer>
                    <Stack direction="row" spacing={1} sx={{ flexWrap: "wrap" }}>
                        <TextField size="small" select label="Product" value={newSize.product} onChange={(e) => setNewSize({ ...newSize, product: e.target.value })} sx={{ minWidth: 160 }}>
                            {products.map((p) => <MenuItem key={p.id} value={p.id}>{p.name}</MenuItem>)}
                        </TextField>
                        <TextField size="small" label='Name (e.g. A4)' value={newSize.name} onChange={(e) => setNewSize({ ...newSize, name: e.target.value })} />
                        <TextField size="small" label="W" value={newSize.width} onChange={(e) => setNewSize({ ...newSize, width: e.target.value })} sx={{ width: 80 }} />
                        <TextField size="small" label="H" value={newSize.height} onChange={(e) => setNewSize({ ...newSize, height: e.target.value })} sx={{ width: 80 }} />
                        <TextField size="small" select label="Unit" value={newSize.unit} onChange={(e) => setNewSize({ ...newSize, unit: e.target.value })} sx={{ width: 100 }}>
                            <MenuItem value="in">in</MenuItem><MenuItem value="ft">ft</MenuItem><MenuItem value="mm">mm</MenuItem>
                        </TextField>
                        <Button variant="contained" onClick={() => {
                            if (!newSize.product || !newSize.name || !newSize.width || !newSize.height) { toast.error("Product, name, W and H are required"); return; }
                            create("print/press/admin/sizes/", { ...newSize, is_active: true }, "Size added");
                        }}>Add size</Button>
                    </Stack>
                </Box>
            )}

            {tab === 1 && (
                <Box>
                    <TableContainer component={Paper} sx={{ mb: 2 }}>
                        <Table size="small">
                            <TableHead>
                                <TableRow><TableCell>Stock</TableCell><TableCell>GSM</TableCell><TableCell>Multiplier</TableCell><TableCell>Flat +/unit</TableCell><TableCell>Active</TableCell><TableCell /></TableRow>
                            </TableHead>
                            <TableBody>
                                {papers.map((p) => (
                                    <TableRow key={p.id}>
                                        <TableCell>{p.name}</TableCell>
                                        <TableCell>{p.gsm}</TableCell>
                                        <TableCell>
                                            <TextField size="small" value={p.multiplier} sx={{ width: 90 }}
                                                onChange={(e) => patch(`print/press/admin/paper/${p.id}/`, { multiplier: e.target.value })} />
                                        </TableCell>
                                        <TableCell>
                                            <TextField size="small" value={p.flat_addon_per_unit} sx={{ width: 90 }}
                                                onChange={(e) => patch(`print/press/admin/paper/${p.id}/`, { flat_addon_per_unit: e.target.value })} />
                                        </TableCell>
                                        <TableCell>
                                            <Switch checked={p.is_active} onChange={(e) => patch(`print/press/admin/paper/${p.id}/`, { is_active: e.target.checked })} />
                                        </TableCell>
                                        <TableCell>
                                            <IconButton size="small" onClick={() => remove(`print/press/admin/paper/${p.id}/`)}><DeleteIcon fontSize="small" /></IconButton>
                                        </TableCell>
                                    </TableRow>
                                ))}
                            </TableBody>
                        </Table>
                    </TableContainer>
                    <Stack direction="row" spacing={1}>
                        <TextField size="small" label="Name (e.g. 300gsm Art Card)" value={newPaper.name} onChange={(e) => setNewPaper({ ...newPaper, name: e.target.value })} />
                        <TextField size="small" label="GSM" value={newPaper.gsm} onChange={(e) => setNewPaper({ ...newPaper, gsm: e.target.value })} sx={{ width: 110 }} />
                        <TextField size="small" label="Multiplier" value={newPaper.multiplier} onChange={(e) => setNewPaper({ ...newPaper, multiplier: e.target.value })} sx={{ width: 110 }} />
                        <Button variant="contained" onClick={() => {
                            if (!newPaper.name.trim()) { toast.error("Name is required"); return; }
                            create("print/press/admin/paper/", { ...newPaper, is_active: true }, "Paper stock added");
                        }}>Add stock</Button>
                    </Stack>
                </Box>
            )}

            {tab === 2 && (
                <Box>
                    <TableContainer component={Paper} sx={{ mb: 2 }}>
                        <Table size="small">
                            <TableHead>
                                <TableRow><TableCell>Kind</TableCell><TableCell>Name</TableCell><TableCell>Price ৳</TableCell><TableCell>Per unit?</TableCell><TableCell>Active</TableCell><TableCell /></TableRow>
                            </TableHead>
                            <TableBody>
                                {finishings.map((f) => (
                                    <TableRow key={f.id}>
                                        <TableCell>{f.kind}</TableCell>
                                        <TableCell>{f.name}</TableCell>
                                        <TableCell>
                                            <TextField size="small" value={f.price} sx={{ width: 90 }}
                                                onChange={(e) => patch(`print/press/admin/finishing/${f.id}/`, { price: e.target.value })} />
                                        </TableCell>
                                        <TableCell>
                                            <Switch checked={f.per_unit} onChange={(e) => patch(`print/press/admin/finishing/${f.id}/`, { per_unit: e.target.checked })} />
                                        </TableCell>
                                        <TableCell>
                                            <Switch checked={f.is_active} onChange={(e) => patch(`print/press/admin/finishing/${f.id}/`, { is_active: e.target.checked })} />
                                        </TableCell>
                                        <TableCell>
                                            <IconButton size="small" onClick={() => remove(`print/press/admin/finishing/${f.id}/`)}><DeleteIcon fontSize="small" /></IconButton>
                                        </TableCell>
                                    </TableRow>
                                ))}
                            </TableBody>
                        </Table>
                    </TableContainer>
                    <Stack direction="row" spacing={1}>
                        <TextField size="small" select label="Kind" value={newFinishing.kind} onChange={(e) => setNewFinishing({ ...newFinishing, kind: e.target.value })} sx={{ minWidth: 140 }}>
                            {FINISHING_KINDS.map((k) => <MenuItem key={k} value={k}>{k}</MenuItem>)}
                        </TextField>
                        <TextField size="small" label="Name" value={newFinishing.name} onChange={(e) => setNewFinishing({ ...newFinishing, name: e.target.value })} />
                        <TextField size="small" label="Price ৳" value={newFinishing.price} onChange={(e) => setNewFinishing({ ...newFinishing, price: e.target.value })} sx={{ width: 100 }} />
                        <Button variant="contained" onClick={() => {
                            if (!newFinishing.name.trim() || !newFinishing.price) { toast.error("Name and price are required"); return; }
                            create("print/press/admin/finishing/", { ...newFinishing, is_active: true }, "Finishing option added");
                        }}>Add option</Button>
                    </Stack>
                </Box>
            )}

            {tab === 3 && (
                <Box>
                    <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                        Inside Dhaka: Pathao / Steadfast home delivery or free hub pickup. Outside Dhaka: Sundarban, SA Paribahan, Paperfly. Fee = base + per-kg × weight.
                    </Typography>
                    <TableContainer component={Paper} sx={{ mb: 2 }}>
                        <Table size="small">
                            <TableHead>
                                <TableRow><TableCell>Zone</TableCell><TableCell>Courier</TableCell><TableCell>Base ৳</TableCell><TableCell>Per-kg ৳</TableCell><TableCell>Active</TableCell><TableCell /></TableRow>
                            </TableHead>
                            <TableBody>
                                {rates.map((r) => (
                                    <TableRow key={r.id}>
                                        <TableCell>{r.zone}</TableCell>
                                        <TableCell>{r.courier}</TableCell>
                                        <TableCell>
                                            <TextField size="small" value={r.base_fee} sx={{ width: 90 }}
                                                onChange={(e) => patch(`print/press/admin/shipping/${r.id}/`, { base_fee: e.target.value })} />
                                        </TableCell>
                                        <TableCell>
                                            <TextField size="small" value={r.per_kg_fee} sx={{ width: 90 }}
                                                onChange={(e) => patch(`print/press/admin/shipping/${r.id}/`, { per_kg_fee: e.target.value })} />
                                        </TableCell>
                                        <TableCell>
                                            <Switch checked={r.is_active} onChange={(e) => patch(`print/press/admin/shipping/${r.id}/`, { is_active: e.target.checked })} />
                                        </TableCell>
                                        <TableCell>
                                            <IconButton size="small" onClick={() => remove(`print/press/admin/shipping/${r.id}/`)}><DeleteIcon fontSize="small" /></IconButton>
                                        </TableCell>
                                    </TableRow>
                                ))}
                            </TableBody>
                        </Table>
                    </TableContainer>
                    <Stack direction="row" spacing={1}>
                        <TextField size="small" select label="Zone" value={newRate.zone} onChange={(e) => setNewRate({ ...newRate, zone: e.target.value })} sx={{ minWidth: 190 }}>
                            {SHIPPING_ZONES.map((z) => <MenuItem key={z} value={z}>{z}</MenuItem>)}
                        </TextField>
                        <TextField size="small" label="Courier" value={newRate.courier} onChange={(e) => setNewRate({ ...newRate, courier: e.target.value })} />
                        <TextField size="small" label="Base ৳" value={newRate.base_fee} onChange={(e) => setNewRate({ ...newRate, base_fee: e.target.value })} sx={{ width: 100 }} />
                        <TextField size="small" label="Per-kg ৳" value={newRate.per_kg_fee} onChange={(e) => setNewRate({ ...newRate, per_kg_fee: e.target.value })} sx={{ width: 100 }} />
                        <Button variant="contained" onClick={() => {
                            if (!newRate.courier.trim() || !newRate.base_fee) { toast.error("Courier and base fee are required"); return; }
                            create("print/press/admin/shipping/", { ...newRate, is_active: true }, "Shipping rate added");
                        }}>Add rate</Button>
                    </Stack>
                </Box>
            )}

            {tab === 4 && shopConfig && (
                <Box sx={{ maxWidth: 560 }}>
                    <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                        BDT (৳) is the booking currency; USD is a display conversion at the rate below. The margin factor feeds Total = (Setup + Material × Qty + Finishing) × Margin.
                    </Typography>
                    <Stack spacing={2}>
                        <TextField label="USD rate (BDT per $1)" value={configDraft.usd_rate}
                            onChange={(e) => setConfigDraft({ ...configDraft, usd_rate: e.target.value })} />
                        <TextField label="Default margin factor (e.g. 1.250)" value={configDraft.default_margin_factor}
                            onChange={(e) => setConfigDraft({ ...configDraft, default_margin_factor: e.target.value })} />
                        <TextField label="Max artwork upload (MB)" type="number" value={configDraft.max_upload_mb}
                            onChange={(e) => setConfigDraft({ ...configDraft, max_upload_mb: e.target.value })} />
                        <Button variant="contained" onClick={saveConfig}>Save shop config</Button>
                    </Stack>
                </Box>
            )}
        </Box>
    );
}
