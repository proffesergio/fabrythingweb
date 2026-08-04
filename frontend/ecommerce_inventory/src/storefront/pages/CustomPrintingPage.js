import React, { useEffect, useState } from 'react';
import {
    Box, Container, Typography, Grid, Card, Tabs, Tab, Button, TextField, MenuItem,
    Chip, IconButton, Stack, CircularProgress, Alert,
} from '@mui/material';
import { Add, Delete, Visibility } from '@mui/icons-material';
import { useNavigate } from 'react-router-dom';
import useApi from '../../hooks/APIHandler';
import { isAuthenticated } from '../../utils/Helper';
import PrintCatalogue from './printing/PrintCatalogue';

const STATUS_COLORS = {
    SUBMITTED: 'default', IN_DESIGN: 'info', PROOF_READY: 'warning',
    REVISION_REQUESTED: 'warning', APPROVED: 'success', IN_PRODUCTION: 'secondary',
    READY: 'primary', COMPLETED: 'success', CANCELLED: 'error',
};

const EMPTY_ROSTER_LINE = { player_name: '', number: '', size: '', quantity: 1 };

// Custom-print storefront entry point: a brief-submission form (the primary
// path -- the owner draws the artwork from this brief) plus the customer's
// own request history. This is NOT an upload-and-print tool -- the optional
// reference image is just a hint for the owner, not the final artwork.
export default function CustomPrintingPage() {
    const [tab, setTab] = useState(0);
    const { callApi, loading } = useApi();
    const navigate = useNavigate();
    const loggedIn = isAuthenticated();

    const [presets, setPresets] = useState([]);
    const [areas, setAreas] = useState([]);
    const [requests, setRequests] = useState([]);

    const [form, setForm] = useState({
        preset: '', color: '', size: '', quantity: 1, brief: '', print_areas: [],
    });
    const [isTeamOrder, setIsTeamOrder] = useState(false);
    const [rosterLines, setRosterLines] = useState([{ ...EMPTY_ROSTER_LINE }]);
    const [refFiles, setRefFiles] = useState([]);
    const [quote, setQuote] = useState(null);
    const [submitting, setSubmitting] = useState(false);
    const [formError, setFormError] = useState('');

    useEffect(() => {
        (async () => {
            const res = await callApi({ url: 'print/presets/' });
            if (res?.data?.data) setPresets(res.data.data);
            const res2 = await callApi({ url: 'print/print-areas/' });
            if (res2?.data?.data) setAreas(res2.data.data);
        })();
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, []);

    useEffect(() => {
        if (loggedIn && tab === 1) fetchRequests();
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [loggedIn, tab]);

    const fetchRequests = async () => {
        const res = await callApi({ url: 'print/requests/' });
        if (res?.data?.data) setRequests(res.data.data);
    };

    useEffect(() => {
        (async () => {
            if (!form.preset && form.print_areas.length === 0) { setQuote(null); return; }
            const res = await callApi({
                url: 'print/quote/', method: 'POST',
                body: { preset: form.preset || null, print_areas: form.print_areas, quantity: form.quantity || 1 },
            });
            if (res?.data?.data) setQuote(res.data.data);
        })();
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [form.preset, form.print_areas, form.quantity]);

    const selectedPreset = presets.find((p) => p.id === form.preset);

    const toggleArea = (id) => {
        setForm((f) => ({
            ...f,
            print_areas: f.print_areas.includes(id) ? f.print_areas.filter((a) => a !== id) : [...f.print_areas, id],
        }));
    };

    const updateRosterLine = (idx, patch) => {
        setRosterLines((prev) => prev.map((l, i) => (i === idx ? { ...l, ...patch } : l)));
    };
    const addRosterLine = () => setRosterLines((prev) => [...prev, { ...EMPTY_ROSTER_LINE }]);
    const removeRosterLine = (idx) => setRosterLines((prev) => prev.filter((_, i) => i !== idx));

    const handleSubmit = async () => {
        if (!loggedIn) { navigate('/auth/login'); return; }
        setFormError('');
        if (!form.brief.trim()) { setFormError('Please describe what you want printed.'); return; }

        setSubmitting(true);
        const payload = {
            preset: form.preset || null,
            color: form.color,
            size: form.size,
            quantity: form.quantity || 1,
            brief: form.brief,
            print_areas: form.print_areas,
        };
        if (isTeamOrder) {
            payload.roster_lines = rosterLines.filter((l) => l.player_name.trim());
        }
        const res = await callApi({ url: 'print/requests/', method: 'POST', body: payload, rawError: true });
        if (res?.status === 201) {
            const requestId = res.data.data.id;
            for (const file of refFiles) {
                const fd = new FormData();
                fd.append('image', file);
                await callApi({ url: `print/requests/${requestId}/reference-images/`, method: 'POST', body: fd, header: { 'Content-Type': 'multipart/form-data' } });
            }
            navigate(`/custom-printing/requests/${requestId}`);
        } else {
            setFormError(res?.data?.message || 'Could not submit your request. Please try again.');
        }
        setSubmitting(false);
    };

    return (
        <Container maxWidth="lg" sx={{ py: 3 }}>
            <Typography variant="h4" sx={{ mb: 1 }}>Custom Printing</Typography>
            <Typography variant="body1" color="text.secondary" sx={{ mb: 3 }}>
                Tell us what you need -- a team jersey, a logo tee, anything. Our designer will draw it up
                and send you a proof to approve before we print.
            </Typography>

            <PrintCatalogue />

            <Tabs value={tab} onChange={(_, v) => setTab(v)} sx={{ mb: 3 }}>
                <Tab label="Submit a Request" />
                <Tab label="My Requests" />
            </Tabs>

            {tab === 0 && (
                <Card sx={{ p: 3, maxWidth: 700 }}>
                    {formError && <Alert severity="error" sx={{ mb: 2 }}>{formError}</Alert>}

                    <TextField
                        select fullWidth label="Garment" value={form.preset}
                        onChange={(e) => setForm({ ...form, preset: e.target.value })}
                        sx={{ mb: 2 }}
                    >
                        <MenuItem value="">Not sure yet / owner will advise</MenuItem>
                        {presets.map((p) => (
                            <MenuItem key={p.id} value={p.id}>{p.name} (৳{p.base_price})</MenuItem>
                        ))}
                    </TextField>

                    <Grid container spacing={2} sx={{ mb: 2 }}>
                        <Grid item xs={6}>
                            <TextField fullWidth label="Colour" value={form.color}
                                onChange={(e) => setForm({ ...form, color: e.target.value })} />
                        </Grid>
                        <Grid item xs={6}>
                            <TextField
                                select fullWidth label="Size" value={form.size}
                                onChange={(e) => setForm({ ...form, size: e.target.value })}
                            >
                                <MenuItem value="">--</MenuItem>
                                {(selectedPreset?.available_sizes?.length
                                    ? selectedPreset.available_sizes
                                    : ['XS', 'S', 'M', 'L', 'XL', 'XXL', 'XXXL', 'FREE']
                                ).map((s) => <MenuItem key={s} value={s}>{s}</MenuItem>)}
                            </TextField>
                        </Grid>
                    </Grid>

                    <Typography variant="subtitle2" sx={{ mb: 1 }}>Print locations</Typography>
                    <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1, mb: 2 }}>
                        {areas.map((a) => (
                            <Chip
                                key={a.id} label={`${a.name} (+৳${a.price})`}
                                color={form.print_areas.includes(a.id) ? 'primary' : 'default'}
                                onClick={() => toggleArea(a.id)}
                                variant={form.print_areas.includes(a.id) ? 'filled' : 'outlined'}
                            />
                        ))}
                    </Box>

                    <TextField
                        fullWidth type="number" label="Quantity" value={form.quantity}
                        inputProps={{ min: 1 }}
                        onChange={(e) => setForm({ ...form, quantity: Math.max(1, parseInt(e.target.value, 10) || 1) })}
                        sx={{ mb: 2 }}
                    />

                    <TextField
                        fullWidth multiline minRows={4} label="Describe what you want"
                        placeholder="e.g. Team name 'Thunder FC', navy blue jerseys, player names + numbers on the back, our logo on the front."
                        value={form.brief}
                        onChange={(e) => setForm({ ...form, brief: e.target.value })}
                        sx={{ mb: 2 }}
                    />

                    <Box sx={{ mb: 2 }}>
                        <Button variant="outlined" component="label">
                            Attach reference image (optional)
                            <input
                                type="file" hidden multiple accept="image/*"
                                onChange={(e) => setRefFiles(Array.from(e.target.files || []))}
                            />
                        </Button>
                        {refFiles.length > 0 && (
                            <Typography variant="caption" sx={{ ml: 1 }}>{refFiles.length} file(s) selected</Typography>
                        )}
                    </Box>

                    <Box sx={{ mb: 2 }}>
                        <Button size="small" onClick={() => setIsTeamOrder((v) => !v)}>
                            {isTeamOrder ? 'Remove team roster' : '+ This is a team order (add player names/numbers)'}
                        </Button>
                        {isTeamOrder && (
                            <Box sx={{ mt: 1 }}>
                                {rosterLines.map((line, idx) => (
                                    <Stack key={idx} direction="row" spacing={1} sx={{ mb: 1 }} alignItems="center">
                                        <TextField size="small" label="Player" value={line.player_name}
                                            onChange={(e) => updateRosterLine(idx, { player_name: e.target.value })} />
                                        <TextField size="small" label="#" sx={{ width: 70 }} value={line.number}
                                            onChange={(e) => updateRosterLine(idx, { number: e.target.value })} />
                                        <TextField size="small" label="Size" sx={{ width: 90 }} value={line.size}
                                            onChange={(e) => updateRosterLine(idx, { size: e.target.value })} />
                                        <TextField size="small" type="number" label="Qty" sx={{ width: 80 }} value={line.quantity}
                                            onChange={(e) => updateRosterLine(idx, { quantity: parseInt(e.target.value, 10) || 1 })} />
                                        <IconButton size="small" onClick={() => removeRosterLine(idx)}><Delete fontSize="small" /></IconButton>
                                    </Stack>
                                ))}
                                <Button size="small" startIcon={<Add />} onClick={addRosterLine}>Add player</Button>
                            </Box>
                        )}
                    </Box>

                    {quote && (
                        <Alert severity="info" sx={{ mb: 2 }}>
                            Estimated: ৳{quote.unit_price} / item x {quote.quantity} = ৳{quote.subtotal}
                            {Number(quote.discount_percent) > 0 && ` (${quote.discount_percent}% bulk discount applied)`}
                            {' -> '}<strong>৳{quote.total_price}</strong> total. Final price is confirmed by our team.
                        </Alert>
                    )}

                    <Button
                        variant="contained" size="large" fullWidth
                        onClick={handleSubmit} disabled={submitting || loading}
                    >
                        {submitting ? <CircularProgress size={22} /> : (loggedIn ? 'Submit Request' : 'Log in to Submit')}
                    </Button>
                </Card>
            )}

            {tab === 1 && (
                <Box>
                    {!loggedIn ? (
                        <Card sx={{ p: 4, textAlign: 'center' }}>
                            <Typography color="text.secondary" sx={{ mb: 2 }}>Log in to see your print requests.</Typography>
                            <Button variant="contained" onClick={() => navigate('/auth/login')}>Log In</Button>
                        </Card>
                    ) : requests.length === 0 ? (
                        <Card sx={{ p: 4, textAlign: 'center' }}>
                            <Typography color="text.secondary">No print requests yet.</Typography>
                        </Card>
                    ) : (
                        requests.map((r) => (
                            <Card key={r.id} sx={{ p: 2, mb: 2 }}>
                                <Grid container spacing={2} alignItems="center">
                                    <Grid item xs={12} sm={5}>
                                        <Typography variant="subtitle2" fontWeight={700}>
                                            {r.preset_name || r.product_name || 'Custom print'} x{r.quantity}
                                        </Typography>
                                        <Typography variant="caption" color="text.secondary">
                                            {new Date(r.created_at).toLocaleDateString()}
                                        </Typography>
                                    </Grid>
                                    <Grid item xs={6} sm={3}>
                                        <Chip label={r.status.replace(/_/g, ' ')} size="small" color={STATUS_COLORS[r.status] || 'default'} />
                                    </Grid>
                                    <Grid item xs={6} sm={2}>
                                        <Typography variant="body2">
                                            {r.agreed_total_price ? `৳${r.agreed_total_price}` : '--'}
                                        </Typography>
                                    </Grid>
                                    <Grid item xs={12} sm={2}>
                                        <Button size="small" startIcon={<Visibility />}
                                            onClick={() => navigate(`/custom-printing/requests/${r.id}`)}>
                                            Details
                                        </Button>
                                    </Grid>
                                </Grid>
                            </Card>
                        ))
                    )}
                </Box>
            )}
        </Container>
    );
}
