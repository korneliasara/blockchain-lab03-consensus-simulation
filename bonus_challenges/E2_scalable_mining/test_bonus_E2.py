
import pytest

from bonus_E2_miner import PersistentMiner, valid_nonce


@pytest.mark.parametrize("workers", [1, 2, 4])
def test_valid_mining(workers):
    target = (1 << 256) // 1000

    with PersistentMiner(workers=workers) as miner:
        result = miner.mine(b"test-block", target)

        assert result["nonce"] >= 0
        assert valid_nonce(
            b"test-block",
            result["nonce"],
            target,
        )


def test_worker_processes_are_reused():
    target = (1 << 256) // 1000

    with PersistentMiner(workers=4) as miner:
        before = [p.pid for p in miner.processes]

        for number in range(5):
            header = f"block-{number}".encode()
            result = miner.mine(header, target)
            assert valid_nonce(
                header, result["nonce"], target
            )

        after = [p.pid for p in miner.processes]

        assert before == after
        assert all(p.is_alive() for p in miner.processes)


def test_invalid_worker_count():
    with pytest.raises(ValueError):
        PersistentMiner(workers=0)
