import logging

from pyproj import Geod
from typing import Literal


logger = logging.getLogger(__name__)


class TopographicCorridorService:
    # Serviço responsavel por gerar a malha ortogonal geodesica entre dois pontos geograficos na superficie terrestre

    _GEOD = Geod(ellps="WGS84")

    # Constantes físicas do limite do corredor 
    MINIMUM_WIDTH_METERS: float = 500.0
    MAXIMUM_WIDTH_METERS: float = 6000.0

    WIDTH_DISPERSION_FACTOR: float = 0.09

    # Constante do Teorema de Nyquist para o SRTM30 
    MINIMUM_STEP_METERS: float = 30.0

    @classmethod
    def _calculate_dynamic_width(
        cls, 
        total_distance_m: float
    ) -> float:
        #  Calculo da distancia transversal (W) do corredor topografico
        # 500m (0.5km) >= W >= 6000m (6km), limites do corredor 
        calculated_width: float = total_distance_m * cls.WIDTH_DISPERSION_FACTOR
         
        # Formula da largura dinamica (W) = max (500.0, min(6000.0, distance))
        return max(
            cls.MINIMUM_WIDTH_METERS,
            min(
                cls.MAXIMUM_WIDTH_METERS,
                calculated_width
            )
        )

    @classmethod
    def _calculate_grid_resolution(
        cls, 
        total_distance_meters: float, 
        precision_mode: Literal['economic', 'deep']
    ) -> float:
        """
        Calcula o espaçamento geodésico entre os nós da malha
        
        economic -:- Passo = max(30, min(2000, Distancia / 20)) 
            - 30m (0.03km) >= Passo >= 2000.0m (2km)
        
        deep -:- Passo = max(30, min(500, Distancia / 100)) 
            - 30m (0.03km) >= Passo >= 500.0m (0.5km)
        """

        if precision_mode == 'deep':
            return max(cls.MINIMUM_STEP_METERS, min(500.0, total_distance_meters / 300.0))
        
        return max(cls.MINIMUM_STEP_METERS, min(2000.0, total_distance_meters / 100.0))
    
    @classmethod
    def generate_swath_profile_mesh(
        cls, 
        target_latitude: float, 
        target_longitude: float, 
        station_latitude: float, 
        station_longitude: float, 
        precision_mode: Literal['economic', 'deep'] = 'economic'
    ) -> dict[str, list[tuple[float, float]]]:
        """
        Gera a matriz as coordenadas geográficas que compõem o Corredor Topografico.
        """
        logger.info(
            f"Gerando malha ortogonal (Modo: {precision_mode}) do Alvo ({target_latitude}, {target_longitude}) "
            f"para a Estação ({station_latitude}, {station_longitude})."
        )

        # Obtenção Vetorial: Azimute frontal e distância verdadeira no elipsoide
        forward_azimuth, _, total_distance_meters = cls._GEOD.inv(
            target_longitude, target_latitude, 
            station_longitude, station_latitude
        )
        # forward_azimuth       -:- ângulo de direção do alvo apontado para a estação (em graus, em relçao ao norte verdadeiro)
        # _ (back_azimuth)      -:- ângulo de retorno da estação apontando de volta ao alvo). Irrelevante no momento
        # total_distance_meters -:- distância geodésica mais curta entre os dois pontos, contornando a curvatura da Terra (em metros).

        total_distance_meters *= 1.1

        corridor_width_meters: float = cls._calculate_dynamic_width(total_distance_meters)
        # distancia transversal (W) do corredor topografico

        step_size_meters: float = cls._calculate_grid_resolution(total_distance_meters, precision_mode)
        # espaçamento geodésico entre os nós da malha

        half_width_meters: float = corridor_width_meters / 2.0
        # distancia de cada lado do corredor topografico
        
        # derivação Vetorial: Azimutes perpendiculares à linha de visada
        left_azimuth: float = (forward_azimuth - 90.0) % 360.0
        right_azimuth: float = (forward_azimuth + 90.0) % 360.0
        

        mesh_coordinates: list[tuple[float, float]] = []
        # conjunto de coordenadas do corredor topografico

        current_longitudinal_distance: float = 0.0

        left_boundary: list[tuple[float, float]] = []
        right_boundary: list[tuple[float, float]] = []
        
        while current_longitudinal_distance <= total_distance_meters:
            
            # Achar o nó central da seção transversal (espinhaço) - vai calcular as novas latitude e longitude analisando o azimut (angulação)
            
            if current_longitudinal_distance == 0.0:
                center_longitude, center_latitude = target_longitude, target_latitude

            else:
                center_longitude, center_latitude, _ = cls._GEOD.fwd(
                    target_longitude, target_latitude, 
                    forward_azimuth, current_longitudinal_distance
                )
            
            mesh_coordinates.append((center_latitude, center_longitude))

            # -- extremos coordenadas para o frontend --

            # Flanco Esquerdo Extremo
            left_lon_ext, left_lat_ext, _ = cls._GEOD.fwd(
                center_longitude, center_latitude, left_azimuth, half_width_meters
            )
            left_boundary.append((left_lat_ext, left_lon_ext))
            
            # Flanco Direito Extremo
            right_lon_ext, right_lat_ext, _ = cls._GEOD.fwd(
                center_longitude, center_latitude, right_azimuth, half_width_meters
            )
            right_boundary.append((right_lat_ext, right_lon_ext))
            
            # Expandir o corredor ortogonalmente (para as bordas), pegar as variaveis laterais a analisado no momento
            current_lateral_distance: float = step_size_meters
            
            # Construção dos pontos laterais
            while current_lateral_distance <= half_width_meters:
                # Translação para o Flanco Esquerdo
                left_longitude, left_latitude, _ = cls._GEOD.fwd(
                    center_longitude, 
                    center_latitude, 
                    left_azimuth, 
                    current_lateral_distance
                )

                mesh_coordinates.append((left_latitude, left_longitude))
                
                # Translação para o Flanco Direito
                right_longitude, right_latitude, _ = cls._GEOD.fwd(
                    center_longitude, center_latitude, 
                    right_azimuth, current_lateral_distance
                )
                
                mesh_coordinates.append((right_latitude, right_longitude))
                
                # Incrementa o passo transversal
                current_lateral_distance += step_size_meters
                
            # Avança na linha de visada rumo à estação
            current_longitudinal_distance += step_size_meters
            
        logger.info(f"Swath Profile gerado com sucesso. Total de nós (amostras): {len(mesh_coordinates)}")

        polygon_perimeter = left_boundary + right_boundary[::-1]
        
        # Cálculo da área total em km² (Distância * Largura / 1.000.000)
        area_total_km2 = (total_distance_meters * corridor_width_meters) / 1000000.0

        return {
            "mesh": mesh_coordinates,
            "perimeter": polygon_perimeter,
            "metadata": {
                "corridor_width_m": corridor_width_meters,
                "step_size_m": step_size_meters,
                "quant_coordinates": len(mesh_coordinates),
                "area_total_km2": area_total_km2
            }
        }