from django.shortcuts import render
from django.views import View
from django.contrib import messages

from ingestion.forms import SpatialSearchForm
from ingestion.services import SpatialSearchService, ElevationSearchService


class SpatialSearchView(View):

    template_name: str = 'ingestion/spatial_search.html'

    def get(self, request):
        form = SpatialSearchForm()

        return render(
            request=request,
            template_name=self.template_name,
            context={
                'form': form,
                'results': None
            }
        )
    
    def post(self, request):
        form = SpatialSearchForm(request.POST)
        results = None
        target_altitude = None

        if form.is_valid():
            latitude = form.cleaned_data['latitude']
            longitude = form.cleaned_data['longitude']
            radius_km = form.cleaned_data['radius_kilometers']
            limit = form.cleaned_data['limit_per_quadrant']

            target_altitude: float | None = ElevationSearchService.get_altitude_for_coordinate(latitude, longitude)

            results = SpatialSearchService.find_nearest_stations_by_quadrant(
                latitude=latitude,
                longitude=longitude,
                radius_kilometers=radius_km,
                limit_per_quadrant=limit
            )

            if results and target_altitude is not None:
                for station in results:
                    if station.altitude is not None:
                        station.delta_h = station.altitude - target_altitude

                    else:
                        station.delta_h = None

        else:
            for error in form.non_field_errors():
                messages.error(request, error)
            
            for field in form:
                for error in field.errors:
                    messages.error(request, f"{field.label}: {error}")
        
        return render(
            request=request,
            template_name=self.template_name,
            context={
                'form': form,
                'results': results,
                'target_altitude': target_altitude
            }
        )