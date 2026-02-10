from dataclasses import dataclass
from typing import Any, Dict, Iterable, Tuple

import httpx

HOP_BY_HOP = {
    "connection",
    "keep-alive",
    "proxy-authenticate",
    "proxy-authorization",
    "te",
    "trailer",
    "transfer-encoding",
    "upgrade",
}

@dataclass(frozen=True)
class UpstreamResponse:
    status_code: int
    headers: Dict[str, str]
    body: bytes


class UpstreamConnectionError(Exception):
    pass


class UpstreamTimeoutError(Exception):
    pass


class ProxyClient:

    def __init__(self, connect_timeout: float, read_timeout: float):
        self._timeout = httpx.Timeout(connect=connect_timeout,read=read_timeout,write=read_timeout,pool=connect_timeout,)
        self._client = httpx.AsyncClient(timeout=self._timeout, follow_redirects=False)




    def _prepare_headers(self, ctx: Any, incoming: Dict[str, str]) -> Dict[str, str]:

        out: Dict[str, str] = {}


        for k, v in incoming.items():
            lk = k.lower()
            if lk in HOP_BY_HOP:
                continue
            if lk == "host":
                continue

            if lk == "content-length":
                continue
            out[k] = v

        out["X-Request-ID"] = ctx.request_id
        if getattr(ctx, "client_ip", ""):
            xff = out.get("X-Forwarded-For")
            out["X-Forwarded-For"] = f"{xff}, {ctx.client_ip}" if xff else ctx.client_ip

        return out

    def _sanitize_response_headers(self, upstream_headers: Iterable[Tuple[str, str]]) -> Dict[str, str]:
        out: Dict[str, str] = {}
        for k, v in upstream_headers:
            if k.lower() in HOP_BY_HOP:
                continue
            out[k] = v
        return out


    async def request(self,ctx: Any,method: str,url: str,headers: Dict[str, str],body: bytes,) -> UpstreamResponse:

        try:
            req_headers = self._prepare_headers(ctx, headers)
            response = await self._client.request(method=method,url=url,headers=req_headers,content=body)

            clean_headers = self._sanitize_response_headers(response.headers.items())
            return UpstreamResponse(status_code=response.status_code, headers=clean_headers, body=response.content)


        except httpx.TimeoutException as e:
            raise UpstreamTimeoutError(str(e)) from e
        except httpx.RequestError as e:
            raise UpstreamConnectionError(str(e)) from e


