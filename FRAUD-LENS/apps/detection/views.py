from rest_framework import viewsets
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.permissions import IsAnalystOrAdmin, IsAnalystWriteOrReadOnly
from apps.core.utils import request_organization

from .ml import explain_transaction, global_explanation
from .models import DetectionRun, FraudFinding, ModelPerformance, RiskScore
from .serializers import DetectionAnalyzeSerializer, DetectionRunSerializer, FraudFindingSerializer, ModelPerformanceSerializer, RiskScoreSerializer
from .services import run_detection


class DetectionRunViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = DetectionRun.objects.select_related("organization", "initiated_by").all()
    serializer_class = DetectionRunSerializer
    permission_classes = [IsAnalystOrAdmin]
    ordering_fields = ["started_at", "transactions_analyzed", "high_risk_count"]

    def get_queryset(self):
        queryset = super().get_queryset()
        organization = request_organization(self.request)
        if organization:
            queryset = queryset.filter(organization_id=organization)
        return queryset


class FraudFindingViewSet(viewsets.ModelViewSet):
    queryset = FraudFinding.objects.select_related("transaction", "detection_run").all()
    serializer_class = FraudFindingSerializer
    permission_classes = [IsAnalystWriteOrReadOnly]
    filterset_fields = ["kind", "severity", "status", "detection_run"]
    search_fields = ["title", "description"]
    ordering_fields = ["detected_at", "confidence", "severity"]

    def get_queryset(self):
        queryset = super().get_queryset()
        organization = request_organization(self.request)
        if organization:
            queryset = queryset.filter(organization_id=organization)
        return queryset


class RiskScoreViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = RiskScore.objects.select_related("transaction", "finding").all()
    serializer_class = RiskScoreSerializer
    permission_classes = [IsAnalystOrAdmin]
    filterset_fields = ["risk_level", "detection_run"]
    search_fields = ["transaction__transaction_id"]
    ordering_fields = ["risk_score", "computed_at"]

    def get_queryset(self):
        queryset = super().get_queryset()
        organization = request_organization(self.request)
        if organization:
            queryset = queryset.filter(organization_id=organization)
        return queryset


class PerformanceViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = ModelPerformance.objects.all()
    serializer_class = ModelPerformanceSerializer
    permission_classes = [IsAnalystOrAdmin]
    ordering_fields = ["trained_at", "f1_score"]

    def get_queryset(self):
        queryset = super().get_queryset()
        organization = request_organization(self.request)
        if organization:
            queryset = queryset.filter(organization_id=organization)
        return queryset


class DetectionAnalyzeView(APIView):
    permission_classes = [IsAnalystOrAdmin]

    def post(self, request):
        serializer = DetectionAnalyzeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        organization = request_organization(request)
        if not organization:
            return Response({"detail": "No organization context"}, status=400)
        result = run_detection(
            organization,
            initiated_by=request.user,
            force=serializer.validated_data.get("force", False),
            parameters=serializer.validated_data,
        )
        return Response(result)


class DetectionExplainView(APIView):
    permission_classes = [IsAnalystOrAdmin]

    def get(self, request):
        organization = request_organization(request)
        if not organization:
            return Response({"detail": "No organization context"}, status=400)
        transaction_id = request.query_params.get("transaction")
        if transaction_id:
            score = RiskScore.objects.filter(organization_id=organization, transaction__transaction_id=transaction_id).select_related("transaction").first()
            if not score:
                return Response({"detail": "Risk score not found"}, status=404)
            return Response(explain_transaction(score))
        return Response(global_explanation(organization))
