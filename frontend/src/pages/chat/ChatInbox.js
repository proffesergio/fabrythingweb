import { useCallback, useEffect, useRef, useState } from "react";
import {
    Box, Typography, Tabs, Tab, List, ListItemButton, ListItemText, Chip, Grid, Paper,
    Stack, TextField, Button, IconButton, Alert, Divider, CircularProgress,
} from "@mui/material";
import ChatIcon from "@mui/icons-material/Chat";
import SendIcon from "@mui/icons-material/Send";
import LockIcon from "@mui/icons-material/LockOutlined";
import LockOpenIcon from "@mui/icons-material/LockOpenOutlined";
import useApi from "../../hooks/APIHandler";

const STATUS_TABS = ["", "OPEN", "CLOSED"];
const STATUS_LABELS = { "": "All", OPEN: "Open", CLOSED: "Closed" };
const KIND_LABELS = {
    GENERAL: "General", ORDER: "Store order", FOOD_ORDER: "Food order",
    EMERGENCY: "Emergency delivery", PRINT_JOB: "Print job",
};
const KIND_COLORS = {
    GENERAL: "default", ORDER: "info", FOOD_ORDER: "secondary",
    EMERGENCY: "error", PRINT_JOB: "warning",
};

// Inbox list refresh -- staff may keep this tab open all shift, so a modest
// interval (not the customer widget's 4s) is enough to surface new threads
// and status changes without hammering the server. See docs/LIVE_CHAT.md.
const INBOX_POLL_MS = 15000;
// Messages in the open conversation poll faster, matching the customer side.
const MESSAGES_POLL_MS = 4000;

export default function ChatInbox() {
    const { callApi } = useApi();
    const [status, setStatus] = useState("");
    const [threads, setThreads] = useState([]);
    const [loadError, setLoadError] = useState("");
    const [active, setActive] = useState(null);
    const [messages, setMessages] = useState([]);
    const [draft, setDraft] = useState("");
    const [sending, setSending] = useState(false);

    const latestIdRef = useRef(null);

    const loadThreads = useCallback(async (st) => {
        const params = {};
        if (st) params.status = st;
        // rawError: a 500/403 here must not render as a cheerful empty inbox.
        const res = await callApi({ url: "chat/admin/threads/", method: "GET", params, rawError: true });
        if (res?.status === 200) {
            setThreads(res.data.data || []);
            setLoadError("");
        } else {
            setThreads([]);
            setLoadError(res?.data?.message || "Could not load the chat inbox.");
        }
    }, []); // eslint-disable-line react-hooks/exhaustive-deps

    useEffect(() => { loadThreads(status); }, [status, loadThreads]);

    // Background inbox refresh, paused while the tab is hidden.
    useEffect(() => {
        const id = setInterval(() => {
            if (document.visibilityState === "visible") loadThreads(status);
        }, INBOX_POLL_MS);
        return () => clearInterval(id);
    }, [status, loadThreads]);

    const fetchMessages = useCallback(async (threadId, { initial } = {}) => {
        if (document.visibilityState !== "visible") return;
        const after = initial ? null : latestIdRef.current;
        const res = await callApi({
            url: `chat/admin/threads/${threadId}/messages/${after != null ? `?after=${after}` : ""}`,
            rawError: true,
        });
        if (res?.status !== 200) return;
        const { messages: newMessages, latest_id: latestId } = res.data.data;
        if (latestId != null) latestIdRef.current = latestId;
        if (initial) setMessages(newMessages);
        else if (newMessages.length) setMessages((prev) => [...prev, ...newMessages]);
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, []);

    const openThread = async (thread) => {
        setActive(thread);
        latestIdRef.current = null;
        setMessages([]);
        setDraft("");
        await fetchMessages(thread.id, { initial: true });
        await callApi({ url: `chat/admin/threads/${thread.id}/read/`, method: "POST" });
        setThreads((prev) => prev.map((t) => (t.id === thread.id ? { ...t, unread_count: 0 } : t)));
    };

    useEffect(() => {
        if (!active) return undefined;
        const id = setInterval(() => {
            if (document.visibilityState === "visible") fetchMessages(active.id);
        }, MESSAGES_POLL_MS);
        return () => clearInterval(id);
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [active?.id]);

    const send = async () => {
        if (!draft.trim() || !active) return;
        setSending(true);
        const res = await callApi({
            url: `chat/admin/threads/${active.id}/messages/`, method: "POST",
            body: { body: draft.trim() }, rawError: true,
        });
        setSending(false);
        if (res?.status === 201) {
            setDraft("");
            setMessages((prev) => [...prev, res.data.data]);
            latestIdRef.current = res.data.data.id;
        }
    };

    const toggleStatus = async () => {
        if (!active) return;
        const nextStatus = active.status === "CLOSED" ? "OPEN" : "CLOSED";
        const res = await callApi({
            url: `chat/admin/threads/${active.id}/status/`, method: "POST",
            body: { status: nextStatus }, rawError: true,
        });
        if (res?.status === 200) {
            setActive((a) => ({ ...a, status: nextStatus }));
            setThreads((prev) => prev.map((t) => (t.id === active.id ? { ...t, status: nextStatus } : t)));
        }
    };

    return (
        <Box>
            <Stack direction="row" spacing={1} alignItems="center" sx={{ mb: 2 }}>
                <ChatIcon color="primary" />
                <Typography variant="h5" fontWeight={800}>Live Chat</Typography>
            </Stack>

            {loadError && <Alert severity="error" sx={{ mb: 2 }}>{loadError}</Alert>}

            <Grid container spacing={2} sx={{ height: { md: "70vh" } }}>
                <Grid item xs={12} md={4}>
                    <Paper sx={{ height: "100%", display: "flex", flexDirection: "column" }}>
                        <Tabs value={status} onChange={(e, v) => { setStatus(v); setActive(null); }} sx={{ px: 1 }}>
                            {STATUS_TABS.map((s) => <Tab key={s || "all"} value={s} label={STATUS_LABELS[s]} />)}
                        </Tabs>
                        <Divider />
                        <List sx={{ flex: 1, overflowY: "auto" }}>
                            {threads.length === 0 && !loadError && (
                                <Typography variant="body2" color="text.secondary" sx={{ p: 2 }}>
                                    No conversations here.
                                </Typography>
                            )}
                            {threads.map((t) => (
                                <ListItemButton
                                    key={t.id}
                                    selected={active?.id === t.id}
                                    onClick={() => openThread(t)}
                                >
                                    <ListItemText
                                        primary={t.customer_name || `Customer #${t.customer_id}`}
                                        secondary={
                                            <Stack direction="row" spacing={0.5} alignItems="center" sx={{ mt: 0.5 }}>
                                                <Chip size="small" label={KIND_LABELS[t.kind] || t.kind} color={KIND_COLORS[t.kind] || "default"} />
                                                {t.status === "CLOSED" && <Chip size="small" variant="outlined" label="Closed" />}
                                            </Stack>
                                        }
                                        secondaryTypographyProps={{ component: "div" }}
                                    />
                                    {t.unread_count > 0 && <Chip size="small" color="error" label={t.unread_count} />}
                                </ListItemButton>
                            ))}
                        </List>
                    </Paper>
                </Grid>

                <Grid item xs={12} md={8}>
                    <Paper sx={{ height: "100%", display: "flex", flexDirection: "column" }}>
                        {!active && (
                            <Box sx={{ flex: 1, display: "flex", alignItems: "center", justifyContent: "center" }}>
                                <Typography variant="body2" color="text.secondary">
                                    Select a conversation to view it.
                                </Typography>
                            </Box>
                        )}
                        {active && (
                            <>
                                <Stack direction="row" alignItems="center" spacing={1} sx={{ p: 2, borderBottom: "1px solid", borderColor: "divider" }}>
                                    <Box sx={{ flex: 1 }}>
                                        <Typography variant="subtitle1" fontWeight={700}>
                                            {active.customer_name || `Customer #${active.customer_id}`}
                                        </Typography>
                                        <Chip size="small" label={KIND_LABELS[active.kind] || active.kind} color={KIND_COLORS[active.kind] || "default"} />
                                    </Box>
                                    <Button
                                        size="small"
                                        variant="outlined"
                                        color={active.status === "CLOSED" ? "success" : "warning"}
                                        startIcon={active.status === "CLOSED" ? <LockOpenIcon /> : <LockIcon />}
                                        onClick={toggleStatus}
                                    >
                                        {active.status === "CLOSED" ? "Reopen" : "Close"}
                                    </Button>
                                </Stack>

                                <Box sx={{ flex: 1, overflowY: "auto", p: 2, display: "flex", flexDirection: "column", gap: 1 }}>
                                    {messages.map((m) => (
                                        <Box
                                            key={m.id}
                                            sx={{
                                                alignSelf: m.sender_role === "STAFF" ? "flex-end" : "flex-start",
                                                bgcolor: m.sender_role === "STAFF" ? "primary.main" : "action.hover",
                                                color: m.sender_role === "STAFF" ? "primary.contrastText" : "text.primary",
                                                borderRadius: 2, px: 1.5, py: 1, maxWidth: "70%",
                                            }}
                                        >
                                            {/* Plain text only -- never dangerouslySetInnerHTML. */}
                                            <Typography variant="body2" sx={{ whiteSpace: "pre-wrap" }}>{m.body}</Typography>
                                        </Box>
                                    ))}
                                </Box>

                                <Stack direction="row" spacing={1} sx={{ p: 2, borderTop: "1px solid", borderColor: "divider" }}>
                                    <TextField
                                        fullWidth size="small" placeholder="Reply…"
                                        value={draft} onChange={(e) => setDraft(e.target.value)}
                                        onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); send(); } }}
                                    />
                                    <IconButton color="primary" disabled={sending || !draft.trim()} onClick={send} aria-label="Send reply">
                                        {sending ? <CircularProgress size={20} /> : <SendIcon />}
                                    </IconButton>
                                </Stack>
                            </>
                        )}
                    </Paper>
                </Grid>
            </Grid>
        </Box>
    );
}
