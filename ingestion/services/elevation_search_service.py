import logging
import math
import time
import requests
from django.db import transaction

from ingestion.models import Station

logger = logging.getLogger(__name__)

class ElevationSearchService:

    API_URL: str = "https://api.opentopodata.org/v1/srtm30m"
    BATCH_SIZE: int = 50
    RATE_LIMIT_SLEEP_SECONDS: float = 1.2
    
    @classmethod
    def search_altitudes_using_API(cls) -> int:
        active_stations_without_altitude: list[Station] = list(Station.objects.filter(is_active=True, altitude__isnull=True))

        if not active_stations_without_altitude:
            logger.info("\033[1;92mTodas as estações mapeadas já possuem altitude! Nenhuma ação necessária.\033[0m")
            return 0
        
        total_stations: int = len(active_stations_without_altitude)
        total_chunks: int = math.ceil(total_stations / cls.BATCH_SIZE) # pega o menor inteiro que seja maior que o resultado da operação
        total_updated: int = 0

        logger.info(f"\033[94mIniciando busca ASSÍNCRONA de altitude para {total_stations} estações via OpenTopoData (Lotes de {cls.BATCH_SIZE})...\033[0m")

        # Para o processamento em lotes
        for i in range(0, total_stations, cls.BATCH_SIZE): # for(inicio=0; vai_ate=total_stations; acrescimo_por_loop=cls.BATCH_SIZE)
            chunk: list[Station] = active_stations_without_altitude[i:i + cls.BATCH_SIZE]

            locations_str: str = "|".join([f"{station.latitude},{station.longitude}" for station in chunk])
            url: str = f"{cls.API_URL}?locations={locations_str}"

            chunk_updated_count: int = 0

            try:

                response: requests.Response = requests.get(url, timeout=20)

                if response.status_code == 200:
                    data: dict = response.json()
                    results: list[dict] = data.get('results', [])

                    stations_to_update: list[Station] = []

                    for idx, res in enumerate(results):
                        elevation = res.get('elevation')
                        if elevation is not None:
                            chunk[idx].altitude = round(float(elevation), 2)
                            stations_to_update.append(chunk[idx])
                            chunk_updated_count += 1
                    
                    if stations_to_update:
                        with transaction.atomic():
                            # Atualização do lote com uma query
                            Station.objects.bulk_update(stations_to_update, ['altitude'])
                            
                        total_updated += chunk_updated_count

                    logger.info(
                        f"[OpenTopoData] Lote {int((i/cls.BATCH_SIZE)+1):04d}/{total_chunks:04d} finalizado. "
                        f"Altitudes encontradas: {chunk_updated_count} de {len(chunk)} | "
                        f"Total no banco: {total_updated}"
                    )

                else:
                    logger.warning(f"\033[1;93m[OpenTopoData] Erro no lote {int((i/cls.BATCH_SIZE)+1)} - Status Code: {response.status_code}. Resposta: {response.text}\033[0m")
            
            except requests.exceptions.RequestException as e:
                logger.error(f"\033[1;91m[OpenTopoData] Falha de conexão/Timeout no lote {int((i/cls.BATCH_SIZE)+1)}: {e}\033[0m")

            time.sleep(cls.RATE_LIMIT_SLEEP_SECONDS)
        
        logger.info(f"\033[1;92mProcesso de altitude concluído! {total_updated} novas altitudes registradas no PostGIS.\033[0m")
        return total_updated
    

    @classmethod
    def get_altitude_for_coordinate(cls, latitude: float, longitude: float) -> float | None:
        try:
            url: str = f"{cls.API_URL}?locations={latitude},{longitude}"

            response = requests.get(url, timeout=3)

            if response.status_code == 200:

                data = response.json()
                if 'results' in data and len(data['results']) > 0:
                    elevation = data['results'][0].get('elevation')
                    return float(elevation) if elevation is not None else None

        except requests.exceptions.RequestException as e:
            logger.error(f"\033[1;91m[OpenTopoData] Falha de conexão/Timeout na busca em tempo real para {latitude},{longitude}: {e}\033[0m")
        
        except Exception as e:
            logger.error(f"Erro inesperado ao buscar altitude em tempo real para {latitude},{longitude}: {e}")
            
        return None