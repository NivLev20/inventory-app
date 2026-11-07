"""
OpenAPI (Swagger) description of the API.
Served as JSON at /api/openapi.json and as an interactive page at /api/docs.
"""

_JSON = "application/json"


def _body(schema_ref, required=True):
    return {
        "required": required,
        "content": {_JSON: {"schema": {"$ref": f"#/components/schemas/{schema_ref}"}}},
    }


def _ok(description, schema=None):
    response = {"description": description}
    if schema:
        response["content"] = {_JSON: {"schema": schema}}
    return response


_PRODUCT = {"$ref": "#/components/schemas/Product"}
_ERROR = {"description": "Error", "content": {_JSON: {"schema": {"$ref": "#/components/schemas/Error"}}}}
_ID = {"name": "product_id", "in": "path", "required": True, "schema": {"type": "integer"}}

SPEC = {
    "openapi": "3.0.3",
    "info": {
        "title": "Smart Retail Inventory API",
        "version": "1.0.0",
        "description": "Stock management for a multi-store retail chain.",
    },
    "tags": [
        {"name": "Products"}, {"name": "Stock movements"}, {"name": "Analytics"}, {"name": "Health"},
    ],
    "paths": {
        "/api/products": {
            "get": {
                "tags": ["Products"], "summary": "List products",
                "parameters": [
                    {"name": "store", "in": "query", "schema": {"type": "string"}, "example": "Haifa"},
                    {"name": "status", "in": "query", "schema": {"type": "string", "enum": ["OK", "LOW", "OUT"]}},
                ],
                "responses": {"200": _ok("Products", {"type": "array", "items": _PRODUCT})},
            },
            "post": {
                "tags": ["Products"], "summary": "Create a product",
                "requestBody": _body("ProductInput"),
                "responses": {"201": _ok("Created", _PRODUCT), "400": _ERROR, "409": _ERROR},
            },
        },
        "/api/products/{product_id}": {
            "parameters": [_ID],
            "get": {"tags": ["Products"], "summary": "Get a product",
                    "responses": {"200": _ok("Product", _PRODUCT), "404": _ERROR}},
            "put": {"tags": ["Products"], "summary": "Update a product or its stock",
                    "requestBody": _body("ProductInput"),
                    "responses": {"200": _ok("Updated", _PRODUCT), "400": _ERROR, "404": _ERROR}},
            "delete": {"tags": ["Products"], "summary": "Delete a product",
                       "responses": {"200": _ok("Deleted"), "404": _ERROR}},
        },
        "/api/products/{product_id}/restock": {
            "parameters": [_ID],
            "post": {"tags": ["Stock movements"], "summary": "Add stock",
                     "requestBody": _body("Restock"),
                     "responses": {"200": _ok("Updated product", _PRODUCT), "400": _ERROR, "404": _ERROR}},
        },
        "/api/products/{product_id}/sell": {
            "parameters": [_ID],
            "post": {"tags": ["Stock movements"], "summary": "Record a sale (decreases stock)",
                     "requestBody": _body("Sale"),
                     "responses": {"200": _ok("Updated product", _PRODUCT), "400": _ERROR,
                                   "404": _ERROR, "409": _ERROR}},
        },
        "/api/restocks": {
            "get": {"tags": ["Stock movements"], "summary": "Restock history",
                    "responses": {"200": _ok("Restock log entries")}},
        },
        "/api/products/low-stock": {
            "get": {"tags": ["Analytics"], "summary": "Products at or below their minimum",
                    "responses": {"200": _ok("Products", {"type": "array", "items": _PRODUCT})}},
        },
        "/api/products/analytics": {
            "get": {"tags": ["Analytics"], "summary": "Totals and daily trends",
                    "parameters": [{"name": "days", "in": "query", "schema": {"type": "integer", "default": 14}}],
                    "responses": {"200": _ok("Analytics")}},
        },
        "/health": {"get": {"tags": ["Health"], "summary": "Liveness probe",
                            "responses": {"200": _ok("Process is running")}}},
        "/ready": {"get": {"tags": ["Health"], "summary": "Readiness probe (checks the database)",
                           "responses": {"200": _ok("Ready"), "503": _ok("Database unreachable")}}},
    },
    "components": {
        "schemas": {
            "Product": {
                "type": "object",
                "properties": {
                    "id": {"type": "integer"}, "name": {"type": "string"}, "sku": {"type": "string"},
                    "category": {"type": "string"}, "store": {"type": "string"},
                    "price": {"type": "number"}, "stock": {"type": "integer"}, "min_stock": {"type": "integer"},
                    "status": {"type": "string", "enum": ["OK", "LOW", "OUT"]},
                    "suggested_reorder": {"type": "integer"}, "stock_value": {"type": "number"},
                },
            },
            "ProductInput": {
                "type": "object", "required": ["name", "sku"],
                "properties": {
                    "name": {"type": "string", "example": "Laptop Stand"},
                    "sku": {"type": "string", "example": "ELC-010"},
                    "category": {"type": "string", "example": "Electronics"},
                    "store": {"type": "string", "example": "Haifa"},
                    "price": {"type": "number", "example": 129},
                    "stock": {"type": "integer", "example": 4},
                    "min_stock": {"type": "integer", "example": 10},
                },
            },
            "Restock": {
                "type": "object", "required": ["quantity"],
                "properties": {"quantity": {"type": "integer", "example": 25},
                               "note": {"type": "string", "example": "supplier order"}},
            },
            "Sale": {
                "type": "object", "required": ["quantity"],
                "properties": {"quantity": {"type": "integer", "example": 2}},
            },
            "Error": {"type": "object", "properties": {"error": {"type": "string"}}},
        }
    },
}

# Swagger UI is loaded from a pinned CDN version; the page only reads /api/openapi.json.
DOCS_HTML = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>Smart Retail Inventory API</title>
  <link rel="stylesheet" href="https://unpkg.com/swagger-ui-dist@5.17.14/swagger-ui.css">
</head>
<body>
  <div id="swagger-ui"></div>
  <script src="https://unpkg.com/swagger-ui-dist@5.17.14/swagger-ui-bundle.js"></script>
  <script>
    window.ui = SwaggerUIBundle({ url: "/api/openapi.json", dom_id: "#swagger-ui" });
  </script>
</body>
</html>
"""
