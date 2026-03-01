from __future__ import annotations

import base64
import json
import os
import time
from decimal import Decimal, InvalidOperation
from typing import Any

import requests
from web3 import Web3

GOAT_MAINNET_RPC = "https://rpc.goat.network"
GOAT_TESTNET3_RPC = "https://rpc.testnet3.goat.network"
GOAT_DASHBOARD_URL = "https://goat-dashboard.vercel.app/"
GOAT_FAUCET_API = "https://bridge-api.testnet3.goat.network/api/faucet"
IDENTITY_MAINNET = "0x8004A169FB4a3325136EB29fA0ceB6D2e539a432"
IDENTITY_TESTNET3 = "0x556089008Fc0a60cD09390Eca93477ca254A5522"
REGISTRATION_TOPIC = "0xca52e62c367d81bb2e328eb795f7c7ba24afb478408a26c0e201d155c449bc4a"
USDC = "0x29d1ee93e9ecf6e50f309f498e40a6b42d352fa1"
USDT = "0xdce0af57e8f2ce957b3838cd2a2f3f3677965dd3"
DEFAULT_AGENT_NAME = "Ayush + Karan and Verdict Protocol"
DEFAULT_AGENT_DESCRIPTION = "Signature identity for Verdict Protocol agent payments"

ERC20_ABI = [
    {
        "inputs": [{"name": "account", "type": "address"}],
        "name": "balanceOf",
        "outputs": [{"name": "", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "inputs": [],
        "name": "decimals",
        "outputs": [{"name": "", "type": "uint8"}],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "inputs": [],
        "name": "symbol",
        "outputs": [{"name": "", "type": "string"}],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "inputs": [{"name": "to", "type": "address"}, {"name": "value", "type": "uint256"}],
        "name": "transfer",
        "outputs": [{"name": "", "type": "bool"}],
        "stateMutability": "nonpayable",
        "type": "function",
    },
]

IDENTITY_ABI = [
    {
        "inputs": [{"name": "metadataURI", "type": "string"}],
        "name": "register",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function",
    }
]


def _bool_env(name: str, default: bool = False) -> bool:
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _normalize_token(token_or_address: str) -> tuple[str, str]:
    value = token_or_address.strip().upper()
    if value == "USDC":
        return USDC, "USDC"
    if value == "USDT":
        return USDT, "USDT"
    return Web3.to_checksum_address(token_or_address), "CUSTOM"


def _fetch_registration_logs(rpc_url: str, contract_address: str) -> list[dict[str, Any]]:
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "eth_getLogs",
        "params": [
            {
                "address": contract_address,
                "fromBlock": "0x0",
                "toBlock": "latest",
                "topics": [REGISTRATION_TOPIC],
            }
        ],
    }
    response = requests.post(rpc_url, json=payload, timeout=30)
    response.raise_for_status()
    body = response.json()
    if "error" in body:
        raise RuntimeError(f"rpc error while loading agent logs: {body['error']}")
    return body.get("result", [])


def _load_agent_wallets() -> set[str]:
    all_logs: list[dict[str, Any]] = []
    all_logs.extend(_fetch_registration_logs(GOAT_MAINNET_RPC, IDENTITY_MAINNET))
    all_logs.extend(_fetch_registration_logs(GOAT_TESTNET3_RPC, IDENTITY_TESTNET3))
    wallets: set[str] = set()
    for log in all_logs:
        topics = log.get("topics", [])
        if len(topics) < 3:
            continue
        wallets.add(("0x" + topics[2][-40:]).lower())
    return wallets


def _pick_recipient(sender: str, agent_wallets: set[str], explicit: str | None) -> str:
    if explicit:
        return Web3.to_checksum_address(explicit)
    for address in sorted(agent_wallets):
        if address != sender.lower():
            return Web3.to_checksum_address(address)
    raise RuntimeError(
        "No candidate agent wallet found from ERC-8004 logs. "
        "Set DASHBOARD_AGENT_RECIPIENT explicitly."
    )


def _amount_to_base_units(amount: str, decimals: int) -> int:
    try:
        decimal_amount = Decimal(amount)
    except InvalidOperation as exc:
        raise RuntimeError(f"invalid DASHBOARD_PAYMENT_AMOUNT={amount}") from exc
    if decimal_amount <= 0:
        raise RuntimeError("DASHBOARD_PAYMENT_AMOUNT must be greater than zero")
    scale = Decimal(10) ** decimals
    return int((decimal_amount * scale).to_integral_value())


def _find_in_explorer_feed(explorer_url: str, token_address: str, tx_hash: str) -> bool:
    url = f"{explorer_url.rstrip('/')}/api/v2/token-transfers?token_address={token_address}"
    response = requests.get(url, timeout=20)
    response.raise_for_status()
    items = response.json().get("items", [])
    target = tx_hash.lower()
    return any(item.get("transaction_hash", "").lower() == target for item in items)


def _request_faucet(evm_address: str, turnstile_token: str) -> dict[str, Any]:
    response = requests.post(
        GOAT_FAUCET_API,
        json={"evm_address": evm_address, "token": turnstile_token},
        timeout=30,
    )
    response.raise_for_status()
    body = response.json()

    code = body.get("code", 0)
    if code not in (0, "0", None):
        raise RuntimeError(f"faucet request failed: {body.get('msg', 'unknown error')}")

    data = body.get("data") or {}
    return {
        "message": body.get("msg"),
        "amount": data.get("amount"),
        "txHash": data.get("txHash"),
        "raw": body,
    }


def _metadata_uri(name: str, description: str) -> str:
    payload = {
        "name": name,
        "description": description,
        "x402Support": True,
        "services": [{"name": "Verdict Protocol", "url": GOAT_DASHBOARD_URL}],
        "signature": DEFAULT_AGENT_NAME,
    }
    encoded = base64.b64encode(json.dumps(payload, separators=(",", ":")).encode()).decode()
    return f"data:application/json;base64,{encoded}"


def _send_contract_tx(
    w3: Web3,
    account,
    fn_call,
    chain_id: int,
    nonce: int,
    *,
    fallback_gas: int,
) -> tuple[str, int]:
    sender = Web3.to_checksum_address(account.address)
    gas_price = w3.eth.gas_price
    try:
        gas_limit = int(fn_call.estimate_gas({"from": sender}) * 1.2)
    except Exception:
        gas_limit = fallback_gas

    tx = fn_call.build_transaction(
        {
            "from": sender,
            "nonce": nonce,
            "chainId": chain_id,
            "gas": gas_limit,
            "gasPrice": gas_price,
        }
    )
    signed = account.sign_transaction(tx)
    tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction).hex()
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=180)
    if int(receipt.status) != 1:
        raise RuntimeError(f"transaction failed on-chain: tx={tx_hash}")
    return tx_hash, nonce + 1


def main() -> None:
    rpc_url = os.environ.get("GOAT_RPC_URL", GOAT_TESTNET3_RPC)
    chain_id = int(os.environ.get("GOAT_CHAIN_ID", "48816"))
    explorer_url = os.environ.get("GOAT_EXPLORER_URL", "https://explorer.testnet3.goat.network")

    private_key = os.environ.get("DASHBOARD_PAYMENT_PRIVATE_KEY") or os.environ.get(
        "CONSUMER_PRIVATE_KEY", ""
    )
    if not private_key:
        raise RuntimeError("Set DASHBOARD_PAYMENT_PRIVATE_KEY or CONSUMER_PRIVATE_KEY")

    token_address, token_hint = _normalize_token(os.environ.get("DASHBOARD_PAYMENT_TOKEN", "USDC"))
    amount_display = os.environ.get("DASHBOARD_PAYMENT_AMOUNT", "0.001")
    explicit_recipient = os.environ.get("DASHBOARD_AGENT_RECIPIENT")
    dry_run = _bool_env("DASHBOARD_PAYMENT_DRY_RUN", default=False)
    register_agent = _bool_env("DASHBOARD_REGISTER_AGENT", default=False)
    request_faucet = _bool_env("DASHBOARD_REQUEST_FAUCET", default=False)
    faucet_turnstile_token = os.environ.get("GOAT_FAUCET_TURNSTILE_TOKEN", "")
    wait_seconds = int(os.environ.get("DASHBOARD_PAYMENT_WAIT_SEC", "120"))
    poll_seconds = float(os.environ.get("DASHBOARD_PAYMENT_POLL_SEC", "3"))
    agent_name = os.environ.get("DASHBOARD_AGENT_NAME", DEFAULT_AGENT_NAME)
    agent_description = os.environ.get("DASHBOARD_AGENT_DESCRIPTION", DEFAULT_AGENT_DESCRIPTION)

    w3 = Web3(Web3.HTTPProvider(rpc_url))
    account = w3.eth.account.from_key(private_key)
    sender = Web3.to_checksum_address(account.address)
    token = w3.eth.contract(address=Web3.to_checksum_address(token_address), abi=ERC20_ABI)

    try:
        symbol = token.functions.symbol().call()
    except Exception:
        symbol = token_hint
    try:
        decimals = int(token.functions.decimals().call())
    except Exception:
        decimals = 6

    amount_base = _amount_to_base_units(amount_display, decimals)
    sender_native_balance = int(w3.eth.get_balance(sender))
    sender_token_balance = int(token.functions.balanceOf(sender).call())
    metadata_uri = _metadata_uri(agent_name, agent_description)
    faucet_result: dict[str, Any] | None = None

    agent_wallets = _load_agent_wallets()
    sender_is_agent = sender.lower() in agent_wallets
    recipient = _pick_recipient(sender, agent_wallets, explicit_recipient)
    recipient_is_agent = recipient.lower() in agent_wallets
    dashboard_eligible = sender_is_agent or recipient_is_agent

    if dry_run:
        result = {
            "mode": "dry-run",
            "dashboardUrl": GOAT_DASHBOARD_URL,
            "sender": sender,
            "recipient": recipient,
            "token": symbol,
            "tokenAddress": token_address,
            "amount": amount_display,
            "amountBaseUnits": str(amount_base),
            "senderBalances": {
                "nativeWei": str(sender_native_balance),
                "tokenBaseUnits": str(sender_token_balance),
            },
            "agentWalletsLoaded": len(agent_wallets),
            "senderIsAgent": sender_is_agent,
            "recipientIsAgent": recipient_is_agent,
            "dashboardEligible": dashboard_eligible,
            "registerAgentRequested": register_agent,
            "requestFaucet": request_faucet,
            "agentName": agent_name,
            "agentMetadataUriPreview": metadata_uri[:80] + "...",
            "nextAction": (
                "Unset DASHBOARD_PAYMENT_DRY_RUN and ensure payer has BTC gas "
                "+ token balance"
            ),
        }
        print(json.dumps(result, indent=2))
        return

    if request_faucet:
        if not faucet_turnstile_token:
            raise RuntimeError(
                "Set GOAT_FAUCET_TURNSTILE_TOKEN with a valid Turnstile "
                "token to request faucet funds"
            )
        faucet_result = _request_faucet(sender, faucet_turnstile_token)
        # Give the faucet tx a moment to confirm before balance checks.
        time.sleep(6)
        sender_native_balance = int(w3.eth.get_balance(sender))

    if sender_native_balance <= 0:
        raise RuntimeError("payer has 0 BTC for gas on GOAT testnet3; fund the sender first")
    if sender_token_balance < amount_base:
        raise RuntimeError(
            f"insufficient {symbol}: have {sender_token_balance}, need {amount_base}. "
            "GOAT faucet provides BTC gas only; fund sender with GOAT testnet USDC/USDT and retry."
        )

    registration_tx: str | None = None
    nonce = w3.eth.get_transaction_count(sender)

    if register_agent:
        identity = w3.eth.contract(
            address=Web3.to_checksum_address(IDENTITY_TESTNET3),
            abi=IDENTITY_ABI,
        )
        registration_tx, nonce = _send_contract_tx(
            w3,
            account,
            identity.functions.register(metadata_uri),
            chain_id,
            nonce,
            fallback_gas=350_000,
        )
        # Give indexers a short head start before we rely on refreshed wallet set.
        time.sleep(4)
        agent_wallets = _load_agent_wallets()

    sender_is_agent = sender.lower() in agent_wallets
    recipient_is_agent = recipient.lower() in agent_wallets
    dashboard_eligible = sender_is_agent or recipient_is_agent
    if not dashboard_eligible:
        raise RuntimeError(
            "Transfer will not show under Agent ↔ Agent Payments. "
            "Set DASHBOARD_REGISTER_AGENT=1 or use DASHBOARD_AGENT_RECIPIENT "
            "as a known agent wallet."
        )

    transfer_tx, _ = _send_contract_tx(
        w3,
        account,
        token.functions.transfer(recipient, amount_base),
        chain_id,
        nonce,
        fallback_gas=120_000,
    )

    visible_in_feed = False
    deadline = time.time() + wait_seconds
    while time.time() < deadline:
        try:
            if _find_in_explorer_feed(explorer_url, token_address, transfer_tx):
                visible_in_feed = True
                break
        except Exception:
            pass
        time.sleep(poll_seconds)

    result = {
        "mode": "live",
        "dashboardUrl": GOAT_DASHBOARD_URL,
        "headerLabel": agent_name,
        "token": symbol,
        "tokenAddress": token_address,
        "amount": amount_display,
        "amountBaseUnits": str(amount_base),
        "sender": sender,
        "recipient": recipient,
        "senderIsAgent": sender_is_agent,
        "recipientIsAgent": recipient_is_agent,
        "dashboardEligible": dashboard_eligible,
        "registrationTxHash": registration_tx,
        "registrationExplorerUrl": (
            f"{explorer_url.rstrip('/')}/tx/{registration_tx}" if registration_tx else None
        ),
        "faucetRequest": faucet_result,
        "txHash": transfer_tx,
        "txExplorerUrl": f"{explorer_url.rstrip('/')}/tx/{transfer_tx}",
        "visibleInDashboardFeed": visible_in_feed,
        "feedCheckWindowSec": wait_seconds,
    }
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
