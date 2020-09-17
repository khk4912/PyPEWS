import datetime
from typing import Union
from dataclasses import dataclass
import requests

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
max_eqk_str_len: int = 60
DATA_PATH: str = "https://www.weather.go.kr/pews/data"


def lpad(text: str, length: int):
    while len(text) < length:
        text = "0" + text
    return text


def get_MMI(url: Union[str, None] = None) -> bytes:

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


def get_sta(url: Union[str, None] = None) -> bytes:
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


def parse_MMI(content: bytes):
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
    print(phase)
    # ====================================
    info_str = []
    for i in range(byte_length - max_eqk_str_len, byte_length):
        info_str.append(bin_data[i])

    # TODO : get_sta 구현 후 재시작 필요 (Line 289~)

    return binary_str, info_str
    # ====================================


# phase 가 1보다 크면
def eqk_handler(data: str, buffer: list):
    data = data[0 - ((max_eqk_str_len * 8 + max_eqk_info_len))]
    origin_lat = 30 + (int(data[0:10], 2) / 100)  # 위도
    origin_lon = 124 + (int(data[10:20], 2) / 100)
    origin_x = None
    origin_y = None  # TODO : fn_parseY, fn_parseX
    eqk_mag = int(data[20:27], 2) / 10
    eak_dep = int(data[27:37], 2) / 10
    eqk_time = int(str(int(data[37:59], 2)) + "000")
    eqk_id = int("20" + str(int(data[69:95], 2)))
    eqk_max = int(data[95:99], 2)
    eqk_max_area_str = data[99:176]
    eqk_max_area = []

    if eqk_max_area_str != "11111111111111111":
        for i in range(17):
            if eqk_max_area_str[0] == "1":
                eqk_max_area.append(regions[i])
    else:
        eqk_max_area.append("-")

    eqk_str = None
    # TODO : 398~400 구현


@dataclass
class EqkInfo:
    """ eqk_handler에서 반환하는 dataclass입니다. """

    origin_lat: int
    origin_lon: int
    origin_x: None
    origin_y: None
    eqk_mag: int
    eqk_dep: int
    eqk_time: int
    eqk_id: int
    eqk_max_area: list
