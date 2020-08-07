import requests
import datetime


def get_MMI(url: str):
    r = requests.get(url, timeout=1.0)

    if r.status_code == 200:
        pass
    else:
        pass
