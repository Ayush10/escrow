from __future__ import annotations

from unittest.mock import patch

from consumer_agent.flow import _runtime_contract_address


def test_runtime_contract_address_uses_legacy_address_by_default() -> None:
    with patch.dict(
        "os.environ",
        {
            "ESCROW_CONTRACT_ADDRESS": "0x" + "1" * 40,
        },
        clear=False,
    ):
        assert _runtime_contract_address() == "0x" + "1" * 40


def test_runtime_contract_address_uses_court_address_in_split_mode() -> None:
    with patch.dict(
        "os.environ",
        {
            "ESCROW_CONTRACT_MODE": "split",
            "ESCROW_CONTRACT_ADDRESS": "0x" + "1" * 40,
            "ESCROW_COURT_ADDRESS": "0x" + "2" * 40,
        },
        clear=False,
    ):
        assert _runtime_contract_address() == "0x" + "2" * 40
