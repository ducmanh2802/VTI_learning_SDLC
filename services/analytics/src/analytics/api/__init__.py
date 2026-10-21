"""Internal HTTP API layer (`/internal/v1`).

Top layer of the Analytics dependency graph: it may import every lower layer
but nothing may import it (SDD 3.4.2).
"""

__all__: list[str] = []
