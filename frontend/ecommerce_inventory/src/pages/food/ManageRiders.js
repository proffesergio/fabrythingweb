import { useEffect, useState, useCallback } from "react";
import {
    Box, Typography, Button, Table, TableBody, TableCell, TableHead, TableRow, Paper,
    TableContainer, Chip, IconButton, Dialog, DialogTitle, DialogContent, DialogActions,
    TextField, MenuItem, Grid, Stack, Avatar, Switch, FormControlLabel, Divider,
    Alert, Tooltip, InputAdornment,
} from "@mui/material";
import AddIcon from "@mui/icons-material/Add";
import DeleteIcon from "@mui/icons-material/DeleteOutline";
import TwoWheelerIcon from "@mui/icons-material/TwoWheeler";
import OpenInNewIcon from "@mui/icons-material/OpenInNew";
import ContentCopyIcon from "@mui/icons-material/ContentCopy";
import KeyIcon from "@mui/icons-material/VpnKey";
import { toast } from "react-toastify";
import useApi from "../../hooks/APIHandler";

const EMPTY = {
    name: "", phone: "", vehicle_type: "BIKE", vehicle_number: "", withLogin: true,
    owner: { username: "", email: "", password: "" },
};
const VEHICLES = [["BIKE", "Motorbike"], ["CYCLE", "Bicycle"], ["FOOT", "On foot"]];

// The rider dashboard is a route on this same app, not a separate deployment.
const RIDER_APP_URL = `${window.location.origin}/rider`;

export default function ManageRiders() {
    const { callApi } = useApi();
    const [riders, setRiders] = useState([]);
    const [dialog, setDialog] = useState(null);
    const [pwDialog, setPwDialog] = useState(null);
    const [loadError, setLoadError] = useState("");

    const load = useCallback(async () => {
        // rawError: callApi returns null on any non-2xx, so without this a 500
        // renders as a cheerful empty table and the real failure is invisible.
        const res = await callApi({ url: "food/admin/riders/", method: "GET", rawError: true });
        if (res?.status === 200) {
            setRiders(res?.data?.data || []);
            setLoadError("");
        } else {
            setRiders([]);
            setLoadError(
                res?.data?.message ||
                "Could not load riders. The server returned an error — check that database migrations have been applied."
            );
        }
    }, []); // eslint-disable-line react-hooks/exhaustive-deps
    useEffect(() => { load(); }, [load]);

    const create = async () => {
        if (!dialog.name.trim()) { toast.error("Name required"); return; }
        const body = {
            name: dialog.name, phone: dialog.phone,
            vehicle_type: dialog.vehicle_type, vehicle_number: dialog.vehicle_number,
        };
        if (dialog.withLogin) body.owner = dialog.owner;
        const res = await callApi({ url: "food/admin/riders/", method: "POST", body, rawError: true });
        if (res?.status === 201) {
            toast.success("Rider added");
            setDialog(null);
            load();
        } else {
            // Surface the actual reason. `message` is always the generic
            // "Validation error"; the detail lives in `errors`.
            const errs = res?.data?.errors;
            toast.error(Array.isArray(errs) ? errs.join(" ") : (res?.data?.message || "Could not add rider"));
        }
    };

    const resetPassword = async () => {
        if ((pwDialog.password || "").length < 8) {
            toast.error("Password must be at least 8 characters");
            return;
        }
        const res = await callApi({
            url: `food/admin/riders/${pwDialog.id}/reset-password/`,
            method: "POST", body: { password: pwDialog.password }, rawError: true,
        });
        if (res?.status === 200) {
            toast.success(`Password updated for ${pwDialog.username}`);
            setPwDialog(null);
        } else {
            const errs = res?.data?.errors;
            toast.error(Array.isArray(errs) ? errs.join(" ") : "Could not update password");
        }
    };

    const toggleVerify = async (r) => {
        await callApi({ url: `food/admin/riders/${r.id}/`, method: "PATCH", body: { is_verified: !r.is_verified } });
        load();
    };
    const remove = async (id) => {
        await callApi({ url: `food/admin/riders/${id}/`, method: "DELETE" });
        load();
    };

    const copy = (text, label) => {
        navigator.clipboard?.writeText(text);
        toast.success(`${label} copied`);
    };

    const setOwner = (k) => (e) => setDialog((d) => ({ ...d, owner: { ...d.owner, [k]: e.target.value } }));

    return (
        <Box>
            <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 2 }}>
                <Stack direction="row" spacing={1} alignItems="center">
                    <TwoWheelerIcon color="primary" />
                    <Typography variant="h5" fontWeight={800}>Riders</Typography>
                </Stack>
                <Stack direction="row" spacing={1}>
                    <Button
                        variant="outlined"
                        startIcon={<OpenInNewIcon />}
                        onClick={() => window.open(RIDER_APP_URL, "_blank", "noopener,noreferrer")}
                    >
                        Open rider app
                    </Button>
                    <Button variant="contained" startIcon={<AddIcon />} onClick={() => setDialog({ ...EMPTY })}>
                        Add rider
                    </Button>
                </Stack>
            </Stack>

            <Alert severity="info" sx={{ mb: 2 }}>
                The rider app opens in a new tab as <strong>you</strong>, the admin — and an admin has no
                rider profile, so the page will be empty. To test a real rider, open{" "}
                <strong>a private / incognito window</strong> (browsers don't allow a site to open one for
                you) and sign in with that rider's username below. Use the key icon to set their password.
            </Alert>

            {loadError && <Alert severity="error" sx={{ mb: 2 }}>{loadError}</Alert>}

            <TableContainer component={Paper}>
                <Table>
                    <TableHead><TableRow>
                        <TableCell>Rider</TableCell>
                        <TableCell>Login</TableCell>
                        <TableCell>Vehicle</TableCell>
                        <TableCell align="center">Deliveries</TableCell>
                        <TableCell align="center">Presence</TableCell>
                        <TableCell align="center">Verified</TableCell>
                        <TableCell align="right">Actions</TableCell>
                    </TableRow></TableHead>
                    <TableBody>
                        {riders.length === 0 && !loadError && (
                            <TableRow><TableCell colSpan={7} align="center">No riders yet</TableCell></TableRow>
                        )}
                        {riders.map((r) => (
                            <TableRow key={r.id} hover>
                                <TableCell>
                                    <Stack direction="row" spacing={1.5} alignItems="center">
                                        <Avatar sx={{ bgcolor: "primary.main", width: 34, height: 34 }}>{(r.name || "?")[0]}</Avatar>
                                        <Box>
                                            <Typography variant="body2" fontWeight={600}>{r.name}</Typography>
                                            <Typography variant="caption" color="text.secondary">
                                                {r.rider_code} · {r.phone || "—"}
                                            </Typography>
                                        </Box>
                                    </Stack>
                                </TableCell>
                                <TableCell>
                                    {r.username ? (
                                        <Stack direction="row" spacing={0.5} alignItems="center">
                                            <Typography variant="body2">{r.username}</Typography>
                                            <Tooltip title="Copy username">
                                                <IconButton size="small" onClick={() => copy(r.username, "Username")}>
                                                    <ContentCopyIcon fontSize="inherit" />
                                                </IconButton>
                                            </Tooltip>
                                        </Stack>
                                    ) : (
                                        <Chip size="small" label="No login" variant="outlined" />
                                    )}
                                </TableCell>
                                <TableCell>{r.vehicle_type} {r.vehicle_number}</TableCell>
                                <TableCell align="center">{r.total_deliveries}</TableCell>
                                <TableCell align="center">
                                    {/* is_online comes from the heartbeat; is_available is the
                                        rider's own Online switch. Both must hold to be dispatchable. */}
                                    <Chip
                                        size="small"
                                        label={r.is_online ? "Online" : (r.is_available ? "Away" : "Offline")}
                                        color={r.is_online ? "success" : (r.is_available ? "warning" : "default")}
                                    />
                                </TableCell>
                                <TableCell align="center">
                                    <Switch size="small" checked={r.is_verified} onChange={() => toggleVerify(r)} />
                                </TableCell>
                                <TableCell align="right">
                                    {r.username && (
                                        <Tooltip title="Set password">
                                            <IconButton
                                                size="small"
                                                onClick={() => setPwDialog({ id: r.id, username: r.username, password: "" })}
                                            >
                                                <KeyIcon fontSize="small" />
                                            </IconButton>
                                        </Tooltip>
                                    )}
                                    <IconButton size="small" color="error" onClick={() => remove(r.id)}>
                                        <DeleteIcon />
                                    </IconButton>
                                </TableCell>
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
                            <Grid item xs={12}>
                                <Divider />
                                <FormControlLabel
                                    control={<Switch checked={dialog.withLogin} onChange={(e) => setDialog({ ...dialog, withLogin: e.target.checked })} />}
                                    label="Create rider app login"
                                />
                            </Grid>
                            {dialog.withLogin && <>
                                <Grid item xs={12} sm={4}><TextField label="Username" fullWidth value={dialog.owner.username} onChange={setOwner("username")} /></Grid>
                                <Grid item xs={12} sm={4}><TextField label="Email" fullWidth value={dialog.owner.email} onChange={setOwner("email")} /></Grid>
                                <Grid item xs={12} sm={4}><TextField label="Password" type="password" fullWidth value={dialog.owner.password} onChange={setOwner("password")} /></Grid>
                            </>}
                        </Grid>
                    )}
                </DialogContent>
                <DialogActions>
                    <Button onClick={() => setDialog(null)}>Cancel</Button>
                    <Button variant="contained" onClick={create}>Create</Button>
                </DialogActions>
            </Dialog>

            <Dialog open={!!pwDialog} onClose={() => setPwDialog(null)} maxWidth="xs" fullWidth>
                <DialogTitle>Set password</DialogTitle>
                <DialogContent>
                    {pwDialog && (
                        <Stack spacing={2} sx={{ mt: 1 }}>
                            <TextField
                                label="Username" fullWidth value={pwDialog.username}
                                InputProps={{
                                    readOnly: true,
                                    endAdornment: (
                                        <InputAdornment position="end">
                                            <IconButton size="small" onClick={() => copy(pwDialog.username, "Username")}>
                                                <ContentCopyIcon fontSize="inherit" />
                                            </IconButton>
                                        </InputAdornment>
                                    ),
                                }}
                            />
                            <TextField
                                label="New password" fullWidth autoFocus
                                value={pwDialog.password}
                                onChange={(e) => setPwDialog({ ...pwDialog, password: e.target.value })}
                                helperText="At least 8 characters. Hand this to the rider directly."
                            />
                        </Stack>
                    )}
                </DialogContent>
                <DialogActions>
                    <Button onClick={() => setPwDialog(null)}>Cancel</Button>
                    <Button variant="contained" onClick={resetPassword}>Save</Button>
                </DialogActions>
            </Dialog>
        </Box>
    );
}
