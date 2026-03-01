from __future__ import annotations

import os
from typing import Any

from x402.http import FacilitatorConfig, HTTPFacilitatorClient, PaymentOption, RouteConfig
from x402.http.middleware.fastapi import payment_middleware
from x402.mechanisms.evm.exact.register import register_exact_evm_server
from x402.server import x402ResourceServer


class X402IntegrationError(RuntimeError):
    pass


def install_x402(app: Any) -> str:
    """Install x402 payment middleware for FastAPI."""
    facilitator_url = os.environ.get("X402_FACILITATOR_URL", "https://www.x402.org/facilitator")
    network = os.environ.get("X402_NETWORK", "eip155:84532")
    seller = os.environ.get("X402_SELLER_WALLET", "")

    if not seller and os.environ.get("X402_ALLOW_MOCK", "0") != "1":
        raise X402IntegrationError("X402_SELLER_WALLET is required when mock mode is disabled")

    # Dev fallback can be enabled explicitly; production should not rely on this.
    if os.environ.get("X402_ALLOW_MOCK", "0") == "1":

        @app.middleware("http")
        async def mock_gate(request, call_next):
            if request.url.path.startswith("/api/") and "x-mock-x402" not in request.headers:
                from fastapi.responses import JSONResponse

                return JSONResponse(
                    status_code=402,
                    content={
                        "error": "x402 payment required",
                        "hint": "Set x-mock-x402 header for local mock mode",
                    },
                )
            return await call_next(request)

        return "mock"

    facilitator = HTTPFacilitatorClient(FacilitatorConfig(url=facilitator_url))
    server = x402ResourceServer(facilitator)
    register_exact_evm_server(server, networks=network)

    routes = {
        "GET /api/data": RouteConfig(
            accepts=[
                PaymentOption(
                    scheme="exact",
                    price="$0.001",
                    network=network,
                    pay_to=seller,
                )
            ],
            description="Protected API endpoint",
            mime_type="application/json",
        )
    }
    middleware = payment_middleware(routes, server)
    app.middleware("http")(middleware)
    return "sdk:fastapi"
