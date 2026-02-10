import secrets
import string
from dataclasses import dataclass
from fastapi import HTTPException,Response
from typing import Any


@dataclass
class RequestContext:
    request_id: str
    start_ms: int
    client_ip: str
    method:str
    path:str
    query:str
    body:bytes
    headers:dict[str, str]

def generate_request_id(length: int = 18) -> str:

    if length <= 0:
        raise ValueError("length pozitif olmalı")
    digits = string.digits
    return ''.join(secrets.choice(digits) for _ in range(length))


class GatewayApp:

    def __init__(self, settings: Any, router: Any, proxy: Any, logger: Any):
        self.settings = settings
        self.router = router
        self.proxy = proxy
        self.logger = logger


    async def handle(self, request:Any):

        ctx = await self._build_context(request)

        try:
            await self._apply_guards( ctx)

            match = self._find_route(ctx)

            self.logger.request_in(ctx, request,match)

            upstream_resp = await self._forward(ctx, match)

            self.logger.request_out(ctx, upstream_resp.status_code, error=None)

            return self._to_response(upstream_resp)

        except Exception as err:
            self.logger.request_out(ctx,500, error=str(err))
            return self._error_response(500, ctx, "internal error", str(err))



    async def _build_context(self, request: Any) -> RequestContext:
        body = await request.body()
        return RequestContext(request_id=generate_request_id,start_ms=0, client_ip=request.client.host if request.client else "", method=request.method, path=request.url.path, query=request.url.query, body= body,headers = dict(request.headers))

    async def _apply_guards(self, ctx: RequestContext):

        if len(ctx.body) > self.settings.max_body_bytes:
            raise HTTPException(status_code=413,detail="request body is too large")

        if ctx.method not in ["GET", "POST", "PUT", "PATCH", "DELETE"]:
            raise HTTPException(status_code=405, detail="invalid method")

        return None

    def _find_route(self, ctx: RequestContext):

        match = self.router.resolve(ctx.method, ctx.path, ctx.query)

        if match is None:
            raise HTTPException(status_code=404, detail="match not found")

        return match

    async def _forward(self, ctx: RequestContext, match: Any):

        method = ctx.method
        headers = ctx.headers
        body = ctx.body
        upstream_url = match.upstream_url,


        response = await self.proxy.request(ctx, method, upstream_url,headers,body)

        return response


    def _to_response(self, upstream_resp: Any):

        return Response(status_code=upstream_resp.status_code, headers=upstream_resp.headers, content=upstream_resp.body)

    def _error_response(self, status_code, ctx:RequestContext, code:str, message:str):
        return {"request_id":ctx.request_id, "error": {"code":code, "message":message}}

