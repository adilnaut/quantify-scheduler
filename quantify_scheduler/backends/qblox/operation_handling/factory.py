# Repository: https://gitlab.com/quantify-os/quantify-scheduler
# Licensed according to the LICENCE file on the main branch
"""Functions for producing operation handling strategies."""

from __future__ import annotations

from quantify_scheduler.backends.qblox.enums import IoMode
from quantify_scheduler.backends.qblox.operation_handling import (
    acquisitions,
    base,
    pulses,
    virtual,
)
from quantify_scheduler.backends.types.qblox import OpInfo
from quantify_scheduler.enums import BinMode


def get_operation_strategy(
    operation_info: OpInfo,
    instruction_generated_pulses_enabled: bool,
    io_mode: IoMode,
) -> base.IOperationStrategy:
    """
    Determines and instantiates the correct strategy object.

    Parameters
    ----------
    operation_info
        The operation we are building the strategy for.
    instruction_generated_pulses_enabled
        Specifies if instruction generated pulses (e.g. staircase through offsets) are
        allowed. If set to False, only generically treated pulses are allowed.
    io_mode
        Either :attr:`.IoMode.REAL`, :attr:`.IoMode.IMAG` or :attr:`.IoMode.COMPLEX`
        depending on whether the signal affects only sequencer path0, path1 or both.

    Returns
    -------
    :
        The instantiated strategy object.
    """
    if operation_info.is_acquisition:
        return _get_acquisition_strategy(operation_info)

    return _get_pulse_strategy(
        operation_info=operation_info,
        instruction_generated_pulses_enabled=instruction_generated_pulses_enabled,
        io_mode=io_mode,
    )


def _get_acquisition_strategy(
    operation_info: OpInfo,
) -> acquisitions.AcquisitionStrategyPartial:
    """Handles the logic for determining the correct acquisition type."""

    protocol = operation_info.data["protocol"]
    if protocol in ("Trace", "SSBIntegrationComplex", "ThresholdedAcquisition"):
        if protocol == "Trace" and operation_info.data["bin_mode"] == BinMode.APPEND:
            raise ValueError(
                f"Trace acquisition does not support APPEND bin mode.\n\n"
                f"{repr(operation_info)} caused this exception to occur."
            )
        return acquisitions.SquareAcquisitionStrategy(operation_info)

    elif protocol == "WeightedIntegratedComplex":
        return acquisitions.WeightedAcquisitionStrategy(operation_info)

    elif protocol == "TriggerCount":
        return acquisitions.TriggerCountAcquisitionStrategy(operation_info)

    raise ValueError(
        f'Unknown acquisition protocol "{protocol}" encountered in '
        f"Qblox backend when processing acquisition {repr(operation_info)}."
    )


def _get_pulse_strategy(
    operation_info: OpInfo,
    instruction_generated_pulses_enabled: bool,
    io_mode: IoMode,
) -> base.IOperationStrategy:
    """Handles the logic for determining the correct pulse type."""
    if operation_info.is_offset_instruction:
        return virtual.AwgOffsetStrategy(operation_info)
    elif operation_info.is_parameter_update:
        return virtual.UpdateParameterStrategy(operation_info)

    elif operation_info.data["port"] is None:
        if "phase_shift" in operation_info.data:
            return virtual.NcoPhaseShiftStrategy(operation_info)
        elif "reset_clock_phase" in operation_info.data:
            return virtual.NcoResetClockPhaseStrategy(operation_info)
        elif "clock_freq_new" in operation_info.data:
            return virtual.NcoSetClockFrequencyStrategy(operation_info)
        else:
            return virtual.IdleStrategy(operation_info)

    elif instruction_generated_pulses_enabled:
        wf_func = operation_info.data["wf_func"]

        if wf_func == "quantify_scheduler.waveforms.square":
            return pulses.StitchedSquarePulseStrategy(operation_info, io_mode)

        elif wf_func == "quantify_scheduler.waveforms.staircase":
            return pulses.StaircasePulseStrategy(operation_info, io_mode)

    elif operation_info.name == "MarkerPulse":
        return pulses.MarkerPulseStrategy(operation_info, io_mode)

    return pulses.GenericPulseStrategy(operation_info, io_mode)
