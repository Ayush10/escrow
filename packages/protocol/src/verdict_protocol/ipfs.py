from __future__ import annotations

import base64
import hashlib
import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import httpx


def _canonical_json_bytes(payload: dict[str, Any]) -> bytes:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")


def _mock_cid(payload_bytes: bytes) -> str:
    digest = hashlib.sha256(payload_bytes).digest()
    encoded = base64.b32encode(digest).decode("ascii").lower().rstrip("=")
    return "bafy" + encoded[:55]


@dataclass(slots=True)
class StoredBundle:
    cid: str
    uri: str
    bundle_hash: str
    mode: str
    gateway_url: str | None = None


class EvidenceBundleStore:
    def __init__(
        self,
        *,
        mode: str | None = None,
        pinata_jwt: str | None = None,
        gateway_base_url: str | None = None,
        local_store_path: str | None = None,
    ) -> None:
        configured_mode = (mode or os.environ.get("IPFS_MODE", "auto")).strip().lower()
        jwt = pinata_jwt or os.environ.get("IPFS_PINATA_JWT") or os.environ.get("PINATA_JWT")
        if configured_mode == "auto":
            configured_mode = "pinata" if jwt else "local"

        self.mode = configured_mode
        self.pinata_jwt = jwt
        self.gateway_base_url = (
            gateway_base_url
            or os.environ.get("IPFS_GATEWAY_BASE_URL")
            or "https://gateway.pinata.cloud/ipfs"
        ).rstrip("/")
        self.local_store_path = Path(
            local_store_path or os.environ.get("IPFS_LOCAL_STORE_PATH", "./data/ipfs")
        )
        self.local_store_path.mkdir(parents=True, exist_ok=True)

        if self.mode == "pinata" and not self.pinata_jwt:
            raise RuntimeError("IPFS pinata mode requires IPFS_PINATA_JWT or PINATA_JWT")

    def pin_json(self, name: str, payload: dict[str, Any]) -> StoredBundle:
        payload_bytes = _canonical_json_bytes(payload)
        bundle_hash = "0x" + hashlib.sha256(payload_bytes).hexdigest()

        if self.mode == "pinata":
            with httpx.Client(timeout=60) as client:
                resp = client.post(
                    "https://api.pinata.cloud/pinning/pinJSONToIPFS",
                    headers={"Authorization": f"Bearer {self.pinata_jwt}"},
                    json={
                        "pinataOptions": {"cidVersion": 1},
                        "pinataMetadata": {"name": name},
                        "pinataContent": payload,
                    },
                )
                resp.raise_for_status()
                body = resp.json()
            cid = str(body["IpfsHash"])
            return StoredBundle(
                cid=cid,
                uri=f"ipfs://{cid}",
                bundle_hash=bundle_hash,
                mode="pinata",
                gateway_url=f"{self.gateway_base_url}/{cid}",
            )

        cid = _mock_cid(payload_bytes)
        path = self.local_store_path / f"{cid}.json"
        path.write_bytes(payload_bytes)
        return StoredBundle(
            cid=cid,
            uri=f"ipfs://{cid}",
            bundle_hash=bundle_hash,
            mode="local",
            gateway_url=str(path),
        )

    def load_json(self, cid_or_uri: str) -> dict[str, Any]:
        cid = cid_or_uri.removeprefix("ipfs://")
        local_path = self.local_store_path / f"{cid}.json"
        if local_path.exists():
            return json.loads(local_path.read_text(encoding="utf-8"))

        with httpx.Client(timeout=60) as client:
            resp = client.get(f"{self.gateway_base_url}/{cid}")
            resp.raise_for_status()
            return resp.json()
