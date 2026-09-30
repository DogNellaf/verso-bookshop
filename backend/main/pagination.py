from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response


class PageNumberWithTotalPagination(PageNumberPagination):
    """Standard page-number pagination that also reports ``total_pages``."""

    def get_paginated_response(self, data):
        return Response(
            {
                "count": self.page.paginator.count,
                "total_pages": self.page.paginator.num_pages,
                "next": self.get_next_link(),
                "previous": self.get_previous_link(),
                "results": data,
            }
        )

    def get_paginated_response_schema(self, schema):
        response = super().get_paginated_response_schema(schema)
        response["properties"]["total_pages"] = {"type": "integer", "example": 2}
        response["required"] = [*response.get("required", []), "total_pages"]
        return response
