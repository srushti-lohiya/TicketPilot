"""Small deployment configuration validators; no network calls or service changes."""
from urllib.parse import urlsplit


def permitted_origins(value):
    origins = []
    for entry in value.split(','):
        origin = entry.strip()
        if not origin:
            continue
        parsed = urlsplit(origin)
        if (parsed.scheme not in {'http', 'https'} or not parsed.hostname or parsed.username
                or parsed.password or parsed.path or parsed.query or parsed.fragment or '*' in origin):
            raise ValueError('CORS_ORIGINS must contain exact http(s) origins without paths or wildcards')
        origins.append(origin)
    return list(dict.fromkeys(origins))


class DemoBodyLimit:
    """Bound public JSON buffering before FastAPI parses it; local mode is unchanged."""
    def __init__(self, app, enabled, max_bytes=32768):
        self.app, self.enabled, self.max_bytes = app, enabled, max_bytes

    async def __call__(self, scope, receive, send):
        if scope['type'] != 'http' or scope['method'] != 'POST' or not self.enabled():
            return await self.app(scope, receive, send)
        messages, size = [], 0
        while True:
            message = await receive()
            if message['type'] == 'http.disconnect':
                return
            size += len(message.get('body', b''))
            if size > self.max_bytes:
                from starlette.responses import JSONResponse
                return await JSONResponse({'detail': 'Public demo request exceeds 32 KiB'}, status_code=413)(scope, receive, send)
            messages.append(message)
            if not message.get('more_body', False):
                break
        pending = iter(messages)

        async def bounded_receive():
            return next(pending, None) or await receive()

        await self.app(scope, bounded_receive, send)
