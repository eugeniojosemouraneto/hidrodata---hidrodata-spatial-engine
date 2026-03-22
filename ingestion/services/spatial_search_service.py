import logging
import math
from django.contrib.gis.geos import Point
from django.contrib.gis.measure import D
from django.contrib.gis.db.models.functions import Distance, Azimuth
from django.db.models import F
from django.db.models.query import QuerySet

from ingestion.models import Station

logger = logging.getLogger(__name__)

class SpatialSearchService:
    # Motor matemático para buscas geoespaciais utilizando PostGIS, aonde realiza uma busca radial por quadrantes das estações mais proximas em cada quadrante

    @classmethod
    def find_nearest_stations_by_quadrant(
        cls,
        latitude: float,
        longitude: float,
        radius_kilometers: float = 50.0,
        limit_per_quadrant: int = 3
    ):
        reference_location = Point(longitude, latitude, srid=4326)
        # Referencia espacial da estação, pelas coordenadas

        logger.info(
            f"\033[94mBuscando até {limit_per_quadrant} estações por quadrante "
            f"num raio de {radius_kilometers}km da coordenada ({latitude}, {longitude})...\033[0m"
        )

        stations_in_radius: QuerySet[Station] = Station.objects.filter(
            is_active=True,
            location__distance_lte=(reference_location, D(km=radius_kilometers))
        ).annotate(
            distance_to_reference=Distance('location', reference_location),
            azimuth_radians=Azimuth(reference_location, 'location') # Calcula direção no DB (Retorna radianos)
        )
        # Já separa as estações que estão dentro do raio máximo do ponto de referencia
        # .annotate( ... ) -:- injeta temporariamente o calculo da distancia da estação com o ponto de referencia

        northeast_stations: list[Station] = list(
            stations_in_radius.filter(
                latitude__gte=latitude, 
                longitude__gte=longitude
            ).order_by('distance_to_reference')[:limit_per_quadrant]
        )
        # Quadrante Nordeste (NE): Latitude maior/igual, Longitude maior/igual

        northwest_stations: list[Station] = list(
            stations_in_radius.filter(
                latitude__gte=latitude, 
                longitude__lt=longitude
            ).order_by('distance_to_reference')[:limit_per_quadrant]
        )
        # Quadrante Noroeste (NW): Latitude maior/igual, Longitude menor
        
        southeast_stations: list[Station] = list(
            stations_in_radius.filter(
                latitude__lt=latitude, 
                longitude__gte=longitude
            ).order_by('distance_to_reference')[:limit_per_quadrant]
        )
        # Quadrante Sudeste (SE): Latitude menor, Longitude maior/igual
        
        southwest_stations: list[Station] = list(
            stations_in_radius.filter(
                latitude__lt=latitude, 
                longitude__lt=longitude
            ).order_by('distance_to_reference')[:limit_per_quadrant]
        )
        # Quadrante Sudoeste (SW): Latitude menor, Longitude menor

        nearest_stations: list[Station] = (
            northeast_stations + northwest_stations + southeast_stations + southwest_stations
        )
        # Combina todas as estações de todos os quadrantes 

        nearest_stations.sort(key=lambda station: station.distance_to_reference)

        for station in nearest_stations:
            if station.azimuth_radians is not None:
                # Transforma de radianos para graus normais (0 a 360)
                station.azimuth_degrees = round(math.degrees(station.azimuth_radians), 2)
                
            else:
                station.azimuth_degrees = None
        
        logger.info(
            f"\033[1;92mBusca espacial concluída: {len(nearest_stations)} "
            f"estações resgatadas cercando o ponto de referência.\033[0m"
        )
        
        return nearest_stations