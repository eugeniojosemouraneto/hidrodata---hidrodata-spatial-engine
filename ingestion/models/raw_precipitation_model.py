from django.contrib.gis.db import models
from django.contrib.postgres.indexes import BrinIndex
from django.db.models import Q, CheckConstraint

class RawPrecipitation(models.Model):
    """
    Tabela operada estritamente via append-only com os dados de precipitação.
    """
    
    station = models.ForeignKey("ingestion.Station", on_delete=models.CASCADE, related_name='precipitations')
    date = models.DateField(verbose_name="Data da Medição")
    measured_value = models.FloatField(verbose_name="Valor Medido (mm)", null=True, blank=True)
    origin = models.CharField(max_length=50, verbose_name="Origem dos Dados") # Ex: ANA, INMET

    class Meta:

        unique_together = ('station', 'date', 'origin')
        indexes = [
            models.Index(fields=['date', 'station']),
            BrinIndex(fields=['date'], name='brin_date_idx'),
        ]
        constraints = [
            CheckConstraint(
                condition=Q(measured_value__gte=0.0) | Q(measured_value__isnull=True),
                name='check_valid_precipitation'
            )
        ]

    def __str__(self):
        val = f"{self.measured_value}mm" if self.measured_value is not None else "FALHA (NULL)"
        return f"{self.station.code} - {self.date}: {val}"