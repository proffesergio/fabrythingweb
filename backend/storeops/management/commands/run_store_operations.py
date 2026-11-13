"""A dedicated, optional CPU worker. Never starts/restarts other services."""

import logging
import threading
import time

from django.core.management.base import BaseCommand
from django.db import close_old_connections

from storeops.alerts import process_one_alert
from storeops.capacity import take_snapshot
from storeops.images import process_one_image
from storeops.models import WorkerHeartbeat


class Command(BaseCommand):
    help = (
        "Drain durable order alerts and product image cleanup, one CPU image at a time."
    )

    def add_arguments(self, parser):
        parser.add_argument("--loop", action="store_true")
        parser.add_argument("--poll-seconds", type=int, default=10)
        parser.add_argument("--alerts-only", action="store_true")

    def handle(self, *args, **options):
        import importlib.util

        image_ready = all(
            importlib.util.find_spec(name)
            for name in ("rembg", "onnxruntime", "psutil")
        )
        stopped = threading.Event()
        poll = max(5, min(300, options["poll_seconds"]))

        def alerts():
            close_old_connections()
            try:
                for _ in range(10):
                    if not process_one_alert():
                        break
                WorkerHeartbeat.objects.update_or_create(
                    name="store-orders", defaults={"status": "healthy", "detail": ""}
                )
            except Exception as exc:  # noqa: BLE001 - durable job boundary must record failures
                WorkerHeartbeat.objects.update_or_create(
                    name="store-orders",
                    defaults={
                        "status": "degraded",
                        "detail": "Alert worker error (" + type(exc).__name__ + ").",
                    },
                )
            finally:
                close_old_connections()

        def alert_lane():
            while not stopped.is_set():
                try:
                    alerts()
                except Exception as exc:  # noqa: BLE001 - retain the independent lane during DB outages
                    logging.getLogger(__name__).warning(
                        "Order alert lane unavailable (%s).", type(exc).__name__
                    )
                stopped.wait(poll)

        parallel_alerts = options["loop"] and not options["alerts_only"]
        if parallel_alerts:
            threading.Thread(
                target=alert_lane, name="store-order-alerts", daemon=True
            ).start()
        try:
            while True:
                status, detail = "healthy", ""
                try:
                    close_old_connections()
                    if not parallel_alerts:
                        alerts()
                    if not options["alerts_only"]:
                        if not image_ready:
                            status, detail = (
                                "images_unavailable",
                                "Optional CPU image-worker dependencies are not installed.",
                            )
                        else:
                            import psutil

                            if psutil.virtual_memory().available < 1536 * 1024 * 1024:
                                status, detail = (
                                    "memory_hold",
                                    "Image cleanup waits for at least 1.5 GiB free RAM.",
                                )
                            else:
                                WorkerHeartbeat.objects.update_or_create(
                                    name="store-operations",
                                    defaults={
                                        "status": "processing",
                                        "detail": "CPU image pipeline active; order alerts run independently.",
                                    },
                                )
                                process_one_image()
                        take_snapshot()
                except Exception as exc:  # noqa: BLE001 - durable job boundary must record failures
                    status, detail = (
                        "degraded",
                        "Worker error ("
                        + type(exc).__name__
                        + "); no raw credentials logged.",
                    )
                if not options["alerts_only"]:
                    WorkerHeartbeat.objects.update_or_create(
                        name="store-operations",
                        defaults={"status": status, "detail": detail},
                    )
                self.stdout.write("Store operations: " + status)
                if not options["loop"]:
                    return
                time.sleep(poll)
        finally:
            stopped.set()
