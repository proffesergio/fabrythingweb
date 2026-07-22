import { useState } from "react";
import { Navigate, useNavigate } from "react-router-dom";
import {
    Box, Card, Typography, TextField, Button, Alert, CircularProgress, Stack,
} from "@mui/material";
import TwoWheelerIcon from "@mui/icons-material/TwoWheeler";
import useApi from "../hooks/APIHandler";
import { getUser, isAuthenticated } from "../utils/Helper";
import BrandLogo from "../components/BrandLogo";

// Riders have no self-serve signup or password reset — an admin creates the
// account and hands over the credentials (see food/views_food_ext.py
// AdminRiderViewSet.reset_password). So this page is login-only on purpose;
// don't add a "Create account" tab without building the approval flow first.
//
// It exists as its own route because riders used to be sent to the customer
// auth page at /auth/login, which defaults its post-login redirect to "/" —
// that is why a rider who logged in landed on the storefront homepage instead
// of their dashboard.
export default function RiderLogin() {
    const { callApi, loading } = useApi();
    const navigate = useNavigate();
    const [form, setForm] = useState({ username: "", password: "" });
    const [error, setError] = useState("");

    // Already signed in as a rider? Skip the form entirely.
    if (isAuthenticated() && getUser()?.role === "Rider") {
        return <Navigate to="/rider" replace />;
    }

    const submit = async (e) => {
        e.preventDefault();
        setError("");

        const res = await callApi({
            url: "store/auth/login/", method: "POST", body: form,
            silent: true, rawError: true,
        });

        if (res?.status !== 200 || !res?.data?.access) {
            setError(res?.data?.data || res?.data?.message || "Login failed. Check your username and password.");
            return;
        }

        // The role claim is embedded in the JWT at login time
        // (storefront/views.py issue_tokens), so this is a decode, not a request.
        localStorage.setItem("token", res.data.access);
        if (getUser()?.role !== "Rider") {
            // A real account, but not a rider one. Drop the token rather than
            // leave them half-signed-in on a dashboard they can't use.
            localStorage.removeItem("token");
            setError("This is not a rider account. Ask an admin to set up your rider login.");
            return;
        }
        navigate("/rider", { replace: true });
    };

    return (
        <Box sx={{
            minHeight: "100vh", bgcolor: "#FDF8F3",
            display: "flex", alignItems: "center", justifyContent: "center", p: 2,
        }}>
            <Card sx={{ p: 4, width: "100%", maxWidth: 420 }}>
                <Stack alignItems="center" spacing={1} sx={{ mb: 3 }}>
                    {/* Riders deliver for the food module, so this screen carries the
                        Fabrything Food mark, not the store one. Card is light. */}
                    <BrandLogo brand="food" variant="stacked" mode="light" height={84} sx={{ mb: 1 }} />
                    <Stack direction="row" alignItems="center" spacing={0.75}>
                        <TwoWheelerIcon sx={{ fontSize: 26, color: "primary.main" }} />
                        <Typography variant="h5" fontWeight={800}>Rider Login</Typography>
                    </Stack>
                    <Typography variant="body2" color="text.secondary" textAlign="center">
                        Sign in with the credentials your admin gave you.
                    </Typography>
                </Stack>

                {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}

                <form onSubmit={submit}>
                    <TextField
                        fullWidth label="Username" required autoFocus sx={{ mb: 2 }}
                        autoComplete="username"
                        value={form.username}
                        onChange={(e) => setForm({ ...form, username: e.target.value })}
                    />
                    <TextField
                        fullWidth label="Password" type="password" required sx={{ mb: 3 }}
                        autoComplete="current-password"
                        value={form.password}
                        onChange={(e) => setForm({ ...form, password: e.target.value })}
                    />
                    <Button type="submit" variant="contained" fullWidth size="large" disabled={loading}>
                        {loading ? <CircularProgress size={24} /> : "Log in"}
                    </Button>
                </form>

                <Typography variant="caption" color="text.secondary" display="block" textAlign="center" sx={{ mt: 3 }}>
                    No account or forgotten password? Contact your delivery admin —
                    rider accounts are created and reset by the admin panel.
                </Typography>
            </Card>
        </Box>
    );
}
