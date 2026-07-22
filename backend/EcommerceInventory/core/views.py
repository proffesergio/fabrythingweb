from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework.parsers import MultiPartParser,FormParser
from rest_framework.response import Response
from django.conf import settings
import os

AWS_ACCESS_KEY_ID = settings.AWS_ACCESS_KEY_ID
AWS_ACESS_KEY_SECRET = settings.AWS_ACESS_KEY_SECRET
AWS_S3_REGION_NAME = settings.AWS_S3_REGION_NAME
AWS_STORAGE_BUCKET_NAME = settings.AWS_STORAGE_BUCKET_NAME
MEDIA_ROOT = settings.MEDIA_ROOT
MEDIA_URL = settings.MEDIA_URL


def index(request):
    return render(request, 'index.html')

class FileUploadViewInS3(APIView):
    parser_classes=(MultiPartParser,FormParser)

    def _use_s3(self):
        return (
            AWS_ACCESS_KEY_ID
            and AWS_ACESS_KEY_SECRET
            and AWS_ACCESS_KEY_ID != 'ACCESS_KEY_ID'
            and AWS_ACESS_KEY_SECRET != 'AWS_ACESS_KEY_SECRET'
        )

    def post(self,request,*args,**kwargs):
        uploaded_files_urls=[]

        if self._use_s3():
            from boto3.session import Session
            for file_key in request.FILES:
                file_obj=request.FILES[file_key]
                s3_client=Session(
                    aws_access_key_id=AWS_ACCESS_KEY_ID,
                    aws_secret_access_key=AWS_ACESS_KEY_SECRET,
                    region_name=AWS_S3_REGION_NAME
                ).client("s3")

                uniqueFileName=os.urandom(24).hex()+"_"+file_obj.name.replace(" ","_")
                file_path="uploads/"+uniqueFileName

                s3_client.upload_fileobj(
                    file_obj,
                    AWS_STORAGE_BUCKET_NAME,
                    file_path,
                    ExtraArgs={
                        'ContentType':file_obj.content_type
                    }
                )
                s3url=f"https://{AWS_STORAGE_BUCKET_NAME}.s3.amazonaws.com/{file_path}"
                uploaded_files_urls.append(s3url)
        else:
            upload_dir = os.path.join(MEDIA_ROOT, "uploads")
            os.makedirs(upload_dir, exist_ok=True)
            for file_key in request.FILES:
                file_obj=request.FILES[file_key]
                uniqueFileName=os.urandom(24).hex()+"_"+file_obj.name.replace(" ","_")
                file_path=os.path.join(upload_dir, uniqueFileName)
                with open(file_path, 'wb+') as destination:
                    for chunk in file_obj.chunks():
                        destination.write(chunk)
                url = f"{MEDIA_URL}uploads/{uniqueFileName}"
                uploaded_files_urls.append(url)

        return Response({'message':'File uploaded successfully','urls':uploaded_files_urls},status=200)


class HealthView(APIView):
    """`GET /api/health/` — is the deployed code actually running against a
    migrated database?

    This exists because the failure it detects is *invisible*. When the schema
    lags the code, every view touching a new column raises a DB error, DEBUG=False
    turns that into a blank "Server Error (500)" page with no body, and the only
    way to tell a missing migration from a code bug was shell access. That cost a
    full debugging session once (food 0008/0009 unapplied while the rider
    dashboard shipped); it should cost one HTTP request next time.

    Deliberately public and deliberately dull: migration *names* only. No host,
    no credentials, no row counts, nothing that isn't already in the repo.
    """
    permission_classes = []
    authentication_classes = []

    def get(self, request):
        from django.db import connection
        from django.db.migrations.executor import MigrationExecutor

        try:
            executor = MigrationExecutor(connection)
            targets = executor.loader.graph.leaf_nodes()
            pending = [f"{app}.{name}" for app, name in executor.migration_plan(targets)]
        except Exception as exc:  # noqa: BLE001 — health must never itself 500
            return Response({"status": "error", "database": "unreachable",
                             "detail": str(exc)[:200]}, status=503)

        return Response({
            "status": "ok" if not pending else "migrations_pending",
            "database": "reachable",
            "pending_migrations": pending,
        }, status=200 if not pending else 503)
