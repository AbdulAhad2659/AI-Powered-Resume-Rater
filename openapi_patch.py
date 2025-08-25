from fastapi.openapi.utils import get_openapi
from config import logger


def custom_openapi(app):
    if app.openapi_schema:
        return app.openapi_schema

    openapi_schema = get_openapi(
        title=app.title,
        version=app.version,
        routes=app.routes,
    )

    candidate_paths = ["/batch-rate", "/batch-rate/"]
    patched = False

    for p in candidate_paths:
        try:
            post_obj = openapi_schema["paths"].get(p, {}).get("post")
            if not post_obj:
                continue

            content = post_obj["requestBody"]["content"]
            if "multipart/form-data" not in content:
                continue

            body = content["multipart/form-data"]

            body_schema = {
                "type": "object",
                "properties": {
                    "job_description": {"title": "job_description", "type": "string"},
                    "include_audio": {"title": "include_audio", "type": "boolean"},
                    "resumes": {
                        "title": "resumes",
                        "type": "array",
                        "items": {"type": "string", "format": "binary"}
                    }
                },
                "required": ["job_description", "resumes"]
            }

            body["schema"] = body_schema
            body["encoding"] = {
                "resumes": {"contentType": "application/octet-stream", "style": "form", "explode": False},
                "job_description": {"contentType": "text/plain"},
                "include_audio": {"contentType": "text/plain"}
            }

            patched = True
            logger.info("Patched OpenAPI schema for path %s to use multi-file resumes array.", p)

        except Exception as e:
            logger.warning("Failed to patch OpenAPI for path %s: %s", p, e)

    if not patched:
        logger.warning("custom_openapi(): did not find /batch-rate in generated OpenAPI paths. Paths: %s",
                       list(openapi_schema.get("paths", {}).keys())[:50])

    app.openapi_schema = openapi_schema
    return app.openapi_schema
