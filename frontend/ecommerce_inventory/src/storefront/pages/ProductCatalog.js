import React, { useEffect, useState, useCallback, Fragment } from 'react';
import {
    Box, Container, Grid, Typography, FormControl, Select, MenuItem,
    Drawer, Button, Chip, Checkbox, FormControlLabel, FormGroup,
    IconButton, Divider, Pagination, Skeleton, useMediaQuery, useTheme,
} from '@mui/material';
import { FilterList, Close } from '@mui/icons-material';
import { useSearchParams } from 'react-router-dom';
import useApi from '../../hooks/APIHandler';
import ProductCard from '../components/ProductCard';
import AffiliateWidget from '../components/AffiliateWidget';
import AffiliateProductCard from '../components/AffiliateProductCard';

const GENDER_OPTIONS = ['MEN', 'WOMEN', 'KIDS', 'UNISEX'];
export default function ProductCatalog() {
    const [searchParams, setSearchParams] = useSearchParams();
    const [products, setProducts] = useState([]);
    const [categories, setCategories] = useState([]);
    const [pagination, setPagination] = useState({ totalPages: 1, currentPage: 1, totalItems: 0 });
    const [filterDrawerOpen, setFilterDrawerOpen] = useState(false);
    const { callApi, loading } = useApi();
    const theme = useTheme();
    const isMobile = useMediaQuery(theme.breakpoints.down('md'));

    // Read filters from URL
    const filters = {
        category: searchParams.get('category') || '',
        gender: searchParams.get('gender') || '',
        search: searchParams.get('search') || '',
        ordering: searchParams.get('ordering') || 'newest',
        page: parseInt(searchParams.get('page') || '1'),
        price_min: searchParams.get('price_min') || '',
        price_max: searchParams.get('price_max') || '',
    };

    const updateFilter = (key, value) => {
        const newParams = new URLSearchParams(searchParams);
        if (value) {
            newParams.set(key, value);
        } else {
            newParams.delete(key);
        }
        if (key !== 'page') newParams.set('page', '1');
        setSearchParams(newParams);
    };

    const clearFilters = () => {
        setSearchParams({});
    };

    const fetchProducts = useCallback(async () => {
        const params = {};
        if (filters.category) params.category = filters.category;
        if (filters.gender) params.gender = filters.gender;
        if (filters.search) params.search = filters.search;
        if (filters.ordering) params.ordering = filters.ordering;
        if (filters.price_min) params.price_min = filters.price_min;
        if (filters.price_max) params.price_max = filters.price_max;
        params.page = filters.page;
        params.pageSize = 12;

        const res = await callApi({ url: 'store/products/', params });
        if (res?.data?.data) {
            setProducts(res.data.data.data || []);
            setPagination({
                totalPages: res.data.data.totalPages || 1,
                currentPage: res.data.data.currentPage || 1,
                totalItems: res.data.data.totalItems || 0,
            });
        }
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [searchParams]);

    const fetchCategories = async () => {
        const res = await callApi({ url: 'store/categories/' });
        if (res?.data?.data) setCategories(res.data.data);
    };

    useEffect(() => { fetchProducts(); }, [fetchProducts]);
    // eslint-disable-next-line react-hooks/exhaustive-deps
    useEffect(() => { fetchCategories(); }, []);

    // Category-grid injection: affiliate products tagged for the active
    // taxonomy category (AffiliateProduct.grid_categories +
    // show_in_category_grid=True) are appended after the real catalog
    // results for that category -- see storefront.views_affiliate.
    // PublicAffiliateListView's ?category= filter.
    const [affiliateGridItems, setAffiliateGridItems] = useState([]);
    useEffect(() => {
        if (!filters.category) { setAffiliateGridItems([]); return undefined; }
        let mounted = true;
        callApi({ url: 'store/partner-picks/', params: { category: filters.category } }).then((res) => {
            if (mounted) setAffiliateGridItems(res?.data?.data || []);
        });
        return () => { mounted = false; };
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [filters.category]);

    const activeFilterCount = [filters.category, filters.gender, filters.price_min, filters.price_max, filters.search]
        .filter(Boolean).length;

    const FilterPanel = () => (
        <Box sx={{ p: isMobile ? 2 : 0 }}>
            {isMobile && (
                <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 2 }}>
                    <Typography variant="h6">Filters</Typography>
                    <IconButton onClick={() => setFilterDrawerOpen(false)}><Close /></IconButton>
                </Box>
            )}

            {/* Categories — parent + nested children */}
            <Typography variant="subtitle2" fontWeight={700} gutterBottom>Category</Typography>
            <FormGroup sx={{ mb: 2 }}>
                {categories.map(cat => (
                    <React.Fragment key={cat.id}>
                        {/* Parent row */}
                        <FormControlLabel
                            control={
                                <Checkbox
                                    size="small"
                                    checked={filters.category === cat.slug}
                                    onChange={() => updateFilter('category', filters.category === cat.slug ? '' : cat.slug)}
                                />
                            }
                            label={
                                <Typography variant="body2" fontWeight={600}>
                                    {cat.name}
                                    <Typography component="span" variant="caption" color="text.secondary" sx={{ ml: 0.5 }}>
                                        ({cat.product_count})
                                    </Typography>
                                </Typography>
                            }
                        />
                        {/* Child rows — indented */}
                        {cat.children?.map(child => (
                            <FormControlLabel
                                key={child.id}
                                sx={{ pl: 2 }}
                                control={
                                    <Checkbox
                                        size="small"
                                        checked={filters.category === child.slug}
                                        onChange={() => updateFilter('category', filters.category === child.slug ? '' : child.slug)}
                                    />
                                }
                                label={
                                    <Typography variant="body2">
                                        {child.name}
                                        <Typography component="span" variant="caption" color="text.secondary" sx={{ ml: 0.5 }}>
                                            ({child.product_count})
                                        </Typography>
                                    </Typography>
                                }
                            />
                        ))}
                    </React.Fragment>
                ))}
            </FormGroup>

            <Divider sx={{ mb: 2 }} />

            {/* Gender */}
            <Typography variant="subtitle2" fontWeight={700} gutterBottom>Gender</Typography>
            <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5, mb: 2 }}>
                {GENDER_OPTIONS.map(g => (
                    <Chip
                        key={g}
                        label={g}
                        size="small"
                        variant={filters.gender === g ? 'filled' : 'outlined'}
                        color={filters.gender === g ? 'secondary' : 'default'}
                        onClick={() => updateFilter('gender', filters.gender === g ? '' : g)}
                    />
                ))}
            </Box>

            <Divider sx={{ mb: 2 }} />

            {/* Price Range */}
            <Typography variant="subtitle2" fontWeight={700} gutterBottom>Price Range (BDT)</Typography>
            <Box sx={{ display: 'flex', gap: 1, mb: 2 }}>
                <FormControl size="small" fullWidth>
                    <Select
                        value={filters.price_min || ''}
                        displayEmpty
                        onChange={(e) => updateFilter('price_min', e.target.value)}
                    >
                        <MenuItem value="">Min</MenuItem>
                        {[0, 200, 500, 1000, 2000, 5000].map(v => (
                            <MenuItem key={v} value={v}>৳{v}</MenuItem>
                        ))}
                    </Select>
                </FormControl>
                <FormControl size="small" fullWidth>
                    <Select
                        value={filters.price_max || ''}
                        displayEmpty
                        onChange={(e) => updateFilter('price_max', e.target.value)}
                    >
                        <MenuItem value="">Max</MenuItem>
                        {[500, 1000, 2000, 5000, 10000, 20000].map(v => (
                            <MenuItem key={v} value={v}>৳{v}</MenuItem>
                        ))}
                    </Select>
                </FormControl>
            </Box>

            {activeFilterCount > 0 && (
                <Button variant="outlined" size="small" fullWidth onClick={clearFilters}>
                    Clear All Filters
                </Button>
            )}
        </Box>
    );

    return (
        <Container maxWidth="lg" sx={{ py: 3 }}>
            {/* Header */}
            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
                <Box>
                    <Typography variant="h4">
                        {filters.search ? `Results for "${filters.search}"` : filters.gender ? `${filters.gender}'s Clothing` : 'All Products'}
                    </Typography>
                    <Typography variant="body2" color="text.secondary">
                        {pagination.totalItems} products found
                    </Typography>
                </Box>
                <Box sx={{ display: 'flex', gap: 1, alignItems: 'center' }}>
                    {isMobile && (
                        <Button
                            variant="outlined"
                            startIcon={<FilterList />}
                            onClick={() => setFilterDrawerOpen(true)}
                            size="small"
                        >
                            Filters {activeFilterCount > 0 && `(${activeFilterCount})`}
                        </Button>
                    )}
                    <FormControl size="small" sx={{ minWidth: 150 }}>
                        <Select
                            value={filters.ordering}
                            onChange={(e) => updateFilter('ordering', e.target.value)}
                        >
                            <MenuItem value="newest">Newest</MenuItem>
                            <MenuItem value="price_low">Price: Low to High</MenuItem>
                            <MenuItem value="price_high">Price: High to Low</MenuItem>
                            <MenuItem value="name">Name: A-Z</MenuItem>
                        </Select>
                    </FormControl>
                </Box>
            </Box>

            <Grid container spacing={3}>
                {/* Desktop Filter Sidebar */}
                {!isMobile && (
                    <Grid item md={3}>
                        <Box sx={{ position: 'sticky', top: 80 }}>
                            <FilterPanel />
                            <AffiliateWidget placement="sidebar" />
                        </Box>
                    </Grid>
                )}

                {/* Product Grid */}
                <Grid item xs={12} md={9}>
                    {loading ? (
                        <Grid container spacing={2}>
                            {[...Array(8)].map((_, i) => (
                                <Grid item xs={6} sm={4} md={4} key={i}>
                                    <Skeleton variant="rectangular" height={260} sx={{ borderRadius: 2 }} />
                                    <Skeleton width="60%" sx={{ mt: 1 }} />
                                    <Skeleton width="40%" />
                                </Grid>
                            ))}
                        </Grid>
                    ) : products.length === 0 ? (
                        <Box sx={{ textAlign: 'center', py: 8 }}>
                            <Typography variant="h6" color="text.secondary">No products found</Typography>
                            <Button onClick={clearFilters} sx={{ mt: 2 }}>Clear Filters</Button>
                        </Box>
                    ) : (
                        <>
                            <Grid container spacing={2}>
                                {products.map(product => (
                                    <Grid item xs={6} sm={4} md={4} key={product.id}>
                                        <ProductCard product={product} />
                                    </Grid>
                                ))}
                                {affiliateGridItems.map(item => (
                                    <Grid item xs={6} sm={4} md={4} key={`affiliate-${item.id}`}>
                                        <AffiliateProductCard item={item} />
                                    </Grid>
                                ))}
                            </Grid>
                            {pagination.totalPages > 1 && (
                                <Box sx={{ display: 'flex', justifyContent: 'center', mt: 4 }}>
                                    <Pagination
                                        count={pagination.totalPages}
                                        page={pagination.currentPage}
                                        onChange={(_, page) => updateFilter('page', page)}
                                        color="primary"
                                    />
                                </Box>
                            )}
                        </>
                    )}
                </Grid>
            </Grid>

            {/* Mobile Filter Drawer */}
            <Drawer anchor="bottom" open={filterDrawerOpen} onClose={() => setFilterDrawerOpen(false)}
                PaperProps={{ sx: { borderTopLeftRadius: 16, borderTopRightRadius: 16, maxHeight: '80vh' } }}
            >
                <FilterPanel />
            </Drawer>
        </Container>
    );
}
