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
