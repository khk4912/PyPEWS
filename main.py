import logging
import time
from datetime import datetime, timedelta
from pprint import pprint
from typing import Optional
from utils import Utils

import requests

from constant import DELAY, ENDPOINT, TIDE


class PyPEWS:
    def __init__(self) -> None:
        super().__init__()
        self.logger = logging.getLogger("PyPEWS")
        self.TIDE = self._update_tide()
        self.clock = datetime.utcnow() - timedelta(seconds=self.TIDE - DELAY)

    @property
    def pTime(self) -> str:
        """str: """
        date = datetime.utcnow() - timedelta(seconds=self.TIDE)
        return date.strftime("%Y%m%d%H%M%S")

    # tide 업데이트 구현하기
    # def _update_tide(self):
    #     r = requests.get(ENDPOINT)
    #     dTime = r.headers["ST"].replace(".", "")
    #     return datetime.utcnow() - datetime.utcfromtimestamp(dTime)

    def get_sta(self, url: Optional[str] = None, data=None):
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

    def get_MMI(self, url: Optional[str] = None):
        pass


client = PyPEWS()
while True:
    client.get_sta()
    time.sleep(1)
