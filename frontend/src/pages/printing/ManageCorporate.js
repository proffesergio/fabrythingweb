import { useEffect, useState, useCallback } from "react";
import {
    Box, Typography, Tabs, Tab, Table, TableBody, TableCell, TableHead, TableRow, Paper,
    TableContainer, Chip, LinearProgress, Button, IconButton, TextField, Stack, Switch, MenuItem,
} from "@mui/material";
import DeleteIcon from "@mui/icons-material/Delete";
import { toast } from "react-toastify";
import useApi from "../../hooks/APIHandler";

// Corporate account suite: trusted accounts (PO + partial advance + ledger),
// quotation queue (draft → sent → accepted → ordered) with printable
// quotation documents.
const QUOTATION_TABS = ["", "DRAFT", "SENT", "ACCEPTED", "ORDERED", "EXPIRED"];

export default function ManageCorporate() {
    const { callApi, loading } = useApi();
    const [tab, setTab] = useState(0);
    const [accounts, setAccounts] = useState([]);
    const [quotations, setQuotations] = useState([]);
    const [qStatus, setQStatus] = useState("");

    const fetchAccounts = useCallback(async () => {
        const res = await callApi({ url: "print/press/admin/corporate/", rawError: true, silent: true });
        if (res?.status === 200) setAccounts(res.data.data);
    }, []); // eslint-disable-line react-hooks/exhaustive-deps

    const fetchQuotations = useCallback(async (st) => {
        const res = await callApi({ url: "print/press/admin/quotations/", method: "GET", params: st ? { status: st } : {}, rawError: true, silent: true });
        if (res?.status === 200) setQuotations(res.data.data);
    }, []); // eslint-disable-line react-hooks/exhaustive-deps

    useEffect(() => { fetchAccounts(); }, [fetchAccounts]);
    useEffect(() => { fetchQuotations(qStatus); }, [qStatus, fetchQuotations]);

    const patchAccount = async (id, body) => {
        const res = await callApi({ url: `print/press/admin/corporate/${id}/`, method: "PATCH", body, rawError: true });
        if (res?.status === 200) fetchAccounts(); else toast.error("Could not update account");
    };
    const deleteAccount = async (id) => {
        const res = await callApi({ url: `print/press/admin/corporate/${id}/`, method: "DELETE", rawError: true });
        if (res?.status === 200) { toast.success("Account removed"); fetchAccounts(); } else toast.error("Could not delete");
    };
    const setQuotationStatus = async (id, status) => {
        const res = await callApi({ url: "print/press/admin/quotations/", method: "PATCH", body: { id, status }, rawError: true });
        if (res?.status === 200) { toast.success(`Quotation ${status}`); fetchQuotations(qStatus); }
        else toast.error(res?.data?.message || "Could not update quotation");
    };

    const printQuotation = (q) => {
        const cfg = q.config_snapshot || {};
        const win = window.open("", "_blank");
        if (!win) { toast.error("Popup blocked — allow popups to print the quotation."); return; }
        win.document.write(`<html><head><title>Quotation #${q.id}</title></head><body style="font-family:sans-serif;padding:32px;max-width:640px;">
            <h2>Quotation #${q.id}</h2>
            <p>Status: ${q.status} · Date: ${new Date(q.created_at).toLocaleString()}</p>
            <hr/>
            <p><strong>Product:</strong> ${q.product_name || cfg.product_name || ""}</p>
            <p><strong>Size:</strong> ${cfg.width || ""} x ${cfg.height || ""}${cfg.unit || ""} · <strong>Sides:</strong> ${cfg.sides || ""} · <strong>Qty:</strong> ${cfg.quantity || ""}</p>
            <p><strong>Paper:</strong> ${cfg.paper_stock_name || "—"} · <strong>Finishing:</strong> ${(cfg.finishing_names || []).join(", ") || "—"}</p>
            ${q.po_number ? `<p><strong>PO:</strong> ${q.po_number}</p>` : ""}
            <hr/>
            <h3>Total: ৳${Number(q.total_bdt || 0).toLocaleString("en-US")} ${q.currency === "USD" ? "(USD conversion on checkout)" : ""}</h3>
            <p style="color:#666;font-size:12px;">Auto-generated quotation — valid subject to artwork review. Convert to an order from the press checkout with this quotation attached.</p>
            <script>window.print()</script></body></html>`);
        win.document.close();
    };

    const fmt = (n) => `৳${Number(n || 0).toLocaleString("en-US")}`;

    return (
        <Box>
            <Typography variant="h5" fontWeight={800} sx={{ mb: 2 }}>Corporate & Quotations</Typography>
            <Tabs value={tab} onChange={(_, v) => setTab(v)} sx={{ mb: 2 }}>
                <Tab label="Corporate Accounts" />
                <Tab label="Quotations" />
            </Tabs>
            {loading && <LinearProgress />}

            {tab === 0 && (
                <TableContainer component={Paper}>
                    <Table size="small">
                        <TableHead>
                            <TableRow>
                                <TableCell>Company</TableCell><TableCell>Customer</TableCell>
                                <TableCell>Credit limit</TableCell><TableCell>Ledger balance</TableCell>
                                <TableCell>Partial trusted</TableCell><TableCell>Active</TableCell><TableCell />
                            </TableRow>
                        </TableHead>
                        <TableBody>
                            {accounts.length === 0 && (
                                <TableRow><TableCell colSpan={7} align="center">No corporate accounts yet</TableCell></TableRow>
                            )}
                            {accounts.map((a) => (
                                <TableRow key={a.id}>
                                    <TableCell><strong>{a.company_name}</strong><Typography variant="caption" display="block" color="text.secondary">{a.contact_phone}</Typography></TableCell>
                                    <TableCell>{a.customer_username}</TableCell>
                                    <TableCell>
                                        <TextField size="small" value={a.credit_limit_bdt} sx={{ width: 110 }}
                                            onChange={(e) => patchAccount(a.id, { credit_limit_bdt: e.target.value })} />
                                    </TableCell>
                                    <TableCell><strong>{fmt(a.ledger_balance_bdt)}</strong></TableCell>
                                    <TableCell>
                                        <Switch checked={a.trusted_for_partial} onChange={(e) => patchAccount(a.id, { trusted_for_partial: e.target.checked })} />
                                    </TableCell>
                                    <TableCell>
                                        <Switch checked={a.is_active} onChange={(e) => patchAccount(a.id, { is_active: e.target.checked })} />
                                    </TableCell>
                                    <TableCell>
                                        <IconButton size="small" onClick={() => deleteAccount(a.id)}><DeleteIcon fontSize="small" /></IconButton>
                                    </TableCell>
                                </TableRow>
                            ))}
                        </TableBody>
                    </Table>
                </TableContainer>
            )}

            {tab === 1 && (
                <Box>
                    <Tabs value={qStatus} onChange={(_, v) => setQStatus(v)} variant="scrollable" sx={{ mb: 2 }}>
                        {QUOTATION_TABS.map((s) => <Tab key={s || "all"} label={s || "All"} value={s} />)}
                    </Tabs>
                    <TableContainer component={Paper}>
                        <Table size="small">
                            <TableHead>
                                <TableRow><TableCell>ID</TableCell><TableCell>Product</TableCell><TableCell>Total</TableCell><TableCell>PO</TableCell><TableCell>Status</TableCell><TableCell>Order</TableCell><TableCell /></TableRow>
                            </TableHead>
                            <TableBody>
                                {quotations.length === 0 && (
                                    <TableRow><TableCell colSpan={7} align="center">No quotations</TableCell></TableRow>
                                )}
                                {quotations.map((q) => (
                                    <TableRow key={q.id}>
                                        <TableCell>#{q.id}</TableCell>
                                        <TableCell>{q.product_name}</TableCell>
                                        <TableCell><strong>{fmt(q.total_bdt)}</strong></TableCell>
                                        <TableCell>{q.po_number || "—"}</TableCell>
                                        <TableCell><Chip size="small" label={q.status} /></TableCell>
                                        <TableCell>{q.press_order ? `#${q.press_order}` : "—"}</TableCell>
                                        <TableCell>
                                            <Stack direction="row" spacing={1}>
                                                <Button size="small" onClick={() => printQuotation(q)}>Print PDF</Button>
                                                <TextField size="small" select value={q.status} sx={{ minWidth: 120 }}
                                                    onChange={(e) => setQuotationStatus(q.id, e.target.value)}>
                                                    {QUOTATION_TABS.filter(Boolean).map((s) => <MenuItem key={s} value={s}>{s}</MenuItem>)}
                                                </TextField>
                                            </Stack>
                                        </TableCell>
                                    </TableRow>
                                ))}
                            </TableBody>
                        </Table>
                    </TableContainer>
                </Box>
            )}
        </Box>
    );
}
