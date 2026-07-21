import { useEffect, useState, useCallback } from "react";
import {
    Box, Typography, Tabs, Tab, Table, TableBody, TableCell, TableHead, TableRow, Paper,
    TableContainer, Chip, Stack, Pagination,
} from "@mui/material";
import PaidIcon from "@mui/icons-material/Paid";
import useApi from "../../hooks/APIHandler";

const METHOD_TABS = ["", "COD", "BKASH", "NAGAD", "QR"];
const STATUS_COLOR = { SUCCESS: "success", PENDING: "warning", FAILED: "error" };

export default function FoodPayments() {
    const { callApi } = useApi();
    const [rows, setRows] = useState([]);
    const [method, setMethod] = useState("");
    const [page, setPage] = useState(1);
    const [totalPages, setTotalPages] = useState(1);

    const load = useCallback(async () => {
        const params = { page };
        if (method) params.method = method;
        const res = await callApi({ url: "food/admin/payments/", method: "GET", params });
        if (res?.status === 200) { setRows(res.data.data.data || []); setTotalPages(res.data.data.totalPages || 1); }
    }, [method, page]); // eslint-disable-line react-hooks/exhaustive-deps

    useEffect(() => { load(); }, [load]);

    return (
        <Box>
            <Stack direction="row" spacing={1} alignItems="center" sx={{ mb: 2 }}><PaidIcon color="primary" /><Typography variant="h5" fontWeight={800}>Payments</Typography></Stack>
            <Tabs value={method} onChange={(_, v) => { setPage(1); setMethod(v); }} sx={{ mb: 2 }}>
                {METHOD_TABS.map((m) => <Tab key={m || "all"} label={m || "All"} value={m} />)}
            </Tabs>
            <TableContainer component={Paper}>
                <Table>
                    <TableHead><TableRow>
                        <TableCell>Order</TableCell><TableCell>Method</TableCell><TableCell align="right">Amount</TableCell>
                        <TableCell>Status</TableCell><TableCell>Reference</TableCell><TableCell>Date</TableCell>
                    </TableRow></TableHead>
                    <TableBody>
                        {rows.length === 0 && <TableRow><TableCell colSpan={6} align="center">No payments</TableCell></TableRow>}
                        {rows.map((p) => (
                            <TableRow key={p.id} hover>
                                <TableCell>{p.order_code}</TableCell>
                                <TableCell><Chip size="small" label={p.method} /></TableCell>
                                <TableCell align="right"><Typography fontWeight={700}>৳{p.amount}</Typography></TableCell>
                                <TableCell><Chip size="small" label={p.status} color={STATUS_COLOR[p.status] || "default"} /></TableCell>
                                <TableCell>{p.provider_ref || "—"}</TableCell>
                                <TableCell>{p.created_at ? new Date(p.created_at).toLocaleString() : "—"}</TableCell>
                            </TableRow>
                        ))}
                    </TableBody>
                </Table>
            </TableContainer>
            {totalPages > 1 && <Stack alignItems="center" sx={{ mt: 2 }}><Pagination count={totalPages} page={page} onChange={(_, p) => setPage(p)} color="primary" /></Stack>}
        </Box>
    );
}
