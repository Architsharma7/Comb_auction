#!/usr/bin/env python3
"""
Benchmark a single auction with automatic fallback.

Methods:
- onchain: Real transaction on Anvil (measures full tx gas)
- forge: Test environment (measures execution gas only)
"""

import argparse
import json
import re
import subprocess
from pathlib import Path
from typing import Optional

SIG_SELECT_WINNERS = "selectWinners((string,address,uint256,(string,address,address,uint256)[])[])"


def get_selector_hex(signature: str) -> str:
    """Compute function selector using cast."""
    result = subprocess.run(
        ["cast", "sig", signature],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(f"cast sig failed: {result.stderr.strip()}")

    selector = result.stdout.strip()
    if not selector.startswith("0x") or len(selector) != 10:
        raise RuntimeError(f"unexpected selector: {selector}")
    return selector


def build_calldata(bin_file: str, selector_hex: str) -> bytes:
    """Combine selector with encoded arguments."""
    args = Path(bin_file).read_bytes()
    selector_bytes = bytes.fromhex(selector_hex[2:])
    return selector_bytes + args


def calldata_stats(calldata: bytes) -> dict:
    """Calculate calldata statistics for gas computation."""
    zeros = calldata.count(b"\x00")
    nonzeros = len(calldata) - zeros
    return {"zeros": zeros, "nonzeros": nonzeros, "calldata_len": len(calldata)}


def benchmark_onchain(
    bin_file: str, rpc: str, pk: str, addr: str, selector_hex: str
) -> dict:
    """Benchmark using real on-chain transaction."""

    calldata = build_calldata(bin_file, selector_hex)
    stats = calldata_stats(calldata)
    calldata_hex = "0x" + calldata.hex()

    result = subprocess.run(
        [
            "cast",
            "send",
            addr,
            calldata_hex,  
            "--rpc-url",
            rpc,
            "--private-key",
            pk,
            "--gas-limit",
            "60000000",
            "--json",
        ],
        capture_output=True,
        text=True,
        check=False,
        timeout=60,
    )

    if result.returncode != 0:
        error_msg = result.stderr.strip() if result.stderr else result.stdout.strip()
        return {"success": False, "reason": f"send failed: {error_msg}"}

    try:
        tx_data = json.loads(result.stdout)
        tx_hash = (
            tx_data.get("transactionHash")
            or tx_data.get("txHash")
            or tx_data.get("hash")
        )
        if not tx_hash:
            return {"success": False, "reason": "no tx hash"}
    except Exception as e:
        return {"success": False, "reason": f"parse error: {e}"}

    receipt_result = subprocess.run(
        ["cast", "receipt", tx_hash, "--rpc-url", rpc, "--json"],
        capture_output=True,
        text=True,
        check=False,
    )

    if receipt_result.returncode != 0:
        return {"success": False, "reason": "receipt failed"}

    try:
        receipt = json.loads(receipt_result.stdout)
        gas_used_hex = receipt["gasUsed"]
        gas_used = (
            int(gas_used_hex, 16) if isinstance(gas_used_hex, str) else int(gas_used_hex)
        )

        status_hex = receipt.get("status", "0x1")
        status = 1 if status_hex == "0x1" else 0

        if status == 0:
            return {"success": False, "reason": "transaction reverted"}

    except Exception as e:
        return {"success": False, "reason": f"receipt parse error: {e}"}

    return {
        "success": True,
        "method": "onchain",
        "tx_hash": tx_hash,
        "gas_tx_measured": gas_used,
        "gas_exec_measured": None,
        **stats,
    }


def benchmark_forge(bin_file: str, selector_hex: str) -> dict:
    """Benchmark using Forge test environment (no gas limit)."""

    bin_file_abs = str(Path(bin_file).resolve())

    env = {**subprocess.os.environ.copy(), "RELATIVE_BIN_SOLUTIONS": bin_file_abs}

    result = subprocess.run(
        [
            "forge",
            "test",
            "--match-contract",
            "SelectWinnersBenchmark",
            "--match-test",
            "test_measureGas",
            "-vv",
        ],
        capture_output=True,
        text=True,
        env=env,
        timeout=120,
        check=False,
    )

    gas_match = re.search(r"GAS_EXEC_USED:\s*(\d+)", result.stdout)
    calldata_match = re.search(r"CALLDATA_LEN:\s*(\d+)", result.stdout)

    if not (gas_match and calldata_match):
        return {
            "success": False,
            "reason": "parse failed",
            "stdout": result.stdout[-1000:],
            "stderr": result.stderr[-1000:],
        }

    gas_exec = int(gas_match.group(1))
    calldata_len_test = int(calldata_match.group(1))

    calldata = build_calldata(bin_file_abs, selector_hex)
    stats = calldata_stats(calldata)

    if stats["calldata_len"] != calldata_len_test:
        print(
            f"Calldata length mismatch: Python={stats['calldata_len']}, Forge={calldata_len_test}"
        )

    return {
        "success": True,
        "method": "forge",
        "gas_exec_measured": gas_exec,
        "gas_tx_measured": None,
        **stats,
    }


def benchmark_auction(
    bin_file: str,
    auction_id: int,
    rpc: Optional[str] = None,
    pk: Optional[str] = None,
    addr: Optional[str] = None,
    force_forge: bool = False,
) -> dict:
    """Benchmark with automatic fallback to Forge."""

    selector_hex = get_selector_hex(SIG_SELECT_WINNERS)

    print(f"[{auction_id}] ", end="", flush=True)

    # Try on-chain first
    if not force_forge and all([rpc, pk, addr]):
        result = benchmark_onchain(bin_file, rpc, pk, addr, selector_hex)
        if result["success"]:
            print(f"on-chain ({result['gas_tx_measured']:,} gas)")
            return result
        print(f"on-chain failed, trying forge ")

    result = benchmark_forge(bin_file, selector_hex)
    if result["success"]:
        print(f"forge ({result['gas_exec_measured']:,} exec gas)")
    else:
        print(f"failed: {result.get('reason', 'unknown')}")

    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--bin", required=True)
    parser.add_argument("--auction-id", type=int, required=True)
    parser.add_argument("--rpc", default=None)
    parser.add_argument("--pk", default=None)
    parser.add_argument("--addr", default=None)
    parser.add_argument("--force-forge", action="store_true")

    args = parser.parse_args()

    result = benchmark_auction(
        args.bin, args.auction_id, args.rpc, args.pk, args.addr, args.force_forge
    )

    print(json.dumps(result, indent=2))