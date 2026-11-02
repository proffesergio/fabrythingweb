import React, { useCallback, useEffect, useRef, useState } from 'react';
import { Box, Typography, TextField, IconButton, Stack } from '@mui/material';
import SendIcon from '@mui/icons-material/Send';
import useApi from '../../hooks/APIHandler';

// Polling cadence -- same rationale as ChatWidget.js (no websocket support on
// Render's free tier): 4s while the panel is visible on screen.
const POLL_MS = 4000;

function formatTime(iso) {
    if (!iso) return '';
    try { return new Date(iso).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }); }
    catch { return ''; }
}

/**
 * Embedded revision conversation for a single print request's PRINT_JOB
 * chat thread. Reuses the same /api/chat/threads/<id>/... endpoints
 * ChatWidget uses -- this is deliberately NOT a second messaging system,
 * just a narrower view onto the same thread pinned to this request.
 */
export default function PrintRequestChatPanel({ threadId }) {
    const { callApi } = useApi();
    const [messages, setMessages] = useState([]);
    const [draft, setDraft] = useState('');
    const [sending, setSending] = useState(false);
    const latestIdRef = useRef(null);
    const endRef = useRef(null);

    const fetchMessages = useCallback(async ({ initial } = {}) => {
        if (!threadId || document.visibilityState !== 'visible') return;
        const after = initial ? null : latestIdRef.current;
        const res = await callApi({
            url: `chat/threads/${threadId}/messages/${after != null ? `?after=${after}` : ''}`,
            rawError: true,
        });
        if (res?.status !== 200) return;
        const { messages: fresh, latest_id: latestId } = res.data.data;
        if (latestId != null) latestIdRef.current = latestId;
        if (initial) setMessages(fresh);
        else if (fresh.length) setMessages((prev) => [...prev, ...fresh]);
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [threadId]);

    useEffect(() => {
        if (!threadId) return undefined;
        latestIdRef.current = null;
        setMessages([]);
        fetchMessages({ initial: true });
        callApi({ url: `chat/threads/${threadId}/read/`, method: 'POST' });
        const id = setInterval(() => {
            if (document.visibilityState === 'visible') fetchMessages();
        }, POLL_MS);
        return () => clearInterval(id);
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [threadId, fetchMessages]);

    useEffect(() => { endRef.current?.scrollIntoView({ block: 'end' }); }, [messages]);

    const send = async () => {
        const body = draft.trim();
        if (!body || !threadId) return;
        setSending(true);
        setDraft('');
        const res = await callApi({
            url: `chat/threads/${threadId}/messages/`, method: 'POST', body: { body }, rawError: true,
        });
        setSending(false);
        if (res?.status === 201) {
            latestIdRef.current = res.data.data.id;
            setMessages((prev) => [...prev, res.data.data]);
        }
    };

    if (!threadId) return null;

    return (
        <Box sx={{ border: '1px solid', borderColor: 'divider', borderRadius: 2, display: 'flex', flexDirection: 'column', height: 360 }}>
            <Box sx={{ p: 1.5, borderBottom: '1px solid', borderColor: 'divider' }}>
                <Typography variant="subtitle2">Design conversation</Typography>
            </Box>
            <Box sx={{ flex: 1, overflowY: 'auto', p: 1.5, display: 'flex', flexDirection: 'column', gap: 1 }}>
                {messages.length === 0 && (
                    <Typography variant="body2" color="text.secondary" sx={{ textAlign: 'center', py: 3 }}>
                        No messages yet. Ask a question about your design here.
                    </Typography>
                )}
                {messages.map((m) => {
                    if (m.sender_role === 'SYSTEM') {
                        return (
                            <Box key={m.id} sx={{ alignSelf: 'center' }}>
                                <Typography variant="caption" sx={{ color: 'text.secondary', fontStyle: 'italic' }}>
                                    {m.body}
                                </Typography>
                            </Box>
                        );
                    }
                    const isCustomer = m.sender_role === 'CUSTOMER';
                    return (
                        <Box key={m.id} sx={{ alignSelf: isCustomer ? 'flex-end' : 'flex-start', maxWidth: '80%' }}>
                            <Box sx={{
                                bgcolor: isCustomer ? 'primary.main' : 'action.hover',
                                color: isCustomer ? 'primary.contrastText' : 'text.primary',
                                borderRadius: 2, px: 1.5, py: 1,
                            }}>
                                <Typography variant="body2" sx={{ whiteSpace: 'pre-wrap' }}>{m.body}</Typography>
                            </Box>
                            <Typography variant="caption" color="text.secondary" sx={{ px: 0.5 }}>
                                {formatTime(m.created_at)}
                            </Typography>
                        </Box>
                    );
                })}
                <div ref={endRef} />
            </Box>
            <Stack direction="row" spacing={1} sx={{ p: 1.5, borderTop: '1px solid', borderColor: 'divider' }}>
                <TextField
                    fullWidth size="small" placeholder="Type a message…"
                    value={draft} onChange={(e) => setDraft(e.target.value)}
                    onKeyDown={(e) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); send(); } }}
                />
                <IconButton color="primary" disabled={sending || !draft.trim()} onClick={send} aria-label="Send message">
                    <SendIcon />
                </IconButton>
            </Stack>
        </Box>
    );
}
