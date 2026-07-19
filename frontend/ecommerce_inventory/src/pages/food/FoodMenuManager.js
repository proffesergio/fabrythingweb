import { useEffect, useState, useCallback } from "react";
import {
    Box, Card, CardContent, Typography, Grid, TextField, Button, Stack, Divider, Chip,
    MenuItem, Select, InputLabel, FormControl, IconButton, Dialog, DialogTitle, DialogContent,
    DialogActions, Table, TableBody, TableCell, TableHead, TableRow, Switch, FormControlLabel,
} from "@mui/material";
import AddIcon from "@mui/icons-material/Add";
import EditIcon from "@mui/icons-material/Edit";
import DeleteIcon from "@mui/icons-material/DeleteOutline";
import TuneIcon from "@mui/icons-material/Tune";
import { toast } from "react-toastify";
import useApi from "../../hooks/APIHandler";

const EMPTY_ITEM = { name: "", price: "", image: "", is_available: true, is_veg: false, spice_level: "" };

export default function FoodMenuManager() {
    const { callApi } = useApi();
    const [restaurants, setRestaurants] = useState([]);
    const [restaurant, setRestaurant] = useState("");
    const [categories, setCategories] = useState([]);
    const [items, setItems] = useState([]);
    const [newCat, setNewCat] = useState("");
    const [itemDialog, setItemDialog] = useState(null); // {...item, category_id}
    const [optionItem, setOptionItem] = useState(null); // item whose options we manage
    const [groups, setGroups] = useState([]);

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
        const [c, i] = await Promise.all([
            callApi({ url: "food/admin/categories/", method: "GET", params: { restaurant: rid } }),
            callApi({ url: "food/admin/items/", method: "GET", params: { restaurant: rid } }),
        ]);
        setCategories(c?.data?.data || []);
        setItems(i?.data?.data || []);
    }, []); // eslint-disable-line react-hooks/exhaustive-deps

    useEffect(() => { loadMenu(restaurant); }, [restaurant, loadMenu]);

    const addCategory = async () => {
        if (!newCat.trim()) return;
        const res = await callApi({ url: "food/admin/categories/", method: "POST", body: { restaurant: Number(restaurant), name: newCat } });
        if (res?.status === 201) { toast.success("Category added"); setNewCat(""); loadMenu(restaurant); }
    };

    const deleteCategory = async (id) => {
        await callApi({ url: `food/admin/categories/${id}/`, method: "DELETE" });
        loadMenu(restaurant);
    };

    const saveItem = async () => {
        const body = { ...itemDialog, restaurant: Number(restaurant) };
        const isEdit = !!itemDialog.id;
        const res = await callApi({
            url: isEdit ? `food/admin/items/${itemDialog.id}/` : "food/admin/items/",
            method: isEdit ? "PATCH" : "POST", body,
        });
        if (res?.status === 200 || res?.status === 201) {
            toast.success(isEdit ? "Item saved" : "Item added"); setItemDialog(null); loadMenu(restaurant);
        }
    };

    const deleteItem = async (id) => {
        await callApi({ url: `food/admin/items/${id}/`, method: "DELETE" });
        loadMenu(restaurant);
    };

    const openOptions = async (item) => {
        setOptionItem(item);
        const res = await callApi({ url: "food/admin/option-groups/", method: "GET", params: { item: item.id } });
        const gs = res?.data?.data || [];
        const withOpts = await Promise.all(gs.map(async (g) => {
            const o = await callApi({ url: "food/admin/options/", method: "GET", params: { group: g.id } });
            return { ...g, options: o?.data?.data || [] };
        }));
        setGroups(withOpts);
    };

    const addGroup = async () => {
        const res = await callApi({ url: "food/admin/option-groups/", method: "POST", body: { item: optionItem.id, name: "New group", max_select: 1 } });
        if (res?.status === 201) openOptions(optionItem);
    };
    const addOption = async (groupId) => {
        const res = await callApi({ url: "food/admin/options/", method: "POST", body: { group: groupId, name: "New option", price_delta: "0.00" } });
        if (res?.status === 201) openOptions(optionItem);
    };

    const itemsByCategory = (catId) => items.filter((i) => (i.category_id === catId || i.category_id?.id === catId));

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
            </Stack>

            <Card sx={{ mb: 2 }}><CardContent>
                <Stack direction="row" spacing={1} alignItems="center">
                    <TextField size="small" label="New category" value={newCat} onChange={(e) => setNewCat(e.target.value)} />
                    <Button variant="contained" startIcon={<AddIcon />} onClick={addCategory}>Add category</Button>
                </Stack>
            </CardContent></Card>

            {categories.length === 0 && <Typography color="text.secondary">No categories yet — add one to start building the menu.</Typography>}

            {categories.map((cat) => (
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
                        <TableHead><TableRow><TableCell>Item</TableCell><TableCell>Price</TableCell><TableCell>Available</TableCell><TableCell align="right">Actions</TableCell></TableRow></TableHead>
                        <TableBody>
                            {itemsByCategory(cat.id).map((it) => (
                                <TableRow key={it.id}>
                                    <TableCell>{it.name}</TableCell>
                                    <TableCell>৳{it.price}</TableCell>
                                    <TableCell><Chip size="small" label={it.is_available ? "Yes" : "No"} color={it.is_available ? "success" : "default"} /></TableCell>
                                    <TableCell align="right">
                                        <IconButton size="small" onClick={() => openOptions(it)}><TuneIcon /></IconButton>
                                        <IconButton size="small" onClick={() => setItemDialog({ ...it, category_id: cat.id })}><EditIcon /></IconButton>
                                        <IconButton size="small" color="error" onClick={() => deleteItem(it.id)}><DeleteIcon /></IconButton>
                                    </TableCell>
                                </TableRow>
                            ))}
                        </TableBody>
                    </Table>
                </CardContent></Card>
            ))}

            {/* Item dialog */}
            <Dialog open={!!itemDialog} onClose={() => setItemDialog(null)} maxWidth="sm" fullWidth>
                <DialogTitle>{itemDialog?.id ? "Edit item" : "Add item"}</DialogTitle>
                <DialogContent>
                    {itemDialog && (
                        <Grid container spacing={2} sx={{ mt: 0 }}>
                            <Grid item xs={12} sm={8}><TextField label="Name" fullWidth value={itemDialog.name} onChange={(e) => setItemDialog({ ...itemDialog, name: e.target.value })} /></Grid>
                            <Grid item xs={12} sm={4}><TextField label="Price" type="number" fullWidth value={itemDialog.price} onChange={(e) => setItemDialog({ ...itemDialog, price: e.target.value })} /></Grid>
                            <Grid item xs={12}><TextField label="Image URL" fullWidth value={itemDialog.image} onChange={(e) => setItemDialog({ ...itemDialog, image: e.target.value })} /></Grid>
                            <Grid item xs={12} sm={4}><TextField label="Spice level" fullWidth value={itemDialog.spice_level} onChange={(e) => setItemDialog({ ...itemDialog, spice_level: e.target.value })} /></Grid>
                            <Grid item xs={12} sm={4}><FormControlLabel control={<Switch checked={itemDialog.is_available} onChange={(e) => setItemDialog({ ...itemDialog, is_available: e.target.checked })} />} label="Available" /></Grid>
                            <Grid item xs={12} sm={4}><FormControlLabel control={<Switch checked={itemDialog.is_veg} onChange={(e) => setItemDialog({ ...itemDialog, is_veg: e.target.checked })} />} label="Veg" /></Grid>
                        </Grid>
                    )}
                </DialogContent>
                <DialogActions><Button onClick={() => setItemDialog(null)}>Cancel</Button><Button variant="contained" onClick={saveItem}>Save</Button></DialogActions>
            </Dialog>

            {/* Options dialog */}
            <Dialog open={!!optionItem} onClose={() => setOptionItem(null)} maxWidth="sm" fullWidth>
                <DialogTitle>Options — {optionItem?.name}</DialogTitle>
                <DialogContent>
                    {groups.map((g) => (
                        <Box key={g.id} sx={{ mb: 2 }}>
                            <Typography variant="subtitle2">{g.name} (max {g.max_select})</Typography>
                            {g.options.map((o) => <Chip key={o.id} size="small" sx={{ mr: 1, mt: 1 }} label={`${o.name} +৳${o.price_delta}`} />)}
                            <Box><Button size="small" startIcon={<AddIcon />} onClick={() => addOption(g.id)}>Add option</Button></Box>
                        </Box>
                    ))}
                    <Button startIcon={<AddIcon />} onClick={addGroup}>Add option group</Button>
                </DialogContent>
                <DialogActions><Button onClick={() => setOptionItem(null)}>Close</Button></DialogActions>
            </Dialog>
        </Box>
    );
}
