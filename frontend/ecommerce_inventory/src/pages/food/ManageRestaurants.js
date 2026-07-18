import React, { useEffect, useState } from "react";
import {
    Box, Breadcrumbs, Button, Chip, Dialog, DialogActions, DialogContent, DialogTitle,
    LinearProgress, Table, TableBody, TableCell, TableContainer, TableHead, TableRow,
    Paper, TextField, Typography, Stack,
} from "@mui/material";
import { useNavigate } from "react-router-dom";
import { toast } from "react-toastify";
import useApi from "../../hooks/APIHandler";

const STATUS_COLORS = {
    PENDING: "warning",
    ACTIVE: "success",
    SUSPENDED: "error",
    REJECTED: "default",
};

const ManageRestaurants = () => {
    const [restaurants, setRestaurants] = useState([]);
    const [editRestaurant, setEditRestaurant] = useState(null);
    const [commission, setCommission] = useState("");
    const [deliveryFee, setDeliveryFee] = useState("");
    const { callApi, loading } = useApi();
    const navigate = useNavigate();

    const fetchRestaurants = async () => {
        const res = await callApi({ url: "food/admin/restaurants/", method: "GET" });
        if (res?.data?.data) {
            setRestaurants(res.data.data);
        }
    };

    useEffect(() => {
        fetchRestaurants();
    }, []);

    const handleApprove = async (id) => {
        const res = await callApi({ url: `food/admin/restaurants/${id}/approve/`, method: "POST" });
        if (res?.data) {
            toast.success(res.data.message || "Restaurant approved");
            fetchRestaurants();
        }
    };

    const handleSuspend = async (id) => {
        const res = await callApi({ url: `food/admin/restaurants/${id}/suspend/`, method: "POST" });
        if (res?.data) {
            toast.success(res.data.message || "Restaurant suspended");
            fetchRestaurants();
        }
    };

    const openEdit = (restaurant) => {
        setEditRestaurant(restaurant);
        setCommission(restaurant.commission_percentage ?? "");
        setDeliveryFee(restaurant.base_delivery_fee ?? "");
    };

    const closeEdit = () => {
        setEditRestaurant(null);
    };

    const handleSaveEdit = async () => {
        if (!editRestaurant) return;
        const res = await callApi({
            url: `food/admin/restaurants/${editRestaurant.id}/`,
            method: "PATCH",
            body: {
                commission_percentage: commission,
                base_delivery_fee: deliveryFee,
            },
        });
        if (res?.data) {
            toast.success(res.data.message || "Restaurant updated");
            closeEdit();
            fetchRestaurants();
        }
    };

    return (
        <Box component="div" sx={{ width: "100%" }}>
            <Box sx={{ display: "flex", justifyContent: "space-between", alignItems: "center", mb: 2 }}>
                <Breadcrumbs>
                    <Typography variant="body2" onClick={() => navigate("/admin")}>Home</Typography>
                    <Typography variant="body2">Manage Restaurants</Typography>
                </Breadcrumbs>
            </Box>
            <Typography variant="h5" gutterBottom>Restaurants</Typography>
            {loading && <LinearProgress />}
            <TableContainer component={Paper}>
                <Table>
                    <TableHead>
                        <TableRow>
                            <TableCell>Name</TableCell>
                            <TableCell>Status</TableCell>
                            <TableCell>Commission %</TableCell>
                            <TableCell>Delivery Fee</TableCell>
                            <TableCell align="right">Actions</TableCell>
                        </TableRow>
                    </TableHead>
                    <TableBody>
                        {restaurants.length === 0 && !loading && (
                            <TableRow>
                                <TableCell colSpan={5} align="center">No restaurants found</TableCell>
                            </TableRow>
                        )}
                        {restaurants.map((restaurant) => (
                            <TableRow key={restaurant.id}>
                                <TableCell>{restaurant.name}</TableCell>
                                <TableCell>
                                    <Chip
                                        label={restaurant.status}
                                        color={STATUS_COLORS[restaurant.status] || "default"}
                                        size="small"
                                    />
                                </TableCell>
                                <TableCell>{restaurant.commission_percentage}</TableCell>
                                <TableCell>{restaurant.base_delivery_fee}</TableCell>
                                <TableCell align="right">
                                    <Stack direction="row" spacing={1} justifyContent="flex-end">
                                        {restaurant.status !== "ACTIVE" && (
                                            <Button size="small" variant="outlined" color="success" onClick={() => handleApprove(restaurant.id)}>
                                                Approve
                                            </Button>
                                        )}
                                        {restaurant.status === "ACTIVE" && (
                                            <Button size="small" variant="outlined" color="error" onClick={() => handleSuspend(restaurant.id)}>
                                                Suspend
                                            </Button>
                                        )}
                                        <Button size="small" variant="outlined" onClick={() => openEdit(restaurant)}>
                                            Edit
                                        </Button>
                                    </Stack>
                                </TableCell>
                            </TableRow>
                        ))}
                    </TableBody>
                </Table>
            </TableContainer>

            <Dialog open={!!editRestaurant} onClose={closeEdit} maxWidth="xs" fullWidth>
                <DialogTitle>Edit {editRestaurant?.name}</DialogTitle>
                <DialogContent>
                    <TextField
                        label="Commission %"
                        type="number"
                        fullWidth
                        margin="normal"
                        value={commission}
                        onChange={(e) => setCommission(e.target.value)}
                    />
                    <TextField
                        label="Base Delivery Fee"
                        type="number"
                        fullWidth
                        margin="normal"
                        value={deliveryFee}
                        onChange={(e) => setDeliveryFee(e.target.value)}
                    />
                </DialogContent>
                <DialogActions>
                    <Button onClick={closeEdit}>Cancel</Button>
                    <Button variant="contained" onClick={handleSaveEdit}>Save</Button>
                </DialogActions>
            </Dialog>
        </Box>
    );
};

export default ManageRestaurants;
