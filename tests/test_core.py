"""Offline unit tests (no network). Run: python3 -m pytest -q"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from chainsentinel.chains import get_chain
from chainsentinel.proxy import _parse_eip1167, _slot_to_address
from chainsentinel.analyzers.heuristics import run_heuristics
from chainsentinel.taxonomy import load as load_taxonomy


def test_chain_aliases():
    assert get_chain("bnb").chain_id == 56
    assert get_chain("bsc").chain_id == 56
    assert get_chain("eth").chain_id == 1


def test_slot_to_address():
    slot = "0x000000000000000000000000abcdef0000000000000000000000000000000001"
    assert _slot_to_address(slot) == "0xabcdef0000000000000000000000000000000001"
    zero = "0x" + "0" * 64
    assert _slot_to_address(zero) is None


def test_parse_eip1167():
    impl = "1234567890123456789012345678901234567890"
    code = "0x363d3d373d3d3d363d73" + impl + "5af43d82803e903d91602b57fd5bf3"
    assert _parse_eip1167(code) == "0x" + impl


def test_taxonomy_loads():
    cats = load_taxonomy()
    ids = {c.id for c in cats}
    assert "reentrancy" in ids
    assert "rugpull-honeypot" in ids
    # every category points at a skill
    assert all(c.skill for c in cats)


def test_heuristics_flag_txorigin():
    cats = load_taxonomy()
    files = {"T.sol": "contract T { function f() public { require(tx.origin == owner); } }"}
    findings = run_heuristics(files, cats)
    assert any("access-control" == f.category for f in findings)
