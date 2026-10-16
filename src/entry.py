from urllib.parse import urlparse

from workers import Response, WorkerEntrypoint


class Default(WorkerEntrypoint):
    async def fetch(self, request):
        path = urlparse(request.url).path
        if request.method != "GET":
            return Response.json({"error": "Method not allowed"}, status=405,
                                 headers={"Allow": "GET"})
        if path == "/health":
            return Response.json({"status": "ok", "service": "persisch-trainer"})
        if path == "/health/db":
            result = await self.env.DB.prepare("SELECT COUNT(*) AS count FROM vocabulary").first()
            return Response.json({"status": "ok", "vocabulary_count": result.count})
        return Response.json({"error": "Not found"}, status=404)
