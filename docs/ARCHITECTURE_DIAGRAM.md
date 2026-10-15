# NADI-HD system diagram

```mermaid
flowchart LR
    A[Open or synthetic patient data] --> Q[Quality and chronology gates]
    M[Dialysis machine stream] --> Q
    Q --> T[Patient twin calibration]
    T --> P[Transparent physiology simulation]
    T --> L[Calibrated learned risk]
    P --> H[Bounded hybrid fusion]
    L --> H
    H --> C[Constrained Parallel Futures]
    C --> U[Nurse / nephrologist review]
    U -->|completed synthetic session| S[(Session memory)]
    S --> T
    Q -->|missing or contradictory| D[Conservative / unavailable mode]
    D --> U
    C -. never writes settings .-> X[Dialysis machine]
```

The dashed edge is a prohibited boundary, not a control connection. NADI-HD never writes to a dialysis
machine. Every risk channel remains separately testable, and disagreement expands uncertainty.
