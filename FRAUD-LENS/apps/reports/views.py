import io

from django.http import FileResponse
from rest_framework import viewsets
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.permissions import IsAnalystOrAdmin
from apps.core.utils import request_organization

from .models import Report
from .serializers import ReportGenerateSerializer, ReportSerializer
from .services import generate_report


class ReportViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Report.objects.select_related("created_by").all()
    serializer_class = ReportSerializer
    permission_classes = [IsAnalystOrAdmin]
    filterset_fields = ["kind", "file_format"]
    search_fields = ["title", "file_name"]
    ordering_fields = ["created_at"]

    def get_queryset(self):
        queryset = super().get_queryset()
        organization = request_organization(self.request)
        if organization:
            queryset = queryset.filter(organization_id=organization)
        return queryset


class ReportGenerateView(APIView):
    permission_classes = [IsAnalystOrAdmin]

    def post(self, request):
        serializer = ReportGenerateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        organization = request_organization(request)
        if not organization:
            return Response({"detail": "No organization context"}, status=400)
        values = serializer.validated_data
        report = generate_report(
            organization,
            created_by=request.user,
            kind=values["kind"],
            file_format=values["file_format"],
            title=values.get("title"),
            parameters={"days": values["days"]},
        )
        return Response(ReportSerializer(report).data, status=201)


class ReportDownloadView(APIView):
    permission_classes = [IsAnalystOrAdmin]

    def get(self, request, pk):
        organization = request_organization(request)
        queryset = Report.objects.all()
        if organization:
            queryset = queryset.filter(organization_id=organization)
        try:
            report = queryset.get(pk=pk)
        except Report.DoesNotExist:
            return Response({"detail": "Report not found"}, status=404)
        return FileResponse(
            io.BytesIO(bytes(report.file_data)),
            as_attachment=True,
            filename=report.file_name,
            content_type=report.content_type,
        )
