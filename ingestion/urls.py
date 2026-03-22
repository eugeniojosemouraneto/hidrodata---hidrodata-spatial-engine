from django.urls import path

from ingestion.views import SpatialSearchView

app_name = 'ingestion'

urlpatterns = [
    path('busca-espacial/', SpatialSearchView.as_view(), name='spatial_search'),
]