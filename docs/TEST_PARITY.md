# Test Parity Dashboard

> Automated test parity tracking across all 6 Agenkit language implementations


### Current Test Parity Summary

**Generated**: 2026-01-15T20:09:14Z | **Python Baseline**: 1792 tests

| Language | Tests | Parity | Threshold | Status | Gap to Threshold |
|----------|-------|--------|-----------|--------|------------------|
| Python | 1792 | 100.0% | baseline | ✅ | — |
| GO | 950 | 53.0% | 50.0% | 🟡 ✅ PASS | +3.0% |
| CPP | 793 | 44.3% | 40.0% | 🟡 ✅ PASS | +4.3% |
| RUST | N/A | N/A | N/A | ⏸️ | N/A |
| TYPESCRIPT | N/A | N/A | N/A | ⏸️ | N/A |
| ZIG | N/A | N/A | N/A | ⏸️ | N/A |

### Parity Progress vs Thresholds

Progress bars show current parity (█) vs minimum threshold (│):


**GO** 🟡 ✅ PASS
```
[█████████████████████░░░░░░░░░░░░░░░░░░░] 53.0%
Tests: 950/1792 | Threshold: 50.0% | Gap to 100%: 47.0%
```

**CPP** 🟡 ✅ PASS
```
[█████████████████░░░░░░░░░░░░░░░░░░░░░░░] 44.3%
Tests: 793/1792 | Threshold: 40.0% | Gap to 100%: 55.7%
```

**RUST**: Not in report yet

**TYPESCRIPT**: Not in report yet

**ZIG**: Not in report yet

### Category Parity Heatmap

Status: 🟢 Excellent (≥80%) | 🟡 Good (60-80%) | 🟠 Fair (40-60%) | 🔴 Poor (<40%) | — N/A

| Language     | patterns | techniqu | safety   | adapters | evaluati | middlewa | memory   | budget   |
|--------------|----------|----------|----------|----------|----------|----------|----------|----------|
| GO           |    🟢     |    🔴     |    🟠     |    🔴     |    🟢     |    🟢     |    🔴     |    🔴     |
| CPP          |    🟡     |    🔴     |    🔴     |    🔴     |    🔴     |    🔴     |    🔴     |    🔴     |
| RUST         |    —     |    —     |    —     |    —     |    —     |    —     |    —     |    —     |
| TYPESCRIPT   |    —     |    —     |    —     |    —     |    —     |    —     |    —     |    —     |
| ZIG          |    —     |    —     |    —     |    —     |    —     |    —     |    —     |    —     |


### Category Breakdown


#### Adapters

**Python baseline**: 141 tests

| Language | Tests | Parity | Status |
|----------|-------|--------|--------|
| GO | 54 | 38.3% | 🟠 |
| CPP | 50 | 35.5% | 🟠 |
| RUST | N/A | N/A | ⏸️ |
| TYPESCRIPT | N/A | N/A | ⏸️ |
| ZIG | N/A | N/A | ⏸️ |

#### Budget

**Python baseline**: 51 tests

| Language | Tests | Parity | Status |
|----------|-------|--------|--------|
| GO | 0 | 0.0% | 🔴 |
| CPP | 0 | 0.0% | 🔴 |
| RUST | N/A | N/A | ⏸️ |
| TYPESCRIPT | N/A | N/A | ⏸️ |
| ZIG | N/A | N/A | ⏸️ |

#### Chaos

**Python baseline**: 53 tests

| Language | Tests | Parity | Status |
|----------|-------|--------|--------|
| GO | 0 | 0.0% | 🔴 |
| CPP | 0 | 0.0% | 🔴 |
| RUST | N/A | N/A | ⏸️ |
| TYPESCRIPT | N/A | N/A | ⏸️ |
| ZIG | N/A | N/A | ⏸️ |

#### Composition

**Python baseline**: 40 tests

| Language | Tests | Parity | Status |
|----------|-------|--------|--------|
| GO | 16 | 40.0% | 🟡 |
| CPP | 0 | 0.0% | 🔴 |
| RUST | N/A | N/A | ⏸️ |
| TYPESCRIPT | N/A | N/A | ⏸️ |
| ZIG | N/A | N/A | ⏸️ |

#### Evaluation

**Python baseline**: 116 tests

| Language | Tests | Parity | Status |
|----------|-------|--------|--------|
| GO | 127 | 109.5% | ✅ |
| CPP | 0 | 0.0% | 🔴 |
| RUST | N/A | N/A | ⏸️ |
| TYPESCRIPT | N/A | N/A | ⏸️ |
| ZIG | N/A | N/A | ⏸️ |

#### Integration

**Python baseline**: 90 tests

| Language | Tests | Parity | Status |
|----------|-------|--------|--------|
| GO | 0 | 0.0% | 🔴 |
| CPP | 65 | 72.2% | 🟢 |
| RUST | N/A | N/A | ⏸️ |
| TYPESCRIPT | N/A | N/A | ⏸️ |
| ZIG | N/A | N/A | ⏸️ |

#### Memory

**Python baseline**: 101 tests

| Language | Tests | Parity | Status |
|----------|-------|--------|--------|
| GO | 18 | 17.8% | 🔴 |
| CPP | 0 | 0.0% | 🔴 |
| RUST | N/A | N/A | ⏸️ |
| TYPESCRIPT | N/A | N/A | ⏸️ |
| ZIG | N/A | N/A | ⏸️ |

#### Middleware

**Python baseline**: 92 tests

| Language | Tests | Parity | Status |
|----------|-------|--------|--------|
| GO | 91 | 98.9% | ✅ |
| CPP | 0 | 0.0% | 🔴 |
| RUST | N/A | N/A | ⏸️ |
| TYPESCRIPT | N/A | N/A | ⏸️ |
| ZIG | N/A | N/A | ⏸️ |

#### Observability

**Python baseline**: 41 tests

| Language | Tests | Parity | Status |
|----------|-------|--------|--------|
| GO | 41 | 100.0% | ✅ |
| CPP | 0 | 0.0% | 🔴 |
| RUST | N/A | N/A | ⏸️ |
| TYPESCRIPT | N/A | N/A | ⏸️ |
| ZIG | N/A | N/A | ⏸️ |

#### Patterns

**Python baseline**: 439 tests

| Language | Tests | Parity | Status |
|----------|-------|--------|--------|
| GO | 362 | 82.5% | ✅ |
| CPP | 310 | 70.6% | 🟢 |
| RUST | N/A | N/A | ⏸️ |
| TYPESCRIPT | N/A | N/A | ⏸️ |
| ZIG | N/A | N/A | ⏸️ |

#### Property

**Python baseline**: 37 tests

| Language | Tests | Parity | Status |
|----------|-------|--------|--------|
| GO | 0 | 0.0% | 🔴 |
| CPP | 0 | 0.0% | 🔴 |
| RUST | N/A | N/A | ⏸️ |
| TYPESCRIPT | N/A | N/A | ⏸️ |
| ZIG | N/A | N/A | ⏸️ |

#### Routing

**Python baseline**: 34 tests

| Language | Tests | Parity | Status |
|----------|-------|--------|--------|
| GO | 0 | 0.0% | 🔴 |
| CPP | 0 | 0.0% | 🔴 |
| RUST | N/A | N/A | ⏸️ |
| TYPESCRIPT | N/A | N/A | ⏸️ |
| ZIG | N/A | N/A | ⏸️ |

#### Safety

**Python baseline**: 162 tests

| Language | Tests | Parity | Status |
|----------|-------|--------|--------|
| GO | 94 | 58.0% | 🟡 |
| CPP | 0 | 0.0% | 🔴 |
| RUST | N/A | N/A | ⏸️ |
| TYPESCRIPT | N/A | N/A | ⏸️ |
| ZIG | N/A | N/A | ⏸️ |

#### Techniques

**Python baseline**: 240 tests

| Language | Tests | Parity | Status |
|----------|-------|--------|--------|
| GO | 37 | 15.4% | 🔴 |
| CPP | 22 | 9.2% | 🔴 |
| RUST | N/A | N/A | ⏸️ |
| TYPESCRIPT | N/A | N/A | ⏸️ |
| ZIG | N/A | N/A | ⏸️ |

#### Tools

**Python baseline**: 32 tests

| Language | Tests | Parity | Status |
|----------|-------|--------|--------|
| GO | 17 | 53.1% | 🟡 |
| CPP | 0 | 0.0% | 🔴 |
| RUST | N/A | N/A | ⏸️ |
| TYPESCRIPT | N/A | N/A | ⏸️ |
| ZIG | N/A | N/A | ⏸️ |

---


**Documentation**: [README-test-parity.md](../README-test-parity.md)

**Raw Data**: [test-parity-report.json](../test-parity-report.json)

**Validation Tests**: [tests/test_parity_validation.py](../tests/test_parity_validation.py)


*Last updated: 2026-01-15 12:36:00 UTC*
