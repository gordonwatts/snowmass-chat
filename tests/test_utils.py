import time
from chathelper.utils import throttle


def test_throttle():
    """Test the throttle decorator"""
    wait_time = 0.1

    @throttle(wait_time)
    def func():
        return time.time()

    begin = time.time()
    start = func()
    assert start is not None
    assert start < begin + wait_time

    time.sleep(wait_time)
    end = func()
    assert end is not None
    assert end > start + wait_time
