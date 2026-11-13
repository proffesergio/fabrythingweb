"""Start only the dedicated store worker from an operator-owned private env file."""

import argparse
import os
import sys
from pathlib import Path

from dotenv import load_dotenv


def main():
    parser = argparse.ArgumentParser(description="Fabrything store operations worker")
    parser.add_argument("--env-file", required=True, type=Path)
    parser.add_argument("--alerts-only", action="store_true")
    args = parser.parse_args()
    if not args.env_file.is_file():
        parser.error("The private environment file was not found.")
    load_dotenv(args.env_file, override=True)
    required = [
        "SECRET_KEY",
        "DATABASE_HOST",
        "DATABASE_NAME",
        "DATABASE_USER",
        "DATABASE_PASSWORD",
    ]
    if any(
        not os.getenv(key) or "[SENSITIVE]" in os.getenv(key, "") for key in required
    ):
        parser.error(
            "Original private database settings are required. Vercel protected export placeholders cannot run a worker."
        )
    for key in (
        "AWS_ACCESS_KEY_ID",
        "AWS_ACCESS_KEY_SECRET",
        "AWS_ACESS_KEY_SECRET",
        "AWS_S3_ENDPOINT_URL",
        "AWS_STORAGE_BUCKET_NAME",
    ):
        if "[SENSITIVE]" in os.getenv(key, ""):
            parser.error(
                "Image-storage settings contain protected export placeholders. Supply original private settings."
            )
    root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(root))
    os.environ["DJANGO_SETTINGS_MODULE"] = "config.settings.prod"
    os.environ["OMP_NUM_THREADS"] = "1"
    from django.core.management import execute_from_command_line

    command = ["store_worker", "run_store_operations", "--loop", "--poll-seconds", "10"]
    if args.alerts_only:
        command.append("--alerts-only")
    execute_from_command_line(command)


if __name__ == "__main__":
    main()
