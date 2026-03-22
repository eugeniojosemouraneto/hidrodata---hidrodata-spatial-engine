from django.contrib import admin
from django.contrib.gis.admin import GISModelAdmin
from ingestion.models import Station, RawPrecipitation

@admin.register(Station)
class StationAdmin(GISModelAdmin):
    list_display = ('code', 'name', 'state', 'altitude', 'station_type', 'is_active', 'missing_percentage')
    search_fields = ('code', 'name', 'basin', 'state', 'city')
    list_filter = ('is_active', 'state', 'station_type', 'operator')
    
    # Configuração do mapa no painel (Centro geográfico do Brasil)
    gis_widget_kwargs = {
        'attrs': {
            'default_lon': -50.0,
            'default_lat': -15.0,
            'default_zoom': 4,
        }
    }

@admin.register(RawPrecipitation)
class RawPrecipitationAdmin(admin.ModelAdmin):
    list_display = ('station', 'date', 'measured_value', 'origin')
    list_filter = ('origin', 'station__basin') 
    search_fields = ('station__code', 'station__name')