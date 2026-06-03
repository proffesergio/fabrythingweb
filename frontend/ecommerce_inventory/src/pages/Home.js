import React, { useEffect, useState } from 'react';
import { Grid, Card, CardContent, Typography, Box, Chip, Button } from '@mui/material';
import {
    ShoppingCart, TrendingUp, People, Inventory,
    ArrowUpward, ArrowDownward, Visibility,
} from '@mui/icons-material';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, PieChart, Pie, Cell } from 'recharts';
import { useNavigate } from 'react-router-dom';
import { getUser } from '../utils/Helper';
import useApi from '../hooks/APIHandler';

const STATUS_COLORS = {
    DRAFT: '#9E9E9E', SENT: '#2196F3', DELIVERED: '#4CAF50',
    CANCELLED: '#F44336', COMPLETED: '#8BC34A',
};

const Home = () => {
    const [data, setData] = useState(null);
    const { callApi, loading } = useApi();
    const navigate = useNavigate();
    const user = getUser();

    useEffect(() => {
        const fetchDashboard = async () => {
            const res = await callApi({ url: 'store/admin/dashboard/' });
            if (res?.data?.data) setData(res.data.data);
        };
        fetchDashboard();
    }, []);

    const StatCard = ({ title, value, icon, color, subtitle }) => (
        <Card>
            <CardContent>
                <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                    <Box>
                        <Typography variant="body2" color="text.secondary">{title}</Typography>
                        <Typography variant="h4" sx={{ fontWeight: 700, my: 0.5 }}>{value}</Typography>
                        {subtitle && <Typography variant="caption" color="text.secondary">{subtitle}</Typography>}
                    </Box>
                    <Box sx={{ bgcolor: color + '20', p: 1, borderRadius: 2 }}>
                        {React.cloneElement(icon, { sx: { color: color, fontSize: 28 } })}
                    </Box>
                </Box>
            </CardContent>
        </Card>
    );

    if (!data) {
        return (
            <Box sx={{ p: 2 }}>
                <Typography variant="h5" gutterBottom>Welcome, {user?.username}</Typography>
                <Typography color="text.secondary">Loading dashboard...</Typography>
            </Box>
        );
    }

    // Prepare pie chart data
    const pieData = Object.entries(data.status_distribution || {})
        .filter(([_, count]) => count > 0)
        .map(([status, count]) => ({ name: status, value: count, color: STATUS_COLORS[status] || '#999' }));

    return (
        <Box>
            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
                <Box>
                    <Typography variant="h5" fontWeight={700}>Welcome back, {user?.username}</Typography>
                    <Typography variant="body2" color="text.secondary">Here's what's happening with your store</Typography>
                </Box>
            </Box>

            {/* Stat Cards */}
            <Grid container spacing={2} sx={{ mb: 3 }}>
                <Grid item xs={6} md={3}>
                    <StatCard
                        title="Today's Orders"
                        value={data.orders?.today || 0}
                        icon={<ShoppingCart />}
                        color="#2196F3"
                        subtitle={`${data.orders?.this_week || 0} this week`}
                    />
                </Grid>
                <Grid item xs={6} md={3}>
                    <StatCard
                        title="Monthly Orders"
                        value={data.orders?.this_month || 0}
                        icon={<TrendingUp />}
                        color="#4CAF50"
                        subtitle={`${data.orders?.total || 0} total`}
                    />
                </Grid>
                <Grid item xs={6} md={3}>
                    <StatCard
                        title="Today's Revenue"
                        value={`৳${(data.revenue?.today || 0).toLocaleString()}`}
                        icon={<TrendingUp />}
                        color="#FF9800"
                        subtitle={`৳${(data.revenue?.this_month || 0).toLocaleString()} this month`}
                    />
                </Grid>
                <Grid item xs={6} md={3}>
                    <StatCard
                        title="Active Products"
                        value={data.total_products || 0}
                        icon={<Inventory />}
                        color="#9C27B0"
                        subtitle={`${data.total_customers || 0} customers`}
                    />
                </Grid>
            </Grid>

            <Grid container spacing={2}>
                {/* Order Status Chart */}
                {pieData.length > 0 && (
                    <Grid item xs={12} md={4}>
                        <Card sx={{ p: 2, height: '100%' }}>
                            <Typography variant="h6" gutterBottom>Order Status</Typography>
                            <Box sx={{ height: 250 }}>
                                <ResponsiveContainer>
                                    <PieChart>
                                        <Pie data={pieData} dataKey="value" nameKey="name" cx="50%" cy="50%" outerRadius={80} label>
                                            {pieData.map((entry, i) => (
                                                <Cell key={i} fill={entry.color} />
                                            ))}
                                        </Pie>
                                        <Tooltip />
                                    </PieChart>
                                </ResponsiveContainer>
                            </Box>
                            <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5, mt: 1 }}>
                                {pieData.map(d => (
                                    <Chip key={d.name} label={`${d.name}: ${d.value}`} size="small"
                                        sx={{ bgcolor: d.color + '20', color: d.color, fontWeight: 600 }} />
                                ))}
                            </Box>
                        </Card>
                    </Grid>
                )}

                {/* Recent Orders */}
                <Grid item xs={12} md={pieData.length > 0 ? 8 : 12}>
                    <Card sx={{ p: 2 }}>
                        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
                            <Typography variant="h6">Recent Orders</Typography>
                            <Button size="small" onClick={() => navigate('/admin/manage/salesorder')}>View All</Button>
                        </Box>
                        {data.recent_orders?.length > 0 ? data.recent_orders.map(order => (
                            <Box key={order.id} sx={{
                                display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                                py: 1.5, borderBottom: '1px solid', borderColor: 'divider',
                            }}>
                                <Box>
                                    <Typography variant="subtitle2" fontWeight={600}>{order.so_code}</Typography>
                                    <Typography variant="caption" color="text.secondary">
                                        {new Date(order.created_at).toLocaleDateString()} | {order.item_count} items
                                    </Typography>
                                </Box>
                                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                                    <Typography variant="subtitle2" fontWeight={700}>
                                        ৳{order.total_amount?.toLocaleString()}
                                    </Typography>
                                    <Chip
                                        label={order.status}
                                        size="small"
                                        sx={{
                                            bgcolor: (STATUS_COLORS[order.status] || '#999') + '20',
                                            color: STATUS_COLORS[order.status] || '#999',
                                            fontWeight: 600,
                                        }}
                                    />
                                </Box>
                            </Box>
                        )) : (
                            <Typography color="text.secondary" sx={{ py: 4, textAlign: 'center' }}>
                                No orders yet. Orders will appear here once customers start shopping.
                            </Typography>
                        )}
                    </Card>
                </Grid>

                {/* Top Products */}
                {data.top_products?.length > 0 && (
                    <Grid item xs={12} md={6}>
                        <Card sx={{ p: 2 }}>
                            <Typography variant="h6" gutterBottom>Top Products</Typography>
                            {data.top_products.map((product, i) => (
                                <Box key={i} sx={{
                                    display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                                    py: 1, borderBottom: '1px solid', borderColor: 'divider',
                                }}>
                                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                                        <Typography variant="body2" sx={{
                                            width: 24, height: 24, borderRadius: '50%', bgcolor: 'primary.main',
                                            color: 'white', display: 'flex', alignItems: 'center', justifyContent: 'center',
                                            fontSize: '0.75rem', fontWeight: 700,
                                        }}>
                                            {i + 1}
                                        </Typography>
                                        <Typography variant="body2" fontWeight={600}>{product.product_id__name}</Typography>
                                    </Box>
                                    <Typography variant="caption" color="text.secondary">
                                        {product.total_sold} sold | {product.order_count} orders
                                    </Typography>
                                </Box>
                            ))}
                        </Card>
                    </Grid>
                )}
            </Grid>
        </Box>
    );
};

export default Home;
