import { useEffect, useState, useCallback } from "react";
import {
    Box, Card, CardContent, Typography, Grid, TextField, Button, Stack, Divider, Chip,
    MenuItem, Select, InputLabel, FormControl, IconButton, Dialog, DialogTitle, DialogContent,
    DialogActions, Table, TableBody, TableCell, TableHead, TableRow, Switch, FormControlLabel,
    Alert, Checkbox,
} from "@mui/material";
import AddIcon from "@mui/icons-material/Add";
import EditIcon from "@mui/icons-material/Edit";
import DeleteIcon from "@mui/icons-material/DeleteOutline";
import TuneIcon from "@mui/icons-material/Tune";
import StarRoundedIcon from "@mui/icons-material/StarRounded";
import StarBorderRoundedIcon from "@mui/icons-material/StarBorderRounded";
import { toast } from "react-toastify";
import useApi from "../../hooks/APIHandler";
import CopyMenuDialog from "./CopyMenuDialog";
import FoodLoader from "./FoodLoader";
import ItemOptionsDialog from "./ItemOptionsDialog";

const EMPTY_ITEM = {
    name: "", name_bn: "", description: "", description_bn: "", price: "", discount_price: "",
    prep_minutes: "", image: "", is_available: true, is_veg: false, is_featured: false, spice_level: "",
    tags: [], available_from: "", available_to: "", available_days: [],
};
const SPICE_LEVELS = ["", "Mild", "Medium", "Hot", "Extra Hot"];
const TAG_OPTIONS = [["spicy", "🌶️ Spicy"], ["new", "✨ New"], ["popular", "🔥 Popular"], ["bestseller", "⭐ Bestseller"], ["veg", "🌱 Veg"]];
const DAYS = [["0", "Mon"], ["1", "Tue"], ["2", "Wed"], ["3", "Thu"], ["4", "Fri"], ["5", "Sat"], ["6", "Sun"]];

export default function FoodMenuManager() {
    const { callApi } = useApi();
    const [restaurants, setRestaurants] = useState([]);
    const [restaurant, setRestaurant] = useState("");
    const [categories, setCategories] = useState([]);
    const [items, setItems] = useState([]);
    const [newCat, setNewCat] = useState("");
    const [newCatBn, setNewCatBn] = useState("");
    const [itemDialog, setItemDialog] = useState(null); // {...item, category_id}
    const [itemErrors, setItemErrors] = useState({});   // {field: [messages]} from a rejected save
    const [uploading, setUploading] = useState(false);
    const [copyOpen, setCopyOpen] = useState(false);
    const [selectedItemIds, setSelectedItemIds] = useState([]);
    const [optionItem, setOptionItem] = useState(null); // item whose modifiers we manage
    const [menuLoading, setMenuLoading] = useState(false);

    useEffect(() => {
        (async () => {
            const res = await callApi({ url: "food/admin/restaurants/", method: "GET" });
            const list = res?.data?.data || [];
            setRestaurants(list);
            if (list.length) setRestaurant(String(list[0].id));
        })();
    }, []); // eslint-disable-line react-hooks/exhaustive-deps

    const loadMenu = useCallback(async (rid) => {
        if (!rid) return;
        setMenuLoading(true);
        try {
            const [c, i] = await Promise.all([
                callApi({ url: "food/admin/categories/", method: "GET", params: { restaurant: rid } }),
                callApi({ url: "food/admin/items/", method: "GET", params: { restaurant: rid } }),
            ]);
            setCategories(c?.data?.data || []);
            setItems(i?.data?.data || []);
        } finally {
            setMenuLoading(false);
        }
    }, []); // eslint-disable-line react-hooks/exhaustive-deps

    useEffect(() => { loadMenu(restaurant); }, [restaurant, loadMenu]);

    const addCategory = async () => {
        if (!newCat.trim()) return;
        const res = await callApi({ url: "food/admin/categories/", method: "POST",
            body: { restaurant: Number(restaurant), name: newCat, name_bn: newCatBn } });
        if (res?.status === 201) { toast.success("Category added"); setNewCat(""); setNewCatBn(""); loadMenu(restaurant); }
    };

    const deleteCategory = async (id) => {
        await callApi({ url: `food/admin/categories/${id}/`, method: "DELETE" });
        loadMenu(restaurant);
    };

    const saveItem = async () => {
        const body = { ...itemDialog, restaurant: Number(restaurant) };
        // Optional numeric/time fields: send null (not ""), so "unset" is explicit
        // and emptying a previously-set field actually clears it server-side.
        ["discount_price", "prep_minutes", "available_from", "available_to"].forEach((k) => {
            if (body[k] === "" || body[k] == null) body[k] = null;
        });
        body.available_days = (itemDialog.available_days || []).map(Number);
        const isEdit = !!itemDialog.id;
        setItemErrors({});
        const res = await callApi({
            url: isEdit ? `food/admin/items/${itemDialog.id}/` : "food/admin/items/",
            method: isEdit ? "PATCH" : "POST", body, rawError: true, silent: true,
        });
        if (res?.status === 200 || res?.status === 201) {
            toast.success(isEdit ? "Item saved" : "Item added");
            setItemDialog(null); setItemErrors({}); loadMenu(restaurant);
            return;
        }
        // On a 400 the envelope carries field_errors ({field: [messages]}). Show them
        // on the offending inputs — the bare "Validation error" message tells the
        // admin nothing about what to fix.
        const fields = (res?.status === 400 && res?.data?.field_errors) || null;
        if (fields && typeof fields === "object" && !Array.isArray(fields)) {
            setItemErrors(fields);
            const summary = Object.entries(fields)
                .map(([f, msgs]) => `${f}: ${[].concat(msgs).join(" ")}`).join(" · ");
            toast.error(summary || res?.data?.message || "Could not save item");
        } else {
            const flat = res?.data?.errors;
            toast.error((flat && [].concat(flat).join(" ")) || res?.data?.message || "Could not save item");
        }
    };

    // Uploads through the shared /api/uploads/ endpoint (S3 when AWS keys are
    // configured, local media otherwise) and stores the URL it returns — the model
    // field is a URLField, so the file itself never touches FoodItem.
    const uploadImage = async (file) => {
        if (!file) return;
        setUploading(true);
        const form = new FormData();
        form.append("image", file);
        const res = await callApi({
            url: "uploads/", method: "POST", body: form,
            header: { "Content-Type": "multipart/form-data" }, rawError: true, silent: true,
        });
        setUploading(false);
        // This endpoint predates the {data,message} envelope — it answers {message, urls}.
        const url = res?.data?.urls?.[0];
        if (url) setItemDialog((d) => ({ ...d, image: url }));
        else toast.error("Upload failed — paste an image URL instead");
    };

    const deleteItem = async (id) => {
        await callApi({ url: `food/admin/items/${id}/`, method: "DELETE" });
        loadMenu(restaurant);
    };

    // Quick inline toggle (availability / featured) without opening the dialog.
    const toggleField = async (item, field) => {
        const res = await callApi({ url: `food/admin/items/${item.id}/`, method: "PATCH", body: { [field]: !item[field] } });
        if (res?.status === 200) loadMenu(restaurant);
    };


    const itemsByCategory = (catId) => items.filter((i) => (i.category_id === catId || i.category_id?.id === catId));

    // MUI props for a field the backend rejected.
    const errProps = (field, fallbackHelper = "") => {
        const msgs = itemErrors[field];
        return msgs
            ? { error: true, helperText: [].concat(msgs).join(" ") }
            : (fallbackHelper ? { helperText: fallbackHelper } : {});
    };

    const closeItemDialog = () => { setItemDialog(null); setItemErrors({}); };

    return (
        <Box>
            <Stack direction={{ xs: "column", sm: "row" }} justifyContent="space-between" alignItems={{ sm: "center" }} sx={{ mb: 2 }} spacing={2}>
                <Typography variant="h5" fontWeight={800}>Menu Management</Typography>
                <FormControl size="small" sx={{ minWidth: 240 }}>
                    <InputLabel id="rest-label">Restaurant</InputLabel>
                    <Select labelId="rest-label" label="Restaurant" value={restaurant} onChange={(e) => setRestaurant(e.target.value)}>
                        {restaurants.map((r) => <MenuItem key={r.id} value={String(r.id)}>{r.name}</MenuItem>)}
                    </Select>
                </FormControl>
                <Button variant="outlined" disabled={!restaurant} onClick={() => setCopyOpen(true)}>
                    {selectedItemIds.length > 0 ? `Copy ${selectedItemIds.length} items to…` : "Copy menu from…"}
                </Button>
            </Stack>

            <Card sx={{ mb: 2 }}><CardContent>
                <Stack direction={{ xs: "column", sm: "row" }} spacing={1} alignItems={{ sm: "center" }}>
                    <TextField size="small" label="New category (English)" value={newCat} onChange={(e) => setNewCat(e.target.value)} />
                    <TextField size="small" label="বিভাগ (বাংলা)" value={newCatBn} onChange={(e) => setNewCatBn(e.target.value)}
                        inputProps={{ lang: "bn" }} />
                    <Button variant="contained" startIcon={<AddIcon />} onClick={addCategory}>Add category</Button>
                </Stack>
            </CardContent></Card>

            {menuLoading && <FoodLoader label="Loading menu…" emoji="🍛" />}
            {!menuLoading && categories.length === 0 && <Typography color="text.secondary">No categories yet — add one to start building the menu.</Typography>}

            {!menuLoading && categories.map((cat) => (
                <Card key={cat.id} sx={{ mb: 2 }}><CardContent>
                    <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 1 }}>
                        <Typography variant="subtitle1" fontWeight={700}>{cat.name}</Typography>
                        <Stack direction="row" spacing={1}>
                            <Button size="small" startIcon={<AddIcon />} onClick={() => setItemDialog({ ...EMPTY_ITEM, category_id: cat.id })}>Add item</Button>
                            <IconButton size="small" color="error" onClick={() => deleteCategory(cat.id)}><DeleteIcon /></IconButton>
                        </Stack>
                    </Stack>
                    <Divider sx={{ mb: 1 }} />
                    <Table size="small">
                        <TableHead><TableRow>
                            <TableCell padding="checkbox" /><TableCell sx={{ width: 56 }} />
                            <TableCell>Item</TableCell><TableCell>Price</TableCell>
                            <TableCell align="center">Featured</TableCell><TableCell align="center">Available</TableCell>
                            <TableCell align="right">Actions</TableCell>
                        </TableRow></TableHead>
                        <TableBody>
                            {itemsByCategory(cat.id).map((it) => (
                                <TableRow key={it.id} sx={{ opacity: it.is_available ? 1 : 0.55 }}>
                                    <TableCell padding="checkbox">
                                        <Checkbox
                                            checked={selectedItemIds.includes(it.id)}
                                            onChange={(e) => setSelectedItemIds((ids) =>
                                                e.target.checked ? [...ids, it.id] : ids.filter((x) => x !== it.id))}
                                        />
                                    </TableCell>
                                    <TableCell sx={{ width: 56 }}>
                                        {it.image
                                            ? <Box component="img" src={it.image} alt={it.name}
                                                sx={{ width: 44, height: 44, borderRadius: 1, objectFit: "cover" }} />
                                            : <Box sx={{
                                                width: 44, height: 44, borderRadius: 1, bgcolor: "grey.200",
                                                display: "grid", placeItems: "center", fontSize: 18,
                                            }}>🍽️</Box>}
                                    </TableCell>
                                    <TableCell>
                                        <Typography variant="body2" fontWeight={600}>{it.name}</Typography>
                                        {it.name_bn && <Typography variant="caption" color="text.secondary">{it.name_bn}</Typography>}
                                    </TableCell>
                                    <TableCell>
                                        {it.discount_price
                                            ? <><Typography variant="body2" component="span" fontWeight={700}>৳{it.discount_price}</Typography>
                                                <Typography variant="caption" component="span" sx={{ ml: 0.5, textDecoration: "line-through" }} color="text.secondary">৳{it.price}</Typography></>
                                            : <>৳{it.price}</>}
                                    </TableCell>
                                    <TableCell align="center">
                                        <IconButton size="small" onClick={() => toggleField(it, "is_featured")}
                                            color={it.is_featured ? "warning" : "default"}>
                                            {it.is_featured ? <StarRoundedIcon /> : <StarBorderRoundedIcon />}
                                        </IconButton>
                                    </TableCell>
                                    <TableCell align="center">
                                        <Switch size="small" checked={!!it.is_available} onChange={() => toggleField(it, "is_available")} />
                                    </TableCell>
                                    <TableCell align="right">
                                        <IconButton size="small" title="Modifiers" onClick={() => setOptionItem(it)}><TuneIcon /></IconButton>
                                        <IconButton size="small" title="Edit" onClick={() => setItemDialog({ ...it, category_id: cat.id })}><EditIcon /></IconButton>
                                        <IconButton size="small" color="error" title="Delete" onClick={() => deleteItem(it.id)}><DeleteIcon /></IconButton>
                                    </TableCell>
                                </TableRow>
                            ))}
                        </TableBody>
                    </Table>
                </CardContent></Card>
            ))}

            {/* Item dialog */}
            <Dialog open={!!itemDialog} onClose={closeItemDialog} maxWidth="sm" fullWidth>
                <DialogTitle>{itemDialog?.id ? "Edit item" : "Add item"}</DialogTitle>
                <DialogContent>
                    {itemDialog && (
                        <Grid container spacing={2} sx={{ mt: 0 }}>
                            {(itemErrors.non_field_errors || itemErrors.detail) && (
                                <Grid item xs={12}>
                                    <Alert severity="error">{[].concat(itemErrors.non_field_errors || itemErrors.detail).join(" ")}</Alert>
                                </Grid>
                            )}
                            <Grid item xs={12} sm={6}><TextField label="Name (English)" fullWidth value={itemDialog.name} onChange={(e) => setItemDialog({ ...itemDialog, name: e.target.value })} {...errProps("name")} /></Grid>
                            <Grid item xs={12} sm={6}><TextField label="নাম (বাংলা)" fullWidth value={itemDialog.name_bn || ""} onChange={(e) => setItemDialog({ ...itemDialog, name_bn: e.target.value })} inputProps={{ lang: "bn" }} {...errProps("name_bn")} /></Grid>
                            <Grid item xs={12} sm={4}><TextField label="Price ৳" type="number" fullWidth value={itemDialog.price} onChange={(e) => setItemDialog({ ...itemDialog, price: e.target.value })} {...errProps("price")} /></Grid>
                            <Grid item xs={12} sm={4}><TextField label="Discount price ৳" type="number" fullWidth value={itemDialog.discount_price || ""} onChange={(e) => setItemDialog({ ...itemDialog, discount_price: e.target.value })} {...errProps("discount_price", "Optional")} /></Grid>
                            <Grid item xs={12} sm={4}><TextField label="Prep minutes" type="number" fullWidth value={itemDialog.prep_minutes || ""} onChange={(e) => setItemDialog({ ...itemDialog, prep_minutes: e.target.value })} {...errProps("prep_minutes")} /></Grid>
                            <Grid item xs={12}><TextField label="Description (English)" fullWidth multiline rows={2} value={itemDialog.description || ""} onChange={(e) => setItemDialog({ ...itemDialog, description: e.target.value })} /></Grid>
                            <Grid item xs={12}><TextField label="বিবরণ (বাংলা)" fullWidth multiline rows={2} value={itemDialog.description_bn || ""} onChange={(e) => setItemDialog({ ...itemDialog, description_bn: e.target.value })} inputProps={{ lang: "bn" }} /></Grid>
                            <Grid item xs={12}>
                                <Stack direction="row" spacing={1} alignItems="flex-start">
                                    {itemDialog.image && (
                                        <Box component="img" src={itemDialog.image} alt="preview"
                                            sx={{ width: 64, height: 64, borderRadius: 1, objectFit: "cover" }} />
                                    )}
                                    <TextField label="Image URL" fullWidth value={itemDialog.image}
                                        onChange={(e) => setItemDialog({ ...itemDialog, image: e.target.value })}
                                        {...errProps("image", "Upload a photo or paste a URL")} />
                                    <Button component="label" variant="outlined" disabled={uploading} sx={{ minWidth: 110 }}>
                                        {uploading ? "Uploading…" : "Upload"}
                                        <input hidden type="file" accept="image/*"
                                            onChange={(e) => uploadImage(e.target.files?.[0])} />
                                    </Button>
                                </Stack>
                            </Grid>
                            <Grid item xs={12} sm={6}>
                                <TextField select fullWidth label="Spice level" value={itemDialog.spice_level || ""}
                                    onChange={(e) => setItemDialog({ ...itemDialog, spice_level: e.target.value })}>
                                    {SPICE_LEVELS.map((s) => <MenuItem key={s || "none"} value={s}>{s || "None"}</MenuItem>)}
                                </TextField>
                            </Grid>
                            <Grid item xs={12} sm={6}>
                                <Stack direction="row" spacing={1} sx={{ flexWrap: "wrap" }}>
                                    <FormControlLabel control={<Switch checked={!!itemDialog.is_available} onChange={(e) => setItemDialog({ ...itemDialog, is_available: e.target.checked })} />} label="Available" />
                                    <FormControlLabel control={<Switch checked={!!itemDialog.is_veg} onChange={(e) => setItemDialog({ ...itemDialog, is_veg: e.target.checked })} />} label="Veg" />
                                    <FormControlLabel control={<Switch color="warning" checked={!!itemDialog.is_featured} onChange={(e) => setItemDialog({ ...itemDialog, is_featured: e.target.checked })} />} label="Bestseller" />
                                </Stack>
                            </Grid>
                            <Grid item xs={12}>
                                <Typography variant="caption" color="text.secondary">Tags</Typography>
                                {itemErrors.tags && <Typography variant="caption" color="error" display="block">{[].concat(itemErrors.tags).join(" ")}</Typography>}
                                <Stack direction="row" sx={{ flexWrap: "wrap", gap: 1, mt: 0.5 }}>
                                    {TAG_OPTIONS.map(([k, label]) => {
                                        const on = (itemDialog.tags || []).includes(k);
                                        return <Chip key={k} label={label} color={on ? "warning" : "default"} variant={on ? "filled" : "outlined"}
                                            onClick={() => setItemDialog((d) => ({ ...d, tags: on ? d.tags.filter((t) => t !== k) : [...(d.tags || []), k] }))} />;
                                    })}
                                </Stack>
                            </Grid>
                            <Grid item xs={12} sm={6}><TextField label="Available from" type="time" fullWidth InputLabelProps={{ shrink: true }} value={itemDialog.available_from || ""} onChange={(e) => setItemDialog({ ...itemDialog, available_from: e.target.value })} {...errProps("available_from", "Optional schedule")} /></Grid>
                            <Grid item xs={12} sm={6}><TextField label="Available to" type="time" fullWidth InputLabelProps={{ shrink: true }} value={itemDialog.available_to || ""} onChange={(e) => setItemDialog({ ...itemDialog, available_to: e.target.value })} {...errProps("available_to")} /></Grid>
                            <Grid item xs={12}>
                                <Typography variant="caption" color="text.secondary">Available days (none = every day)</Typography>
                                {itemErrors.available_days && <Typography variant="caption" color="error" display="block">{[].concat(itemErrors.available_days).join(" ")}</Typography>}
                                <Stack direction="row" sx={{ flexWrap: "wrap", gap: 0.5, mt: 0.5 }}>
                                    {DAYS.map(([k, label]) => {
                                        const on = (itemDialog.available_days || []).map(String).includes(k);
                                        return <Chip key={k} size="small" label={label} color={on ? "primary" : "default"} variant={on ? "filled" : "outlined"}
                                            onClick={() => setItemDialog((d) => { const cur = (d.available_days || []).map(String); return { ...d, available_days: on ? cur.filter((x) => x !== k) : [...cur, k] }; })} />;
                                    })}
                                </Stack>
                            </Grid>
                        </Grid>
                    )}
                </DialogContent>
                <DialogActions><Button onClick={closeItemDialog}>Cancel</Button><Button variant="contained" onClick={saveItem}>Save</Button></DialogActions>
            </Dialog>

            {/* Modifier / add-on editor */}
            <ItemOptionsDialog open={!!optionItem} item={optionItem} onClose={() => setOptionItem(null)} />

            <CopyMenuDialog
                open={copyOpen}
                restaurants={restaurants}
                targetRestaurant={restaurant}
                selectedItemIds={selectedItemIds}
                onClose={() => setCopyOpen(false)}
                onCopied={() => { setCopyOpen(false); setSelectedItemIds([]); loadMenu(restaurant); }}
            />
        </Box>
    );
}
