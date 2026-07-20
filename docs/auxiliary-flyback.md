# Auxiliary +67 V / −5 V flyback converter

[Русская версия](auxiliary-flyback.ru.md) · [System architecture](architecture.md) · [Full schematic](images/lab-psu-schematic-en.svg)

## Purpose

The OPA454 linear regulator needs an upper rail above the maximum output voltage and a small negative rail to regulate close to zero. A low-power UC3845 flyback converter generates:

| Parameter | Design value |
| --- | --- |
| Input | +12 V from the MP9486 converter |
| Positive raw output | approximately +67 V, regulated, up to about 20 mA |
| Negative raw output | approximately −5 V, cross-regulated, up to about 15 mA |
| Output power | approximately 1.5 W, designed with margin toward 2 W |
| Topology | non-isolated, discontinuous-conduction flyback |
| Controller | UC3845 current-mode PWM |
| Switching frequency | approximately 95 kHz |

The converter is magnetically coupled but **not galvanically isolated**: primary and secondary returns are connected to the system ground.

## Controller timing

UC3845 limits maximum duty cycle to approximately 50% and divides its oscillator frequency by two at the output. With `Rt = 10 kΩ` and `Ct = 910 pF`:

```text
Fosc ≈ 1.72 / (Rt × Ct) ≈ 190 kHz
Fsw  ≈ Fosc / 2 ≈ 95 kHz
```

This divide-by-two behavior is the important timing difference from UC3843 for this design.

## Transformer

The transformer uses an approximately EE16 CFL core:

| Parameter | Value |
| --- | --- |
| Core center leg | approximately 4 × 5 mm, `Ae ≈ 20 mm²` |
| Air gap | approximately 0.4–0.6 mm |
| Winding width | approximately 8 mm |
| Wire | approximately 0.25–0.30 mm |
| Primary | 24 turns, one layer |
| Secondary | one continuous 181-turn winding with a tap: 13 turns for −5 V, then 168 turns for +67 V |
| Estimated primary inductance | approximately 24–36 µH |
| Current limit | approximately 1.2 A peak |

### Winding order and phasing

1. Wind the 24-turn primary as the inner layer.
2. Apply two insulation layers.
3. Start the secondary at the −5 V end.
4. Wind 13 turns and bring out the system-ground tap.
5. Continue in the same winding direction for another 168 turns to the +67 V end, adding interlayer insulation.
6. Apply the external insulation.

The primary start connects to `V12`; its finish connects to the MOSFET drain. When both windings are wound in the same physical direction, the secondary end at the same bobbin edge as the `V12` primary start is the −5 V end. The opposite end is the +67 V end.

## Power stage

- external CS630, 200 V N-channel MOSFET in DPAK/TO-252;
- `0.82 Ω`, 1 W current-sense resistor from source to ground;
- `1 kΩ + 470 pF` current-sense input filter;
- `10 Ω` gate resistor and `10 kΩ` gate-to-source pulldown;
- UF4005 rectifier on the +67 V winding;
- SS14 rectifier on the −5 V winding;
- mandatory RCD clamp using UF4005, `22 kΩ`, and `1 nF`;
- local 12 V input decoupling of `22 µF + 100 nF`.

The expected MOSFET off-state voltage is below 50 V including the nominal leakage allowance, so the 200 V device provides substantial margin. The RCD clamp remains necessary because actual leakage inductance and layout determine the drain spike.

## Feedback and filtering

The +67 V raw output is regulated directly:

```text
Vout ≈ 2.5 V × (1 + 130 kΩ / 5.1 kΩ) ≈ 66 V
```

The −5 V winding follows by transformer ratio and does not require precision regulation for the OPA454.

Both rails are filtered after rectification:

```text
V_P67R ── 47 Ω ── V_P67
                    │
                 4.7 µF

V_N5R  ── 47 Ω ── V_N5
                    │
                 4.7 µF
```

The approximately 700 Hz RC corner provides roughly 42 dB attenuation at 95 kHz. The UC3845 feedback divider senses `V_P67R` before the RC filter so the additional pole remains outside the control loop. OPA454 loads and preload resistors connect to the clean sides, `V_P67` and `V_N5`.

## Bring-up checks

Initial testing should use a current-limited 8–12 V source rather than the complete mains power stage.

1. Verify that the +67 V output is positive and the −5 V output is negative.
2. If both polarities are reversed, exchange the two outer secondary ends while leaving the ground tap unchanged.
3. If both outputs remain near zero and the transformer or MOSFET heats rapidly, reverse the primary connections.
4. Measure primary peak current and confirm it remains below approximately 1.2 A.
5. Check the MOSFET drain waveform and RCD clamp voltage.
6. Verify regulation and stability at no load and at maximum auxiliary load.
7. Confirm the clean rails after the 47 Ω / 4.7 µF filters before connecting the OPA454.

All final loop values and transformer assumptions require confirmation on the assembled PCB.

