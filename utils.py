class Utils:
    @staticmethod
    def lpad(text: str, length: int) -> str:
        while len(text) < length:
            text = "0" + text
        return text