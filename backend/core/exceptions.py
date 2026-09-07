from rest_framework.views import exception_handler

def api_exception_handler(exc, context):
    response = exception_handler(exc, context)
    if response is not None:
        detail = response.data
        response.data = {"error": {"code": getattr(exc, "default_code", "request_error"), "message": detail}, "request_id": context["request"].headers.get("X-Request-ID")}
    return response

