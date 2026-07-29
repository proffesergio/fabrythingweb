import React, { useCallback, useEffect, useRef, useState } from 'react';
import {
    Fab, Badge, Tooltip, Drawer, Box, Typography, IconButton, List, ListItemButton,
    ListItemText, Chip, TextField, Button, MenuItem, Divider, Stack, CircularProgress,
} from '@mui/material';
import ChatBubbleOutlineIcon from '@mui/icons-material/ChatBubbleOutline';
import CloseIcon from '@mui/icons-material/Close';
import ArrowBackIcon from '@mui/icons-material/ArrowBack';
import SendIcon from '@mui/icons-material/Send';
import useApi from '../../hooks/APIHandler';
import { isAuthenticated } from '../../utils/Helper';

// Kinds a customer can pick when opening a conversation. PRINT_JOB is not
// listed -- nothing creates those threads yet (see chat/models.py + docs/LIVE_CHAT.md);
// FOOD_ORDER isn't offered here either since this widget lives on the store
// side, not the /food frontend.
const KIND_OPTIONS = [
    { value: 'GENERAL', label: 'General question' },
    { value: 'ORDER', label: 'About a store order' },
    { value: 'EMERGENCY', label: 'Emergency delivery request' },
];

function kindLabel(kind) {
    return KIND_OPTIONS.find((k) => k.value === kind)?.label || kind;
}

// Polling cadence, deliberately not "every second" -- see docs/LIVE_CHAT.md
// for why: this is polling, not a websocket, and a tighter interval buys
// nothing but load on a Render free-tier instance.
const OPEN_POLL_MS = 4000;        // new messages, while a conversation is open
const IDLE_BADGE_POLL_MS = 45000; // unread badge, while the panel is closed

function fabSx(bottom) {
    return {
        position: 'fixed',
        right: { xs: 16, md: 24 },
        bottom: bottom ?? { xs: 16, md: 24 },
        zIndex: (theme) => theme.zIndex.speedDial,
        minWidth: 44,
        minHeight: 44,
    };
}

// Floating live-chat launcher + panel. Every network call here hits
// /api/chat/... (chat/urls.py on the backend) with rawError:true so a
// non-2xx response is visible instead of silently rendering as "nothing
// happened" -- see utils/config.js / hooks/APIHandler.js's callApi contract.
export default function ChatWidget({ bottom }) {
    const { callApi } = useApi();
    const loggedIn = isAuthenticated();

    const [open, setOpen] = useState(false);
    const [unread, setUnread] = useState(0);
    const [threads, setThreads] = useState(null); // null = not loaded yet
    const [activeThread, setActiveThread] = useState(null);
    const [messages, setMessages] = useState([]);
    const [composerKind, setComposerKind] = useState('GENERAL');
    const [draft, setDraft] = useState('');
    const [sending, setSending] = useState(false);
    const [creating, setCreating] = useState(false);

    const latestIdRef = useRef(null);
    const messagesEndRef = useRef(null);

    const refreshBadge = useCallback(async () => {
        const res = await callApi({ url: 'chat/threads/updates/' });
        if (res?.data?.data) setUnread(res.data.data.total_unread || 0);
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, []);

    // ── Background badge poll: only while logged in and the panel is
    // closed, and only while this tab is the visible one. ──────────────────
    useEffect(() => {
        if (!loggedIn || open) return undefined;

        let cancelled = false;
        const tick = () => { if (!cancelled && document.visibilityState === 'visible') refreshBadge(); };
        tick();
        const id = setInterval(tick, IDLE_BADGE_POLL_MS);
        return () => { cancelled = true; clearInterval(id); };
    }, [loggedIn, open, refreshBadge]);

    // ── Thread list, (re)loaded whenever the panel opens. ───────────────────
    const loadThreads = useCallback(async () => {
        const res = await callApi({ url: 'chat/threads/', rawError: true });
        setThreads(res?.status === 200 ? res.data.data : []);
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, []);

    useEffect(() => {
        if (open && loggedIn) loadThreads();
    }, [open, loggedIn, loadThreads]);

    // ── Messages: initial load + polling while a thread is open. ───────────
    const fetchMessages = useCallback(async (threadId, { initial } = {}) => {
        if (document.visibilityState !== 'visible') return;
        const after = initial ? null : latestIdRef.current;
        const res = await callApi({
            url: `chat/threads/${threadId}/messages/${after != null ? `?after=${after}` : ''}`,
            rawError: true,
        });
        if (res?.status !== 200) return;
        const { messages: newMessages, latest_id: latestId } = res.data.data;
        if (latestId != null) latestIdRef.current = latestId;
        if (initial) setMessages(newMessages);
        else if (newMessages.length) setMessages((prev) => [...prev, ...newMessages]);
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, []);

    useEffect(() => {
        if (!open || !activeThread) return undefined;

        latestIdRef.current = null;
        setMessages([]);
        setDraft('');
        fetchMessages(activeThread.id, { initial: true });
        callApi({ url: `chat/threads/${activeThread.id}/read/`, method: 'POST' }).then(refreshBadge);

        const id = setInterval(() => {
            if (document.visibilityState === 'visible') fetchMessages(activeThread.id);
        }, OPEN_POLL_MS);
        return () => clearInterval(id);
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [open, activeThread?.id]);

    useEffect(() => {
        messagesEndRef.current?.scrollIntoView({ block: 'end' });
    }, [messages]);

    const openPanel = () => setOpen(true);
    const closePanel = () => { setOpen(false); setActiveThread(null); };

    const send = async () => {
        if (!draft.trim() || !activeThread) return;
        setSending(true);
        const res = await callApi({
            url: `chat/threads/${activeThread.id}/messages/`, method: 'POST',
            body: { body: draft.trim() }, rawError: true,
        });
        setSending(false);
        if (res?.status === 201) {
            setDraft('');
            setMessages((prev) => [...prev, res.data.data]);
            latestIdRef.current = res.data.data.id;
        }
    };

    const startThread = async () => {
        if (!draft.trim()) return;
        setCreating(true);
        const res = await callApi({
            url: 'chat/threads/', method: 'POST',
            body: { kind: composerKind, body: draft.trim() }, rawError: true,
        });
        setCreating(false);
        if (res?.status === 201) {
            const thread = res.data.data;
            setThreads((prev) => [thread, ...(prev || [])]);
            setActiveThread(thread);
        }
    };

    if (!loggedIn) {
        // The launcher is always visible so the option is discoverable, but
        // every chat endpoint requires an authenticated customer -- the panel
        // just points an anonymous visitor at login instead of pretending to
        // open a conversation it can't create.
        return (
            <>
                <Tooltip title="Chat with us">
                    <Fab onClick={openPanel} aria-label="Chat with us" color="secondary" sx={fabSx(bottom)}>
                        <ChatBubbleOutlineIcon />
                    </Fab>
                </Tooltip>
                <Drawer anchor="right" open={open} onClose={closePanel}>
                    <Box sx={{ width: { xs: '100vw', sm: 360 }, p: 3 }}>
                        <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 2 }}>
                            <Typography variant="h6">Live chat</Typography>
                            <IconButton onClick={closePanel} aria-label="Close"><CloseIcon /></IconButton>
                        </Stack>
                        <Typography variant="body2" sx={{ mb: 2 }}>
                            Please log in to start a conversation with us.
                        </Typography>
                        <Button variant="contained" href="/auth/login">Log in</Button>
                    </Box>
                </Drawer>
            </>
        );
    }

    return (
        <>
            <Tooltip title="Chat with us">
                <Fab onClick={openPanel} aria-label="Chat with us" color="secondary" sx={fabSx(bottom)}>
                    <Badge badgeContent={unread} color="error" max={99}>
                        <ChatBubbleOutlineIcon />
                    </Badge>
                </Fab>
            </Tooltip>

            <Drawer anchor="right" open={open} onClose={closePanel}>
                <Box sx={{ width: { xs: '100vw', sm: 380 }, height: '100%', display: 'flex', flexDirection: 'column' }}>
                    <Stack direction="row" alignItems="center" spacing={1}
                        sx={{ p: 2, borderBottom: '1px solid', borderColor: 'divider' }}>
                        {activeThread && (
                            <IconButton size="small" onClick={() => setActiveThread(null)} aria-label="Back to conversations">
                                <ArrowBackIcon fontSize="small" />
                            </IconButton>
                        )}
                        <Typography variant="h6" sx={{ flex: 1 }}>
                            {activeThread ? kindLabel(activeThread.kind) : 'Live chat'}
                        </Typography>
                        <IconButton size="small" onClick={closePanel} aria-label="Close">
                            <CloseIcon fontSize="small" />
                        </IconButton>
                    </Stack>

                    {!activeThread && (
                        <Box sx={{ flex: 1, overflowY: 'auto', p: 2 }}>
                            <Typography variant="subtitle2" sx={{ mb: 1 }}>Start a new conversation</Typography>
                            <TextField
                                select fullWidth size="small" label="What's this about?"
                                value={composerKind} onChange={(e) => setComposerKind(e.target.value)}
                                sx={{ mb: 1 }}
                            >
                                {KIND_OPTIONS.map((k) => <MenuItem key={k.value} value={k.value}>{k.label}</MenuItem>)}
                            </TextField>
                            <TextField
                                fullWidth multiline minRows={2} size="small"
                                placeholder="Tell us what you need..."
                                value={draft} onChange={(e) => setDraft(e.target.value)}
                                sx={{ mb: 1 }}
                            />
                            <Button fullWidth variant="contained" disabled={creating || !draft.trim()} onClick={startThread}>
                                {creating ? <CircularProgress size={20} /> : 'Send'}
                            </Button>

                            <Divider sx={{ my: 2 }} />
                            <Typography variant="subtitle2" sx={{ mb: 1 }}>Your conversations</Typography>
                            {threads === null && <Typography variant="body2" color="text.secondary">Loading…</Typography>}
                            {threads?.length === 0 && (
                                <Typography variant="body2" color="text.secondary">No conversations yet.</Typography>
                            )}
                            <List disablePadding>
                                {threads?.map((t) => (
                                    <ListItemButton key={t.id} onClick={() => setActiveThread(t)} sx={{ borderRadius: 1, mb: 0.5 }}>
                                        <ListItemText
                                            primary={kindLabel(t.kind)}
                                            secondary={t.status === 'CLOSED' ? 'Closed' : 'Open'}
                                        />
                                        {t.unread_count > 0 && <Chip size="small" color="error" label={t.unread_count} />}
                                    </ListItemButton>
                                ))}
                            </List>
                        </Box>
                    )}

                    {activeThread && (
                        <>
                            <Box sx={{ flex: 1, overflowY: 'auto', p: 2, display: 'flex', flexDirection: 'column', gap: 1 }}>
                                {messages.map((m) => (
                                    <Box
                                        key={m.id}
                                        sx={{
                                            alignSelf: m.sender_role === 'CUSTOMER' ? 'flex-end' : 'flex-start',
                                            bgcolor: m.sender_role === 'CUSTOMER' ? 'primary.main' : 'action.hover',
                                            color: m.sender_role === 'CUSTOMER' ? 'primary.contrastText' : 'text.primary',
                                            borderRadius: 2, px: 1.5, py: 1, maxWidth: '80%',
                                        }}
                                    >
                                        {/* Plain text only -- body is never HTML, so it is never
                                            rendered via dangerouslySetInnerHTML. */}
                                        <Typography variant="body2" sx={{ whiteSpace: 'pre-wrap' }}>{m.body}</Typography>
                                    </Box>
                                ))}
                                <div ref={messagesEndRef} />
                            </Box>
                            {activeThread.status === 'CLOSED' ? (
                                <Box sx={{ p: 2, borderTop: '1px solid', borderColor: 'divider' }}>
                                    <Typography variant="body2" color="text.secondary">This conversation is closed.</Typography>
                                </Box>
                            ) : (
                                <Stack direction="row" spacing={1} sx={{ p: 2, borderTop: '1px solid', borderColor: 'divider' }}>
                                    <TextField
                                        fullWidth size="small" placeholder="Type a message…"
                                        value={draft} onChange={(e) => setDraft(e.target.value)}
                                        onKeyDown={(e) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); send(); } }}
                                    />
                                    <IconButton color="primary" disabled={sending || !draft.trim()} onClick={send} aria-label="Send message">
                                        <SendIcon />
                                    </IconButton>
                                </Stack>
                            )}
                        </>
                    )}
                </Box>
            </Drawer>
        </>
    );
}
