from core.helpers import getDynamicFormFields, getDynamicFormModels, getExludeFields, renderResponse, PLATFORM_STAFF_ROLES, isPlatformStaff, absolutize_image_list
from accounts.models import Users
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.authentication import JWTAuthentication
from django.core.serializers import serialize
import json
from django.apps import apps

# The category/product editor is the ONLY place the platform-scope widening
# (core.helpers.isPlatformStaff) was ever meant to apply -- seeded categories
# and products are owned by the first Super Admin, so domain-root staff need
# to reach them across domains to edit them (see core.helpers.isPlatformStaff
# docstring). Every other dynamic-form model ('supplier'/'users' ->
# accounts.Users, 'warehouse' -> inventory.Warehouse, 'rackShelfFloor' ->
# inventory.RackAndShelvesAndFloor) has real per-tenant rows. Widening the
# lookup for those too let one tenant's domain-root Admin fetch AND edit
# another tenant's Users row via POST /api/getForm/users/<id>/ -- including
# flipping role to "Super Admin" -- a full cross-tenant privilege escalation.
# Keep this list to exactly what the widening was designed for.
#
# isPlatformStaff, not isPlatformScope, gates the widening below: isPlatformScope
# alone is true for ANY domain-root user, and Users.save() self-assigns
# domain_user_id = self.id for every account created without one -- so a
# plain self-signed-up Customer/Rider/Restaurant is their own domain root
# too. Without the role check, that let any such account fetch AND edit ANY
# product/category belonging to ANY tenant through this same widening --
# see accounts/test_dynamic_form_scope.py::DynamicFormNonStaffRoleEscalationTests.
PLATFORM_SCOPE_WIDENED_MODELS = {'category', 'product'}

class DynamicFormController(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self,request,modelName,id=None):
        #Checking if Model Exist in Our Dynamic Form Models
        if modelName not in getDynamicFormModels():
            return renderResponse(data='Model Not Exist',message='Model Not Exist',status=404)

        if id is None and not isPlatformStaff(request.user):
            # Creation is a back-office action for every dynamic-form model
            # (product, category, warehouse, supplier/users, rackShelfFloor),
            # not just the widened ones -- without this gate any authenticated
            # Customer/Rider/Restaurant (isPlatformScope is True for them too,
            # see isPlatformStaff's docstring) could write arbitrary rows into
            # these tables under their own domain. Those rows are still real:
            # they land in admin lists/counts, so a "your own domain" caveat
            # doesn't make it safe.
            return renderResponse(data='Forbidden', message='Forbidden', status=403)

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
            if modelName in PLATFORM_SCOPE_WIDENED_MODELS and request.user.role not in PLATFORM_STAFF_ROLES:
                # Non-back-office roles (Customer/Rider/Restaurant/...) must
                # never touch the product/category editor at all -- see
                # PLATFORM_SCOPE_WIDENED_MODELS' comment above.
                return renderResponse(data='Forbidden', message='Forbidden', status=403)
            qs = model_class.objects.filter(id=id)
            if modelName not in PLATFORM_SCOPE_WIDENED_MODELS or not isPlatformStaff(request.user):
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
        #This raw serialize() bypasses the normal DRF serializers
        #(ProductSerializer/CategorySerializer) that absolutize a stored
        #relative media path -- without this, a product/category saved here
        #would carry a bare /api/media/<hash>/ path in the response until the
        #next list refetch re-serializes it correctly. See
        #core.helpers.absolutize_media_url.
        if 'image' in response_json:
            response_json['image']=absolutize_image_list(response_json['image'], request)
        #Returning the Response
        return renderResponse(data=response_json,message='Data saved successfully')

    def get(self,request,modelName,id=None):
        if modelName not in getDynamicFormModels():
            return renderResponse(data='Model Not Found',message='Model Not Found',status=404)

        if id is None and not isPlatformStaff(request.user):
            # Matches the same gate on post() above -- a blank create-form
            # schema is low severity on its own, but it should require the
            # same authorization as actually being able to submit it.
            return renderResponse(data='Forbidden', message='Forbidden', status=403)

        model = getDynamicFormModels()[modelName]
        model_class=apps.get_model(model)

        if model_class is None:
            return renderResponse(data='Model Not Found',message='Model Not Found',status=404)
        
        if id:
            if modelName in PLATFORM_SCOPE_WIDENED_MODELS and request.user.role not in PLATFORM_STAFF_ROLES:
                return renderResponse(data='Forbidden', message='Forbidden', status=403)
            qs = model_class.objects.filter(id=id)
            if modelName not in PLATFORM_SCOPE_WIDENED_MODELS or not isPlatformStaff(request.user):
                qs = qs.filter(domain_user_id_id=request.user.domain_user_id_id)
            model_instance = qs.first()
            if model_instance is None:
                return renderResponse(data='Model Item Not Found',message='Model Item Not Found',status=404)
        else:
            model_instance = model_class()

        fields=getDynamicFormFields(model_instance,request.user.domain_user_id)
        return renderResponse(data=fields,message='Form fields fetched successfully')