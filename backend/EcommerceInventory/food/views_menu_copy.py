"""Admin endpoint for copying one restaurant's menu onto another."""
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.authentication import JWTAuthentication

from core.helpers import renderResponse
from food.models import FoodCategory, Restaurant
from food.permissions import IsPlatformAdmin
from food.services_menu_copy import copy_menu


class AdminMenuCopyView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, IsPlatformAdmin]

    def post(self, request):
        source = Restaurant.objects.filter(pk=request.data.get("source_restaurant")).first()
        target = Restaurant.objects.filter(pk=request.data.get("target_restaurant")).first()
        if not source or not target:
            return renderResponse(
                data={"restaurant": ["Choose an existing source and target restaurant."]},
                message="Validation error", status=400)
        if source.id == target.id:
            return renderResponse(
                data={"target_restaurant": ["Pick a different restaurant to copy into."]},
                message="Validation error", status=400)

        target_category = None
        category_id = request.data.get("target_category")
        if category_id:
            target_category = FoodCategory.objects.filter(pk=category_id, restaurant=target).first()
            if not target_category:
                return renderResponse(
                    data={"target_category": ["That category is not on the target restaurant."]},
                    message="Validation error", status=400)

        item_ids = request.data.get("item_ids")
        if item_ids is not None and not isinstance(item_ids, list):
            return renderResponse(data={"item_ids": ["Expected a list of item ids."]},
                                  message="Validation error", status=400)

        dry_run = request.GET.get("dry_run") == "true"
        result = copy_menu(source, target, item_ids=item_ids,
                           target_category=target_category, dry_run=dry_run)
        return renderResponse(data=result, message="Copy preview" if dry_run else "Menu copied")
