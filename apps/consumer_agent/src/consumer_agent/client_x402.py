from __future__ import annotations

import hashlib
import os
from dataclasses import dataclass

import httpx
import requests
from eth_account import Account
from x402.client import x402ClientSync
from x402.http.clients.requests import wrapRequestsWithPayment
from x402.mechanisms.evm.exact.register import register_exact_evm_client
from x402.mechanisms.evm.signers import EthAccountSigner


@dataclass(slots=True)
class X402Response:
    status_code: int
    payload: dict
    headers: dict[str, str]
    payment_reference: str


class X402Client:
    def __init__(self, consumer_private_key: str) -> None:
        self.consumer_private_key = consumer_private_key
        self.network = os.environ.get("X402_NETWORK", "eip155:84532")
        self._session = self._build_sdk_session()

    def _build_sdk_session(self) -> requests.Session | None:
        try:
            account = Account.from_key(self.consumer_private_key)
            signer = EthAccountSigner(account)

            xclient = x402ClientSync()
            register_exact_evm_client(xclient, signer, networks=self.network)

            return wrapRequestsWithPayment(requests.Session(), xclient)
        except Exception:
            return None

    def get(self, url: str) -> X402Response:
        if self._session is not None:
            try:
                resp = self._session.get(url, timeout=60)
                data = resp.json() if resp.content else {}
                headers = {k.lower(): v for k, v in resp.headers.items()}
            except Exception:
                mock = os.environ.get("X402_ALLOW_MOCK", "0") == "1"
                if not mock:
                    raise
                with httpx.Client(timeout=60) as client:
                    resp = client.get(url, headers={"x-mock-x402": "1"})
                data = resp.json()
                headers = {k.lower(): v for k, v in resp.headers.items()}
        else:
            headers = {}
            mock = os.environ.get("X402_ALLOW_MOCK", "0") == "1"
            if not mock:
                raise RuntimeError(
                    "x402 client initialization failed; set X402_ALLOW_MOCK=1 for local mock mode"
                )
            req_headers = {"x-mock-x402": "1"} if mock else {}
            with httpx.Client(timeout=60) as client:
                resp = client.get(url, headers=req_headers)
            data = resp.json()
            headers = {k.lower(): v for k, v in resp.headers.items()}

        payment_ref = headers.get("x402-payment-reference") or headers.get("x-payment-reference")
        if not payment_ref:
            digest_input = f"{url}:{self.consumer_private_key[:10]}:{data}".encode()
            payment_ref = "fallback-" + hashlib.sha256(digest_input).hexdigest()

        return X402Response(
            status_code=resp.status_code,
            payload=data,
            headers=headers,
            payment_reference=payment_ref,
        )
