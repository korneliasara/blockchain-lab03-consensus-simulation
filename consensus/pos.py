
"""Blockchain Lab 03 - Proof of Stake and Casper FFG."""

from dataclasses import dataclass


GWEI = 10**9
MAX_EFFECTIVE_BALANCE = 32 * GWEI

MIN_EPOCHS_TO_INACTIVITY_PENALTY = 4
INACTIVITY_PENALTY_QUOTIENT = 64

@dataclass(frozen=True)
class Checkpoint:
    epoch: int
    root: str


@dataclass(frozen=True)
class Attestation:
    validator: int
    source: Checkpoint
    target: Checkpoint


@dataclass
class Validator:
    index: int
    balance: int = MAX_EFFECTIVE_BALANCE
    slashed: bool = False
    slashed_epoch: int | None = None
    exited: bool = False

    @property
    def is_active(self) -> bool:
        return (
            not self.exited
            and not self.slashed
            and self.balance > 0
        )

    @property
    def effective_balance(self) -> int:
        return min(self.balance, MAX_EFFECTIVE_BALANCE)


class BeaconState:
    """Manage validators and Casper FFG checkpoints."""

    def __init__(
        self,
        validator_count: int,
        genesis_root: str = "genesis",
    ):
        self.validators = [
            Validator(index=i)
            for i in range(validator_count)
        ]

        self.genesis_checkpoint = Checkpoint(
            epoch=0,
            root=genesis_root,
        )

        self.justified = {self.genesis_checkpoint}
        self.current_justified = self.genesis_checkpoint
        self.finalized = self.genesis_checkpoint

        
        self.current_epoch = 0
        self.last_finalized_epoch = 0
        self.attestation_log = []

        self.slashings = []
        self.slashed_balance_total = 0


    @property
    def total_active_balance(self) -> int:
        return sum(
            validator.effective_balance
            for validator in self.validators
            if validator.is_active
        )

    def supermajority_threshold(self) -> int:
        """Strictly more than two-thirds is required."""
        return (2 * self.total_active_balance) // 3

    def attest(self, attestation: Attestation) -> None:
        validator = self.validators[attestation.validator]

        if validator.is_active:
            self.attestation_log.append(attestation)

    def attest_many(
        self,
        attestations: list[Attestation],
    ) -> None:
        for attestation in attestations:
            self.attest(attestation)

    def _process_justification(
        self,
        epoch: int,
    ) -> Checkpoint | None:
        """Justify checkpoints with sufficient stake."""

        votes = {}

        for attestation in self.attestation_log:
            if attestation.target.epoch != epoch:
                continue

            validator = self.validators[
                attestation.validator
            ]

            if not validator.is_active:
                continue

            # Votes must come from justified checkpoints.
            if attestation.source not in self.justified:
                continue

            key = (
                attestation.source,
                attestation.target,
            )

            votes[key] = (
                votes.get(key, 0)
                + validator.effective_balance
            )

        threshold = self.supermajority_threshold()

        for (source, target), weight in votes.items():
            if weight > threshold:
                self.justified.add(target)

                if (
                    target.epoch
                    > self.current_justified.epoch
                ):
                    self.current_justified = target

                return target

        return None

    def _process_finalization(
        self,
        epoch: int,
    ) -> Checkpoint | None:
        """Finalize a checkpoint after its successor is justified."""

        checkpoints = sorted(
            self.justified,
            key=lambda checkpoint: checkpoint.epoch,
        )

        for checkpoint in checkpoints:
            successor_exists = any(
                other.epoch == checkpoint.epoch + 1
                for other in self.justified
            )

            if (
                successor_exists
                and checkpoint.epoch > self.finalized.epoch
            ):
                self.finalized = checkpoint
                self.last_finalized_epoch = epoch
                return checkpoint

        return None
    
    def _process_slashings(self, epoch: int):
        records = []
        already_slashed = {
            record.validator for record in self.slashings
        }

        for a, b, rule in find_violations(self.attestation_log):
            index = a.validator

            if index in already_slashed:
                continue

            validator = self.validators[index]

            initial_penalty = (
                validator.effective_balance
                // INITIAL_SLASHING_QUOTIENT
            )

            validator.balance -= initial_penalty
            validator.slashed = True
            validator.slashed_epoch = epoch

            self.slashed_balance_total += (
                validator.effective_balance
            )

            record = SlashingRecord(
                validator=index,
                epoch=epoch,
                rule=rule,
                initial_penalty=initial_penalty,
            )

            records.append(record)
            self.slashings.append(record)
            already_slashed.add(index)

        if records:
            self._apply_correlated_penalty(records)

        return records

    def _apply_correlated_penalty(self, records):
        total = (
            self.total_active_balance
            + self.slashed_balance_total
        )

        if total == 0:
            return

        fraction = min(
            1.0,
            PROPORTIONAL_SLASHING_MULTIPLIER
            * self.slashed_balance_total / total
        )

        for record in records:
            validator = self.validators[record.validator]

            extra_penalty = int(
                validator.effective_balance * fraction
            )

            extra_penalty = min(
                extra_penalty, validator.balance
            )

            validator.balance -= extra_penalty
            record.correlated_penalty = extra_penalty

    
    def _process_inactivity_leak(self, epoch: int) -> int:
        """Reduce absent validators' balances after finality stalls."""

        # Allow four epochs without finality.
        if (
            epoch - self.last_finalized_epoch
            <= MIN_EPOCHS_TO_INACTIVITY_PENALTY
        ):
            return 0

        # Validators who voted during this epoch.
        participating = {
            attestation.validator
            for attestation in self.attestation_log
            if attestation.target.epoch == epoch
        }

        total_leaked = 0

        for validator in self.validators:
            if not validator.is_active:
                continue

            # Participating validators are not penalised.
            if validator.index in participating:
                continue

            penalty = (
                validator.effective_balance
                // INACTIVITY_PENALTY_QUOTIENT
            )

            penalty = min(penalty, validator.balance)
            validator.balance -= penalty
            total_leaked += penalty

        return total_leaked

    
    
    def process_epoch(self, epoch: int) -> dict:
        self.current_epoch = epoch

        slashed = self._process_slashings(epoch)
        justified = self._process_justification(epoch)
        finalized = self._process_finalization(epoch)
        leaked = self._process_inactivity_leak(epoch)

        return {
            "epoch": epoch,
            "slashed": slashed,
            "justified": justified,
            "finalized": finalized,
            "inactivity_leak": leaked,
        }






from itertools import combinations


INITIAL_SLASHING_QUOTIENT = 32
PROPORTIONAL_SLASHING_MULTIPLIER = 3


@dataclass
class SlashingRecord:
    validator: int
    epoch: int
    rule: str
    initial_penalty: int
    correlated_penalty: int = 0


def is_double_vote(a: Attestation, b: Attestation) -> bool:
    return (
        a.validator == b.validator
        and a.target.epoch == b.target.epoch
        and a.target.root != b.target.root
    )


def is_surround_vote(a: Attestation, b: Attestation) -> bool:
    return (
        a.validator == b.validator
        and a.source.epoch < b.source.epoch
        and b.target.epoch < a.target.epoch
    )


def find_violations(attestations: list[Attestation]):
    violations = []

    for a, b in combinations(attestations, 2):
        if is_double_vote(a, b):
            violations.append((a, b, "double_vote"))
        elif (
            is_surround_vote(a, b)
            or is_surround_vote(b, a)
        ):
            violations.append((a, b, "surround_vote"))

    return violations


def honest_attestations(
    state: BeaconState,
    source: Checkpoint,
    target: Checkpoint,
    validators: list[int] | None = None,
) -> list[Attestation]:
    """Create honest votes for a checkpoint link."""

    if validators is None:
        validators = [
            validator.index
            for validator in state.validators
            if validator.is_active
        ]

    return [
        Attestation(
            validator=index,
            source=source,
            target=target,
        )
        for index in validators
    ]
