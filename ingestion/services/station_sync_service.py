import logging
from django.db import transaction
from django.contrib.gis.geos import Point
from pydantic import ValidationError

from ingestion.models import Station
from ingestion.schemas import StationAPISchema

logger = logging.getLogger(__name__)


class StationSyncService:

    @staticmethod
    def _validate_clean_API_data(list_weather_stations: list[dict]) -> list[dict]:
        # Validação dos dados oriundos da API, se tem os campos e tipagem determinado no schema 'StationAPISchema'
        
        valid_data: list = []

        for data_item in list_weather_stations:
            try:
                validated_station = StationAPISchema(**data_item) # **data_item desacopla o disionario em chave-valor para parametro(kwargs)-valor
                valid_data.append(validated_station.model_dump()) # acopla em um dicionario
            
            except ValidationError as e:
                logger.warning(f"Falha de validação ignorada para estação da API: {data_item.get('code', 'Desconhecido')}. Detalhes: {e}")
        
        return valid_data

    @staticmethod
    def _data_indexing_by_station_code__optimization(validated_stations: list[dict]) -> tuple[dict, set]:
        # Processo de otimização onde apartir dos dados validos da API é gerado uma tupla de duas extruturas rapidas:
        # 1° dicionario chave(codigo da estação)-valor(dados da estação)
        # 2° set/tabela-hash conjunto matemático somente dos codigos
        
        stations_index_by_station_code_API: dict[str, dict] = {}

        for station_data in validated_stations:
            stations_index_by_station_code_API[str(station_data['code'])] = station_data

        station_code_set: set[str] = set(stations_index_by_station_code_API.keys())

        return stations_index_by_station_code_API, station_code_set
    
    @staticmethod
    def _retrieve_stations_from_database__optimization() -> tuple[dict[str, Station], set[str]]:
        # Processo de otimização onde apartir dos dados validos do Bando de Dados é gerado uma tupla de duas extruturas rapidas:
        # 1° dicionario chave(codigo da estação)-valor(dados da estação)
        # 2° set/tabela-hash conjunto matemático somente dos codigos
        
        database_stations_indexed_by_code_DB: dict[str, Station] = Station.objects.only(
            'code', 'latitude', 'longitude', 'is_active', 'state', 'city', 
            'station_type', 'operator', 'start_date', 'end_date', 'missing_percentage'
        ).in_bulk(field_name='code')
        # O in_bulk(field_name='code') já devolve um dict no formato { 'codigo': Instancia_Station }

        return database_stations_indexed_by_code_DB, set(database_stations_indexed_by_code_DB.keys())
    
    @staticmethod
    def _set_mathematics__differences_in_DB_for_API(DB_station_code_set: set[str], API_station_code_set: set[str]) -> dict[str, set[str]]:
        # Teoria de conjuntos (conjuntos matemáticos) -:- será usados duas metodologias diferentes neste metodo, diferença de conjuntos e interseção de conjuntos.
        # Diferença de conjuntos (A - B) -:- o resultado será um conjunto c com todos os elementos que só existe no conjunto A.
        # Interseção de conjuntos (A & B) -:- o resultado será um conjunto c com todos os elementos que existem nos dois conjuntos.

        # newly_discovered_station_codes -:- novas estações (tem na API, mas não tem no DB)
        # missing_station_codes_to_deactivate -:- estações que tinham na API mas agora não vem mais, estações desativadas (não tem na API, mas tem no DB)
        # overlapping_station_codes_to_verify -:- estações em comum a API e DB, verificar dados

        return {
            'newly_discovered_station_codes'      : API_station_code_set - DB_station_code_set,
            'missing_station_codes_to_deactivate' : DB_station_code_set - API_station_code_set,
            'overlapping_station_codes_to_verify' : DB_station_code_set & API_station_code_set
        }
    
    @staticmethod
    def _deactivate_missing_stations(code_stations_deactivate: set[str]) -> int:
        if not code_stations_deactivate:
            return 0
        
        return Station.objects.filter(code__in=code_stations_deactivate).update(is_active=False)
    
    @staticmethod
    def _create_new_stations(
        set_news_codes: set[str], 
        API_stations_index_by_station_code: dict[str, any]
    ) -> int:
        if not set_news_codes:
            return 0
        
        new_stations: list = []
        for code_station in set_news_codes:
            data = API_stations_index_by_station_code[code_station]
            station: Station = Station(
                code=data['code'],
                name=data['name'],
                basin=data['basin'],
                latitude=data['latitude'],
                longitude=data['longitude'],
                altitude=data.get('altitude'),
                state=data.get('state'),
                city=data.get('city'),
                station_type=data.get('station_type'),
                operator=data.get('operator'),
                start_date=data.get('start_date'),
                end_date=data.get('end_date'),
                missing_percentage=data.get('missing_percentage'),
                location=Point(data['longitude'], data['latitude'], srid=4326),
                is_active=True
            )
            new_stations.append(station)

        Station.objects.bulk_create(new_stations)
        # Criação de todas as stations em uma unica query
        return len(new_stations)
    
    @staticmethod
    def _update_existing_stations(
        overlapping_codes: set[str], 
        API_stations_index_by_station_code: dict[str, any], 
        DB_stations_index_by_station_code: dict[str, Station]
    ):
        if not overlapping_codes:
            return 0
        
        stations_to_update: list = []
        
        fields_to_check: list[str] = [
            'name', 'basin', 'state', 'city', 'station_type', 'operator', 'start_date', 'end_date', 'missing_percentage'
        ]

        for code_station in overlapping_codes:
            DB_station_instance = DB_stations_index_by_station_code[code_station]
            API_station = API_stations_index_by_station_code[code_station]

            has_changed = False

            if DB_station_instance.latitude != API_station['latitude'] or DB_station_instance.longitude != API_station['longitude']:
                DB_station_instance.latitude = API_station['latitude']
                DB_station_instance.longitude = API_station['longitude']

                DB_station_instance.location = Point(API_station['longitude'], API_station['latitude'], srid=4326)

                has_changed = True

            if not DB_station_instance.is_active:
                DB_station_instance.is_active = True
                has_changed = True
            
            for field in fields_to_check:
                API_value = API_station.get(field)

                if getattr(DB_station_instance, field) != API_value:
                    setattr(DB_station_instance, field, API_value)
                    has_changed = True

            if has_changed:
                stations_to_update.append(DB_station_instance)

        if stations_to_update:
            update_columns = ['latitude', 'longitude', 'location', 'is_active'] + fields_to_check
            Station.objects.bulk_update(stations_to_update, update_columns)

        return len(stations_to_update)

    @classmethod
    @transaction.atomic
    def _persist_station_mutations_to_database(
        cls, 
        differences_between_stations_in_DB_for_API: dict[str, set[str]], 
        API_stations_index_by_station_code: dict[str, dict[str, any]], 
        DB_stations_index_by_station_code: dict[str, Station]
    ) -> dict[str, int]:
        status_stations: dict[str, int] = { 'new': 0, 'updated': 0, 'deactivated': 0 }

        status_stations['deactivated'] = cls._deactivate_missing_stations(
            code_stations_deactivate=differences_between_stations_in_DB_for_API['missing_station_codes_to_deactivate']
        )

        status_stations['new'] = cls._create_new_stations(
            set_news_codes=differences_between_stations_in_DB_for_API['newly_discovered_station_codes'],
            API_stations_index_by_station_code=API_stations_index_by_station_code
        )

        status_stations['updated'] = cls._update_existing_stations(
            overlapping_codes=differences_between_stations_in_DB_for_API['overlapping_station_codes_to_verify'],
            API_stations_index_by_station_code=API_stations_index_by_station_code,
            DB_stations_index_by_station_code=DB_stations_index_by_station_code
        )

        return status_stations

    @classmethod
    def synchronize_meteorological_stations_with_agency(cls, list_weather_stations: list[dict]) -> dict[str, int]:

        validated_stations: list[dict] = cls._validate_clean_API_data(list_weather_stations)

        API_stations_index_by_station_code, API_station_code_set = cls._data_indexing_by_station_code__optimization(validated_stations)
        DB_stations_index_by_station_code, DB_station_code_set = cls._retrieve_stations_from_database__optimization()

        differences_between_stations_in_DB_for_API: dict[str, set[str]] = cls._set_mathematics__differences_in_DB_for_API(DB_station_code_set, API_station_code_set)

        synchronization_statistics_summary: dict[str, int] = cls._persist_station_mutations_to_database(
            differences_between_stations_in_DB_for_API,
            API_stations_index_by_station_code,
            DB_stations_index_by_station_code
        )

        return synchronization_statistics_summary