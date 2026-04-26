from django.urls import path

from .views import (
    download_prescription_file,
    MyPrescriptionDetailView,
    MyPrescriptionListCreateView,
    PharmacistPrescriptionDetailView,
    PharmacistQueueView,
    review_prescription,
)


urlpatterns = [
    path("", MyPrescriptionListCreateView.as_view(), name="prescription-list-create"),
    path("<str:reference_code>/file/", download_prescription_file, name="prescription-file"),
    path("<str:reference_code>/", MyPrescriptionDetailView.as_view(), name="prescription-detail"),
    path("pharmacist/queue/", PharmacistQueueView.as_view(), name="pharmacist-prescription-queue"),
    path("pharmacist/queue/<str:reference_code>/", PharmacistPrescriptionDetailView.as_view(), name="pharmacist-prescription-detail"),
    path("pharmacist/queue/<str:reference_code>/review/", review_prescription, name="pharmacist-prescription-review"),
]
