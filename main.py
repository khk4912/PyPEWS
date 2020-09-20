import time
import datetime
from urllib.parse import unquote
from typing import List, Tuple, Union

import requests
from requests import Response

from stations import sta
from errors import HTMLStatusException
from models import EqkInfo, StaInfo


class PEWSClient:
    def __init__(self):
        self.regions: list = [
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
        self.timeZone: int = 9
        self.tzMsec: int = self.timeZone * 3600000
        self.tide: float = 1.0
        self.header_len: int = 4
        self.max_eqk_info_len: int = 120
        self.stations: list = sta
        self.need_sync = True
        self.max_eqk_str_len: int = 60
        self.DATA_PATH: str = "https://www.weather.go.kr/pews/data"

        self.update_tide()

    def lpad(self, text: str, length: int):
        while len(text) < length:
            text = "0" + text
        return text

    def escape(self, text: str) -> str:
        """
        https://bit.ly/2ZQiad8 escape() 함수의 파이썬 구현입니다.
        
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

    def get_MMI(self, url: Union[str, None] = None) -> bytes:
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
                datetime.datetime.utcnow()
                - datetime.timedelta(seconds=self.tide)
            ).strftime("%Y%m%d%H%M%S")
            url = f"{self.DATA_PATH}/{pTime}.b"

        r = requests.get(url, timeout=1.0)

        if (status := r.status_code) == 200:
            return r.content
        else:
            raise HTMLStatusException(str(status))

    def parse_MMI(self, content: bytes) -> Tuple[int, str, list]:
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
        binary_str = self.lpad(str(bin_data[0]), 8)

        for i in range(0, self.header_len):
            header += self.lpad(bin_data[i], 8)

        for i in range(self.header_len, byte_length):
            binary_str += self.lpad(bin_data[i], 8)

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
        for i in range(byte_length - self.max_eqk_str_len, byte_length):
            info_str_arr.append(bin_data[i])

        # TODO : get_sta 구현 후 재시작 필요 (Line 289~)

        return phase, binary_str, info_str_arr
        # ====================================

    def eqk_handler(self, data: str, buffer: list) -> EqkInfo:
        """
        phase가 1 이상인 경우 호출하여 지진의 정보를 반환합니다.

        Args:
            data (str): parse_MMI 에서 반환하는 binary_str
            buffer (list): parse_MMI에서 반환하는 info_str_arr
        
        Returns:
            Eqkinfo: 지진 정보를 나타내는 EqkInfo dataclass를 반환합니다.
        """
        data = data[0 - ((self.max_eqk_str_len * 8 + self.max_eqk_info_len)) :]
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
        buf_chr_str = "".join(map(chr, buffer))
        eqk_str = unquote(self.escape(buf_chr_str))

        if eqk_max_area_str != "11111111111111111":
            for i in range(17):
                if eqk_max_area_str[i] == "1":
                    eqk_max_area.append(self.regions[i])
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

    def update_tide(self, res: Union[Response, None] = None) -> None:
        if res is None:
            res = requests.get(
                "https://www.weather.go.kr/pews/pews.html"
            )  # Dummy
        server_time = float(res.headers["ST"])
        print(time.time() - (server_time - 1))
        self.tide = time.time() - (server_time - 1)

    def callback(self, data: list):
        mmi_object = self.mmi_bin_handler()

    def mmi_bin_handler(self):
        pass

    def get_sta(self, url: Union[str, None] = None) -> bytes:
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
                datetime.datetime.utcnow()
                - datetime.timedelta(seconds=self.tide)
            ).strftime("%Y%m%d%H%M%S")
            url = f"{self.DATA_PATH}/{pTime}.s"

        r = requests.get(url, timeout=1.0)

        if (status := r.status_code) == 200:
            return r.content
        else:
            raise HTMLStatusException(str(status))

    def parse_sta(self, content: bytes) -> str:
        data = bytearray(content)
        bin_data = ["{:0b}".format(x) for x in data]
        binary_str = ""

        for i in bin_data:
            binary_str += self.lpad(i, 8)

        return binary_str

    def get_sta_info(self, data: str) -> List[StaInfo]:
        new_sta = []
        sta_lat = []
        sta_lon = []

        for i in range(0, len(data), 20):
            sta_lat.append(30 + int(data[i : i + 10], 2) / 100)
            sta_lon.append(120 + int(data[i + 10 : i + 20], 2) / 100)

        for i in range(len(sta_lat)):
            new_sta.append(
                StaInfo(self.stations[i], sta_lat[i], sta_lon[i], i)
            )

        return new_sta
