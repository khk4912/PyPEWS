import requests
import datetime

timeZone = 9
tzMsec = timeZone * 3600000
tide = delay = 1000
DATA_PATH = "https://www.weather.go.kr/pews/data"


def get_MMI() -> bytes:
    pTime = datetime.datetime.now().strftime("%Y%m%H%M%S")
    r = requests.get(f"{DATA_PATH}/{pTime}.b", timeout=1.0)

    if (status := r.status_code) == 200:
        return r.content
    else:
        raise ZeroDivisionError(str(status))  # XXX : 임시

