import datetime
import time
from pprint import pprint
from typing import Any, List, Union
from urllib.parse import unquote

import requests

from errors import HTMLStatusException, SimNeedURLException
from models import EqkInfo, StaInfo
from stations import stations_name


def escape(text: str) -> str:
    """
    JavaScript escape() 함수의 파이썬 구현입니다.
    
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


class PyPEWS:
    """
    PyPEWS 클라이언트 클래스입니다.

    Attr:
        sim (bool): 시뮬레이션 여부
    """

    def __init__(self, sim: bool = False) -> None:
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
        self.sim = sim
        self.timeZone: int = 9
        self.tzMsec: int = self.timeZone * 3600000
        self.tide: float = 1.0
        self.max_eqk_info_len: int = 120
        self.stations_name: list = []
        self.max_eqk_str_len: int = 60
        self.DATA_PATH: str = "https://www.weather.go.kr/pews/data"
        if sim:
            self.header_len: int = 1
        else:
            self.header_len: int = 4

        self._update_tide()

    def lpad(self, text: str, length: int):
        """
        origin의 lpad 함수입니다. 


        Args:
            text (str): 목표 스트링
            length (int): 목표 길이

        Returns:
            str: 길이가 length가 될 때까지 앞에 0을 넣은 문자열
        """
        while len(text) < length:
            text = "0" + text
        return text

    def _update_tide(self) -> None:
        """
        현재 시간과 서버 시간을 대조하여 tide를 재설정합니다.
        """
        res = requests.get("https://www.weather.go.kr/pews/pews.html")
        server_time = float(res.headers["ST"])
        print(time.time() - (server_time - 1))
        self.tide = time.time() - (server_time - 1)

    def get_MMI(self, url: Union[str, None] = None) -> Any:
        """
        진도 정보를 불러옵니다.

        Args:
            url (Union[str, None]): 진도 정보를 불러올 시기의 url입니다.
                비어있다면 자동으로 url을 생성하여 요청합니다.

        Returns:
            Any: 몰라
        """
        if self.sim and url is None:
            raise SimNeedURLException("시뮬레이션에는 URL이 필요합니다.")

        if url is None:
            pTime = (
                datetime.datetime.utcnow()
                - datetime.timedelta(seconds=self.tide)
            ).strftime("%Y%m%d%H%M%S")
            url = f"{self.DATA_PATH}/{pTime}.b"
        sta_url = url.replace(".b", ".s")
        r = requests.get(url, timeout=1.0)

        if (status := r.status_code) != 200:
            raise HTMLStatusException(f"Status Code {status}")

        # TODO : refactor
        data = bytearray(r.content)
        bin_data = ["{:0b}".format(x) for x in data]
        bin_length = len(bin_data)

        header = ""
        binary_str = self.lpad(bin_data[0], 8)
        phase = None

        for i in range(self.header_len):
            header += self.lpad(bin_data[i], 8)

        for i in range(self.header_len, bin_length):
            binary_str += self.lpad(bin_data[i], 8)

        staF = header[0] == "1"
        if header[1] == "0":
            phase = 1
        elif header[1] == "1" and header[2] == "0":
            phase = 2
        elif header[2] == "1":
            phase = 3

        info_str_arr = []
        for i in range(bin_length - self.max_eqk_str_len, bin_length):
            info_str_arr.append(bin_data[i])

        mmi_arr = self.mmi_bin_handler(binary_str)[0]
        final_arr = self.get_sta(sta_url, binary_str, mmi_arr)
        return phase, final_arr, binary_str, info_str_arr

    def mmi_bin_handler(self, binary_str: str) -> List[List[int]]:
        """
        get_MMI에서 얻은 binary_str을 이용하여 진도 정보를 얻습니다.

        Args:
            binary_str (str): get_MMI() 에서 얻은 binary_str

        Returns:
            List[int]: 해당 idx의 지진계가 가지는 진도 값이 반환됩니다.
        """
        if len(binary_str) == 0:
            return []

        bin_arr = binary_str.split("11111111")
        mmi_arr = []
        sta_info = []

        for i in range(len(bin_arr)):
            mmi_obj = []
            for j in range(8, len(bin_arr[i]), 4):
                mmi_obj.append(int(bin_arr[i][j : j + 4], 2))
            mmi_arr.append(mmi_obj)

        # TODO : 이거 구현
        if self.sim:
            pass
        else:
            pass

        return mmi_arr

    def get_sta(self, url: str, data: str, mmi_arr: list) -> List[StaInfo]:
        """
        지진계 정보를 .s url에서 받아 가져옵니다.

        Args:
            url (str): 진도 정보를 불러올 시기의 url.
                비어있다면 자동으로 url을 생성하여 요청.
            data (str): get_MMI() 의 binary_str
            mmi_arr (list): mmi_bin_handler() 에서 얻은 진도 정보

        Returns:
            몰라요
        """
        if self.sim and url is None:
            raise SimNeedURLException("시뮬레이션에는 URL이 필요합니다.")

        if url is None:
            pTime = (
                datetime.datetime.utcnow()
                - datetime.timedelta(seconds=self.tide)
            ).strftime("%Y%m%d%H%M%S")
            url = f"{self.DATA_PATH}/{pTime}.s"
        r = requests.get(url, timeout=1.0)

        binary_str = ""
        dt = bytearray(r.content)
        bin_data = ["{:0b}".format(x) for x in dt]

        for i in range(len(bin_data)):
            binary_str += self.lpad(bin_data[i], 8)
        return self.sta_bin_handler(binary_str, mmi_arr)

    def sta_bin_handler(self, binary_str: str, mmi_arr: list) -> List[StaInfo]:
        """
        get_sta() 에서 얻은 binary_str로 지진계 부가 정보를 얻습니다.

        Args:
            binary_str (str): get_sta() 에서 얻은 binary_str
            mmi_arr (list): mmi_bin_handler() 에서 얻은 진도 정보
        Returns:
            Any: 몰라
        """
        sta_arr = []
        lat_arr = []
        lon_arr = []

        for i in range(0, len(binary_str), 20):
            lat_arr.append(30 + int(binary_str[i : i + 10], 2) / 100)
            lon_arr.append(120 + int(binary_str[i + 10 : i + 20], 2) / 100)

        for i in range(len(lat_arr)):
            sta_arr.append(
                StaInfo(
                    name=None if self.sim else stations_name[i],
                    lat=lat_arr[i],
                    lon=lon_arr[i],
                    idx=i,
                    mmi=mmi_arr[i],
                )
            )
        return sta_arr

    def eqk_handler(self, data: str, buffer: list) -> Any:
        """
        phase가 1이 아니면 호출되는 메소드입니다.

        Args:
            data (str): get_MMI() 의 binary_str
            buffer (list): get_MMI() 의 info_str_arr
        """
        data = data[0 - (self.max_eqk_str_len * 8 + self.max_eqk_info_len) :]
        origin_lat = 30 + (int(data[0:10], 2) / 100)
        origin_lon = 124 + (int(data[10:20], 2) / 100)
        origin_x = None
        origin_y = None  # TODO : 구현
        eqk_mag = int(data[20:27], 2) / 10
        eqk_dep = int(data[27:37], 2) / 10
        eqk_time = int(str(int(data[37:59], 2)) + "000")
        eqk_id = int("20" + str(int(data[69:95], 2)))
        eqk_max = int(data[95:99], 2)
        eqk_max_area_str = data[99:116]

        eqk_max_area = []
        if eqk_max_area != "11111111111111111":
            for i in range(17):
                if eqk_max_area_str[i] == "1":
                    eqk_max_area.append(self.regions[i])

        else:
            eqk_max_area.append("-")

        buffer = [int(x, 2) for x in buffer]
        buf_chr_str = "".join(map(chr, buffer))
        eqk_str = unquote(escape(buf_chr_str))

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
        )

    def get_grid(self, url: str):
        binary_str = ""
        r = requests.get(url, timeout=1)
        data = bytearray(r.content)
        bin_data = ["{:0b}".format(x) for x in data]
        
