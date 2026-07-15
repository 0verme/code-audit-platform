from flask import jsonify

from app.services import ServiceError


def service_error_response(error: ServiceError):
    return jsonify(error.payload), error.status_code
