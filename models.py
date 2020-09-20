from dataclasses import dataclass


@dataclass
class EqkInfo:
    """
    지진 정보를 나타내는 dataclass입니다.

    Args:
        origin_lat (float): 위도
        origin_lon (float): 경도
        origin_x (None): 
        origin_y (None):
        eqk_mag (float): 지진의 메그니튜드 규모
        eqk_dep (float): 지진의 깊이
        eqk_id (int): 지진 고유 ID
        eqk_max (int): 지진의 최대진도
        eqk_max_area (list): 최대진도 지역
        eqk_str (str): 지진 상세문구
    """

    origin_lat: float
    origin_lon: float
    origin_x: None
    origin_y: None
    eqk_mag: float
    eqk_dep: float
    eqk_time: int
    eqk_id: int
    eqk_max: int
    eqk_max_area: list
    eqk_str: str


@dataclass
class StaInfo:
    name: str
    lat: float
    lon: float
    idx: int
