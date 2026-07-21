import { useEffect, useState, useCallback } from "react";
import {
    Box, Typography, Card, Button, Table, TableBody, TableCell, TableHead, TableRow, Paper,
    TableContainer, Chip, IconButton, Dialog, DialogTitle, DialogContent, DialogActions,
    TextField, MenuItem, Grid, Switch, FormControlLabel, Stack,
} from "@mui/material";
import AddIcon from "@mui/icons-material/Add";
import EditIcon from "@mui/icons-material/Edit";
import DeleteIcon from "@mui/icons-material/DeleteOutline";
import RedeemIcon from "@mui/icons-material/Redeem";
import { toast } from "react-toastify";
import useApi from "../../hooks/APIHandler";

const EMPTY = {
    code: "", restaurant: "", discount_type: "PERCENT", discount_value: "", min_order_amount: "0",
    max_discount: "", usage_limit: "", is_active: true,
};

export default function ManageCoupons() {
    const { callApi } = useApi();
    const [coupons, setCoupons] = useState([]);
    const [restaurants, setRestaurants] = useState([]);
    const [dialog, setDialog] = useState(null);

    const load = useCallback(async () => {
        const [c, r] = await Promise.all([
            callApi({ url: "food/admin/coupons/", method: "GET" }),
            callApi({ url: "food/admin/restaurants/", method: "GET" }),
        ]);
        setCoupons(c?.data?.data || []);
        setRestaurants(r?.data?.data || []);
    }, []); // eslint-disable-line react-hooks/exhaustive-deps

    useEffect(() => { load(); }, [load]);

    const save = async () => {
        const body = { ...dialog };
        ["max_discount", "usage_limit"].forEach((k) => { if (body[k] === "" || body[k] == null) delete body[k]; });
        if (!body.restaurant) body.restaurant = null;
        const isEdit = !!dialog.id;
        const res = await callApi({
            url: isEdit ? `food/admin/coupons/${dialog.id}/` : "food/admin/coupons/",
            method: isEdit ? "PATCH" : "POST", body,
        });
        if (res?.status === 200 || res?.status === 201) { toast.success("Coupon saved"); setDialog(null); load(); }
    };
    const remove = async (id) => { await callApi({ url: `food/admin/coupons/${id}/`, method: "DELETE" }); load(); };

    return (
        <Box>
            <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 2 }}>
                <Stack direction="row" spacing={1} alignItems="center"><RedeemIcon color="primary" /><Typography variant="h5" fontWeight={800}>Coupons</Typography></Stack>
                <Button variant="contained" startIcon={<AddIcon />} onClick={() => setDialog({ ...EMPTY })}>New coupon</Button>
            </Stack>

            <TableContainer component={Paper}>
                <Table>
                    <TableHead><TableRow>
                        <TableCell>Code</TableCell><TableCell>Scope</TableCell><TableCell>Discount</TableCell>
                        <TableCell>Min order</TableCell><TableCell align="center">Used</TableCell>
                        <TableCell align="center">Active</TableCell><TableCell align="right">Actions</TableCell>
                    </TableRow></TableHead>
                    <TableBody>
                        {coupons.length === 0 && <TableRow><TableCell colSpan={7} align="center">No coupons yet</TableCell></TableRow>}
                        {coupons.map((c) => (
                            <TableRow key={c.id} hover>
                                <TableCell><Typography fontWeight={700}>{c.code}</Typography></TableCell>
                                <TableCell>{c.restaurant_name || "Platform-wide"}</TableCell>
                                <TableCell>{c.discount_type === "PERCENT" ? `${c.discount_value}%` : `৳${c.discount_value}`}</TableCell>
                                <TableCell>৳{c.min_order_amount}</TableCell>
                                <TableCell align="center">{c.used_count}{c.usage_limit ? `/${c.usage_limit}` : ""}</TableCell>
                                <TableCell align="center"><Chip size="small" label={c.is_active ? "Yes" : "No"} color={c.is_active ? "success" : "default"} /></TableCell>
                                <TableCell align="right">
                                    <IconButton size="small" onClick={() => setDialog({ ...c, restaurant: c.restaurant || "" })}><EditIcon /></IconButton>
                                    <IconButton size="small" color="error" onClick={() => remove(c.id)}><DeleteIcon /></IconButton>
                                </TableCell>
                            </TableRow>
                        ))}
                    </TableBody>
                </Table>
            </TableContainer>

            <Dialog open={!!dialog} onClose={() => setDialog(null)} maxWidth="sm" fullWidth>
                <DialogTitle>{dialog?.id ? "Edit coupon" : "New coupon"}</DialogTitle>
                <DialogContent>
                    {dialog && (
                        <Grid container spacing={2} sx={{ mt: 0 }}>
                            <Grid item xs={12} sm={6}><TextField label="Code" fullWidth value={dialog.code} onChange={(e) => setDialog({ ...dialog, code: e.target.value.toUpperCase() })} /></Grid>
                            <Grid item xs={12} sm={6}>
                                <TextField select label="Restaurant" fullWidth value={dialog.restaurant} onChange={(e) => setDialog({ ...dialog, restaurant: e.target.value })}>
                                    <MenuItem value="">Platform-wide</MenuItem>
                                    {restaurants.map((r) => <MenuItem key={r.id} value={r.id}>{r.name}</MenuItem>)}
                                </TextField>
                            </Grid>
                            <Grid item xs={12} sm={6}>
                                <TextField select label="Type" fullWidth value={dialog.discount_type} onChange={(e) => setDialog({ ...dialog, discount_type: e.target.value })}>
                                    <MenuItem value="PERCENT">Percent %</MenuItem><MenuItem value="FLAT">Flat ৳</MenuItem>
                                </TextField>
                            </Grid>
                            <Grid item xs={12} sm={6}><TextField label="Value" type="number" fullWidth value={dialog.discount_value} onChange={(e) => setDialog({ ...dialog, discount_value: e.target.value })} /></Grid>
                            <Grid item xs={12} sm={4}><TextField label="Min order ৳" type="number" fullWidth value={dialog.min_order_amount} onChange={(e) => setDialog({ ...dialog, min_order_amount: e.target.value })} /></Grid>
                            <Grid item xs={12} sm={4}><TextField label="Max discount ৳" type="number" fullWidth value={dialog.max_discount || ""} onChange={(e) => setDialog({ ...dialog, max_discount: e.target.value })} helperText="Percent cap" /></Grid>
                            <Grid item xs={12} sm={4}><TextField label="Usage limit" type="number" fullWidth value={dialog.usage_limit || ""} onChange={(e) => setDialog({ ...dialog, usage_limit: e.target.value })} /></Grid>
                            <Grid item xs={12}><FormControlLabel control={<Switch checked={!!dialog.is_active} onChange={(e) => setDialog({ ...dialog, is_active: e.target.checked })} />} label="Active" /></Grid>
                        </Grid>
                    )}
                </DialogContent>
                <DialogActions><Button onClick={() => setDialog(null)}>Cancel</Button><Button variant="contained" onClick={save}>Save</Button></DialogActions>
            </Dialog>
        </Box>
    );
}
