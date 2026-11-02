import React, { useState } from 'react';
import {
    Box, Container, Card, TextField, Button, Tab, Tabs, Alert,
    CircularProgress,
} from '@mui/material';
import { useNavigate, useSearchParams, Link } from 'react-router-dom';
import { useDispatch } from 'react-redux';
import { login } from '../../redux/reducer/IsLoggedInReducer';
import { syncCartOnLogin } from '../../redux/reducer/cartSlice';
import useApi from '../../hooks/APIHandler';
import { getUser } from '../../utils/Helper';
import roleHome from '../../utils/roleHome';
import BrandLogo from '../../components/BrandLogo';

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
            // Staff-side accounts (vendors, riders) land on their own dashboard
            // rather than wherever the customer flow was headed — the role claim is
            // embedded in the JWT at login time (storefront/views.py issue_tokens),
            // so this is just a decode, no extra request.
            //
            // This used to hardcode the Restaurant case only, so a rider signing in
            // here fell through to `redirect`, which defaults to "/" — the reported
            // "login sends me to fabrything.com" bounce. Route through roleHome so
            // every non-customer role is covered by one table.
            const role = getUser()?.role;
            navigate(role && role !== 'Customer' ? roleHome(role) : redirect);
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
            <Box sx={{ display: 'flex', justifyContent: 'center', mb: 4 }}>
                <Box component={Link} to="/" sx={{ display: 'inline-flex' }}>
                    {/* StorefrontAuthTheme renders this page on a light canvas. */}
                    <BrandLogo brand="fabrything" variant="stacked" mode="light" height={96} />
                </Box>
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
            </Card>
        </Container>
    );
}
