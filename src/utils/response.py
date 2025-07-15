from typing import Any

from fastapi import status
from fastapi.responses import JSONResponse


class CustomResponse:

    @staticmethod
    def success(
        data: Any = None,
        message: str = "Successful",
        status_code: int = status.HTTP_200_OK,
    ):
        content = {"success": True, "message": message, "data": data}
        return JSONResponse(status_code=status_code, content=content)

    @staticmethod
    def error(
        data: Any = None,
        message: str = "Unsuccessful",
        status_code: int = status.HTTP_400_BAD_REQUEST,
    ):
        content = {"success": False, "message": message, "data": data}
        return JSONResponse(status_code=status_code, content=content)
