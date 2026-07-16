import React, { useState } from 'react';
import {
    Box, Container, Card, Typography, TextField, Button, Tab, Tabs, Alert,
    CircularProgress, Divider,
} from '@mui/material';
import { useNavigate, useSearchParams, Link } from 'react-router-dom';
import { useDispatch } from 'react-redux';
import { login } from '../../redux/reducer/IsLoggedInReducer';
import { syncCartOnLogin } from '../../redux/reducer/cartSlice';
import useApi from '../../hooks/APIHandler';

export default function CustomerAuth() {
    const [tab, setTab] = useState(0);
    const [error, setError] = useState('');
    const { callApi, loading } = useApi();
    const navigate = useNavigate();
    const dispatch = useDispatch();
    const [searchParams] = useSearchParams();
    const redirect = searchParams.get('redirect') || '/';

    const [loginData, setLoginData] = useState({ username: '', password: '' });
    const [signupData, setSignupData] = useState({
        username: '', email: '', password: '', first_name: '', last_name: '', phone: '',
    });

    const handleLogin = async (e) => {
        e.preventDefault();
        setError('');
        const res = await callApi({ url: 'store/auth/login/', method: 'POST', body: loginData });
        if (res?.data?.access) {
            localStorage.setItem('token', res.data.access);
            dispatch(login());
            await dispatch(syncCartOnLogin());  // merge guest cart into the account
            navigate(redirect);
        }
    };

    const handleSignup = async (e) => {
        e.preventDefault();
        setError('');
        if (signupData.password.length < 8) {
            setError('Password must be at least 8 characters');
            return;
        }
        const res = await callApi({ url: 'store/auth/signup/', method: 'POST', body: signupData });
        if (res?.data?.access) {
            localStorage.setItem('token', res.data.access);
            dispatch(login());
            await dispatch(syncCartOnLogin());  // merge guest cart into the new account
            navigate(redirect);
        }
    };

    return (
        <Container maxWidth="sm" sx={{ py: 6 }}>
            <Box sx={{ textAlign: 'center', mb: 4 }}>
                <Typography variant="h4" fontWeight={800} component={Link} to="/" sx={{ textDecoration: 'none', color: 'text.primary' }}>
                    FABRYTHING
                </Typography>
            </Box>

            <Card sx={{ p: 4 }}>
                <Tabs value={tab} onChange={(_, v) => setTab(v)} variant="fullWidth" sx={{ mb: 3 }}>
                    <Tab label="Login" />
                    <Tab label="Create Account" />
                </Tabs>

                {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}

                {tab === 0 ? (
                    <form onSubmit={handleLogin}>
                        <TextField
                            fullWidth label="Username" required sx={{ mb: 2 }}
                            value={loginData.username}
                            onChange={(e) => setLoginData({ ...loginData, username: e.target.value })}
                        />
                        <TextField
                            fullWidth label="Password" type="password" required sx={{ mb: 3 }}
                            value={loginData.password}
                            onChange={(e) => setLoginData({ ...loginData, password: e.target.value })}
                        />
                        <Button type="submit" variant="contained" color="secondary" fullWidth size="large" disabled={loading}>
                            {loading ? <CircularProgress size={24} /> : 'Login'}
                        </Button>
                    </form>
                ) : (
                    <form onSubmit={handleSignup}>
                        <Box sx={{ display: 'flex', gap: 2, mb: 2 }}>
                            <TextField
                                fullWidth label="First Name"
                                value={signupData.first_name}
                                onChange={(e) => setSignupData({ ...signupData, first_name: e.target.value })}
                            />
                            <TextField
                                fullWidth label="Last Name"
                                value={signupData.last_name}
                                onChange={(e) => setSignupData({ ...signupData, last_name: e.target.value })}
                            />
                        </Box>
                        <TextField
                            fullWidth label="Username" required sx={{ mb: 2 }}
                            value={signupData.username}
                            onChange={(e) => setSignupData({ ...signupData, username: e.target.value })}
                        />
                        <TextField
                            fullWidth label="Email" type="email" required sx={{ mb: 2 }}
                            value={signupData.email}
                            onChange={(e) => setSignupData({ ...signupData, email: e.target.value })}
                        />
                        <TextField
                            fullWidth label="Phone Number" placeholder="01XXXXXXXXX" sx={{ mb: 2 }}
                            value={signupData.phone}
                            onChange={(e) => setSignupData({ ...signupData, phone: e.target.value })}
                        />
                        <TextField
                            fullWidth label="Password" type="password" required sx={{ mb: 3 }}
                            value={signupData.password}
                            onChange={(e) => setSignupData({ ...signupData, password: e.target.value })}
                            helperText="At least 8 characters"
                        />
                        <Button type="submit" variant="contained" color="secondary" fullWidth size="large" disabled={loading}>
                            {loading ? <CircularProgress size={24} /> : 'Create Account'}
                        </Button>
                    </form>
                )}

                <Divider sx={{ my: 3 }} />
                <Typography variant="body2" color="text.secondary" textAlign="center">
                    Are you an admin? <Link to="/admin/auth" style={{ color: '#E85D4A' }}>Login to Admin Panel</Link>
                </Typography>
            </Card>
        </Container>
    );
}
