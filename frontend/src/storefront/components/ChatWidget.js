import React, { useCallback, useEffect, useRef, useState } from 'react';
import {
    Fab, Badge, Tooltip, Drawer, Box, Typography, IconButton, List, ListItemButton,
    ListItemText, Chip, TextField, Button, MenuItem, Divider, Stack, CircularProgress,
} from '@mui/material';
import ChatBubbleOutlineIcon from '@mui/icons-material/ChatBubbleOutline';
import CloseIcon from '@mui/icons-material/Close';
import ArrowBackIcon from '@mui/icons-material/ArrowBack';
import SendIcon from '@mui/icons-material/Send';
import ForumOutlinedIcon from '@mui/icons-material/ForumOutlined';
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

function formatTime(iso) {
    if (!iso) return '';
    try {
        return new Date(iso).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    } catch {
        return '';
    }
}

// Polling cadence, deliberately not "every second" -- see docs/LIVE_CHAT.md
// for why: this is polling, not a websocket, and a tighter interval buys
// nothing but load on a Render free-tier instance.
const OPEN_POLL_MS = 4000;        // new messages, while a conversation is open
const IDLE_BADGE_POLL_MS = 45000; // unread badge, while the panel is closed

// How long the first-appearance ripple/attention animation runs before easing
// off on its own (roughly 5 pulse cycles at PULSE_DURATION_MS below) -- "live
// chat with us now" should read as an invitation, not a permanent distraction.
const PULSE_EASE_OFF_MS = 13000;
const PULSE_DURATION_S = 2.6;

function launcherBoxSx(bottom) {
    return {
        position: 'fixed',
        right: { xs: 16, md: 24 },
        bottom: bottom ?? { xs: 16, md: 24 },
        zIndex: (theme) => theme.zIndex.speedDial,
    };
}

// Soft ripple ring behind the launcher -- purely decorative (aria-hidden),
// absolutely positioned so it can never shift layout, and gone entirely
// under prefers-reduced-motion. `show` is false once the panel has been
// opened at least once or after PULSE_EASE_OFF_MS, whichever comes first.
function LauncherRing({ show }) {
    if (!show) return null;
    return (
        <Box
            aria-hidden
            sx={{
                position: 'absolute',
                inset: 0,
                borderRadius: '50%',
                border: '2px solid',
                borderColor: 'secondary.main',
                pointerEvents: 'none',
                animation: `chatPulseRing ${PULSE_DURATION_S}s ease-out infinite`,
                '@keyframes chatPulseRing': {
                    '0%': { transform: 'scale(0.85)', opacity: 0.5 },
                    '100%': { transform: 'scale(1.7)', opacity: 0 },
                },
                '@media (prefers-reduced-motion: reduce)': { animation: 'none', display: 'none' },
            }}
        />
    );
}

// The launcher icon itself gets a brief, gentle "notice me" bounce a handful
// of times on first appearance (animation-iteration-count is finite, so it
// stops on its own -- no JS teardown needed) and never at all under
// prefers-reduced-motion.
function launcherFabSx() {
    return {
        minWidth: 44,
        minHeight: 44,
        position: 'relative',
        animation: 'chatAttentionBounce 1.8s ease-in-out 3',
        '@keyframes chatAttentionBounce': {
            '0%, 100%': { transform: 'scale(1)' },
            '25%': { transform: 'scale(1.1)' },
            '50%': { transform: 'scale(0.97)' },
            '75%': { transform: 'scale(1.05)' },
        },
        '@media (prefers-reduced-motion: reduce)': { animation: 'none' },
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
    const [pulseActive, setPulseActive] = useState(true);

    const latestIdRef = useRef(null);
    const messagesEndRef = useRef(null);
    const activeThreadIdRef = useRef(null);

    // Ease the ripple off after a while even if the visitor never interacts
    // with the launcher at all.
    useEffect(() => {
        const t = setTimeout(() => setPulseActive(false), PULSE_EASE_OFF_MS);
        return () => clearTimeout(t);
    }, []);

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

        activeThreadIdRef.current = activeThread.id;
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

    const openPanel = () => { setOpen(true); setPulseActive(false); };
    const closePanel = () => { setOpen(false); setActiveThread(null); };

    // Optimistic send: the pending bubble renders immediately with a
    // "sending" state and is reconciled in place once the server confirms
    // (swapped for the real row) or marked "failed" with a retry affordance
    // -- the biggest perceived-speed win for a polling-based chat.
    const send = async () => {
        const body = draft.trim();
        if (!body || !activeThread) return;
        const tempId = `pending-${Date.now()}-${Math.random().toString(36).slice(2)}`;
        setMessages((prev) => [...prev, {
            id: tempId, thread_id: activeThread.id, sender_role: 'CUSTOMER',
            body, created_at: new Date().toISOString(), _status: 'sending',
        }]);
        setDraft('');
        setSending(true);
        const res = await callApi({
            url: `chat/threads/${activeThread.id}/messages/`, method: 'POST',
            body: { body }, rawError: true,
        });
        setSending(false);
        if (res?.status === 201) {
            latestIdRef.current = res.data.data.id;
            setMessages((prev) => prev.map((m) => (m.id === tempId ? res.data.data : m)));
        } else {
            setMessages((prev) => prev.map((m) => (m.id === tempId ? { ...m, _status: 'failed' } : m)));
        }
    };

    const retryMessage = async (tempId, body) => {
        if (!activeThread) return;
        setMessages((prev) => prev.map((m) => (m.id === tempId ? { ...m, _status: 'sending' } : m)));
        const res = await callApi({
            url: `chat/threads/${activeThread.id}/messages/`, method: 'POST',
            body: { body }, rawError: true,
        });
        if (res?.status === 201) {
            latestIdRef.current = res.data.data.id;
            setMessages((prev) => prev.map((m) => (m.id === tempId ? res.data.data : m)));
        } else {
            setMessages((prev) => prev.map((m) => (m.id === tempId ? { ...m, _status: 'failed' } : m)));
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
                <Box sx={launcherBoxSx(bottom)}>
                    <LauncherRing show={pulseActive} />
                    <Tooltip title="Chat with us — live now">
                        <Fab onClick={openPanel} aria-label="Chat with us" color="secondary" sx={launcherFabSx()}>
                            <ChatBubbleOutlineIcon />
                        </Fab>
                    </Tooltip>
                </Box>
                <Drawer anchor="right" open={open} onClose={closePanel}>
                    <Box sx={{ width: { xs: '100%', sm: 360 }, p: 3 }}>
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
            <Box sx={launcherBoxSx(bottom)}>
                <LauncherRing show={pulseActive && !open} />
                <Tooltip title="Chat with us — live now">
                    <Fab onClick={openPanel} aria-label="Chat with us" color="secondary" sx={launcherFabSx()}>
                        <Badge badgeContent={unread} color="error" max={99}>
                            <ChatBubbleOutlineIcon />
                        </Badge>
                    </Fab>
                </Tooltip>
            </Box>

            <Drawer anchor="right" open={open} onClose={closePanel}>
                <Box sx={{ width: { xs: '100%', sm: 380 }, height: '100%', display: 'flex', flexDirection: 'column' }}>
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
                                onKeyDown={(e) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); startThread(); } }}
                                sx={{ mb: 1 }}
                            />
                            <Button fullWidth variant="contained" disabled={creating || !draft.trim()} onClick={startThread}>
                                {creating ? <CircularProgress size={20} /> : 'Send'}
                            </Button>

                            <Divider sx={{ my: 2 }} />
                            <Typography variant="subtitle2" sx={{ mb: 1 }}>Your conversations</Typography>
                            {threads === null && <Typography variant="body2" color="text.secondary">Loading…</Typography>}
                            {threads?.length === 0 && (
                                <Box sx={{ textAlign: 'center', py: 3, color: 'text.secondary' }}>
                                    <ForumOutlinedIcon sx={{ fontSize: 40, mb: 1, opacity: 0.5 }} />
                                    <Typography variant="body2">
                                        No conversations yet — say hello! We usually reply fast.
                                    </Typography>
                                </Box>
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
                            <Box sx={{ flex: 1, overflowY: 'auto', p: 2, display: 'flex', flexDirection: 'column', gap: 1.25 }}>
                                {messages.length === 0 && (
                                    <Box sx={{ textAlign: 'center', py: 3, color: 'text.secondary' }}>
                                        <ForumOutlinedIcon sx={{ fontSize: 32, mb: 1, opacity: 0.5 }} />
                                        <Typography variant="body2">No messages yet.</Typography>
                                    </Box>
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
                                            <Box
                                                sx={{
                                                    bgcolor: isCustomer ? 'primary.main' : 'action.hover',
                                                    color: isCustomer ? 'primary.contrastText' : 'text.primary',
                                                    borderRadius: 2,
                                                    borderBottomRightRadius: isCustomer ? 4 : 16,
                                                    borderBottomLeftRadius: isCustomer ? 16 : 4,
                                                    px: 1.5, py: 1,
                                                    opacity: m._status === 'sending' ? 0.65 : 1,
                                                }}
                                            >
                                                {/* Plain text only -- body is never HTML, so it is never
                                                    rendered via dangerouslySetInnerHTML. */}
                                                <Typography variant="body2" sx={{ whiteSpace: 'pre-wrap' }}>{m.body}</Typography>
                                            </Box>
                                            <Stack
                                                direction="row" spacing={0.75} alignItems="center"
                                                justifyContent={isCustomer ? 'flex-end' : 'flex-start'}
                                                sx={{ mt: 0.25, px: 0.5 }}
                                            >
                                                <Typography variant="caption" color="text.secondary">
                                                    {formatTime(m.created_at)}
                                                </Typography>
                                                {m._status === 'sending' && <CircularProgress size={10} thickness={6} />}
                                                {m._status === 'failed' && (
                                                    <Typography
                                                        component="button"
                                                        type="button"
                                                        variant="caption"
                                                        onClick={() => retryMessage(m.id, m.body)}
                                                        sx={{
                                                            border: 'none', background: 'none', p: 0, m: 0,
                                                            color: 'error.main', cursor: 'pointer', textDecoration: 'underline',
                                                            font: 'inherit',
                                                        }}
                                                    >
                                                        Failed · Retry
                                                    </Typography>
                                                )}
                                            </Stack>
                                        </Box>
                                    );
                                })}
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
