import React, { useEffect, useState } from "react";
import {
    Box, Breadcrumbs, Button, Chip, Dialog, DialogActions, DialogContent, DialogTitle,
    FormControlLabel, IconButton, LinearProgress, Switch, Table, TableBody, TableCell,
    TableContainer, TableHead, TableRow, Paper, TextField, Typography, Stack,
} from "@mui/material";
import { Add, Delete, Edit, Place } from "@mui/icons-material";
import { useNavigate } from "react-router-dom";
import { Controller, useForm } from "react-hook-form";
import { toast } from "react-toastify";
import useApi from "../../hooks/APIHandler";
import ZoneVillagesDialog from "./ZoneVillagesDialog";

const defaultValues = {
    name: "",
    name_bn: "",
    center_lat: "",
    center_lng: "",
    radius_km: "",
    is_active: true,
};

const ManageZones = () => {
    const [zones, setZones] = useState([]);
    const [open, setOpen] = useState(false);
    const [editingZone, setEditingZone] = useState(null);
    const [villageZone, setVillageZone] = useState(null);
    const { callApi, loading } = useApi();
    const navigate = useNavigate();
    const { register, handleSubmit, control, reset, formState: { errors } } = useForm({ defaultValues });

    const fetchZones = async () => {
        const res = await callApi({ url: "food/admin/zone-tree/", method: "GET" });
        if (res?.data?.data) {
            setZones(res.data.data);
        }
    };

    useEffect(() => {
        fetchZones();
    }, []);

    const openCreate = () => {
        setEditingZone(null);
        reset(defaultValues);
        setOpen(true);
    };

    const openEdit = (zone) => {
        setEditingZone(zone);
        reset({
            name: zone.name,
            name_bn: zone.name_bn || "",
            center_lat: zone.center_lat,
            center_lng: zone.center_lng,
            radius_km: zone.radius_km,
            is_active: zone.is_active,
        });
        setOpen(true);
    };

    const handleClose = () => {
        setOpen(false);
        setEditingZone(null);
    };

    const onSubmit = async (data) => {
        const body = {
            name: data.name,
            name_bn: data.name_bn,
            center_lat: data.center_lat,
            center_lng: data.center_lng,
            radius_km: data.radius_km,
            is_active: data.is_active,
        };
        const res = editingZone
            ? await callApi({ url: `food/admin/zones/${editingZone.id}/`, method: "PATCH", body })
            : await callApi({ url: "food/admin/zones/", method: "POST", body });
        if (res?.data) {
            toast.success(res.data.message || `Zone ${editingZone ? "updated" : "created"}`);
            handleClose();
            fetchZones();
        }
    };

    const handleDelete = async (id) => {
        if (!window.confirm("Delete this delivery zone?")) return;
        const res = await callApi({ url: `food/admin/zones/${id}/`, method: "DELETE" });
        if (res) {
            toast.success("Zone deleted");
            fetchZones();
        }
    };

    return (
        <Box component="div" sx={{ width: "100%" }}>
            <Box sx={{ display: "flex", justifyContent: "space-between", alignItems: "center", mb: 2 }}>
                <Breadcrumbs>
                    <Typography variant="body2" onClick={() => navigate("/admin")}>Home</Typography>
                    <Typography variant="body2">Delivery Zones</Typography>
                </Breadcrumbs>
                <Button variant="contained" startIcon={<Add />} onClick={openCreate}>Add Zone</Button>
            </Box>
            <Typography variant="h5" gutterBottom>Delivery Zones</Typography>
            {loading && <LinearProgress />}
            <TableContainer component={Paper}>
                <Table>
                    <TableHead>
                        <TableRow>
                            <TableCell>Name</TableCell>
                            <TableCell>বাংলা নাম</TableCell>
                            <TableCell align="center">Villages</TableCell>
                            <TableCell>Center Lat</TableCell>
                            <TableCell>Center Lng</TableCell>
                            <TableCell>Radius (km)</TableCell>
                            <TableCell>Active</TableCell>
                            <TableCell align="right">Actions</TableCell>
                        </TableRow>
                    </TableHead>
                    <TableBody>
                        {zones.length === 0 && !loading && (
                            <TableRow>
                                <TableCell colSpan={8} align="center">No delivery zones found</TableCell>
                            </TableRow>
                        )}
                        {zones.map((zone) => (
                            <TableRow key={zone.id}>
                                <TableCell>{zone.name}</TableCell>
                                <TableCell>
                                    {zone.name_bn || (
                                        <Chip size="small" color="warning" variant="outlined" label="Missing" />
                                    )}
                                </TableCell>
                                <TableCell align="center">
                                    <Button size="small" startIcon={<Place />} onClick={() => setVillageZone(zone)}>
                                        {zone.village_count ?? 0}
                                    </Button>
                                </TableCell>
                                <TableCell>{zone.center_lat}</TableCell>
                                <TableCell>{zone.center_lng}</TableCell>
                                <TableCell>{zone.radius_km}</TableCell>
                                <TableCell>
                                    <Chip
                                        label={zone.is_active ? "Active" : "Inactive"}
                                        color={zone.is_active ? "success" : "default"}
                                        size="small"
                                    />
                                </TableCell>
                                <TableCell align="right">
                                    <Stack direction="row" spacing={1} justifyContent="flex-end">
                                        <IconButton onClick={() => openEdit(zone)}>
                                            <Edit color="primary" />
                                        </IconButton>
                                        <IconButton onClick={() => handleDelete(zone.id)}>
                                            <Delete color="error" />
                                        </IconButton>
                                    </Stack>
                                </TableCell>
                            </TableRow>
                        ))}
                    </TableBody>
                </Table>
            </TableContainer>

            <ZoneVillagesDialog
                zone={villageZone}
                open={!!villageZone}
                onClose={() => setVillageZone(null)}
                onChanged={fetchZones}
            />

            <Dialog open={open} onClose={handleClose} maxWidth="xs" fullWidth>
                <form onSubmit={handleSubmit(onSubmit)}>
                    <DialogTitle>{editingZone ? "Edit Delivery Zone" : "Add Delivery Zone"}</DialogTitle>
                    <DialogContent>
                        <TextField
                            label="Name"
                            fullWidth
                            margin="normal"
                            {...register("name", { required: true })}
                            error={!!errors.name}
                            helperText={errors.name && "This field is required"}
                        />
                        <TextField
                            label="Name (Bangla)"
                            fullWidth
                            margin="normal"
                            {...register("name_bn")}
                        />
                        <TextField
                            label="Center Latitude"
                            type="number"
                            fullWidth
                            margin="normal"
                            inputProps={{ step: "any" }}
                            {...register("center_lat", { required: true })}
                            error={!!errors.center_lat}
                            helperText={errors.center_lat && "This field is required"}
                        />
                        <TextField
                            label="Center Longitude"
                            type="number"
                            fullWidth
                            margin="normal"
                            inputProps={{ step: "any" }}
                            {...register("center_lng", { required: true })}
                            error={!!errors.center_lng}
                            helperText={errors.center_lng && "This field is required"}
                        />
                        <TextField
                            label="Radius (km)"
                            type="number"
                            fullWidth
                            margin="normal"
                            inputProps={{ step: "any" }}
                            {...register("radius_km", { required: true })}
                            error={!!errors.radius_km}
                            helperText={errors.radius_km && "This field is required"}
                        />
                        <Controller
                            name="is_active"
                            control={control}
                            render={({ field }) => (
                                <FormControlLabel
                                    control={<Switch checked={!!field.value} onChange={(e) => field.onChange(e.target.checked)} />}
                                    label="Active"
                                />
                            )}
                        />
                    </DialogContent>
                    <DialogActions>
                        <Button onClick={handleClose}>Cancel</Button>
                        <Button type="submit" variant="contained">Save</Button>
                    </DialogActions>
                </form>
            </Dialog>
        </Box>
    );
};

export default ManageZones;
