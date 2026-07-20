import { useState, useEffect, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import {
    Box, Breadcrumbs, Button, Chip, IconButton, LinearProgress, Table, TableBody, TableCell,
    TableContainer, TableHead, TableRow, Paper, TextField, Typography, Stack, Avatar,
    InputAdornment, Pagination, Tooltip, Dialog, DialogContent, Divider,
} from "@mui/material";
import Add from "@mui/icons-material/Add";
import Edit from "@mui/icons-material/Edit";
import SearchIcon from "@mui/icons-material/Search";
import RateReviewOutlinedIcon from "@mui/icons-material/RateReviewOutlined";
import HelpOutlineIcon from "@mui/icons-material/HelpOutline";
import useApi from "../../hooks/APIHandler";
import ManageReviews from "./ManageReview";
import ManageQuestions from "./ManageQuestions";

const firstImage = (img) => (Array.isArray(img) ? img[0] : img) || "";
const cleanCategory = (c) => (typeof c === "string" ? c : "");

const ManageProducts = ({ onProductSelected }) => {
    const { callApi, loading } = useApi();
    const navigate = useNavigate();
    const [products, setProducts] = useState([]);
    const [search, setSearch] = useState("");
    const [debounced, setDebounced] = useState("");
    const [page, setPage] = useState(1);
    const [totalPages, setTotalPages] = useState(1);
    const [reviewsFor, setReviewsFor] = useState(null);
    const [questionsFor, setQuestionsFor] = useState(null);

    useEffect(() => {
        const t = setTimeout(() => { setPage(1); setDebounced(search); }, 600);
        return () => clearTimeout(t);
    }, [search]);

    const getProducts = useCallback(async () => {
        const res = await callApi({
            url: "products/", method: "GET",
            params: { page, pageSize: 12, search: debounced, ordering: "-id" },
        });
        if (res?.status === 200) {
            setProducts(res.data.data.data || []);
            setTotalPages(res.data.data.totalPages || 1);
        }
    }, [page, debounced]); // eslint-disable-line react-hooks/exhaustive-deps

    useEffect(() => { getProducts(); }, [getProducts]);

    return (
        <Box sx={{ width: "100%" }}>
            {!onProductSelected && (
                <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 2 }}>
                    <Breadcrumbs>
                        <Typography variant="body2" sx={{ cursor: "pointer" }} onClick={() => navigate("/admin")}>Home</Typography>
                        <Typography variant="body2">Products</Typography>
                    </Breadcrumbs>
                    <Button variant="contained" startIcon={<Add />} onClick={() => navigate("/admin/form/product")}>
                        Add Product
                    </Button>
                </Stack>
            )}

            <TextField
                size="small" fullWidth placeholder="Search products…" value={search}
                onChange={(e) => setSearch(e.target.value)} sx={{ mb: 2 }}
                InputProps={{ startAdornment: <InputAdornment position="start"><SearchIcon /></InputAdornment> }}
            />

            {loading && <LinearProgress sx={{ mb: 1 }} />}
            <TableContainer component={Paper}>
                <Table>
                    <TableHead>
                        <TableRow>
                            <TableCell>Product</TableCell>
                            <TableCell>Category</TableCell>
                            <TableCell align="right">Price</TableCell>
                            <TableCell>Status</TableCell>
                            <TableCell align="right">Actions</TableCell>
                        </TableRow>
                    </TableHead>
                    <TableBody>
                        {products.length === 0 && !loading && (
                            <TableRow><TableCell colSpan={5} align="center">No products found</TableCell></TableRow>
                        )}
                        {products.map((p) => (
                            <TableRow key={p.id} hover>
                                <TableCell>
                                    <Stack direction="row" spacing={1.5} alignItems="center">
                                        <Avatar variant="rounded" src={firstImage(p.image)} sx={{ width: 44, height: 44 }}>
                                            {(p.name || "?").charAt(0)}
                                        </Avatar>
                                        <Box>
                                            <Typography variant="body2" fontWeight={600}>{p.name}</Typography>
                                            <Typography variant="caption" color="text.secondary">{p.brand || p.sku}</Typography>
                                        </Box>
                                    </Stack>
                                </TableCell>
                                <TableCell><Typography variant="body2">{cleanCategory(p.category_id)}</Typography></TableCell>
                                <TableCell align="right">
                                    {p.discount_price ? (
                                        <Stack alignItems="flex-end">
                                            <Typography variant="body2" fontWeight={700} color="secondary.main">৳{p.discount_price}</Typography>
                                            <Typography variant="caption" color="text.secondary" sx={{ textDecoration: "line-through" }}>
                                                ৳{p.initial_selling_price}
                                            </Typography>
                                        </Stack>
                                    ) : (
                                        <Typography variant="body2" fontWeight={700}>৳{p.initial_selling_price}</Typography>
                                    )}
                                </TableCell>
                                <TableCell>
                                    <Chip size="small" label={p.status} color={p.status === "ACTIVE" ? "success" : "default"} />
                                </TableCell>
                                <TableCell align="right">
                                    {onProductSelected ? (
                                        <Button size="small" variant="contained" startIcon={<Add />} onClick={() => onProductSelected(p)}>Select</Button>
                                    ) : (
                                        <Stack direction="row" justifyContent="flex-end">
                                            <Tooltip title="Edit"><IconButton size="small" onClick={() => navigate(`/admin/form/product/${p.id}`)}><Edit fontSize="small" color="primary" /></IconButton></Tooltip>
                                            <Tooltip title="Reviews"><IconButton size="small" onClick={() => { setReviewsFor(p.id); setQuestionsFor(null); }}><RateReviewOutlinedIcon fontSize="small" /></IconButton></Tooltip>
                                            <Tooltip title="Questions"><IconButton size="small" onClick={() => { setQuestionsFor(p.id); setReviewsFor(null); }}><HelpOutlineIcon fontSize="small" /></IconButton></Tooltip>
                                        </Stack>
                                    )}
                                </TableCell>
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

            <Dialog maxWidth="lg" fullWidth open={!!reviewsFor} onClose={() => setReviewsFor(null)}>
                <DialogContent><ManageReviews product_id={reviewsFor} /><Divider /></DialogContent>
            </Dialog>
            <Dialog maxWidth="lg" fullWidth open={!!questionsFor} onClose={() => setQuestionsFor(null)}>
                <DialogContent><ManageQuestions product_id={questionsFor} /></DialogContent>
            </Dialog>
        </Box>
    );
};

export default ManageProducts;
