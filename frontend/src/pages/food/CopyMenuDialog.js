import { useCallback, useEffect, useState } from "react";
import {
    Dialog, DialogTitle, DialogContent, DialogActions, Button, TextField, MenuItem,
    Alert, Stack, Typography, CircularProgress,
} from "@mui/material";
import { toast } from "react-toastify";
import useApi from "../../hooks/APIHandler";

// Copies another restaurant's menu into the one being edited. Always previews
// first (a server-side dry run) so the admin sees how much will be created and
// how much is already there before anything is written.
export default function CopyMenuDialog({ open, restaurants, targetRestaurant, selectedItemIds, onClose, onCopied }) {
    const { callApi } = useApi();
    const [source, setSource] = useState("");
    const [preview, setPreview] = useState(null);
    const [busy, setBusy] = useState(false);

    const selective = selectedItemIds?.length > 0;

    const body = useCallback(() => ({
        source_restaurant: Number(source),
        target_restaurant: Number(targetRestaurant),
        ...(selective ? { item_ids: selectedItemIds } : {}),
    }), [source, targetRestaurant, selective, selectedItemIds]);

    useEffect(() => {
        if (!open || !source) { setPreview(null); return undefined; }
        let cancelled = false;
        (async () => {
            setBusy(true);
            const res = await callApi({
                url: "food/admin/menu/copy/", method: "POST",
                params: { dry_run: "true" }, body: body(), rawError: true, silent: true,
            });
            if (cancelled) return;
            setBusy(false);
            if (res?.status === 200) setPreview(res.data.data);
            else toast.error(res?.data?.message || "Could not preview the copy");
        })();
        return () => { cancelled = true; };
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [open, source]);

    const doCopy = async () => {
        setBusy(true);
        const res = await callApi({
            url: "food/admin/menu/copy/", method: "POST", body: body(), rawError: true, silent: true,
        });
        setBusy(false);
        if (res?.status === 200) {
            const d = res.data.data;
            toast.success(`Copied ${d.items_copied} items (${d.items_skipped} already there)`);
            setSource(""); setPreview(null);
            onCopied();
        } else {
            toast.error(res?.data?.message || "Copy failed");
        }
    };

    return (
        <Dialog open={open} onClose={onClose} maxWidth="xs" fullWidth>
            <DialogTitle>{selective ? `Copy ${selectedItemIds.length} items from…` : "Copy a whole menu"}</DialogTitle>
            <DialogContent>
                <Stack spacing={2} sx={{ mt: 1 }}>
                    <TextField select fullWidth label="Copy menu from" value={source}
                        onChange={(e) => setSource(e.target.value)}>
                        {restaurants.filter((r) => r.id !== Number(targetRestaurant))
                            .map((r) => <MenuItem key={r.id} value={r.id}>{r.name}</MenuItem>)}
                    </TextField>

                    {busy && <CircularProgress size={22} />}

                    {preview && !busy && (
                        <Alert severity="info">
                            <Typography variant="body2">
                                {preview.items_copied} items will be copied, {preview.items_skipped} skipped as duplicates.
                            </Typography>
                            <Typography variant="caption" color="text.secondary">
                                {preview.categories_created} new categories, {preview.categories_merged} merged
                                into existing ones · {preview.options_copied} add-ons.
                            </Typography>
                        </Alert>
                    )}
                </Stack>
            </DialogContent>
            <DialogActions>
                <Button onClick={onClose}>Cancel</Button>
                <Button variant="contained" disabled={!source || busy || !preview} onClick={doCopy}>
                    Copy menu
                </Button>
            </DialogActions>
        </Dialog>
    );
}
