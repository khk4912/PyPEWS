import datetime
from typing import List, Tuple, Union
from urllib.parse import unquote
from dataclasses import dataclass

import requests

from stations import sta
from errors import HTMLStatusException

regions: list = [
    "서울",
    "부산",
    "대구",
    "인천",
    "광주",
    "대전",
    "울산",
    "세종",
    "경기",
    "강원",
    "충북",
    "충남",
    "전북",
    "전남",
    "경북",
    "경남",
    "제주",
]
timeZone: int = 9
tzMsec: int = timeZone * 3600000
tide: int = 1000
header_len: int = 4
max_eqk_info_len: int = 120
stations: list = sta
max_eqk_str_len: int = 60
DATA_PATH: str = "https://www.weather.go.kr/pews/data"


def lpad(text: str, length: int):
    while len(text) < length:
        text = "0" + text
    return text


def escape(text: str) -> str:
    """
    https://bit.ly/2ZQiad8 의 파이썬 구현입니다.
    
    Args:
        text (str): escape할 문자열.
    
    Returns:
        str: escape된 문자열
    """
    ignore_char = (
        "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"
        "0123456789@*_+-./"
    )
    result = ""

    for i in text:
        if i in ignore_char:
            result += i
        else:
            result += "%{0:02x}".format(ord(i))
    return result


def get_MMI(url: Union[str, None] = None) -> bytes:
    """
    MMI 정보를 얻는 url에서 binary 정보를 얻습니다.

    Args:
        url (str, optional): MMI 정보를 얻을 url입니다.
            만약 입력하지 않으면 현재 시간으로 url을 자동 생성합니다.
    
    Returns:
        bytes: URL 에서 얻은 MMI 바이트 정보를 반환합니다.
    """
    if url is None:
        pTime = (
            datetime.datetime.utcnow() - datetime.timedelta(seconds=1)
        ).strftime("%Y%m%d%H%M%S")
        url = f"{DATA_PATH}/{pTime}.b"

    r = requests.get(url, timeout=1.0)

    if (status := r.status_code) == 200:
        return r.content
    else:
        raise HTMLStatusException(str(status))


def parse_MMI(content: bytes) -> Tuple[int, str, list]:
    """
    get_MMI 에서 얻은 바이트 정보를 파싱하여 
    원본 JS 함수 변수인 phase, binaryStr, infoStrArr을 반환합니다.

    Args:
        content (bytes): get_MMI 에서 얻은 바이트 정보입니다.
    
    Returns:
        Tuple[int, str, list]: phase, binaryStr, infoStrArr을 반환합니다.
    """
    data = bytearray(content)
    bin_data = ["{:0b}".format(x) for x in data]  # .toString(2) 된 값
    byte_length = len(bin_data)

    # TODO : 헤더로 시간 동기화 구현
    # === origin_pews.js 그대로 Reverse ===
    header = ""
    binary_str = lpad(str(bin_data[0]), 8)

    for i in range(0, header_len):
        header += lpad(bin_data[i], 8)

    for i in range(header_len, byte_length):
        binary_str += lpad(bin_data[i], 8)

    staF = header[0] == "1"

    phase = None
    if header[1] == "0":
        phase = 1
    elif header[1] == "1" and header[2] == "0":
        phase = 2
    elif header[2] == "1":
        phase = 3

    assert phase is not None
    # ====================================
    info_str_arr = []
    for i in range(byte_length - max_eqk_str_len, byte_length):
        info_str_arr.append(bin_data[i])

    # TODO : get_sta 구현 후 재시작 필요 (Line 289~)

    return phase, binary_str, info_str_arr
    # ====================================


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


def eqk_handler(data: str, buffer: list) -> EqkInfo:
    """
    phase가 1 이상인 경우 호출하여 지진의 정보를 반환합니다.

    Args:
        data (str): parse_MMI 에서 반환하는 binary_str
        buffer (list): parse_MMI에서 반환하는 info_str_arr
    
    Returns:
        Eqkinfo: 지진 정보를 나타내는 EqkInfo dataclass를 반환합니다.
    """
    data = data[0 - ((max_eqk_str_len * 8 + max_eqk_info_len)) :]
    origin_lat = 30 + (int(data[0:10], 2) / 100)  # 위도
    origin_lon = 124 + (int(data[10:20], 2) / 100)
    origin_x = None
    origin_y = None  # TODO : fn_parseY, fn_parseX
    eqk_mag = int(data[20:27], 2) / 10
    eqk_dep = int(data[27:37], 2) / 10
    eqk_time = int(str(int(data[37:59], 2)) + "000")
    eqk_id = int("20" + str(int(data[69:95], 2)))
    eqk_max = int(data[95:99], 2)
    eqk_max_area_str = data[99:116]
    eqk_max_area = []

    buffer = [int(x, 2) for x in buffer]
    eqk_str = unquote(escape("".join(map(chr, buffer))))

    if eqk_max_area_str != "11111111111111111":
        for i in range(17):
            if eqk_max_area_str[i] == "1":
                eqk_max_area.append(regions[i])
    else:
        eqk_max_area.append("-")

    return EqkInfo(
        origin_lat,
        origin_lon,
        origin_x,
        origin_y,
        eqk_mag,
        eqk_dep,
        eqk_time,
        eqk_id,
        eqk_max,
        eqk_max_area,
        eqk_str,
    )  # TODO : 398~400 구현


def callback(data: list):
    mmi_object = mmi_bin_handler()


def mmi_bin_handler():
    pass


def get_sta(url: Union[str, None] = None) -> bytes:
    """
    스테이션 정보를 얻는 url에서 binary 정보를 얻습니다.

    Args:
        url (str, optional): 스테이션 정보를 얻을 url입니다.
            만약 입력하지 않으면 현재 시간으로 url을 자동 생성합니다.
    
    Returns:
        bytes: URL 에서 얻은 스테이션 바이트 정보를 반환합니다.
    """

    if url is None:
        pTime = (
            datetime.datetime.utcnow() - datetime.timedelta(seconds=1)
        ).strftime("%Y%m%d%H%M%S")
        url = f"{DATA_PATH}/{pTime}.s"

    r = requests.get(url, timeout=1.0)

    if (status := r.status_code) == 200:
        return r.content
    else:
        raise HTMLStatusException(str(status))


@dataclass
class StaInfo:
    name: str
    lat: float
    lon: float
    idx: int


def parse_sta(content: bytes) -> str:
    data = bytearray(content)
    bin_data = ["{:0b}".format(x) for x in data]
    binary_str = ""

    for i in bin_data:
        binary_str += lpad(i, 8)

    return binary_str


def get_sta_info(data: str) -> List[StaInfo]:
    new_sta = []
    sta_lat = []
    sta_lon = []

    for i in range(0, len(data), 20):
        sta_lat.append(30 + int(data[i : i + 10], 2) / 100)
        sta_lon.append(120 + int(data[i + 10 : i + 20], 2) / 100)

    for i in range(len(sta_lat)):
        new_sta.append(StaInfo(stations[i], sta_lat[i], sta_lon[i], i))

    return new_sta
