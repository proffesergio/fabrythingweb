import React, { useEffect } from "react";
import {
    Alert, AlertTitle, Box, Button, Card, CardContent, Chip, FormControlLabel, Grid,
    LinearProgress, Stack, Switch, TextField, Typography,
} from "@mui/material";
import { Controller, useForm } from "react-hook-form";
import { toast } from "react-toastify";
import useApi from "../hooks/APIHandler";

// Editable fields on the vendor's own restaurant profile. `slug`,
// `commission_percentage` and `status` are read-only on the backend
// serializer (food/serializers_write.py::VendorRestaurantSerializer) so we
// never send them back on PATCH — they're rendered as read-only info instead.
const defaultValues = {
    name: "",
    name_bn: "",
    description: "",
    description_bn: "",
    logo: "",
    cover_image: "",
    cuisine_type: "",
    phone: "",
    address: "",
    pickup_lat: "",
    pickup_lng: "",
    base_delivery_fee: "",
    avg_prep_minutes: "",
    min_order_amount: "",
    is_open: true,
};

const STATUS_COLORS = {
    PENDING: "warning",
    ACTIVE: "success",
    SUSPENDED: "error",
    REJECTED: "default",
};

const VendorRestaurant = () => {
    const { callApi, loading } = useApi();
    const { register, handleSubmit, control, reset, formState: { errors } } = useForm({ defaultValues });
    const [readOnlyInfo, setReadOnlyInfo] = React.useState({ slug: "", status: "", commission_percentage: "" });

    const fetchRestaurant = async () => {
        const res = await callApi({ url: "food/vendor/restaurant/", method: "GET" });
        const data = res?.data?.data;
        if (data) {
            reset({
                name: data.name || "",
                name_bn: data.name_bn || "",
                description: data.description || "",
                description_bn: data.description_bn || "",
                logo: data.logo || "",
                cover_image: data.cover_image || "",
                cuisine_type: data.cuisine_type || "",
                phone: data.phone || "",
                address: data.address || "",
                pickup_lat: data.pickup_lat ?? "",
                pickup_lng: data.pickup_lng ?? "",
                base_delivery_fee: data.base_delivery_fee ?? "",
                avg_prep_minutes: data.avg_prep_minutes ?? "",
                min_order_amount: data.min_order_amount ?? "",
                is_open: !!data.is_open,
            });
            setReadOnlyInfo({
                slug: data.slug || "",
                status: data.status || "",
                commission_percentage: data.commission_percentage ?? "",
            });
        }
    };

    useEffect(() => {
        fetchRestaurant();
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, []);

    const onSubmit = async (data) => {
        const res = await callApi({ url: "food/vendor/restaurant/", method: "PATCH", body: data });
        if (res?.data) {
            toast.success(res.data.message || "Restaurant profile updated");
            fetchRestaurant();
        }
    };

    return (
        <Box component="div" sx={{ width: "100%" }}>
            <Typography variant="h5" gutterBottom>Restaurant Profile</Typography>
            {loading && <LinearProgress sx={{ mb: 2 }} />}

            {/* A self-signed-up partner can do everything except be seen. Saying
                so plainly is the difference between "building my menu while I
                wait" and "the site is broken, nobody can find me". */}
            {readOnlyInfo.status === "PENDING" && (
                <Alert severity="info" sx={{ mb: 2 }}>
                    <AlertTitle>Awaiting approval</AlertTitle>
                    Your application is with our team. You can set up your profile, menu and
                    opening hours now — customers will see your restaurant as soon as it is
                    approved.
                </Alert>
            )}
            {readOnlyInfo.status === "REJECTED" && (
                <Alert severity="warning" sx={{ mb: 2 }}>
                    <AlertTitle>Application not approved</AlertTitle>
                    Please get in touch with the Fabrything team if you think this is a mistake.
                </Alert>
            )}

            <Card sx={{ mb: 2 }}>
                <CardContent>
                    <Stack direction="row" spacing={1} flexWrap="wrap" alignItems="center">
                        <Chip label={readOnlyInfo.status || "—"} color={STATUS_COLORS[readOnlyInfo.status] || "default"} size="small" />
                        <Typography variant="body2" color="text.secondary">
                            Slug: {readOnlyInfo.slug || "—"}
                        </Typography>
                        <Typography variant="body2" color="text.secondary">
                            Commission: {readOnlyInfo.commission_percentage !== "" ? `${readOnlyInfo.commission_percentage}%` : "—"}
                        </Typography>
                    </Stack>
                    <Typography variant="caption" color="text.secondary">
                        Slug, status and commission are managed by the platform and cannot be edited here.
                    </Typography>
                </CardContent>
            </Card>

            <Card>
                <CardContent>
                    <form onSubmit={handleSubmit(onSubmit)}>
                        <Controller
                            name="is_open"
                            control={control}
                            render={({ field }) => (
                                <FormControlLabel
                                    sx={{ mb: 2 }}
                                    control={<Switch checked={!!field.value} onChange={(e) => field.onChange(e.target.checked)} />}
                                    label={field.value ? "Open for orders" : "Closed"}
                                />
                            )}
                        />

                        <Grid container spacing={2}>
                            <Grid item xs={12} sm={6}>
                                <TextField
                                    label="Name" fullWidth required
                                    {...register("name", { required: true })}
                                    error={!!errors.name}
                                    helperText={errors.name && "This field is required"}
                                />
                            </Grid>
                            <Grid item xs={12} sm={6}>
                                <TextField label="Name (Bangla)" fullWidth {...register("name_bn")} />
                            </Grid>

                            <Grid item xs={12}>
                                <TextField label="Description" fullWidth multiline minRows={2} {...register("description")} />
                            </Grid>
                            <Grid item xs={12}>
                                <TextField label="Description (Bangla)" fullWidth multiline minRows={2} {...register("description_bn")} />
                            </Grid>

                            <Grid item xs={12} sm={6}>
                                <TextField label="Logo URL" fullWidth {...register("logo")} />
                            </Grid>
                            <Grid item xs={12} sm={6}>
                                <TextField label="Cover Image URL" fullWidth {...register("cover_image")} />
                            </Grid>

                            <Grid item xs={12} sm={6}>
                                <TextField label="Cuisine Type" fullWidth {...register("cuisine_type")} />
                            </Grid>
                            <Grid item xs={12} sm={6}>
                                <TextField label="Phone" fullWidth {...register("phone")} />
                            </Grid>

                            <Grid item xs={12}>
                                <TextField label="Address" fullWidth {...register("address")} />
                            </Grid>

                            <Grid item xs={12} sm={6}>
                                <TextField
                                    label="Pickup Latitude" type="number" fullWidth
                                    inputProps={{ step: "any" }}
                                    {...register("pickup_lat")}
                                />
                            </Grid>
                            <Grid item xs={12} sm={6}>
                                <TextField
                                    label="Pickup Longitude" type="number" fullWidth
                                    inputProps={{ step: "any" }}
                                    {...register("pickup_lng")}
                                />
                            </Grid>

                            <Grid item xs={12} sm={4}>
                                <TextField
                                    label="Base Delivery Fee" type="number" fullWidth
                                    inputProps={{ step: "any" }}
                                    {...register("base_delivery_fee")}
                                />
                            </Grid>
                            <Grid item xs={12} sm={4}>
                                <TextField
                                    label="Avg Prep Minutes" type="number" fullWidth
                                    {...register("avg_prep_minutes")}
                                />
                            </Grid>
                            <Grid item xs={12} sm={4}>
                                <TextField
                                    label="Min Order Amount" type="number" fullWidth
                                    inputProps={{ step: "any" }}
                                    {...register("min_order_amount")}
                                />
                            </Grid>
                        </Grid>

                        <Box sx={{ mt: 3 }}>
                            <Button type="submit" variant="contained" disabled={loading}>
                                Save Changes
                            </Button>
                        </Box>
                    </form>
                </CardContent>
            </Card>
        </Box>
    );
};

export default VendorRestaurant;
