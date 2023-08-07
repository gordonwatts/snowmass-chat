import time


def throttle(wait_time: float):
    """Generator that limits the number of times a method or function is called
    to once every `wait_time` seconds at maximum.

    Args:
        wait_time (int): Minimum seconds between calls
    """

    def decorator(func):
        last_called = 0

        def wrapper(*args, **kwargs):
            nonlocal last_called
            elapsed = time.time() - last_called
            if elapsed < wait_time:
                time.sleep(wait_time - elapsed)
            result = func(*args, **kwargs)
            last_called = time.time()
            return result

        return wrapper

    return decorator
