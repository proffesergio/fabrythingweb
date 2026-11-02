import { useEffect, useState, useCallback } from "react";
import {
    Box, Typography, Card, CardContent, TextField, InputAdornment, Table, TableBody,
    TableCell, TableHead, TableRow, TableContainer, Paper, Avatar, Stack, Chip, LinearProgress,
    Pagination,
} from "@mui/material";
import SearchIcon from "@mui/icons-material/Search";
import GroupIcon from "@mui/icons-material/Group";

import useApi from "../../hooks/APIHandler";

export default function ManageCustomers() {
    const { callApi, loading } = useApi();
    const [customers, setCustomers] = useState([]);
    const [search, setSearch] = useState("");
    const [page, setPage] = useState(1);
    const [totalPages, setTotalPages] = useState(1);

    const fetchCustomers = useCallback(async () => {
        const params = { page };
        if (search) params.search = search;
        const res = await callApi({ url: "store/admin/customers/", method: "GET", params });
        if (res?.status === 200) {
            setCustomers(res.data.data.data || []);
            setTotalPages(res.data.data.totalPages || 1);
        }
    }, [page, search]); // eslint-disable-line react-hooks/exhaustive-deps

    useEffect(() => { fetchCustomers(); }, [fetchCustomers]);

    return (
        <Box>
            <Stack direction="row" alignItems="center" spacing={1} sx={{ mb: 2 }}>
                <GroupIcon color="primary" />
                <Typography variant="h5" fontWeight={800}>Customers</Typography>
            </Stack>

            <Card sx={{ mb: 2 }}>
                <CardContent>
                    <TextField
                        size="small" fullWidth placeholder="Search by name, email, or phone"
                        value={search}
                        onChange={(e) => { setPage(1); setSearch(e.target.value); }}
                        InputProps={{ startAdornment: <InputAdornment position="start"><SearchIcon /></InputAdornment> }}
                    />
                </CardContent>
            </Card>

            {loading && <LinearProgress sx={{ mb: 1 }} />}
            <TableContainer component={Paper}>
                <Table>
                    <TableHead>
                        <TableRow>
                            <TableCell>Customer</TableCell>
                            <TableCell>Contact</TableCell>
                            <TableCell align="center">Orders</TableCell>
                            <TableCell align="right">Total spent</TableCell>
                            <TableCell>Joined</TableCell>
                        </TableRow>
                    </TableHead>
                    <TableBody>
                        {customers.length === 0 && !loading && (
                            <TableRow><TableCell colSpan={5} align="center">No customers found</TableCell></TableRow>
                        )}
                        {customers.map((c) => (
                            <TableRow key={c.id} hover>
                                <TableCell>
                                    <Stack direction="row" spacing={1.5} alignItems="center">
                                        <Avatar sx={{ width: 34, height: 34, bgcolor: "primary.main" }}>
                                            {(c.username || "?").charAt(0).toUpperCase()}
                                        </Avatar>
                                        <Box>
                                            <Typography variant="body2" fontWeight={600}>{c.username}</Typography>
                                            <Typography variant="caption" color="text.secondary">{c.city || c.country || ""}</Typography>
                                        </Box>
                                    </Stack>
                                </TableCell>
                                <TableCell>
                                    <Typography variant="body2">{c.email}</Typography>
                                    <Typography variant="caption" color="text.secondary">{c.phone || "—"}</Typography>
                                </TableCell>
                                <TableCell align="center"><Chip size="small" label={c.order_count} color={c.order_count > 0 ? "primary" : "default"} /></TableCell>
                                <TableCell align="right">৳{Number(c.total_spent || 0).toLocaleString()}</TableCell>
                                <TableCell>{c.date_joined ? new Date(c.date_joined).toLocaleDateString() : "—"}</TableCell>
                            </TableRow>
                        ))}
                    </TableBody>
                </Table>
            </TableContainer>

            {totalPages > 1 && (
                <Stack alignItems="center" sx={{ mt: 2 }}>
                    <Pagination count={totalPages} page={page} onChange={(_, p) => setPage(p)} color="primary" />
                </Stack>
            )}
        </Box>
    );
}
