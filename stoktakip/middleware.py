"""
Request flags used by templates (e.g. base.html for tab iframe embed mode).
"""


class NuviaTabEmbedMiddleware:
    """Mark requests that render inside the app's tab iframe (no duplicate chrome)."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        dest = (request.headers.get("Sec-Fetch-Dest") or "").lower()
        request.nuvia_tab_embed = dest == "iframe" or request.GET.get("nuvia_embed") == "1"
        return self.get_response(request)
