import logging
import time
from datetime import datetime, timedelta
from pprint import pprint
from typing import List, Optional

import requests

from constant import DELAY, ENDPOINT, HEADER_LEN, MAX_EQK_STR_LEN
from model import StaInfo
from utils import Utils


class PyPEWS:
    def __init__(self) -> None:
        super().__init__()
        self.clock = datetime.utcnow() - timedelta(seconds=self.TIDE - DELAY)
        self.logger = logging.getLogger("PyPEWS")
        self.phase = 1
        self.sta_list: List[StaInfo] = []
        self.TIDE = self._update_tide()

    @property
    def pTime(self) -> str:
        """str: YYYYMMDDHHMMSS"""
        date = datetime.utcnow() - timedelta(seconds=self.TIDE)
        return date.strftime("%Y%m%d%H%M%S")

    def _update_tide(self) -> float:
        r = requests.get("https://www.weather.go.kr/pews/pews.html")
        dTime = int(r.headers["ST"].replace(".", ""))

        return (
            datetime.utcnow() - datetime.utcfromtimestamp(dTime / 1000)
        ).total_seconds()

    def get_sta(
        self, url: Optional[str] = None, binary_str: Optional[str] = None
    ):
        print(self.pTime)
        if url is None:
            url = f"{ENDPOINT}/{self.pTime}.s"
        binary_str = ""
        r = requests.get(url)
        if r.status_code != 200:
            self.logger.info(f"HTTP Status {r.status_code}")

        sta_array = ["{:0b}".format(x) for x in bytearray(r.content)]
        for i in sta_array:
            binary_str += Utils.lpad(i, 8)

        self.sta_bin_handler(binary_str)
        if binary_str is not None:
            self.callback(binary_str)

    def get_MMI(self, url: Optional[str] = None):
        if url is None:
            url = f"{ENDPOINT}/{self.pTime}.b"
        r = requests.get(url)
        sta_array = ["{:0b}".format(x) for x in bytearray(r.content)]

        header = ""
        binary_str = ""
        for i in range(HEADER_LEN):
            header += Utils.lpad(sta_array[i], 8)
        for j in range(HEADER_LEN, len(sta_array)):
            binary_str += Utils.lpad(sta_array[j], 8)

        staF = header[0] == "1"
        self.phase = int(header[1])

        info_str_arr = []
        for i in range(len(sta_array) - MAX_EQK_STR_LEN, len(sta_array)):
            info_str_arr.append(sta_array[i])

        if staF or len(self.sta_list) < 99:
            self.get_sta(binary_str=binary_str)

    def sta_bin_handler(self, binary_data: str):
        new_sta_list = []
        sta_lat_arr = []
        sta_lon_arr = []

        for i in range(0, len(binary_data), 20):
            sta_lat_arr.append(30 + int(binary_data[i : i + 10], 2) / 100)
            sta_lon_arr.append(120 + int(binary_data[i + 10 : i + 20], 2) / 100)

        for i in range(len(sta_lat_arr)):
            new_sta_list.append(
                StaInfo(lat=sta_lat_arr[i], lon=sta_lon_arr[i], idx=i)
            )

        if len(new_sta_list) > 99:
            self.sta_list = new_sta_list

    def callback(self, binary_str: str):
        mmi_data = self.mmi_bin_handler(binary_str)
        for i in range(len(self.sta_list)):
            self.sta_list[i].mmi = mmi_data[self.sta_list[i].idx]

    def mmi_bin_handler(self, binary_str: str) -> List[int]:
        mmi_data = []
        if binary_str and len(binary_str) > 0:
            for i in range(0, len(binary_str), 4):
                mmi_data.append(int(binary_str[i : i + 4], 2))
        return mmi_data


client = PyPEWS()
while True:
    client.get_sta()
    time.sleep(1)
