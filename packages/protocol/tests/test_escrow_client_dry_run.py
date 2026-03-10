import os
import tempfile
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from verdict_protocol import EscrowClient, EscrowTxResult


def test_escrow_client_dry_run_lifecycle() -> None:
    with tempfile.TemporaryDirectory() as td:
        os.environ["ESCROW_MOCK_DB_PATH"] = f"{td}/escrow_mock.db"

        client = EscrowClient(
            rpc_url="https://rpc.testnet3.goat.network",
            chain_id=48816,
            contract_address="0x" + "1" * 40,
            private_key="0x" + "1" * 64,
            dry_run=True,
        )

        root_hash = "0x" + "a" * 64
        commit = client.commit_evidence_hash("agreement-1", root_hash)
        assert commit.status == 1

        dispute = client.file_dispute(
            "agreement-1",
            tx_id=42,
            defendant="0x" + "2" * 40,
            stake=100,
            plaintiff_evidence=root_hash,
        )
        assert dispute.status == 1
        dispute_id = int(dispute.extra["disputeId"])

        loaded = client.get_dispute(dispute_id)
        assert loaded is not None
        assert loaded[0] == 42
        assert loaded[8] is False

        ruling = client.submit_ruling(
            dispute_id,
            {
                "winner": "0x" + "1" * 40,
                "transfers": [
                    {
                        "to": "0x" + "1" * 40,
                        "amount": "200",
                        "reason": "dispute_resolution",
                    }
                ],
            },
        )
        assert ruling.status == 1

        updated = client.get_dispute(dispute_id)
        assert updated is not None
        assert updated[8] is True
        assert updated[9].lower() == ("0x" + "1" * 40)

        dispute_events = client.poll_events("DisputeFiled", from_block=0)
        ruling_events = client.poll_events("RulingSubmitted", from_block=0)
        evidence_events = client.poll_events("EvidenceCommitted", from_block=0)

        assert dispute_events
        assert ruling_events
        assert evidence_events


def test_escrow_client_dry_run_is_idempotent_for_anchor_and_dispute() -> None:
    with tempfile.TemporaryDirectory() as td:
        os.environ["ESCROW_MOCK_DB_PATH"] = f"{td}/escrow_mock.db"

        client = EscrowClient(
            rpc_url="https://rpc.testnet3.goat.network",
            chain_id=48816,
            contract_address="0x" + "1" * 40,
            private_key="0x" + "1" * 64,
            dry_run=True,
        )

        root_hash = "0x" + "a" * 64
        first_commit = client.commit_evidence_hash("agreement-1", root_hash)
        second_commit = client.commit_evidence_hash("agreement-1", root_hash)
        assert second_commit.extra == {"idempotent": True}
        assert second_commit.tx_hash == first_commit.tx_hash
        assert second_commit.block_number == first_commit.block_number

        with pytest.raises(ValueError, match="different root_hash"):
            client.commit_evidence_hash("agreement-1", "0x" + "b" * 64)

        first_dispute = client.file_dispute(
            "agreement-1",
            tx_id=42,
            defendant="0x" + "2" * 40,
            stake=100,
            plaintiff_evidence=root_hash,
        )
        second_dispute = client.file_dispute(
            "agreement-1",
            tx_id=42,
            defendant="0x" + "2" * 40,
            stake=100,
            plaintiff_evidence=root_hash,
        )
        assert second_dispute.extra == {
            "disputeId": int(first_dispute.extra["disputeId"]),
            "idempotent": True,
        }
        assert second_dispute.tx_hash == first_dispute.tx_hash
        assert second_dispute.block_number == first_dispute.block_number

        dispute_events = client.poll_events("DisputeFiled", from_block=0)
        evidence_events = client.poll_events("EvidenceCommitted", from_block=0)
        assert len(dispute_events) == 1
        assert len(evidence_events) == 1


class _FakeCall:
    def __init__(self, value):
        self._value = value

    def call(self):
        return self._value


class _FakeEventFilter:
    def __init__(self, entries):
        self._entries = entries

    def get_all_entries(self):
        return list(self._entries)


class _FakeEvent:
    def __init__(self, entries):
        self._entries = entries

    def create_filter(self, from_block=0, to_block="latest"):
        return _FakeEventFilter(self._entries)


class _FakeCourtFunctions:
    def __init__(self, *, plaintiff: str, defendant: str, judge: str, winner: str):
        self._plaintiff = plaintiff
        self._defendant = defendant
        self._judge = judge
        self._winner = winner

    def contracts(self, dispute_id: int):
        return _FakeCall(
            (
                self._defendant,  # principal
                self._plaintiff,  # client
                self._judge,
                100,
                15,
                bytes.fromhex("11" * 32),
                self._plaintiff,
                123456,
                self._winner,
                4,
                115,
                115,
                123999,
                124000,
                0,
            )
        )

    def disputes(self, dispute_id: int):
        return _FakeCall(
            (
                self._plaintiff,
                self._defendant,
                self._judge,
                self._defendant,
                123500,
                123700,
                bytes.fromhex("22" * 32),
            )
        )

    def evidenceCount(self, dispute_id: int):
        return _FakeCall(2)

    def evidenceSubmitters(self, dispute_id: int, idx: int):
        return _FakeCall(self._plaintiff if idx == 0 else self._defendant)

    def evidenceHashes(self, dispute_id: int, idx: int):
        return _FakeCall(bytes.fromhex(("aa" if idx == 0 else "bb") * 32))


class _FakeCourtEvents:
    def __init__(self, *, plaintiff: str, winner: str):
        self.DisputeFiled = _FakeEvent(
            [{"args": {"id": 7, "plaintiff": plaintiff}, "blockNumber": 12, "transactionHash": "0xabc"}]
        )
        self.Ruled = _FakeEvent(
            [{"args": {"id": 7, "winner": winner, "judge": "0x" + "4" * 40}, "blockNumber": 15, "transactionHash": "0xdef"}]
        )


class _FakeCourtContract:
    def __init__(self, *, plaintiff: str, defendant: str, judge: str, winner: str):
        self.functions = _FakeCourtFunctions(
            plaintiff=plaintiff,
            defendant=defendant,
            judge=judge,
            winner=winner,
        )
        self.events = _FakeCourtEvents(plaintiff=plaintiff, winner=winner)


class _FakeRegistryFunctions:
    def __init__(self, judge: str):
        self._judge = judge

    def judges(self, judge: str):
        return _FakeCall(("0x" + "0" * 40, 5, 50, 3, True, True, "https://judge.example", 300))


class _FakeRegistryContract:
    def __init__(self, judge: str):
        self.functions = _FakeRegistryFunctions(judge)


class _FakeEvidenceAnchorEvents:
    def __init__(self):
        self.EvidenceCommitted = _FakeEvent(
            [
                {
                    "args": {
                        "agreementId": "agreement-7",
                        "rootHash": bytes.fromhex("cc" * 32),
                        "bundleHash": bytes.fromhex("dd" * 32),
                        "bundleCid": "ipfs://bafy-test",
                        "submitter": "0x" + "5" * 40,
                    },
                    "blockNumber": 22,
                    "transactionHash": "0xghi",
                }
            ]
        )


class _FakeEvidenceAnchorContract:
    def __init__(self):
        self.events = _FakeEvidenceAnchorEvents()


class _FakeERC20Functions:
    def __init__(self, allowance: int):
        self._allowance = allowance

    def allowance(self, owner: str, spender: str):
        return _FakeCall(self._allowance)

    def approve(self, spender: str, amount: int):
        return ("approve", spender, amount)


class _FakeVaultTxFunctions:
    def deposit(self, amount: int):
        return ("deposit", amount)

    def moveToBond(self, amount: int):
        return ("moveToBond", amount)


class _FakeRegistryTxFunctions:
    def registerJudge(self, superior: str, fee: int, endpoint: str, max_response_time: int):
        return ("registerJudge", superior, fee, endpoint, max_response_time)


def test_escrow_client_split_mode_reports_capabilities_and_synthesizes_disputes() -> None:
    with tempfile.TemporaryDirectory() as td:
        env = {
            "ESCROW_MOCK_DB_PATH": f"{td}/escrow_mock.db",
            "ESCROW_CONTRACT_MODE": "split",
            "ESCROW_COURT_ADDRESS": "0x" + "1" * 40,
            "ESCROW_VAULT_ADDRESS": "0x" + "2" * 40,
            "ESCROW_JUDGE_REGISTRY_ADDRESS": "0x" + "3" * 40,
        }
        with patch.dict(os.environ, env, clear=False):
            client = EscrowClient(
                rpc_url="https://rpc.testnet3.goat.network",
                chain_id=48816,
                contract_address="0x" + "1" * 40,
                private_key="0x" + "1" * 64,
                dry_run=True,
            )

            caps = client.capabilities()
            sanity = client.contract_sanity()

            assert caps["splitContractSet"] is True
            assert caps["commitEvidenceHash"] is False
            assert sanity["deploymentMode"] == "split"
            assert sanity["courtAddress"] == "0x" + "1" * 40
            assert sanity["vaultAddress"] == "0x" + "2" * 40
            assert sanity["judgeRegistryAddress"] == "0x" + "3" * 40


def test_escrow_client_split_mode_mock_contract_lifecycle_uses_court_id() -> None:
    provider_key = "0x" + "1" * 64
    consumer_key = "0x" + "2" * 64
    judge = "0x" + "4" * 40

    with tempfile.TemporaryDirectory() as td:
        env = {
            "ESCROW_MOCK_DB_PATH": f"{td}/escrow_mock.db",
            "ESCROW_CONTRACT_MODE": "split",
            "ESCROW_COURT_ADDRESS": "0x" + "1" * 40,
            "ESCROW_VAULT_ADDRESS": "0x" + "2" * 40,
            "ESCROW_JUDGE_REGISTRY_ADDRESS": "0x" + "3" * 40,
        }
        with patch.dict(os.environ, env, clear=False):
            provider_client = EscrowClient(
                rpc_url="https://rpc.testnet3.goat.network",
                chain_id=48816,
                contract_address="0x" + "1" * 40,
                private_key=provider_key,
                dry_run=True,
            )
            consumer_client = EscrowClient(
                rpc_url="https://rpc.testnet3.goat.network",
                chain_id=48816,
                contract_address="0x" + "1" * 40,
                private_key=consumer_key,
                dry_run=True,
            )
            provider = provider_client.account.address
            consumer = consumer_client.account.address

            created = provider_client.create_agreement(
                "agreement-split-1",
                principal=provider,
                client=consumer,
                judge=judge,
                consideration=100,
                terms_hash="0x" + "a" * 64,
            )
            assert created.extra == {"contractId": 0}

            accepted = consumer_client.accept_agreement(0)
            assert accepted.extra == {"contractId": 0}

            dispute = consumer_client.file_dispute(
                "agreement-split-1",
                tx_id=0,
                defendant=provider,
                stake=100,
                plaintiff_evidence="0x" + "b" * 64,
            )
            assert dispute.extra == {"disputeId": 0}

            fetched = consumer_client.get_dispute(0)
            assert fetched is not None
            assert fetched[0] == 0
            assert fetched[1] == consumer
            assert fetched[2] == provider


def test_escrow_client_split_mode_synthesizes_events_and_disputes() -> None:
    plaintiff = "0x" + "1" * 40
    defendant = "0x" + "2" * 40
    judge = "0x" + "4" * 40
    winner = plaintiff

    env = {
        "ESCROW_CONTRACT_MODE": "split",
        "ESCROW_COURT_ADDRESS": "0x" + "1" * 40,
        "ESCROW_VAULT_ADDRESS": "0x" + "2" * 40,
        "ESCROW_JUDGE_REGISTRY_ADDRESS": "0x" + "3" * 40,
    }
    with patch.dict(os.environ, env, clear=False):
        client = EscrowClient(
            rpc_url="https://rpc.testnet3.goat.network",
            chain_id=48816,
            contract_address="0x" + "1" * 40,
            private_key=None,
            dry_run=True,
        )

    client.dry_run = False
    client.contract = _FakeCourtContract(
        plaintiff=plaintiff,
        defendant=defendant,
        judge=judge,
        winner=winner,
    )
    client.registry_contract = _FakeRegistryContract(judge)
    client.evidence_anchor_contract = _FakeEvidenceAnchorContract()

    dispute = client.get_dispute(7)
    assert dispute is not None
    assert dispute[0] == 7
    assert dispute[1] == plaintiff
    assert dispute[2] == defendant
    assert dispute[4] == 5
    assert dispute[5] == 0
    assert dispute[6] == "0x" + "aa" * 32
    assert dispute[7] == "0x" + "bb" * 32
    assert dispute[8] is True
    assert dispute[9] == plaintiff
    assert client.assigned_judge(7) == judge

    dispute_events = client.poll_events("DisputeFiled", from_block=0)
    ruling_events = client.poll_events("RulingSubmitted", from_block=0)
    evidence_events = client.poll_events("EvidenceCommitted", from_block=0)

    assert dispute_events[0]["args"]["disputeId"] == 7
    assert dispute_events[0]["args"]["defendant"] == defendant
    assert ruling_events[0]["args"]["winner"] == plaintiff
    assert ruling_events[0]["args"]["loser"] == defendant
    assert evidence_events[0]["args"]["agreementId"] == "agreement-7"
    assert evidence_events[0]["args"]["bundleCid"] == "ipfs://bafy-test"


def test_escrow_client_split_mode_dry_run_anchor_is_idempotent_with_bundle_metadata() -> None:
    with tempfile.TemporaryDirectory() as td:
        env = {
            "ESCROW_MOCK_DB_PATH": f"{td}/escrow_mock.db",
            "ESCROW_CONTRACT_MODE": "split",
            "ESCROW_COURT_ADDRESS": "0x" + "1" * 40,
            "ESCROW_VAULT_ADDRESS": "0x" + "2" * 40,
            "ESCROW_JUDGE_REGISTRY_ADDRESS": "0x" + "3" * 40,
            "ESCROW_EVIDENCE_ANCHOR_ADDRESS": "0x" + "4" * 40,
        }
        with patch.dict(os.environ, env, clear=False):
            client = EscrowClient(
                rpc_url="https://rpc.testnet3.goat.network",
                chain_id=48816,
                contract_address="0x" + "1" * 40,
                private_key="0x" + "1" * 64,
                dry_run=True,
            )

            first = client.commit_evidence_hash(
                "agreement-1",
                "0x" + "a" * 64,
                bundle_hash="0x" + "b" * 64,
                bundle_cid="ipfs://bafy-bundle",
            )
            second = client.commit_evidence_hash(
                "agreement-1",
                "0x" + "a" * 64,
                bundle_hash="0x" + "b" * 64,
                bundle_cid="ipfs://bafy-bundle",
            )

            assert client.capabilities()["commitEvidenceHash"] is True
            assert second.extra == {"idempotent": True}
            assert second.tx_hash == first.tx_hash

            evidence_events = client.poll_events("EvidenceCommitted", from_block=0)
            assert evidence_events[0]["args"]["bundleHash"] == "0x" + "b" * 64
            assert evidence_events[0]["args"]["bundleCid"] == "ipfs://bafy-bundle"


def test_escrow_client_split_mode_live_deposit_auto_approves_asset() -> None:
    env = {
        "ESCROW_CONTRACT_MODE": "split",
        "ESCROW_COURT_ADDRESS": "0x" + "1" * 40,
        "ESCROW_VAULT_ADDRESS": "0x" + "2" * 40,
        "ESCROW_JUDGE_REGISTRY_ADDRESS": "0x" + "3" * 40,
    }
    with patch.dict(os.environ, env, clear=False):
        client = EscrowClient(
            rpc_url="https://rpc.testnet3.goat.network",
            chain_id=48816,
            contract_address="0x" + "1" * 40,
            private_key="0x" + "1" * 64,
            dry_run=True,
        )

    client.dry_run = False
    client.asset_contract = SimpleNamespace(functions=_FakeERC20Functions(allowance=0))
    client.vault_contract = SimpleNamespace(functions=_FakeVaultTxFunctions())

    sent_calls: list[tuple] = []

    def fake_send(fn_call, *, value: int = 0):
        sent_calls.append(fn_call)
        idx = len(sent_calls)
        return EscrowTxResult(tx_hash=f"0x{idx:064x}", block_number=idx, status=1)

    client._send_tx = fake_send  # type: ignore[method-assign]

    result = client.deposit_pool(25)

    assert sent_calls[0][0] == "approve"
    assert sent_calls[1] == ("deposit", 25)
    assert sent_calls[2] == ("moveToBond", 25)
    assert result.extra == {
        "depositTxHash": "0x" + "2".zfill(64),
        "bondMoveTxHash": "0x" + "3".zfill(64),
        "approveTxHash": "0x" + "1".zfill(64),
    }


def test_escrow_client_split_mode_register_judge_bonds_then_registers() -> None:
    env = {
        "ESCROW_CONTRACT_MODE": "split",
        "ESCROW_COURT_ADDRESS": "0x" + "1" * 40,
        "ESCROW_VAULT_ADDRESS": "0x" + "2" * 40,
        "ESCROW_JUDGE_REGISTRY_ADDRESS": "0x" + "3" * 40,
    }
    with patch.dict(os.environ, env, clear=False):
        client = EscrowClient(
            rpc_url="https://rpc.testnet3.goat.network",
            chain_id=48816,
            contract_address="0x" + "1" * 40,
            private_key="0x" + "4" * 64,
            dry_run=True,
        )

    client.dry_run = False
    client.asset_contract = SimpleNamespace(functions=_FakeERC20Functions(allowance=0))
    client.vault_contract = SimpleNamespace(functions=_FakeVaultTxFunctions())
    client.registry_contract = SimpleNamespace(functions=_FakeRegistryTxFunctions())

    sent_calls: list[tuple] = []

    def fake_send(fn_call, *, value: int = 0):
        sent_calls.append(fn_call)
        idx = len(sent_calls)
        return EscrowTxResult(tx_hash=f"0x{idx:064x}", block_number=idx, status=1)

    client._send_tx = fake_send  # type: ignore[method-assign]

    result = client.register_judge(
        fee=25,
        endpoint="https://judge.example",
        max_response_time=60,
        bond_amount=25,
    )

    assert sent_calls[0][0] == "approve"
    assert sent_calls[1] == ("deposit", 25)
    assert sent_calls[2] == ("moveToBond", 25)
    assert sent_calls[3] == (
        "registerJudge",
        "0x" + "0" * 40,
        25,
        "https://judge.example",
        60,
    )
    assert result.extra == {
        "judge": client.account.address,
        "superior": "0x" + "0" * 40,
        "fee": 25,
        "bondAmount": 25,
        "approveTxHash": "0x" + "1".zfill(64),
        "depositTxHash": "0x" + "2".zfill(64),
        "bondMoveTxHash": "0x" + "3".zfill(64),
    }
