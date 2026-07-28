from django.http import Http404, HttpResponse, HttpResponseNotModified
from django.shortcuts import render
from django.views.decorators.http import require_GET
from rest_framework.views import APIView
from rest_framework.parsers import MultiPartParser,FormParser
from rest_framework.response import Response
import os

from core.storage import save_file


def index(request):
    return render(request, 'index.html')


@require_GET
def serve_media_blob(request, sha256):
    """`GET /api/media/<sha256>/` — public, content-addressed image serving.

    This is the read side of the DB image fallback in ``core.storage``: when
    there are no S3 keys, ``save_file`` stores bytes as an ``ImageBlob`` row
    instead of on the ephemeral local disk, and this is how a browser
    ``<img src>`` gets them back. It is a plain Django view, not a DRF
    APIView, so a large JPEG is written straight out rather than passed
    through DRF's renderer/content-negotiation machinery.

    Public by construction (see ``PUBLIC_API_PREFIXES`` in
    ``core.middleware``): this is unauthenticated image content referenced
    from `<img>` tags, which never carry a bearer token.

    The URL is content-addressed — the bytes behind a given sha256 can never
    change — so the response is cacheable forever. ``ETag`` is the sha256
    itself, and a matching ``If-None-Match`` short-circuits to 304 without
    touching the row's bytes again. This matters in practice: Render's free
    tier is slow, and every product card on the storefront hits this
    endpoint.
    """
    from core.models import ImageBlob

    try:
        blob = ImageBlob.objects.get(sha256=sha256)
    except ImageBlob.DoesNotExist:
        raise Http404("Unknown image hash")

    if request.headers.get("If-None-Match") == blob.sha256:
        response = HttpResponseNotModified()
    else:
        response = HttpResponse(bytes(blob.data), content_type=blob.content_type)

    response["ETag"] = blob.sha256
    response["Cache-Control"] = "public, max-age=31536000, immutable"
    return response

class FileUploadViewInS3(APIView):
    parser_classes=(MultiPartParser,FormParser)

    def post(self,request,*args,**kwargs):
        uploaded_files_urls=[]

        for file_key in request.FILES:
            file_obj=request.FILES[file_key]
            uniqueFileName=os.urandom(24).hex()+"_"+file_obj.name.replace(" ","_")
            content=file_obj.read()
            url=save_file(uniqueFileName, content, file_obj.content_type)
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
