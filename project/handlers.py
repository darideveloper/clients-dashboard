from rest_framework.views import exception_handler


def custom_exception_handler(exc, context):
    response = exception_handler(exc, context)

    if response is not None:
        original_data = response.data
        response.data = {}
        response.data["status"] = "error"
        details = original_data.get("detail", None)
        if details:
            del original_data["detail"]
            response.data["message"] = str(details)
        else:
            response.data["message"] = "Invalid data"
        response.data["data"] = original_data

    return response
