import asyncio
from functools import wraps

def timeout(seconds):
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                return await asyncio.wait_for(func(*args, **kwargs), timeout=seconds)
            except asyncio.TimeoutError:
                raise asyncio.TimeoutError(f"Function {func.__name__} timed out after {seconds} seconds")
        return wrapper
    return decorator