from rest_framework import viewsets
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.permissions import IsAnalystOrAdmin
from apps.core.utils import request_organization
from apps.transactions.models import TransactionRelationship
from apps.transactions.serializers import TransactionRelationshipSerializer

from .services import cluster_payload, graph_payload, path_payload, sync_transaction_relationships


class GraphView(APIView):
    permission_classes = [IsAnalystOrAdmin]

    def get(self, request):
        organization = request_organization(request)
        if not organization:
            return Response({"detail": "No organization context"}, status=400)
        days = int(request.query_params.get("days", 30))
        min_amount = float(request.query_params.get("min_amount", 0))
        limit = int(request.query_params.get("limit", 500))
        return Response(graph_payload(organization, days=days, min_amount=min_amount, limit=limit))


class ClusterView(APIView):
    permission_classes = [IsAnalystOrAdmin]

    def get(self, request):
        organization = request_organization(request)
        if not organization:
            return Response({"detail": "No organization context"}, status=400)
        days = int(request.query_params.get("days", 30))
        min_amount = float(request.query_params.get("min_amount", 0))
        return Response(cluster_payload(organization, days=days, min_amount=min_amount))


class PathView(APIView):
    permission_classes = [IsAnalystOrAdmin]

    def get(self, request):
        organization = request_organization(request)
        if not organization:
            return Response({"detail": "No organization context"}, status=400)
        source = request.query_params.get("source")
        target = request.query_params.get("target")
        if not source or not target:
            return Response({"detail": "source and target are required"}, status=400)
        return Response(path_payload(organization, source, target))


class RelationshipSyncView(APIView):
    permission_classes = [IsAnalystOrAdmin]

    def post(self, request):
        organization = request_organization(request)
        if not organization:
            return Response({"detail": "No organization context"}, status=400)
        count = sync_transaction_relationships(organization)
        return Response({"relationships": count})


class RelationshipViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = TransactionRelationship.objects.select_related("source_account", "target_account").all()
    serializer_class = TransactionRelationshipSerializer
    permission_classes = [IsAnalystOrAdmin]
    search_fields = ["source_identifier", "target_identifier"]
    ordering_fields = ["last_seen", "total_amount", "transaction_count"]

    def get_queryset(self):
        queryset = super().get_queryset()
        organization = request_organization(self.request)
        if organization:
            queryset = queryset.filter(organization_id=organization)
        return queryset
