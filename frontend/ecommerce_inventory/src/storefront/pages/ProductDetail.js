import React, { useEffect, useState } from 'react';
import {
    Box, Container, Grid, Typography, Button, Rating, Chip, Divider,
    Tab, Tabs, IconButton, Dialog, DialogTitle, DialogContent, Paper,
    Table, TableHead, TableBody, TableRow, TableCell, Skeleton, Breadcrumbs,
} from '@mui/material';
import { ShoppingCart, Add, Remove, NavigateNext, LocalShipping } from '@mui/icons-material';
import { useParams, Link } from 'react-router-dom';
import { useDispatch } from 'react-redux';
import { addToCart } from '../../redux/reducer/cartSlice';
import useApi from '../../hooks/APIHandler';
import ProductCard from '../components/ProductCard';
import { taka } from '../format';

export default function ProductDetail() {
    const { slug } = useParams();
    const [product, setProduct] = useState(null);
    const [selectedImage, setSelectedImage] = useState(0);
    const [selectedSize, setSelectedSize] = useState('');
    const [quantity, setQuantity] = useState(1);
    const [tab, setTab] = useState(0);
    const [sizeChartOpen, setSizeChartOpen] = useState(false);
    const [sizeChartUnit, setSizeChartUnit] = useState('inch');
    const { callApi, loading } = useApi();
    const dispatch = useDispatch();

    useEffect(() => {
        const fetchProduct = async () => {
            const res = await callApi({ url: `store/products/${slug}/` });
            if (res?.data?.data) {
                setProduct(res.data.data);
                const vs = res.data.data.variants;
                if (Array.isArray(vs) && vs.length > 0) {
                    const firstInStock = vs.find(v => v.in_stock) || vs[0];
                    setSelectedSize(firstInStock.size);
                } else {
                    const sizes = res.data.data.available_sizes;
                    if (Array.isArray(sizes) && sizes.length > 0) setSelectedSize(sizes[0]);
                }
            }
        };
        fetchProduct();
        window.scrollTo(0, 0);
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [slug]);

    if (loading || !product) {
        return (
            <Container maxWidth="lg" sx={{ py: 4 }}>
                <Grid container spacing={4}>
                    <Grid item xs={12} md={6}>
                        <Skeleton variant="rectangular" height={500} sx={{ borderRadius: 2 }} />
                    </Grid>
                    <Grid item xs={12} md={6}>
                        <Skeleton width="40%" height={30} />
                        <Skeleton width="80%" height={40} />
                        <Skeleton width="30%" height={40} />
                    </Grid>
                </Grid>
            </Container>
        );
    }

    const images = Array.isArray(product.image) ? product.image : [];
    const variants = Array.isArray(product.variants) ? product.variants : [];
    const selectedVariant = variants.find(v => v.size === selectedSize) || variants[0] || null;
    const price = selectedVariant
        ? Number(selectedVariant.effective_price)
        : (product.discount_price || product.initial_selling_price);
    const hasDiscount = product.discount_price && product.discount_price < product.initial_selling_price;
    // Prefer real variant sizes; fall back to the legacy available_sizes list.
    const variantSizes = [...new Set(variants.map(v => v.size).filter(Boolean))];
    const sizes = variantSizes.length
        ? variantSizes
        : (Array.isArray(product.available_sizes) ? product.available_sizes : []);
    const inStock = selectedVariant ? selectedVariant.in_stock : false;
    const specs = product.specifications && typeof product.specifications === 'object' ? product.specifications : {};
    const highlights = Array.isArray(product.highlights) ? product.highlights : [];
    const sizeChart = product.size_chart && typeof product.size_chart === 'object' ? product.size_chart : {};
    // Fashion-only, and never an empty table: a size chart is only shown at
    // all when there is at least one size with at least one measurement --
    // most Fabrilife products (and every non-fashion product) have none.
    const sizeChartSizes = Object.keys(sizeChart).filter(
        size => sizeChart[size] && Object.keys(sizeChart[size]).length > 0
    );
    const sizeChartMeasurementKeys = sizeChartSizes.length
        ? [...new Set(sizeChartSizes.flatMap(size => Object.keys(sizeChart[size])))]
        : [];
    const hasSizeChart = sizeChartSizes.length > 0 && sizeChartMeasurementKeys.length > 0;
    // The source data is in inches (see catalog.models.Products.size_chart);
    // CM is a straight unit conversion computed here rather than sourced
    // separately, so it can never drift out of sync with the inch values.
    const inchToCm = (value) => Math.round(value * 2.54 * 10) / 10;
    // `effective_shipping_fee` is always a number from the storefront API --
    // this product's own override, or the store's flat rate when it has none
    // -- so the customer is never shown nothing here. `free_shipping` is the
    // separate, explicit promo flag (distinct from shipping_fee == 0, see
    // docs/SHIPPING_FEES.md); either one flips this box into its "Free
    // delivery" state, which always takes precedence over the "Delivery: ৳X"
    // text -- the two never show together, since it's the same box.
    const shippingFee = product.effective_shipping_fee;
    const freeDelivery = !!product.free_shipping || shippingFee === 0;

    const handleAddToCart = () => {
        if (!selectedVariant || !inStock) return;
        const firstImage = Array.isArray(product.image) && product.image.length ? product.image[0] : '';
        dispatch(addToCart({
            variantId: selectedVariant.id,
            productId: product.id,
            name: product.name,
            slug: product.slug,
            image: firstImage,
            sku: selectedVariant.sku,
            size: selectedVariant.size,
            color: selectedVariant.color,
            price: Number(selectedVariant.effective_price),
            stock: selectedVariant.stock_quantity,
            quantity,
        }));
    };

    return (
        <Container maxWidth="lg" sx={{ py: 3 }}>
            {/* Breadcrumbs */}
            <Breadcrumbs separator={<NavigateNext fontSize="small" />} sx={{ mb: 2 }}>
                <Typography component={Link} to="/" color="inherit" sx={{ textDecoration: 'none' }}>Home</Typography>
                <Typography component={Link} to="/shop" color="inherit" sx={{ textDecoration: 'none' }}>Shop</Typography>
                <Typography color="text.primary">{product.name}</Typography>
            </Breadcrumbs>

            <Grid container spacing={4}>
                {/* Images */}
                <Grid item xs={12} md={6}>
                    <Box sx={{ position: 'sticky', top: 80 }}>
                        {/* Partner photos have inconsistent aspect ratios and tight crops --
                            padding + object-fit: contain shows the whole product instead of
                            edge-cropping it (matches ProductCard's treatment). Explicit white,
                            not a theme surface token: the photos are shot on white, so a white
                            tile is what makes them read correctly, even in dark mode (a dark
                            tile would show an obvious white rectangle around the photo). */}
                        <Paper
                            variant="outlined"
                            sx={{
                                width: '100%', maxWidth: '100%', height: { xs: 400, md: 500 },
                                // boxSizing must be explicit here: this Box has both a
                                // percentage width AND padding, and the storefront route is
                                // never wrapped in <CssBaseline /> (only the admin/food shells
                                // are), so it does not inherit the browser-default-defeating
                                // `border-box` reset. Under the browser's real default
                                // (content-box), the padding below is added ON TOP of the
                                // 100% width, so this tile silently renders wider than its
                                // Grid column and its opaque #fff background paints over the
                                // start of the details column's text -- that was the reported
                                // "image overlapping the product details" bug (brand/title/
                                // price clipped on the left edge). Do not remove this.
                                boxSizing: 'border-box',
                                borderRadius: 2, overflow: 'hidden', bgcolor: '#fff', mb: 1.5,
                                p: { xs: 2, md: 3 },
                            }}>
                            {images.length > 0 ? (
                                <img
                                    src={images[selectedImage]}
                                    alt={product.name}
                                    style={{ width: '100%', height: '100%', objectFit: 'contain', display: 'block' }}
                                    onError={(e) => { e.target.src = 'https://via.placeholder.com/500x600?text=No+Image'; }}
                                />
                            ) : (
                                <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100%' }}>
                                    <Typography color="text.secondary">No Image</Typography>
                                </Box>
                            )}
                        </Paper>
                        {images.length > 1 && (
                            <Box sx={{ display: 'flex', gap: 1, overflowX: 'auto', pb: 0.5 }}>
                                {images.map((img, i) => (
                                    <Box
                                        key={i}
                                        onClick={() => setSelectedImage(i)}
                                        sx={{
                                            width: 64, height: 64, borderRadius: 1, overflow: 'hidden',
                                            cursor: 'pointer', flexShrink: 0,
                                            // Same content-box trap as the main image tile above:
                                            // a fixed width plus padding needs an explicit
                                            // border-box or it renders larger than 64px.
                                            boxSizing: 'border-box',
                                            bgcolor: '#fff', p: 0.5,
                                            transition: 'border-color 120ms, transform 120ms',
                                            '&:hover': { transform: 'translateY(-1px)' },
                                            border: '2px solid',
                                            borderColor: selectedImage === i ? 'secondary.main' : 'divider',
                                        }}
                                    >
                                        <img src={img} alt="" style={{ width: '100%', height: '100%', objectFit: 'contain' }} />
                                    </Box>
                                ))}
                            </Box>
                        )}
                    </Box>
                </Grid>

                {/* Product Info */}
                <Grid item xs={12} md={6}>
                    {product.brand && (
                        <Typography
                            variant="overline"
                            color="secondary.main"
                            sx={{ fontWeight: 700, letterSpacing: 1.2, lineHeight: 1.2, display: 'block' }}
                        >
                            {product.brand}
                        </Typography>
                    )}
                    <Typography
                        variant="h4"
                        component="h1"
                        sx={{ fontWeight: 700, mb: 1, fontSize: { xs: '1.5rem', sm: '1.75rem', md: '2rem' }, lineHeight: 1.25 }}
                    >
                        {product.name}
                    </Typography>

                    {/* Rating */}
                    {product.average_rating > 0 && (
                        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 2 }}>
                            <Rating value={product.average_rating} precision={0.5} readOnly />
                            <Typography variant="body2" color="text.secondary">
                                {product.average_rating} ({product.review_count} reviews)
                            </Typography>
                        </Box>
                    )}

                    {/* Price */}
                    <Box sx={{ display: 'flex', alignItems: 'baseline', gap: 2, mb: 3, flexWrap: 'wrap' }}>
                        <Typography
                            variant="h4"
                            sx={{ fontWeight: 800, fontSize: { xs: '1.6rem', md: '2rem' }, color: hasDiscount ? 'secondary.main' : 'text.primary' }}
                        >
                            {taka(price)}
                        </Typography>
                        {hasDiscount && (
                            <>
                                <Typography variant="h6" sx={{ textDecoration: 'line-through', color: 'text.secondary' }}>
                                    {taka(product.initial_selling_price)}
                                </Typography>
                                <Chip label={`-${product.discount_percentage}%`} color="secondary" size="small" />
                            </>
                        )}
                    </Box>

                    {/* Delivery fee -- more prominent than the card's quiet caption, and
                        always shown (falls back to the store's flat rate) so the customer
                        knows the shipping cost before they add to cart. */}
                    {(shippingFee != null || freeDelivery) && (
                        <Box sx={{
                            display: 'flex', alignItems: 'center', gap: 1, mb: 2,
                            px: 1.5, py: 1, borderRadius: 1,
                            bgcolor: freeDelivery ? 'success.main' : 'action.hover',
                            color: freeDelivery ? 'success.contrastText' : 'text.primary',
                        }}>
                            <LocalShipping fontSize="small" />
                            <Typography variant="body2" fontWeight={600}>
                                {freeDelivery ? 'Free delivery' : `Delivery: ${taka(shippingFee)}`}
                            </Typography>
                        </Box>
                    )}

                    {/* Material & Color */}
                    <Box sx={{ display: 'flex', gap: 2, mb: 2, flexWrap: 'wrap' }}>
                        {product.material && <Chip label={product.material} variant="outlined" size="small" />}
                        {product.color && <Chip label={product.color} variant="outlined" size="small" />}
                        {product.gender && <Chip label={product.gender} variant="outlined" size="small" />}
                    </Box>

                    <Divider sx={{ my: 2 }} />

                    {/* Size Selection */}
                    {sizes.length > 0 && (
                        <Box sx={{ mb: 3 }}>
                            <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1 }}>
                                <Typography variant="subtitle2" fontWeight={700}>Select Size</Typography>
                                {hasSizeChart && (
                                    <Button size="small" onClick={() => setSizeChartOpen(true)}>Size Chart</Button>
                                )}
                            </Box>
                            <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap' }}>
                                {sizes.map(size => (
                                    <Button
                                        key={size}
                                        variant={selectedSize === size ? 'contained' : 'outlined'}
                                        color={selectedSize === size ? 'primary' : 'inherit'}
                                        onClick={() => setSelectedSize(size)}
                                        sx={{ minWidth: 48, height: 40, fontWeight: 600 }}
                                    >
                                        {size}
                                    </Button>
                                ))}
                            </Box>
                        </Box>
                    )}

                    {/* Quantity */}
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, mb: 3 }}>
                        <Typography variant="subtitle2" fontWeight={700}>Quantity</Typography>
                        <Box sx={{
                            display: 'flex', alignItems: 'center', border: '1px solid',
                            borderColor: 'divider', borderRadius: 1.5, overflow: 'hidden',
                        }}>
                            <IconButton
                                size="small" onClick={() => setQuantity(q => Math.max(1, q - 1))}
                                disabled={quantity <= 1}
                                sx={{ borderRadius: 0 }}
                            ><Remove fontSize="small" /></IconButton>
                            <Typography sx={{ px: 2.5, minWidth: 32, textAlign: 'center', fontWeight: 600 }}>{quantity}</Typography>
                            <IconButton size="small" onClick={() => setQuantity(q => q + 1)} sx={{ borderRadius: 0 }}>
                                <Add fontSize="small" />
                            </IconButton>
                        </Box>
                    </Box>

                    {/* Stock status */}
                    <Box sx={{ mb: 1 }}>
                        {selectedVariant ? (
                            inStock ? (
                                <Chip
                                    size="small" color="success" variant="outlined"
                                    label={selectedVariant.stock_quantity <= 5
                                        ? `Only ${selectedVariant.stock_quantity} left`
                                        : 'In stock'}
                                />
                            ) : (
                                <Chip size="small" color="error" variant="outlined" label="Out of stock" />
                            )
                        ) : (
                            <Chip size="small" color="warning" variant="outlined" label="Unavailable" />
                        )}
                    </Box>

                    {/* Add to Cart */}
                    <Button
                        variant="contained"
                        color="secondary"
                        size="large"
                        fullWidth
                        disabled={!inStock}
                        startIcon={<ShoppingCart />}
                        onClick={handleAddToCart}
                        sx={{ py: 1.5, mb: 2, fontSize: '1.1rem' }}
                    >
                        {inStock ? `Add to Cart - ${taka(price * quantity)}` : 'Out of Stock'}
                    </Button>

                    {/* Description */}
                    {product.description && (
                        <Box sx={{ mb: 2 }}>
                            <Typography variant="subtitle2" fontWeight={700} gutterBottom>Description</Typography>
                            <Typography variant="body2" color="text.secondary" sx={{ lineHeight: 1.7 }}>
                                {product.description}
                            </Typography>
                        </Box>
                    )}

                    {/* Highlights */}
                    {highlights.length > 0 && (
                        <Box sx={{ mb: 2 }}>
                            <Typography variant="subtitle2" fontWeight={700} gutterBottom>Highlights</Typography>
                            <Box component="ul" sx={{ m: 0, pl: 2 }}>
                                {highlights.map((h, i) => (
                                    <Typography component="li" variant="body2" key={i} color="text.secondary">{h}</Typography>
                                ))}
                            </Box>
                        </Box>
                    )}
                </Grid>
            </Grid>

            {/* Specifications, Reviews, Q&A */}
            <Paper variant="outlined" sx={{ mt: 6, borderRadius: 2, overflow: 'hidden' }}>
                <Tabs
                    value={tab}
                    onChange={(_, v) => setTab(v)}
                    variant="scrollable"
                    scrollButtons="auto"
                    allowScrollButtonsMobile
                    sx={{ borderBottom: '1px solid', borderColor: 'divider', px: 1 }}
                >
                    <Tab label="Specifications" />
                    <Tab label={`Reviews (${product.review_count})`} />
                    <Tab label="Questions & Answers" />
                </Tabs>

                <Box sx={{ p: { xs: 2, sm: 3 } }}>
                    {tab === 0 && (
                        Object.keys(specs).length > 0 ? (
                            <Table size="small">
                                <TableBody>
                                    {Object.entries(specs).map(([key, val]) => (
                                        <TableRow
                                            key={key}
                                            sx={{
                                                '&:nth-of-type(odd)': { bgcolor: 'action.hover' },
                                                '& td': { border: 0 },
                                            }}
                                        >
                                            <TableCell sx={{ fontWeight: 600, width: '30%', textTransform: 'capitalize' }}>
                                                {key.replace(/_/g, ' ')}
                                            </TableCell>
                                            <TableCell>{typeof val === 'object' ? JSON.stringify(val) : String(val)}</TableCell>
                                        </TableRow>
                                    ))}
                                </TableBody>
                            </Table>
                        ) : (
                            <Typography color="text.secondary">No specifications available.</Typography>
                        )
                    )}

                    {tab === 1 && (
                        <Box>
                            {product.reviews?.length > 0 ? product.reviews.map(review => (
                                <Box key={review.id} sx={{ mb: 3, pb: 3, '&:not(:last-child)': { borderBottom: '1px solid', borderColor: 'divider' } }}>
                                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
                                        <Rating value={review.rating} size="small" readOnly />
                                        <Typography variant="body2" fontWeight={600}>{review.reviewer_name}</Typography>
                                    </Box>
                                    <Typography variant="body2" color="text.secondary">{review.reviews}</Typography>
                                </Box>
                            )) : (
                                <Typography color="text.secondary">No reviews yet.</Typography>
                            )}
                        </Box>
                    )}

                    {tab === 2 && (
                        <Box>
                            {product.questions?.length > 0 ? product.questions.map(q => (
                                <Box key={q.id} sx={{ mb: 3, pb: 3, '&:not(:last-child)': { borderBottom: '1px solid', borderColor: 'divider' } }}>
                                    <Typography variant="body2" fontWeight={600}>Q: {q.question}</Typography>
                                    {q.answer && <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>A: {q.answer}</Typography>}
                                </Box>
                            )) : (
                                <Typography color="text.secondary">No questions yet.</Typography>
                            )}
                        </Box>
                    )}
                </Box>
            </Paper>

            {/* Related Products */}
            {product.related_products?.length > 0 && (
                <Box sx={{ mt: 6 }}>
                    <Typography variant="h5" sx={{ mb: 3 }}>You May Also Like</Typography>
                    <Grid container spacing={2}>
                        {product.related_products.slice(0, 4).map(p => (
                            <Grid item xs={6} sm={3} key={p.id}>
                                <ProductCard product={p} />
                            </Grid>
                        ))}
                    </Grid>
                </Box>
            )}

            {/* Size Chart Dialog -- only ever mounted with content when there is
                real data (hasSizeChart), so it can never render an empty table. */}
            {hasSizeChart && (
                <Dialog open={sizeChartOpen} onClose={() => setSizeChartOpen(false)} maxWidth="xs" fullWidth>
                    <DialogTitle sx={{ pb: 0.5 }}>
                        Size chart
                        <Typography variant="body2" color="text.secondary" sx={{ fontWeight: 400 }}>
                            In {sizeChartUnit === 'cm' ? 'centimeters' : 'inches'} (Expected Deviation &lt; 3%)
                        </Typography>
                    </DialogTitle>
                    <DialogContent>
                        <Tabs
                            value={sizeChartUnit}
                            onChange={(_, v) => setSizeChartUnit(v)}
                            sx={{ mb: 2, minHeight: 36 }}
                        >
                            <Tab value="inch" label="INCH" sx={{ minHeight: 36, py: 0.5 }} />
                            <Tab value="cm" label="CM" sx={{ minHeight: 36, py: 0.5 }} />
                        </Tabs>
                        <Table size="small">
                            <TableHead>
                                <TableRow>
                                    <TableCell sx={{ fontWeight: 700 }}>Size</TableCell>
                                    {sizeChartMeasurementKeys.map(key => (
                                        <TableCell key={key} sx={{ fontWeight: 700, textTransform: 'capitalize' }}>
                                            {key.replace(/_/g, ' ')}
                                        </TableCell>
                                    ))}
                                </TableRow>
                            </TableHead>
                            <TableBody>
                                {sizeChartSizes.map(size => (
                                    <TableRow key={size}>
                                        <TableCell sx={{ fontWeight: 600 }}>{size}</TableCell>
                                        {sizeChartMeasurementKeys.map(key => {
                                            const raw = sizeChart[size]?.[key];
                                            if (raw == null) return <TableCell key={key}>-</TableCell>;
                                            const value = sizeChartUnit === 'cm' ? inchToCm(raw) : raw;
                                            return <TableCell key={key}>{value}{sizeChartUnit === 'cm' ? ' cm' : '"'}</TableCell>;
                                        })}
                                    </TableRow>
                                ))}
                            </TableBody>
                        </Table>
                    </DialogContent>
                </Dialog>
            )}
        </Container>
    );
}
