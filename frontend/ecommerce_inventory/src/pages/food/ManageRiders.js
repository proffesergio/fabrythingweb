import { useEffect, useState, useCallback } from "react";
import {
    Box, Typography, Card, Button, Table, TableBody, TableCell, TableHead, TableRow, Paper,
    TableContainer, Chip, IconButton, Dialog, DialogTitle, DialogContent, DialogActions,
    TextField, MenuItem, Grid, Stack, Avatar, Switch, FormControlLabel, Divider,
} from "@mui/material";
import AddIcon from "@mui/icons-material/Add";
import DeleteIcon from "@mui/icons-material/DeleteOutline";
import TwoWheelerIcon from "@mui/icons-material/TwoWheeler";
import { toast } from "react-toastify";
import useApi from "../../hooks/APIHandler";

const EMPTY = { name: "", phone: "", vehicle_type: "BIKE", vehicle_number: "", withLogin: true,
    owner: { username: "", email: "", password: "" } };
const VEHICLES = [["BIKE", "Motorbike"], ["CYCLE", "Bicycle"], ["FOOT", "On foot"]];

export default function ManageRiders() {
    const { callApi } = useApi();
    const [riders, setRiders] = useState([]);
    const [dialog, setDialog] = useState(null);

    const load = useCallback(async () => {
        const res = await callApi({ url: "food/admin/riders/", method: "GET" });
        setRiders(res?.data?.data || []);
    }, []); // eslint-disable-line react-hooks/exhaustive-deps
    useEffect(() => { load(); }, [load]);

    const create = async () => {
        if (!dialog.name.trim()) { toast.error("Name required"); return; }
        const body = { name: dialog.name, phone: dialog.phone, vehicle_type: dialog.vehicle_type, vehicle_number: dialog.vehicle_number };
        if (dialog.withLogin) body.owner = dialog.owner;
        const res = await callApi({ url: "food/admin/riders/", method: "POST", body });
        if (res?.status === 201) { toast.success("Rider added"); setDialog(null); load(); }
    };
    const toggleVerify = async (r) => { await callApi({ url: `food/admin/riders/${r.id}/`, method: "PATCH", body: { is_verified: !r.is_verified } }); load(); };
    const remove = async (id) => { await callApi({ url: `food/admin/riders/${id}/`, method: "DELETE" }); load(); };

    const setOwner = (k) => (e) => setDialog((d) => ({ ...d, owner: { ...d.owner, [k]: e.target.value } }));

    return (
        <Box>
            <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 2 }}>
                <Stack direction="row" spacing={1} alignItems="center"><TwoWheelerIcon color="primary" /><Typography variant="h5" fontWeight={800}>Riders</Typography></Stack>
                <Button variant="contained" startIcon={<AddIcon />} onClick={() => setDialog({ ...EMPTY })}>Add rider</Button>
            </Stack>

            <TableContainer component={Paper}>
                <Table>
                    <TableHead><TableRow>
                        <TableCell>Rider</TableCell><TableCell>Vehicle</TableCell><TableCell align="center">Deliveries</TableCell>
                        <TableCell align="center">Available</TableCell><TableCell align="center">Verified</TableCell><TableCell align="right">Actions</TableCell>
                    </TableRow></TableHead>
                    <TableBody>
                        {riders.length === 0 && <TableRow><TableCell colSpan={6} align="center">No riders yet</TableCell></TableRow>}
                        {riders.map((r) => (
                            <TableRow key={r.id} hover>
                                <TableCell>
                                    <Stack direction="row" spacing={1.5} alignItems="center">
                                        <Avatar sx={{ bgcolor: "primary.main", width: 34, height: 34 }}>{(r.name || "?")[0]}</Avatar>
                                        <Box><Typography variant="body2" fontWeight={600}>{r.name}</Typography>
                                            <Typography variant="caption" color="text.secondary">{r.rider_code} · {r.phone || "—"}</Typography></Box>
                                    </Stack>
                                </TableCell>
                                <TableCell>{r.vehicle_type} {r.vehicle_number}</TableCell>
                                <TableCell align="center">{r.total_deliveries}</TableCell>
                                <TableCell align="center"><Chip size="small" label={r.is_available ? "Online" : "Offline"} color={r.is_available ? "success" : "default"} /></TableCell>
                                <TableCell align="center"><Switch size="small" checked={r.is_verified} onChange={() => toggleVerify(r)} /></TableCell>
                                <TableCell align="right"><IconButton size="small" color="error" onClick={() => remove(r.id)}><DeleteIcon /></IconButton></TableCell>
                            </TableRow>
                        ))}
                    </TableBody>
                </Table>
            </TableContainer>

            <Dialog open={!!dialog} onClose={() => setDialog(null)} maxWidth="sm" fullWidth>
                <DialogTitle>Add rider</DialogTitle>
                <DialogContent>
                    {dialog && (
                        <Grid container spacing={2} sx={{ mt: 0 }}>
                            <Grid item xs={12} sm={6}><TextField label="Name" fullWidth value={dialog.name} onChange={(e) => setDialog({ ...dialog, name: e.target.value })} /></Grid>
                            <Grid item xs={12} sm={6}><TextField label="Phone" fullWidth value={dialog.phone} onChange={(e) => setDialog({ ...dialog, phone: e.target.value })} /></Grid>
                            <Grid item xs={12} sm={6}>
                                <TextField select label="Vehicle" fullWidth value={dialog.vehicle_type} onChange={(e) => setDialog({ ...dialog, vehicle_type: e.target.value })}>
                                    {VEHICLES.map(([v, l]) => <MenuItem key={v} value={v}>{l}</MenuItem>)}
                                </TextField>
                            </Grid>
                            <Grid item xs={12} sm={6}><TextField label="Vehicle number" fullWidth value={dialog.vehicle_number} onChange={(e) => setDialog({ ...dialog, vehicle_number: e.target.value })} /></Grid>
                            <Grid item xs={12}><Divider /><FormControlLabel control={<Switch checked={dialog.withLogin} onChange={(e) => setDialog({ ...dialog, withLogin: e.target.checked })} />} label="Create rider app login" /></Grid>
                            {dialog.withLogin && <>
                                <Grid item xs={12} sm={4}><TextField label="Username" fullWidth value={dialog.owner.username} onChange={setOwner("username")} /></Grid>
                                <Grid item xs={12} sm={4}><TextField label="Email" fullWidth value={dialog.owner.email} onChange={setOwner("email")} /></Grid>
                                <Grid item xs={12} sm={4}><TextField label="Password" type="password" fullWidth value={dialog.owner.password} onChange={setOwner("password")} /></Grid>
                            </>}
                        </Grid>
                    )}
                </DialogContent>
                <DialogActions><Button onClick={() => setDialog(null)}>Cancel</Button><Button variant="contained" onClick={create}>Create</Button></DialogActions>
            </Dialog>
        </Box>
    );
}
