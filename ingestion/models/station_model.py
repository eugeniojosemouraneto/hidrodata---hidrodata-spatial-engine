from django.contrib.gis.db import models
from django.db.models import Q

class Station(models.Model):
    """
    Armazena metadados (Código, Nome, Bacia), localização espacial e status de atividade.    
    """

    code = models.CharField(max_length=50, unique=True, verbose_name="Código da Estação")
    name = models.CharField(max_length=255, verbose_name="Nome")
    basin = models.CharField(max_length=255, db_index=True, verbose_name="Bacia Hidrográfica")
    
    state = models.CharField(max_length=50, null=True, blank=True, db_index=True, verbose_name="Estado")
    city = models.CharField(max_length=255, null=True, blank=True, db_index=True, verbose_name="Município")

    station_type = models.CharField(max_length=50, null=True, blank=True, db_index=True, verbose_name="Tipo de Estação")
    operator = models.CharField(max_length=255, null=True, blank=True, verbose_name="Órgão Operador")

    start_date = models.DateField(null=True, blank=True, verbose_name="Data de Início")
    end_date = models.DateField(null=True, blank=True, verbose_name="Data de Fim")
    missing_percentage = models.FloatField(null=True, blank=True, verbose_name="% de Falhas")

    is_active = models.BooleanField(
        default=True, 
        verbose_name="Estação Ativa",
        help_text="Estações inativas não recebem novos dados das agências."
    )
    
    # Coordenadas X, Y, Z
    latitude = models.FloatField()
    longitude = models.FloatField()
    altitude = models.FloatField(null=True, blank=True)
    
    # Campo espacial PointField do PostGIS para indexação geográfica
    location = models.PointField(srid=4326, spatial_index=True)

    last_historical_sync = models.DateTimeField(
        null=True, 
        blank=True, 
        verbose_name="Última Sincronização Histórica",
        help_text="Define quando o robô de background baixou a série temporal desta estação pela última vez."
    )

    latest_raw_data_date = models.DateField(
        null=True, 
        blank=True, 
        verbose_name="Último Dado Bruto da ANA",
        help_text="Cursor Delta: Maior data de precipitação já extraída para não reprocessar o passado."
    )

    last_gap_fill_date = models.DateField(
        null=True, 
        blank=True, 
        verbose_name="Último Preenchimento de Falha",
        help_text="Cursor Matemático: Ponteiro para a Fase 3 saber a partir de que data deve iniciar o preenchimento (IDW/Thiessen)."
    )

    class Meta:
        indexes = [
            models.Index(
                fields=['is_active'], 
                name='active_stations_idx', 
                condition=Q(is_active=True)
            ),
            models.Index(
                fields=['state', 'station_type'], 
                name='state_type_idx'
            ),
            models.Index(
                fields=['missing_percentage'], 
                name='quality_idx'
            ),
            models.Index(
                fields=['last_historical_sync'], 
                name='historical_sync_idx'
            ),
            models.Index(
                fields=['latest_raw_data_date'], 
                name='latest_raw_idx'
            ),
            models.Index(
                fields=['last_gap_fill_date'], 
                name='last_gap_idx'
            ),
        ]

    def __str__(self):
        status = "Ativa" if self.is_active else "Inativa"
        return f"{self.code} - {self.name} ({self.state}) - {status}"

