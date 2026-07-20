# System architecture

[Русская версия](architecture.ru.md) · [Project overview](../README.md) · [Full schematic](images/lab-psu-schematic-en.svg)

## Design objective

The power supply is designed for a programmable 0–50 V output with 1 mV and 1 mA user-setting increments and a target output ripple of no more than 1 mV. Efficiency and low noise are combined by splitting regulation between a switching preregulator and a fast analog post-regulator.

These figures are design targets. PCB layout, firmware, thermal characterization, loop compensation, and final electrical validation are still in progress.

## Power path

```mermaid
flowchart LR
    A[230 V AC] --> B[Active PFC<br/>about 380 V DC]
    B --> C[Two-switch forward<br/>galvanic isolation]
    C --> D[Rectifier and filter<br/>about 55 V]
    D --> E[Synchronous buck<br/>tracking preregulator]
    E --> F[Damped C-L-C filter]
    F --> G[OPA454 + pass MOSFET<br/>linear post-regulator]
    G --> H[Protection and relay]
    H --> I[0-50 V output]
```

### Isolated mains converter

The hot side reuses the power stage of a modified NEO500 500 W ATX supply:

- CM6800TX active PFC and an approximately 380 V DC bus;
- two-switch forward converter with 18N50 primary MOSFETs;
- a gate-drive transformer for the synchronized high-side and low-side switches;
- transformer isolation between the mains circuitry and the output/control domain;
- STTH30R03 ultrafast secondary rectification and 100 V-rated filtering.

The current transformer uses a 22-turn secondary made from four parallel 0.6 mm conductors. It is treated as approximately 5–6 A continuous / 8 A peak hardware. The power stage is dimensioned for a later transformer upgrade toward 10 A.

### Tracking synchronous buck

Two IRFB4110 MOSFETs and a UCC27211 driver form the synchronous buck. STM32G474 HRTIM generates complementary PWM. Fast ADC channels measure the linear-stage drain and source nodes, and firmware maintains approximately 2–2.5 V of headroom across the pass MOSFET.

This tracking strategy moves most dissipation into the efficient switching stage while preserving enough voltage for the linear loop to reject ripple and load transients.

The buck output contains:

- 1000 µF / 100 V bulk capacitance and local 4.7 µF / 100 V ceramics;
- a 2.2 µH, at least 12 A series inductor;
- two 4.7 µF / 100 V ceramics at the linear-stage drain;
- a 100 µF / 100 V electrolytic whose ESR damps the C–L–C resonance.

The filter corner is around 10 kHz and provides additional attenuation at the approximately 95–100 kHz switching frequency.

### Linear post-regulator

An OPA454 compares the DAC setpoint with the scaled output voltage and drives an IRFB4110 pass MOSFET as a source follower. The baseline assembly uses one MOSFET; the PCB provides positions for additional parallel devices if thermal testing requires them.

The voltage-feedback ratio is approximately 110 kΩ / 5.1 kΩ, giving a gain close to 22. The resistors are specified as matched 0.1%, 25 ppm/°C parts, with final gain and offset corrected by calibration.

A −5 V auxiliary rail keeps the OPA454 away from its lower output swing limit. An active approximately 6 mA preload referenced to that rail keeps the analog loop controlled near zero output and also provides controlled down-programming.

## Setpoint and measurement

| Function | Implementation |
| --- | --- |
| Voltage setpoint | DAC8830, 16 bit, 0–2.5 V from REF5025 |
| Nominal output increment | `2.5 V / 65536 × 22 ≈ 0.84 mV` |
| Terminal voltage/current | INA228, 20-bit converter |
| Current shunt | approximately 10 mΩ constantan element with Kelvin connections |
| Current measurement increment | approximately 31 µA per LSB with the selected shunt |
| Current control | firmware CC loop, approximately 1–2 kHz target update rate |
| Fast tracking channels | STM32 ADCs synchronized with HRTIM |

The INA228 measures output-bus voltage directly and shunt current independently of the MCU ADC reference. A sense relay connects its bus-voltage input to the actual terminals when the output relay is closed. A slow digital correction loop compensates relay, fuse, trace, and shunt drops without placing the fast analog voltage loop across a switching relay contact.

## Control modes

- constant voltage with a fast analog regulation loop;
- digital constant current using INA228 feedback;
- firmware-defined current foldback as a function of output voltage;
- controlled startup and downward voltage ramps;
- output enable/disable with preflight checks;
- thermal current reduction and shutdown.

The STM32G474 also drives a 480×320 SPI display, separate voltage and current encoders, an output button, a fault-reset input, a temperature-controlled fan, USB DFU/CDC, and audible fault indication.

## Protection architecture

Protection is divided by required response time.

### Fast hardware path

The Kelvin shunt signal is amplified by STM32 OPAMP1 and routed externally to COMP1. The comparator threshold comes from an internal DAC. A fault drives HRTIM BRK in hardware, terminating buck PWM within the peripheral path. The same event generates an interrupt that writes zero to the external DAC8830, closes the linear pass element, latches the fault, and commands output disconnection.

An independent overvoltage comparator uses the same shutdown concept.

### Output-domain protection

- reverse-polarity optocoupler monitors the terminals before relay closure;
- a separate terminal-voltage divider detects an external positive voltage and a welded relay;
- backfeed supervision watches the approximately 55 V buck input;
- a unidirectional 1.5KE56A TVS and antiparallel power diode clamp the regulator-side output node;
- a 15 A, 5×20 mm high-breaking-capacity fuse interrupts sustained faults;
- an RC snubber limits arcing when an inductive load is disconnected;
- the output relay normally switches only after current has been reduced to approximately zero.

### Thermal protection

An NTC on the pass-device heatsink provides fan control, foldback, and firmware shutdown. A normally closed Klixon contact in the relay-coil return is an independent hardware overtemperature interlock.

## Power rails

- `5VSB` powers the control domain and TFT module.
- The controller module generates 3.3 V for digital logic.
- REF5025 is filtered and powered from `5VSB`.
- An MP9486 high-voltage buck converts the approximately 55 V rail to 12 V for the buck driver, relays, fan, and auxiliary converter.
- A UC3845 flyback generates the OPA454 rails: approximately +67 V and −5 V. See [Auxiliary flyback converter](auxiliary-flyback.md).

## Development status

| Item | Status |
| --- | --- |
| System architecture | defined |
| Current electrical schematic | complete |
| English schematic annotations | available |
| PCB layout | in development |
| Firmware | in development |
| Loop compensation and thermal tuning | pending hardware bring-up |
| Final accuracy, ripple, transient, and protection validation | pending |

