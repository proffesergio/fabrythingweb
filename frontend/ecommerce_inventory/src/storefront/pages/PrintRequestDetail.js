import React, { useCallback, useEffect, useState } from 'react';
import {
    Box, Container, Typography, Grid, Card, Chip, Divider, Button, TextField,
    CircularProgress, Alert, Stack,
} from '@mui/material';
import { useParams, useNavigate } from 'react-router-dom';
import useApi from '../../hooks/APIHandler';
import PrintRequestChatPanel from '../components/PrintRequestChatPanel';

const STATUS_COLORS = {
    SUBMITTED: 'default', IN_DESIGN: 'info', PROOF_READY: 'warning',
    REVISION_REQUESTED: 'warning', APPROVED: 'success', IN_PRODUCTION: 'secondary',
    READY: 'primary', COMPLETED: 'success', CANCELLED: 'error',
};

// Customer-facing detail view for a single print request: the brief, the
// garment, every proof version with Approve/Request-revision actions on the
// latest pending one, the roster (for team orders) and the linked design
// chat. This -- not an upload form -- is where the proof-approval loop lives.
export default function PrintRequestDetail() {
    const { id } = useParams();
    const navigate = useNavigate();
    const { callApi, loading } = useApi();

    const [request, setRequest] = useState(null);
    const [feedback, setFeedback] = useState('');
    const [revisingProofId, setRevisingProofId] = useState(null);
    const [error, setError] = useState('');
    const [uploading, setUploading] = useState(false);

    const fetchRequest = useCallback(async () => {
        const res = await callApi({ url: `print/requests/${id}/`, rawError: true });
        if (res?.status === 200) setRequest(res.data.data);
        else setError('Could not load this request.');
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [id]);

    useEffect(() => { fetchRequest(); }, [fetchRequest]);

    const latestProof = request?.proofs?.[0]; // ordering=["-version"] on the backend
    const canDecide = latestProof && latestProof.decision === 'PENDING'
        && ['PROOF_READY'].includes(request?.status);

    const decide = async (proofId, decision) => {
        setError('');
        const body = { decision };
        if (decision === 'REVISION_REQUESTED') {
            if (!feedback.trim()) { setError('Please describe what needs to change.'); return; }
            body.feedback = feedback;
        }
        const res = await callApi({
            url: `print/requests/${id}/proofs/${proofId}/decision/`, method: 'POST', body, rawError: true,
        });
        if (res?.status === 200) {
            setRequest(res.data.data);
            setFeedback('');
            setRevisingProofId(null);
        } else {
            setError(res?.data?.message || 'Could not record your decision.');
        }
    };

    const uploadReferenceImage = async (file) => {
        if (!file) return;
        setUploading(true);
        const fd = new FormData();
        fd.append('image', file);
        const res = await callApi({
            url: `print/requests/${id}/reference-images/`, method: 'POST', body: fd,
            header: { 'Content-Type': 'multipart/form-data' }, rawError: true,
        });
        setUploading(false);
        if (res?.status === 201) fetchRequest();
    };

    if (loading && !request) {
        return <Container sx={{ py: 4, textAlign: 'center' }}><CircularProgress /></Container>;
    }
    if (!request) {
        return (
            <Container sx={{ py: 4 }}>
                <Alert severity="error">This print request could not be found.</Alert>
                <Button sx={{ mt: 2 }} onClick={() => navigate('/custom-printing')}>Back</Button>
            </Container>
        );
    }

    return (
        <Container maxWidth="lg" sx={{ py: 3 }}>
            <Button onClick={() => navigate('/custom-printing')} sx={{ mb: 2 }}>&larr; Back to Custom Printing</Button>

            <Grid container spacing={3}>
                <Grid item xs={12} md={7}>
                    <Card sx={{ p: 3, mb: 3 }}>
                        <Stack direction="row" justifyContent="space-between" alignItems="flex-start">
                            <Typography variant="h5">Request #{request.id}</Typography>
                            <Chip label={request.status.replace(/_/g, ' ')} color={STATUS_COLORS[request.status] || 'default'} />
                        </Stack>
                        <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
                            {request.product_name || request.preset_name || 'Custom item'}
                            {request.color ? ` · ${request.color}` : ''}{request.size ? ` · ${request.size}` : ''} · Qty {request.quantity}
                        </Typography>
                        <Divider sx={{ my: 2 }} />
                        <Typography variant="subtitle2">Brief</Typography>
                        <Typography variant="body2" sx={{ whiteSpace: 'pre-wrap', mb: 2 }}>{request.brief}</Typography>

                        <Typography variant="subtitle2">Price</Typography>
                        {request.agreed_unit_price != null ? (
                            <Typography variant="body2">
                                Agreed: ৳{request.agreed_unit_price} / item &times; {request.quantity} = <strong>৳{request.agreed_total_price}</strong>
                            </Typography>
                        ) : request.quoted_unit_price != null ? (
                            <Typography variant="body2">
                                Quoted: ৳{request.quoted_unit_price} / item (subject to change until approved)
                            </Typography>
                        ) : (
                            <Typography variant="body2" color="text.secondary">Not yet quoted by our team.</Typography>
                        )}

                        {request.roster_lines?.length > 0 && (
                            <>
                                <Divider sx={{ my: 2 }} />
                                <Typography variant="subtitle2" sx={{ mb: 1 }}>Roster</Typography>
                                {request.roster_lines.map((l) => (
                                    <Typography key={l.id} variant="body2">
                                        {l.player_name} {l.number ? `#${l.number}` : ''} — {l.size} &times;{l.quantity}
                                    </Typography>
                                ))}
                            </>
                        )}

                        <Divider sx={{ my: 2 }} />
                        <Typography variant="subtitle2" sx={{ mb: 1 }}>Reference images</Typography>
                        <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap', mb: 1 }}>
                            {(request.reference_images || []).map((url) => (
                                <Box key={url} component="img" src={url} alt="Reference"
                                    sx={{ width: 90, height: 90, objectFit: 'cover', borderRadius: 1, border: '1px solid', borderColor: 'divider' }} />
                            ))}
                        </Box>
                        <Button size="small" component="label" disabled={uploading}>
                            {uploading ? 'Uploading…' : 'Add reference image'}
                            <input type="file" hidden accept="image/*"
                                onChange={(e) => uploadReferenceImage(e.target.files?.[0])} />
                        </Button>
                    </Card>

                    <Card sx={{ p: 3 }}>
                        <Typography variant="subtitle1" sx={{ mb: 2 }}>Proofs</Typography>
                        {(!request.proofs || request.proofs.length === 0) && (
                            <Typography variant="body2" color="text.secondary">
                                No proof yet — our designer is working on it.
                            </Typography>
                        )}
                        {request.proofs?.map((proof) => (
                            <Box key={proof.id} sx={{ mb: 3 }}>
                                <Stack direction="row" justifyContent="space-between" alignItems="center">
                                    <Typography variant="subtitle2">Version {proof.version}</Typography>
                                    <Chip
                                        size="small"
                                        label={proof.decision.replace(/_/g, ' ')}
                                        color={proof.decision === 'APPROVED' ? 'success' : proof.decision === 'REVISION_REQUESTED' ? 'warning' : 'default'}
                                    />
                                </Stack>
                                <Box component="img" src={proof.image} alt={`Proof v${proof.version}`}
                                    sx={{ maxWidth: '100%', maxHeight: 320, borderRadius: 1, mt: 1, border: '1px solid', borderColor: 'divider' }} />
                                {proof.note && <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>{proof.note}</Typography>}
                                {proof.customer_feedback && (
                                    <Alert severity="info" sx={{ mt: 1 }}>Your feedback: {proof.customer_feedback}</Alert>
                                )}

                                {canDecide && proof.id === latestProof.id && (
                                    <Box sx={{ mt: 2 }}>
                                        {error && <Alert severity="error" sx={{ mb: 1 }}>{error}</Alert>}
                                        {revisingProofId === proof.id ? (
                                            <Stack spacing={1}>
                                                <TextField
                                                    multiline minRows={2} size="small" label="What needs to change?"
                                                    value={feedback} onChange={(e) => setFeedback(e.target.value)}
                                                />
                                                <Stack direction="row" spacing={1}>
                                                    <Button variant="contained" onClick={() => decide(proof.id, 'REVISION_REQUESTED')}>
                                                        Send revision request
                                                    </Button>
                                                    <Button onClick={() => setRevisingProofId(null)}>Cancel</Button>
                                                </Stack>
                                            </Stack>
                                        ) : (
                                            <Stack direction="row" spacing={1}>
                                                <Button variant="contained" color="success" onClick={() => decide(proof.id, 'APPROVED')}>
                                                    Approve
                                                </Button>
                                                <Button variant="outlined" onClick={() => setRevisingProofId(proof.id)}>
                                                    Request revision
                                                </Button>
                                            </Stack>
                                        )}
                                    </Box>
                                )}
                            </Box>
                        ))}
                    </Card>
                </Grid>

                <Grid item xs={12} md={5}>
                    <PrintRequestChatPanel threadId={request.chat_thread} />
                </Grid>
            </Grid>
        </Container>
    );
}
