import logging
import pandas
import numpy
import hydrobr

logger = logging.getLogger(__name__)

class ExternalComunicationHidroBRService:

    @classmethod
    def search_stations_ana(cls, state: str = '') -> list[dict]:
        logger.info(f"Iniciando download de dados das estações pluviométricas (Estado: {state if state else 'Todos'})...")

        try:
            # --- FLUXO 1: EXTRAÇÃO DIRETA ---
            # Busca todas as estações de uma única vez. Se state for vazio (''), a API tenta trazer o Brasil inteiro.
            stations_dataframe: pandas.DataFrame = hydrobr.get_data.ANA.list_prec_stations(state=state, source='ANA')

            # --- FLUXO 2: VALIDAÇÃO INICIAL ---
            if stations_dataframe is None or stations_dataframe.empty:
                logger.warning("\033[1;95mNenhuma estação encontrada pela biblioteca hydrobr.\033[0m")
                return []
            
            logger.info(f"\033[94m{len(stations_dataframe)} estações obtidas. Iniciando tradução do DataFrame...\033[0m")
            
            # --- FLUXO 3: TRADUÇÃO E LIMPEZA DE COLUNAS ---
            if stations_dataframe.index.name == 'Code' or not 'Code' in stations_dataframe.columns:
                stations_dataframe = stations_dataframe.reset_index()
                if 'index' in stations_dataframe.columns:
                    stations_dataframe = stations_dataframe.rename(columns={'index': 'Code'})

            column_mapping: dict = {
                'Code': 'code', 'Name': 'name', 'Basin': 'basin', 'SubBasin': 'basin', 
                'Latitude': 'latitude', 'Lat': 'latitude', 'Longitude': 'longitude', 
                'Lon': 'longitude', 'Altitude': 'altitude', 'Alt': 'altitude',
                'State': 'state', 'City': 'city', 'Responsible': 'operator', 'Type': 'station_type'
            }

            stations_dataframe = stations_dataframe.rename(columns=lambda column_name: column_mapping.get(column_name, column_name))

            # --- FLUXO 4: FILTRO GEOGRÁFICO ---
            if state:
                # Força o estado solicitado caso a ANA mande vazio
                stations_dataframe['state'] = state.upper()

            else:
                # Se buscou o Brasil todo, preenche vazios e remove estações de outros países
                if 'state' not in stations_dataframe.columns:
                    stations_dataframe['state'] = 'BR'
                    
                    stations_dataframe['state'] = stations_dataframe['state'].fillna('BR').astype(str).str.strip().str.upper()                    
                    
                    brazilian_states: list[str] = [ 
                        'AC', 'AL', 'AP', 'AM', 'BA', 'CE', 'DF', 'ES', 'GO', 'MA', 'MT', 
                        'MS', 'MG', 'PA', 'PB', 'PR', 'PE', 'PI', 'RJ', 'RN', 'RS', 'RO', 
                        'RR', 'SC', 'SP', 'SE', 'TO', 'BR'
                    ]
                    
                    mask_invalid_states = ~stations_dataframe['state'].isin(brazilian_states)
                    
                    invalid_count = mask_invalid_states.sum()
                
                    if invalid_count > 0:
                        stations_dataframe.loc[mask_invalid_states, 'state'] = 'BR'
                        logger.info(f"\033[1;93mMetadados: {invalid_count} estações vieram sem estado da ANA. Classificadas como 'BR'.\033[0m")
                        
            # --- FLUXO 5: FORMATAÇÃO FINAL PARA O BANCO DE DADOS ---
            expected_columns_list: list[str] = [
                'code', 'name', 'basin', 'latitude', 'longitude',
                'altitude', 'state', 'city', 'station_type', 'operator',
                'start_date', 'end_date', 'missing_percentage'
            ]
            
            # Garante que todas as colunas existam antes do reindex para evitar erros
            for expected_column in expected_columns_list:
                if expected_column not in stations_dataframe.columns:
                    stations_dataframe[expected_column] = None

            stations_dataframe = stations_dataframe.reindex(columns=expected_columns_list)
            stations_dataframe['basin'] = stations_dataframe['basin'].fillna('NA')
            
            # Transforma os vazios padrão do pandas (NaN) em valores None nativos do python (para o PostGIS)
            stations_dataframe = stations_dataframe.astype(object).where(pandas.notna(stations_dataframe), None)
            
            formatted_stations_list = stations_dataframe.to_dict(orient='records')
            
            logger.info("\033[1;92mConversão concluída com sucesso. Retornando os dados para a orquestração.\033[0m")
            return formatted_stations_list
                
        except Exception as critical_error:
            logger.error(f"\033[1;91mFalha crítica ao buscar os dados das estações com hydrobr: {critical_error}\033[0m")
            raise