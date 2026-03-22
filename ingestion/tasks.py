import logging
from celery import shared_task

from ingestion.services import (
    ExternalComunicationHidroBRService, 
    StationSyncService, 
    ElevationSearchService
)

logger = logging.getLogger(__name__)

@shared_task(bind=True, max_retries=3, queue='auto_sync')
def task_sync_search_altitudes(self) -> dict[str, int]:
    task_id = self.request.id
    logger.info(f"\033[94m[Task ID: {task_id}] Iniciando rotina de enriquecimento de altitudes via OpenTopoData...\033[0m")
    
    try:
        total_update_altitudes: int = ElevationSearchService.search_altitudes_using_API()
        logger.info(f"\033[1;92m[Task ID: {task_id}] Sucesso! {total_update_altitudes} estações atualizadas com novas altitudes no PostGIS.\033[0m")

        return {
            "altitudes_enriquecidas": total_update_altitudes
        }

    except Exception as exc:
        attempt = self.request.retries + 1
        logger.error(f"\033[1;91m[Task ID: {task_id}] Falha na integração com OpenTopoData (Tentativa {attempt}/{self.max_retries}). Motivo: {exc}\033[0m")
        
        # Em caso de falha da API externa, tenta novamente em 60 segundos
        raise self.retry(exc=exc, countdown=60)

@shared_task(bind=True, max_retries=3, queue='auto_sync')
def task_sync_stations(self) -> dict[str, int]:
    task_id = self.request.id
    logger.info(f"\033[94m[Task ID: {task_id}] Iniciando extração e sincronização da malha de estações pluviométricas (Escopo: Nacional)...\033[0m")

    try:
        list_weather_stations: list[dict] = ExternalComunicationHidroBRService.search_stations_ana()
        logger.info(f"[Task ID: {task_id}] Download da agência concluído. Motor de sincronização PostGIS será acionado para {len(list_weather_stations)} registros brutos.")

        status_states: dict[str, int] = StationSyncService.synchronize_meteorological_stations_with_agency(list_weather_stations)
        logger.info(
            f"\033[1;92m[Task ID: {task_id}] Mutação no banco finalizada! "
            f"Novas: {status_states.get('new', 0)} | "
            f"Atualizadas: {status_states.get('updated', 0)} | "
            f"Desativadas: {status_states.get('deactivated', 0)}\033[0m"
        )

        if status_states.get('new', 0) > 0 or status_states.get('updated', 0) > 0:
            logger.info(f"[Task ID: {task_id}] Detectadas mudanças na malha. Enfileirando sub-tarefa de altitudes (task_enrich_altitudes)...")
            
            task_sync_search_altitudes.apply_async()
            

            logger.info(f"[Task ID: {task_id}] Sub-tarefa delegada para a fila 'auto_sync' com sucesso.")
        
        else:
            logger.info(f"\033[1;93m[Task ID: {task_id}] Nenhuma alteração estrutural nas estações. Sub-tarefa de altitudes ignorada para poupar recursos.\033[0m")
        
        return status_states
    
    except Exception as exc:
        attempt = self.request.retries + 1
        logger.error(f"\033[1;91m[Task ID: {task_id}] Quebra crítica na sincronização de metadados (Tentativa {attempt}/{self.max_retries}). Traceback: {exc}\033[0m")
        raise self.retry(exc=exc, countdown=60)