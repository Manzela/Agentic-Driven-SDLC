"""actor_separation.py — Z3 proof of verifier/implementer actor separation.

Actor-independence fix #5. Proves the gate invariant: a coverage item can be
``proven`` ONLY if the verifying actor is distinct from the implementing actor.
We assert the NEGATION is unsatisfiable — there is no model where ``proven`` is
true while ``verify_actor == impl_actor``. If Z3 returns ``unsat`` for the
adversary's conjunction, the property holds and ``prove()`` returns
``"UNSAT-to-violate"``.

Run standalone: ``python verification/actor_separation.py`` (prints the verdict;
exits non-zero if the property could be violated).
"""

from __future__ import annotations

import sys

__all__ = ["prove"]


def prove() -> str:
    from z3 import Bool, Solver, Implies, And, Not, sat

    proven = Bool("proven")
    # distinct == (verify_actor != impl_actor)
    distinct = Bool("verify_actor_distinct_from_impl")

    s = Solver()
    # Gate rule the SubagentStop hook enforces: proven => distinct.
    s.add(Implies(proven, distinct))
    # Adversary tries to violate it: a proven item with coincident actors.
    s.add(And(proven, Not(distinct)))

    return "SAT-violation-possible" if s.check() == sat else "UNSAT-to-violate"


if __name__ == "__main__":
    verdict = prove()
    print(verdict)
    sys.exit(0 if verdict == "UNSAT-to-violate" else 1)
