from rest_framework import viewsets
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.permissions import IsAnalystOrAdmin
from apps.core.utils import request_organization

from .models import AccountBehaviorProfile
from .serializers import AccountBehaviorProfileSerializer
from .services import explain_anomalies, rebuild_profiles


class BehaviorProfileViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = AccountBehaviorProfile.objects.select_related("account").all()
    serializer_class = AccountBehaviorProfileSerializer
    permission_classes = [IsAnalystOrAdmin]
    search_fields = ["account__account_number", "account__account_holder"]
    ordering_fields = ["updated_at", "transaction_count", "avg_amount"]

    def get_queryset(self):
        queryset = super().get_queryset()
        organization = request_organization(self.request)
        if organization:
            queryset = queryset.filter(organization_id=organization)
        return queryset


class BehaviorRebuildView(APIView):
    permission_classes = [IsAnalystOrAdmin]

    def post(self, request):
        organization = request_organization(request)
        if not organization:
            return Response({"detail": "No organization context"}, status=400)
        days = request.data.get("days")
        profiles = rebuild_profiles(organization, days=int(days) if days else None)
        return Response({"profiles_rebuilt": len(profiles)})


class BehaviorAnomaliesView(APIView):
    permission_classes = [IsAnalystOrAdmin]

    def get(self, request):
        organization = request_organization(request)
        if not organization:
            return Response({"detail": "No organization context"}, status=400)
        return Response(explain_anomalies(organization))
