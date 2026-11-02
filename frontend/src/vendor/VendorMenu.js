import React, { useEffect, useMemo, useState } from "react";
import {
    Box, Button, Card, CardContent, Chip, Dialog, DialogActions, DialogContent, DialogTitle,
    FormControlLabel, Grid, IconButton, LinearProgress, List, ListItemButton, ListItemText,
    MenuItem, Paper, Stack, Switch, Table, TableBody, TableCell, TableContainer, TableHead,
    TableRow, TextField, Typography,
} from "@mui/material";
import { Add, Delete, Edit } from "@mui/icons-material";
import { Controller, useForm } from "react-hook-form";
import { toast } from "react-toastify";
import useApi from "../hooks/APIHandler";

// Categories and items live under vendor-scoped endpoints (food/vendor/categories/,
// food/vendor/items/) — the backend always resolves them to request.user.restaurant,
// so there is no restaurant id to pass from here. Deliberately no image upload
// (v1.1 stores image as a plain URL string, see FoodItem.image) and no option-group
// editor (deferred to v1.2, see task-11 scope).

const categoryDefaults = { name: "", name_bn: "", display_order: 0, is_active: true };
const itemDefaults = {
    name: "", name_bn: "", description: "", description_bn: "", image: "",
    price: "", discount_price: "", prep_minutes: "", is_available: true,
    is_veg: false, spice_level: "", display_order: 0,
};

const VendorMenu = () => {
    const [categories, setCategories] = useState([]);
    const [items, setItems] = useState([]);
    const [selectedCategoryId, setSelectedCategoryId] = useState(null);

    const [categoryDialogOpen, setCategoryDialogOpen] = useState(false);
    const [editingCategory, setEditingCategory] = useState(null);
    const [itemDialogOpen, setItemDialogOpen] = useState(false);
    const [editingItem, setEditingItem] = useState(null);

    const { callApi, loading } = useApi();
    const categoryForm = useForm({ defaultValues: categoryDefaults });
    const itemForm = useForm({ defaultValues: itemDefaults });

    const fetchCategories = async () => {
        const res = await callApi({ url: "food/vendor/categories/", method: "GET" });
        if (res?.data?.data) {
            setCategories(res.data.data);
        }
    };

    const fetchItems = async () => {
        const res = await callApi({ url: "food/vendor/items/", method: "GET" });
        if (res?.data?.data) {
            setItems(res.data.data);
        }
    };

    useEffect(() => {
        fetchCategories();
        fetchItems();
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, []);

    useEffect(() => {
        if (selectedCategoryId === null && categories.length > 0) {
            setSelectedCategoryId(categories[0].id);
        }
    }, [categories, selectedCategoryId]);

    const visibleItems = useMemo(
        () => items.filter((item) => item.category_id === selectedCategoryId),
        [items, selectedCategoryId]
    );

    // ── Category dialog ──────────────────────────────────────────────
    const openCreateCategory = () => {
        setEditingCategory(null);
        categoryForm.reset(categoryDefaults);
        setCategoryDialogOpen(true);
    };

    const openEditCategory = (category) => {
        setEditingCategory(category);
        categoryForm.reset({
            name: category.name,
            name_bn: category.name_bn || "",
            display_order: category.display_order ?? 0,
            is_active: !!category.is_active,
        });
        setCategoryDialogOpen(true);
    };

    const closeCategoryDialog = () => {
        setCategoryDialogOpen(false);
        setEditingCategory(null);
    };

    const onSubmitCategory = async (data) => {
        const res = editingCategory
            ? await callApi({ url: `food/vendor/categories/${editingCategory.id}/`, method: "PATCH", body: data })
            : await callApi({ url: "food/vendor/categories/", method: "POST", body: data });
        if (res?.data) {
            toast.success(res.data.message || `Category ${editingCategory ? "updated" : "created"}`);
            closeCategoryDialog();
            fetchCategories();
        }
    };

    const handleDeleteCategory = async (category) => {
        if (!window.confirm(`Delete category "${category.name}"? Its items will need a new category.`)) return;
        const res = await callApi({ url: `food/vendor/categories/${category.id}/`, method: "DELETE" });
        if (res) {
            toast.success("Category deleted");
            if (selectedCategoryId === category.id) setSelectedCategoryId(null);
            fetchCategories();
            fetchItems();
        }
    };

    // ── Item dialog ──────────────────────────────────────────────────
    const openCreateItem = () => {
        if (!selectedCategoryId) {
            toast.error("Add a category first");
            return;
        }
        setEditingItem(null);
        itemForm.reset(itemDefaults);
        setItemDialogOpen(true);
    };

    const openEditItem = (item) => {
        setEditingItem(item);
        itemForm.reset({
            name: item.name,
            name_bn: item.name_bn || "",
            description: item.description || "",
            description_bn: item.description_bn || "",
            image: item.image || "",
            price: item.price ?? "",
            discount_price: item.discount_price ?? "",
            prep_minutes: item.prep_minutes ?? "",
            is_available: !!item.is_available,
            is_veg: !!item.is_veg,
            spice_level: item.spice_level || "",
            display_order: item.display_order ?? 0,
        });
        setItemDialogOpen(true);
    };

    const closeItemDialog = () => {
        setItemDialogOpen(false);
        setEditingItem(null);
    };

    const onSubmitItem = async (data) => {
        const body = { ...data, category_id: editingItem ? editingItem.category_id : selectedCategoryId };
        const res = editingItem
            ? await callApi({ url: `food/vendor/items/${editingItem.id}/`, method: "PATCH", body })
            : await callApi({ url: "food/vendor/items/", method: "POST", body });
        if (res?.data) {
            toast.success(res.data.message || `Item ${editingItem ? "updated" : "created"}`);
            closeItemDialog();
            fetchItems();
        }
    };

    const handleDeleteItem = async (item) => {
        if (!window.confirm(`Delete item "${item.name}"?`)) return;
        const res = await callApi({ url: `food/vendor/items/${item.id}/`, method: "DELETE" });
        if (res) {
            toast.success("Item deleted");
            fetchItems();
        }
    };

    return (
        <Box component="div" sx={{ width: "100%" }}>
            <Typography variant="h5" gutterBottom>Menu</Typography>
            {loading && <LinearProgress sx={{ mb: 2 }} />}

            <Grid container spacing={2}>
                <Grid item xs={12} sm={4}>
                    <Card>
                        <CardContent>
                            <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 1 }}>
                                <Typography variant="subtitle1">Categories</Typography>
                                <Button size="small" variant="contained" startIcon={<Add />} onClick={openCreateCategory}>
                                    Add Category
                                </Button>
                            </Stack>
                            {categories.length === 0 && !loading && (
                                <Typography variant="body2" color="text.secondary">No categories yet</Typography>
                            )}
                            <List dense>
                                {categories.map((category) => (
                                    <ListItemButton
                                        key={category.id}
                                        selected={category.id === selectedCategoryId}
                                        onClick={() => setSelectedCategoryId(category.id)}
                                        sx={{ borderRadius: 1, mb: 0.5 }}
                                    >
                                        <ListItemText
                                            primary={category.name}
                                            secondary={category.is_active ? null : "Inactive"}
                                        />
                                        <IconButton size="small" onClick={(e) => { e.stopPropagation(); openEditCategory(category); }}>
                                            <Edit fontSize="small" color="primary" />
                                        </IconButton>
                                        <IconButton size="small" onClick={(e) => { e.stopPropagation(); handleDeleteCategory(category); }}>
                                            <Delete fontSize="small" color="error" />
                                        </IconButton>
                                    </ListItemButton>
                                ))}
                            </List>
                        </CardContent>
                    </Card>
                </Grid>

                <Grid item xs={12} sm={8}>
                    <Card>
                        <CardContent>
                            <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 1 }}>
                                <Typography variant="subtitle1">
                                    Items{selectedCategoryId ? ` — ${categories.find((c) => c.id === selectedCategoryId)?.name || ""}` : ""}
                                </Typography>
                                <Button size="small" variant="contained" startIcon={<Add />} onClick={openCreateItem} disabled={!selectedCategoryId}>
                                    Add Item
                                </Button>
                            </Stack>
                            <TableContainer component={Paper} variant="outlined">
                                <Table size="small">
                                    <TableHead>
                                        <TableRow>
                                            <TableCell>Name</TableCell>
                                            <TableCell>Price</TableCell>
                                            <TableCell>Available</TableCell>
                                            <TableCell align="right">Actions</TableCell>
                                        </TableRow>
                                    </TableHead>
                                    <TableBody>
                                        {visibleItems.length === 0 && !loading && (
                                            <TableRow>
                                                <TableCell colSpan={4} align="center">No items in this category</TableCell>
                                            </TableRow>
                                        )}
                                        {visibleItems.map((item) => (
                                            <TableRow key={item.id}>
                                                <TableCell>{item.name}</TableCell>
                                                <TableCell>
                                                    {item.discount_price ? (
                                                        <>
                                                            <Typography component="span" sx={{ textDecoration: "line-through", mr: 0.5 }} color="text.secondary" variant="body2">
                                                                {item.price}
                                                            </Typography>
                                                            {item.discount_price}
                                                        </>
                                                    ) : item.price}
                                                </TableCell>
                                                <TableCell>
                                                    <Chip
                                                        label={item.is_available ? "Available" : "Unavailable"}
                                                        color={item.is_available ? "success" : "default"}
                                                        size="small"
                                                    />
                                                </TableCell>
                                                <TableCell align="right">
                                                    <Stack direction="row" spacing={1} justifyContent="flex-end">
                                                        <IconButton size="small" onClick={() => openEditItem(item)}>
                                                            <Edit fontSize="small" color="primary" />
                                                        </IconButton>
                                                        <IconButton size="small" onClick={() => handleDeleteItem(item)}>
                                                            <Delete fontSize="small" color="error" />
                                                        </IconButton>
                                                    </Stack>
                                                </TableCell>
                                            </TableRow>
                                        ))}
                                    </TableBody>
                                </Table>
                            </TableContainer>
                        </CardContent>
                    </Card>
                </Grid>
            </Grid>

            {/* Category dialog */}
            <Dialog open={categoryDialogOpen} onClose={closeCategoryDialog} maxWidth="xs" fullWidth>
                <form onSubmit={categoryForm.handleSubmit(onSubmitCategory)}>
                    <DialogTitle>{editingCategory ? "Edit Category" : "Add Category"}</DialogTitle>
                    <DialogContent>
                        <TextField
                            label="Name" fullWidth margin="normal"
                            {...categoryForm.register("name", { required: true })}
                            error={!!categoryForm.formState.errors.name}
                            helperText={categoryForm.formState.errors.name && "This field is required"}
                        />
                        <TextField label="Name (Bangla)" fullWidth margin="normal" {...categoryForm.register("name_bn")} />
                        <TextField
                            label="Display Order" type="number" fullWidth margin="normal"
                            {...categoryForm.register("display_order")}
                        />
                        <Controller
                            name="is_active"
                            control={categoryForm.control}
                            render={({ field }) => (
                                <FormControlLabel
                                    control={<Switch checked={!!field.value} onChange={(e) => field.onChange(e.target.checked)} />}
                                    label="Active"
                                />
                            )}
                        />
                    </DialogContent>
                    <DialogActions>
                        <Button onClick={closeCategoryDialog}>Cancel</Button>
                        <Button type="submit" variant="contained">Save</Button>
                    </DialogActions>
                </form>
            </Dialog>

            {/* Item dialog */}
            <Dialog open={itemDialogOpen} onClose={closeItemDialog} maxWidth="sm" fullWidth>
                <form onSubmit={itemForm.handleSubmit(onSubmitItem)}>
                    <DialogTitle>{editingItem ? "Edit Item" : "Add Item"}</DialogTitle>
                    <DialogContent>
                        <Grid container spacing={2}>
                            <Grid item xs={12} sm={6}>
                                <TextField
                                    label="Name" fullWidth margin="normal"
                                    {...itemForm.register("name", { required: true })}
                                    error={!!itemForm.formState.errors.name}
                                    helperText={itemForm.formState.errors.name && "This field is required"}
                                />
                            </Grid>
                            <Grid item xs={12} sm={6}>
                                <TextField label="Name (Bangla)" fullWidth margin="normal" {...itemForm.register("name_bn")} />
                            </Grid>
                            <Grid item xs={12}>
                                <TextField label="Description" fullWidth margin="normal" multiline minRows={2} {...itemForm.register("description")} />
                            </Grid>
                            <Grid item xs={12}>
                                <TextField label="Description (Bangla)" fullWidth margin="normal" multiline minRows={2} {...itemForm.register("description_bn")} />
                            </Grid>
                            <Grid item xs={12}>
                                <TextField label="Image URL" fullWidth margin="normal" {...itemForm.register("image")} />
                            </Grid>
                            <Grid item xs={12} sm={6}>
                                <TextField
                                    label="Price" type="number" fullWidth margin="normal" required
                                    inputProps={{ step: "any" }}
                                    {...itemForm.register("price", { required: true })}
                                    error={!!itemForm.formState.errors.price}
                                    helperText={itemForm.formState.errors.price && "This field is required"}
                                />
                            </Grid>
                            <Grid item xs={12} sm={6}>
                                <TextField
                                    label="Discount Price" type="number" fullWidth margin="normal"
                                    inputProps={{ step: "any" }}
                                    {...itemForm.register("discount_price")}
                                />
                            </Grid>
                            <Grid item xs={12} sm={4}>
                                <TextField label="Prep Minutes" type="number" fullWidth margin="normal" {...itemForm.register("prep_minutes")} />
                            </Grid>
                            <Grid item xs={12} sm={4}>
                                <Controller
                                    name="spice_level"
                                    control={itemForm.control}
                                    render={({ field }) => (
                                        <TextField
                                            {...field}
                                            label="Spice Level" fullWidth margin="normal" select
                                            value={field.value || ""}
                                        >
                                            <MenuItem value="">None</MenuItem>
                                            <MenuItem value="mild">Mild</MenuItem>
                                            <MenuItem value="medium">Medium</MenuItem>
                                            <MenuItem value="hot">Hot</MenuItem>
                                        </TextField>
                                    )}
                                />
                            </Grid>
                            <Grid item xs={12} sm={4}>
                                <TextField label="Display Order" type="number" fullWidth margin="normal" {...itemForm.register("display_order")} />
                            </Grid>
                            <Grid item xs={12}>
                                <Stack direction="row" spacing={3}>
                                    <Controller
                                        name="is_available"
                                        control={itemForm.control}
                                        render={({ field }) => (
                                            <FormControlLabel
                                                control={<Switch checked={!!field.value} onChange={(e) => field.onChange(e.target.checked)} />}
                                                label="Available"
                                            />
                                        )}
                                    />
                                    <Controller
                                        name="is_veg"
                                        control={itemForm.control}
                                        render={({ field }) => (
                                            <FormControlLabel
                                                control={<Switch checked={!!field.value} onChange={(e) => field.onChange(e.target.checked)} />}
                                                label="Vegetarian"
                                            />
                                        )}
                                    />
                                </Stack>
                            </Grid>
                        </Grid>
                    </DialogContent>
                    <DialogActions>
                        <Button onClick={closeItemDialog}>Cancel</Button>
                        <Button type="submit" variant="contained">Save</Button>
                    </DialogActions>
                </form>
            </Dialog>
        </Box>
    );
};

export default VendorMenu;
