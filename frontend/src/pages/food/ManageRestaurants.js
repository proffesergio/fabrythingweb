import React, { useEffect, useState } from "react";
import {
    Box, Breadcrumbs, Button, Chip, Dialog, DialogActions, DialogContent, DialogTitle,
    LinearProgress, Table, TableBody, TableCell, TableContainer, TableHead, TableRow,
    Paper, TextField, Typography, Stack, Grid, Switch, FormControlLabel, Divider,
} from "@mui/material";
import AddIcon from "@mui/icons-material/Add";
import { useNavigate } from "react-router-dom";
import { toast } from "react-toastify";
import useApi from "../../hooks/APIHandler";

const STATUS_COLORS = { PENDING: "warning", ACTIVE: "success", SUSPENDED: "error", REJECTED: "default" };
const EMPTY_CREATE = {
    name: "", cuisine_type: "", phone: "", commission_percentage: "15", base_delivery_fee: "40",
    min_order_amount: "0", withOwner: true,
    owner: { username: "", email: "", phone: "", password: "" },
};

const ManageRestaurants = () => {
    const [restaurants, setRestaurants] = useState([]);
    const [editRestaurant, setEditRestaurant] = useState(null);
    const [commission, setCommission] = useState("");
    const [deliveryFee, setDeliveryFee] = useState("");
    const [createOpen, setCreateOpen] = useState(false);
    const [form, setForm] = useState(EMPTY_CREATE);
    const { callApi, loading } = useApi();
    const navigate = useNavigate();

    const fetchRestaurants = async () => {
        const res = await callApi({ url: "food/admin/restaurants/", method: "GET" });
        if (res?.data?.data) setRestaurants(res.data.data);
    };

    useEffect(() => { fetchRestaurants(); }, []); // eslint-disable-line react-hooks/exhaustive-deps

    const handleApprove = async (id) => {
        const res = await callApi({ url: `food/admin/restaurants/${id}/approve/`, method: "POST" });
        if (res?.data) { toast.success(res.data.message || "Restaurant approved"); fetchRestaurants(); }
    };
    const handleSuspend = async (id) => {
        const res = await callApi({ url: `food/admin/restaurants/${id}/suspend/`, method: "POST" });
        if (res?.data) { toast.success(res.data.message || "Restaurant suspended"); fetchRestaurants(); }
    };

    const openEdit = (restaurant) => {
        setEditRestaurant(restaurant);
        setCommission(restaurant.commission_percentage ?? "");
        setDeliveryFee(restaurant.base_delivery_fee ?? "");
    };
    const closeEdit = () => setEditRestaurant(null);

    const handleSaveEdit = async () => {
        if (!editRestaurant) return;
        const res = await callApi({
            url: `food/admin/restaurants/${editRestaurant.id}/`, method: "PATCH",
            body: { commission_percentage: commission, base_delivery_fee: deliveryFee },
        });
        if (res?.data) { toast.success(res.data.message || "Restaurant updated"); closeEdit(); fetchRestaurants(); }
    };

    const setF = (k) => (e) => setForm((f) => ({ ...f, [k]: e.target.value }));
    const setOwner = (k) => (e) => setForm((f) => ({ ...f, owner: { ...f.owner, [k]: e.target.value } }));

    const handleCreate = async () => {
        if (!form.name.trim()) { toast.error("Restaurant name is required"); return; }
        const body = {
            name: form.name, cuisine_type: form.cuisine_type, phone: form.phone,
            commission_percentage: form.commission_percentage, base_delivery_fee: form.base_delivery_fee,
            min_order_amount: form.min_order_amount,
        };
        if (form.withOwner) body.owner = form.owner;
        const res = await callApi({ url: "food/admin/restaurants/", method: "POST", body });
        if (res?.status === 201) {
            toast.success("Restaurant created");
            setCreateOpen(false); setForm(EMPTY_CREATE); fetchRestaurants();
        }
    };

    return (
        <Box component="div" sx={{ width: "100%" }}>
            <Box sx={{ display: "flex", justifyContent: "space-between", alignItems: "center", mb: 2 }}>
                <Breadcrumbs>
                    <Typography variant="body2" onClick={() => navigate("/admin")}>Home</Typography>
                    <Typography variant="body2">Manage Restaurants</Typography>
                </Breadcrumbs>
                <Button variant="contained" startIcon={<AddIcon />} onClick={() => setCreateOpen(true)}>
                    Add Restaurant
                </Button>
            </Box>
            <Typography variant="h5" gutterBottom>Restaurants</Typography>
            {loading && <LinearProgress />}
            <TableContainer component={Paper}>
                <Table>
                    <TableHead>
                        <TableRow>
                            <TableCell>Name</TableCell><TableCell>Status</TableCell>
                            <TableCell>Commission %</TableCell><TableCell>Delivery Fee</TableCell>
                            <TableCell align="right">Actions</TableCell>
                        </TableRow>
                    </TableHead>
                    <TableBody>
                        {restaurants.length === 0 && !loading && (
                            <TableRow><TableCell colSpan={5} align="center">No restaurants found</TableCell></TableRow>
                        )}
                        {restaurants.map((restaurant) => (
                            <TableRow key={restaurant.id} hover>
                                <TableCell sx={{ cursor: "pointer" }}
                                    onClick={() => navigate(`/admin/manage/food/restaurants/${restaurant.id}`)}>
                                    {restaurant.name}
                                </TableCell>
                                <TableCell>
                                    <Chip label={restaurant.status} color={STATUS_COLORS[restaurant.status] || "default"} size="small" />
                                </TableCell>
                                <TableCell>{restaurant.commission_percentage}</TableCell>
                                <TableCell>{restaurant.base_delivery_fee}</TableCell>
                                <TableCell align="right">
                                    <Stack direction="row" spacing={1} justifyContent="flex-end">
                                        {restaurant.status !== "ACTIVE" && (
                                            <Button size="small" variant="outlined" color="success" onClick={() => handleApprove(restaurant.id)}>Approve</Button>
                                        )}
                                        {restaurant.status === "ACTIVE" && (
                                            <Button size="small" variant="outlined" color="error" onClick={() => handleSuspend(restaurant.id)}>Suspend</Button>
                                        )}
                                        <Button size="small" variant="outlined" onClick={() => openEdit(restaurant)}>Edit</Button>
                                        <Button size="small" onClick={() => navigate(`/admin/manage/food/restaurants/${restaurant.id}`)}>Manage</Button>
                                    </Stack>
                                </TableCell>
                            </TableRow>
                        ))}
                    </TableBody>
                </Table>
            </TableContainer>

            {/* Edit commission/fee */}
            <Dialog open={!!editRestaurant} onClose={closeEdit} maxWidth="xs" fullWidth>
                <DialogTitle>Edit {editRestaurant?.name}</DialogTitle>
                <DialogContent>
                    <TextField label="Commission %" type="number" fullWidth margin="normal"
                        value={commission} onChange={(e) => setCommission(e.target.value)} />
                    <TextField label="Base Delivery Fee" type="number" fullWidth margin="normal"
                        value={deliveryFee} onChange={(e) => setDeliveryFee(e.target.value)} />
                </DialogContent>
                <DialogActions>
                    <Button onClick={closeEdit}>Cancel</Button>
                    <Button variant="contained" onClick={handleSaveEdit}>Save</Button>
                </DialogActions>
            </Dialog>

            {/* Create restaurant + owner */}
            <Dialog open={createOpen} onClose={() => setCreateOpen(false)} maxWidth="sm" fullWidth>
                <DialogTitle>Add Restaurant</DialogTitle>
                <DialogContent>
                    <Grid container spacing={2} sx={{ mt: 0 }}>
                        <Grid item xs={12} sm={6}><TextField label="Restaurant name" fullWidth value={form.name} onChange={setF("name")} /></Grid>
                        <Grid item xs={12} sm={6}><TextField label="Cuisine type" fullWidth value={form.cuisine_type} onChange={setF("cuisine_type")} /></Grid>
                        <Grid item xs={12} sm={6}><TextField label="Contact phone" fullWidth value={form.phone} onChange={setF("phone")} /></Grid>
                        <Grid item xs={12} sm={6}><TextField label="Commission %" type="number" fullWidth value={form.commission_percentage} onChange={setF("commission_percentage")} /></Grid>
                        <Grid item xs={12} sm={6}><TextField label="Base delivery fee" type="number" fullWidth value={form.base_delivery_fee} onChange={setF("base_delivery_fee")} /></Grid>
                        <Grid item xs={12} sm={6}><TextField label="Min order amount" type="number" fullWidth value={form.min_order_amount} onChange={setF("min_order_amount")} /></Grid>
                    </Grid>
                    <Divider sx={{ my: 2 }} />
                    <FormControlLabel
                        control={<Switch checked={form.withOwner} onChange={(e) => setForm((f) => ({ ...f, withOwner: e.target.checked }))} />}
                        label="Create owner login (vendor dashboard access)"
                    />
                    {form.withOwner && (
                        <Grid container spacing={2} sx={{ mt: 0 }}>
                            <Grid item xs={12} sm={6}><TextField label="Owner username" fullWidth value={form.owner.username} onChange={setOwner("username")} /></Grid>
                            <Grid item xs={12} sm={6}><TextField label="Owner email" fullWidth value={form.owner.email} onChange={setOwner("email")} /></Grid>
                            <Grid item xs={12} sm={6}><TextField label="Owner phone" fullWidth value={form.owner.phone} onChange={setOwner("phone")} /></Grid>
                            <Grid item xs={12} sm={6}><TextField label="Owner password" type="password" fullWidth value={form.owner.password} onChange={setOwner("password")} /></Grid>
                        </Grid>
                    )}
                </DialogContent>
                <DialogActions>
                    <Button onClick={() => setCreateOpen(false)}>Cancel</Button>
                    <Button variant="contained" onClick={handleCreate}>Create</Button>
                </DialogActions>
            </Dialog>
        </Box>
    );
};

export default ManageRestaurants;
