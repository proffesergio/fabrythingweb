from core.helpers import getDynamicFormFields, getDynamicFormModels, getExludeFields, renderResponse, isPlatformScope
from accounts.models import Users
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.authentication import JWTAuthentication
from django.core.serializers import serialize
import json
from django.apps import apps

class DynamicFormController(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self,request,modelName,id=None):
        #Checking if Model Exist in Our Dynamic Form Models
        if modelName not in getDynamicFormModels():
            return renderResponse(data='Model Not Exist',message='Model Not Exist',status=404)
        
        #Getting the Model Name from Dynamic Form Models
        model=getDynamicFormModels()[modelName]
        #Getting the Model Class from the Model Name
        model_class=apps.get_model(model)

        #Checking if Model Class Exist
        if model_class is None:
            return renderResponse(data='Model Not Found',message='Model Not Found',status=404)
        
        #Getting the Model Fields Info
        fields_info=model_class._meta.fields
        #Getting the Model Fields Name
        model_fields={field.name for field in fields_info}
        #Getting the Excluded Fields
        exclude_fields=getExludeFields()

        #Checking the Required Fields are in the Model Data
        required_fields=[field.name for field in fields_info if not field.null and field.default is not None and field.name not in exclude_fields]

        #matching with validation for fields not exist in Post Data
        missing_fields=[field for field in required_fields if field not in request.data]
        #If Missing Fields Exist
        if missing_fields:
            return renderResponse(data=[f'The Following field in required : {field}' for field in missing_fields],message='Validation Error',status=400)
        
        #Creating a Copy of Post Data for Manipulation
        fields=request.data.copy()

        #Adding the Domain User ID and Added By User ID in the Post Data

        #Filtering the Post Data Fields by Model Fields and Eliminating the Extra Fields
        fieldsdata={key:value for key,value in fields.items() if key in model_fields}

        #Assigning Foreign key instance for ForeignKey Fields in the Post Data by getting the instance of the related model by the ID
        for field in fields_info:
            if field.is_relation and field.name in fieldsdata and isinstance(fieldsdata[field.name],int):
                related_model=field.related_model
                try:
                    fieldsdata[field.name]=related_model.objects.get(id=fieldsdata[field.name])
                except related_model.DoesNotExist:
                    return renderResponse(data=f'{field.name} Relation Not Exist found',message=f'{field.name} Relation Not Exist found',status=404)
            elif field.is_relation and field.name in fieldsdata:
                fieldsdata.pop(field.name)

        #Creating the Model Instance and Saving the Data in the Database
        if id:
            qs = model_class.objects.filter(id=id)
            if not isPlatformScope(request.user):
                qs = qs.filter(domain_user_id_id=request.user.domain_user_id_id)
            model_instace = qs.first()
            if model_instace is None:
                return renderResponse(data='Model Item Not Found',message='Model Item Not Found',status=404)
            # Editing must never re-own the row: ownership set at creation only.
            fieldsdata.pop('domain_user_id', None)
            fieldsdata.pop('added_by_user_id', None)
            for key, value in fieldsdata.items():
                setattr(model_instace, key, value)
            model_instace.save()
        else:
            fieldsdata['domain_user_id'] = request.user.domain_user_id
            fieldsdata['added_by_user_id'] = Users.objects.get(id=request.user.id)
            model_instace = model_class.objects.create(**fieldsdata)

        #Serializing Data
        serialized_data=serialize('json',[model_instace])
        #Converting Serialized Data to JSON
        model_json=json.loads(serialized_data)
        #Getting the first object of the JSON
        response_json=model_json[0]['fields']
        response_json['id']=model_json[0]['pk']
        #Returning the Response
        return renderResponse(data=response_json,message='Data saved successfully')

    def get(self,request,modelName,id=None):
        if modelName not in getDynamicFormModels():
            return renderResponse(data='Model Not Found',message='Model Not Found',status=404)
        
        model = getDynamicFormModels()[modelName]
        model_class=apps.get_model(model)

        if model_class is None:
            return renderResponse(data='Model Not Found',message='Model Not Found',status=404)
        
        if id:
            qs = model_class.objects.filter(id=id)
            if not isPlatformScope(request.user):
                qs = qs.filter(domain_user_id_id=request.user.domain_user_id_id)
            model_instance = qs.first()
            if model_instance is None:
                return renderResponse(data='Model Item Not Found',message='Model Item Not Found',status=404)
        else:
            model_instance = model_class()

        fields=getDynamicFormFields(model_instance,request.user.domain_user_id)
        return renderResponse(data=fields,message='Form fields fetched successfully')