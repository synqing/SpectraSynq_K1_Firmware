| Gate | Verdict | Edge A | Edge B | Detail |
|---|---|---|---|---|
| G1 g1-a1 vs g1-a2 | PASS | 0/1778 differ; first hop None | 0/1778 differ; first hop None | |
| G1 g1-a1 vs g3-cont (shared input prefix, hops 4000-5332 at every 6th) | PASS | 0/222 differ; first hop None | 0/222 differ; first hop None | |
| G2 passage vs zero | FAIL | 1778/1778 differ; first hop 0 | 1778/1778 differ; first hop 0 | |
| G2 passage vs other-music | FAIL | 1705/1778 differ; first hop 30 | 1705/1778 differ; first hop 30 | |
| G2 zero vs other-music | FAIL | 1778/1778 differ; first hop 0 | 1778/1778 differ; first hop 0 | |
| G3 continuous vs forward | FAIL | 665/667 differ after R; first m-hop 4667; window agrees from never in window | 665/667 differ after R; first m-hop 4667; window agrees from never in window | R=667 hops |
| G3 continuous vs backward | FAIL | 667/667 differ after R; first m-hop 4667; window agrees from never in window | 667/667 differ after R; first m-hop 4667; window agrees from never in window | R=667 hops |
| G3 forward vs backward | FAIL | 667/667 differ after R; first m-hop 4667; window agrees from never in window | 667/667 differ after R; first m-hop 4667; window agrees from never in window | R=667 hops |
| G4 m2 vs twin | PASS | 0/1778 differ | 0/1778 differ | {"g4-m2": {"reached_AUTHORED": true, "rx_all_consumed": true, "rx_end": "records=9599/9599 queued=614400 consumed=614400 auth_state=2", "hotkey_state_changes":  |
