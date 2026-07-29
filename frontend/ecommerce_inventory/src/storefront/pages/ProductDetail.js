import React, { useEffect, useState } from 'react';
import {
    Box, Container, Grid, Typography, Button, Rating, Chip, Divider,
    Tab, Tabs, IconButton, Dialog, DialogTitle, DialogContent,
    Table, TableBody, TableRow, TableCell, Skeleton, Breadcrumbs,
} from '@mui/material';
import { ShoppingCart, Add, Remove, NavigateNext } from '@mui/icons-material';
import { useParams, Link } from 'react-router-dom';
import { useDispatch } from 'react-redux';
import { addToCart } from '../../redux/reducer/cartSlice';
import useApi from '../../hooks/APIHandler';
import ProductCard from '../components/ProductCard';

export default function ProductDetail() {
    const { slug } = useParams();
    const [product, setProduct] = useState(null);
    const [selectedImage, setSelectedImage] = useState(0);
    const [selectedSize, setSelectedSize] = useState('');
    const [quantity, setQuantity] = useState(1);
    const [tab, setTab] = useState(0);
    const [sizeChartOpen, setSizeChartOpen] = useState(false);
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
                            edge-cropping it (matches ProductCard's treatment). Neutral
                            `action.hover` surface instead of a hardcoded hex so this reads
                            correctly in dark mode too. */}
                        <Box sx={{
                            width: '100%', height: { xs: 400, md: 500 },
                            borderRadius: 2, overflow: 'hidden', bgcolor: 'action.hover', mb: 1,
                            p: { xs: 2, md: 3 },
                        }}>
                            {images.length > 0 ? (
                                <img
                                    src={images[selectedImage]}
                                    alt={product.name}
                                    style={{ width: '100%', height: '100%', objectFit: 'contain' }}
                                    onError={(e) => { e.target.src = 'https://via.placeholder.com/500x600?text=No+Image'; }}
                                />
                            ) : (
                                <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100%' }}>
                                    <Typography color="text.secondary">No Image</Typography>
                                </Box>
                            )}
                        </Box>
                        {images.length > 1 && (
                            <Box sx={{ display: 'flex', gap: 1, overflowX: 'auto' }}>
                                {images.map((img, i) => (
                                    <Box
                                        key={i}
                                        onClick={() => setSelectedImage(i)}
                                        sx={{
                                            width: 64, height: 64, borderRadius: 1, overflow: 'hidden',
                                            cursor: 'pointer', flexShrink: 0,
                                            bgcolor: 'action.hover', p: 0.5,
                                            border: selectedImage === i ? '2px solid' : '2px solid transparent',
                                            borderColor: selectedImage === i ? 'secondary.main' : 'transparent',
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
                        <Typography variant="body2" color="text.secondary" sx={{ textTransform: 'uppercase', letterSpacing: 1 }}>
                            {product.brand}
                        </Typography>
                    )}
                    <Typography variant="h4" sx={{ fontWeight: 700, mb: 1 }}>{product.name}</Typography>

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
                    <Box sx={{ display: 'flex', alignItems: 'baseline', gap: 2, mb: 3 }}>
                        <Typography variant="h4" sx={{ fontWeight: 800, color: hasDiscount ? 'secondary.main' : 'text.primary' }}>
                            ৳{price?.toLocaleString()}
                        </Typography>
                        {hasDiscount && (
                            <>
                                <Typography variant="h6" sx={{ textDecoration: 'line-through', color: 'text.secondary' }}>
                                    ৳{product.initial_selling_price?.toLocaleString()}
                                </Typography>
                                <Chip label={`-${product.discount_percentage}%`} color="secondary" size="small" />
                            </>
                        )}
                    </Box>

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
                                {Object.keys(sizeChart).length > 0 && (
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
                                        sx={{ minWidth: 48 }}
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
                        <Box sx={{ display: 'flex', alignItems: 'center', border: '1px solid', borderColor: 'divider', borderRadius: 1 }}>
                            <IconButton size="small" onClick={() => setQuantity(q => Math.max(1, q - 1))}><Remove /></IconButton>
                            <Typography sx={{ px: 2, minWidth: 30, textAlign: 'center' }}>{quantity}</Typography>
                            <IconButton size="small" onClick={() => setQuantity(q => q + 1)}><Add /></IconButton>
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
                        {inStock ? `Add to Cart - ৳${(price * quantity)?.toLocaleString()}` : 'Out of Stock'}
                    </Button>

                    {/* Description */}
                    <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                        {product.description}
                    </Typography>

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

            {/* Tabs: Specifications, Reviews, Q&A */}
            <Box sx={{ mt: 6 }}>
                <Tabs value={tab} onChange={(_, v) => setTab(v)} sx={{ mb: 3 }}>
                    <Tab label="Specifications" />
                    <Tab label={`Reviews (${product.review_count})`} />
                    <Tab label="Questions & Answers" />
                </Tabs>

                {tab === 0 && Object.keys(specs).length > 0 && (
                    <Table size="small">
                        <TableBody>
                            {Object.entries(specs).map(([key, val]) => (
                                <TableRow key={key}>
                                    <TableCell sx={{ fontWeight: 600, width: '30%', textTransform: 'capitalize' }}>
                                        {key.replace(/_/g, ' ')}
                                    </TableCell>
                                    <TableCell>{typeof val === 'object' ? JSON.stringify(val) : String(val)}</TableCell>
                                </TableRow>
                            ))}
                        </TableBody>
                    </Table>
                )}

                {tab === 1 && (
                    <Box>
                        {product.reviews?.length > 0 ? product.reviews.map(review => (
                            <Box key={review.id} sx={{ mb: 3, pb: 3, borderBottom: '1px solid', borderColor: 'divider' }}>
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
                            <Box key={q.id} sx={{ mb: 3, pb: 3, borderBottom: '1px solid', borderColor: 'divider' }}>
                                <Typography variant="body2" fontWeight={600}>Q: {q.question}</Typography>
                                {q.answer && <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>A: {q.answer}</Typography>}
                            </Box>
                        )) : (
                            <Typography color="text.secondary">No questions yet.</Typography>
                        )}
                    </Box>
                )}
            </Box>

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

            {/* Size Chart Dialog */}
            <Dialog open={sizeChartOpen} onClose={() => setSizeChartOpen(false)} maxWidth="sm" fullWidth>
                <DialogTitle>Size Chart</DialogTitle>
                <DialogContent>
                    <Table size="small">
                        <TableBody>
                            <TableRow>
                                <TableCell sx={{ fontWeight: 700 }}>Size</TableCell>
                                {Object.keys(sizeChart).length > 0 &&
                                    Object.keys(Object.values(sizeChart)[0] || {}).map(key => (
                                        <TableCell key={key} sx={{ fontWeight: 700, textTransform: 'capitalize' }}>{key}</TableCell>
                                    ))
                                }
                            </TableRow>
                            {Object.entries(sizeChart).map(([size, measurements]) => (
                                <TableRow key={size}>
                                    <TableCell sx={{ fontWeight: 600 }}>{size}</TableCell>
                                    {Object.values(measurements).map((val, i) => (
                                        <TableCell key={i}>{val}"</TableCell>
                                    ))}
                                </TableRow>
                            ))}
                        </TableBody>
                    </Table>
                </DialogContent>
            </Dialog>
        </Container>
    );
}
