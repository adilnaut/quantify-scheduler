# Repository: https://gitlab.com/quantify-os/quantify-scheduler
# Licensed according to the LICENCE file on the main branch
from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from typing import Any, List

from numpy import isclose

from quantify_scheduler.backends.qblox import constants as qblox_constants
from quantify_scheduler.operations.operation import Operation
from quantify_scheduler.operations.pulse_library import VoltageOffset


class StitchedPulse(Operation):
    """
    A pulse composed of multiple operations that together constitute a waveform.

    This class can be used to construct arbitrarily long
    waveforms by stitching together pulses with optional changes in offset in
    between.
    """

    def __init__(
        self,
        pulse_info: List[Any] | None = None,
    ) -> None:
        """
        Parameters
        ----------
        pulse_info : List[Any] or None, optional
            A list containing the pulses that are part of the StitchedPulse. By default
            None.
        """
        pulse_info = pulse_info or []
        super().__init__(name=self.__class__.__name__)
        self.data["pulse_info"] = pulse_info
        self._update()

    def __str__(self) -> str:
        pulse_info = self.data["pulse_info"]
        return f"StitchedPulse(pulse_info={pulse_info}) "

    def add_pulse(self, pulse_operation: Operation) -> None:
        """
        Adds pulse_info of pulse_operation Operation to this Operation.

        Parameters
        ----------
        pulse_operation : Operation
            an operation containing pulse_info.

        Raises
        ------
        ValueError
            When the operation's port and/or clock do not match those of the previously
            added SitchedPulse components.
        """
        if not self._pulse_and_clock_match(pulse_operation["pulse_info"]):
            raise ValueError(
                "All ports and clocks of a StitchedPulse's components must be equal."
            )

        super().add_pulse(pulse_operation)

    def _pulse_and_clock_match(self, operation_info: List[dict[str, Any]]) -> bool:
        """
        Check if the port and clock of an operation match the ports and clocks of the
        operations already present in the StitchedPulse. Returns True if the
        StitchedPulse is still empty.
        """
        if len(self.data["pulse_info"]) == 0:
            return True

        port = self["pulse_info"][0]["port"]
        clock = self["pulse_info"][0]["clock"]

        for pulse_info in operation_info:
            if pulse_info["port"] != port or pulse_info["clock"] != clock:
                return False
        return True


@dataclass
class _VoltageOffsetInfo:
    path_0: float
    path_1: float
    t0: float
    duration: float | None = None


class StitchedPulseBuilder:
    """
    The StitchedPulseBuilder can be used to create a StitchedPulse incrementally by
    adding pulse and offset operations.
    """

    def __init__(
        self, port: str | None = None, clock: str | None = None, t0: float = 0.0
    ) -> None:
        """
        Parameters
        ----------
        port : str or None, optional
            Port of the stitched pulse. This can also be added later through
            :meth:`~.set_port`. By default None.
        clock : str or None, optional
            Clock used to modulate the stitched pulse. This can also be added later
            through :meth:`~.set_clock`. By default None.
        t0 : float, optional
            Time in seconds when to start the pulses relative to the start time
            of the Operation in the Schedule. This can also be added later through
            :meth:`~.set_t0`. By default None.
        """
        self._port = port
        self._clock = clock
        self._t0 = t0
        self._pulses: List[Operation] = []
        self._offsets: List[_VoltageOffsetInfo] = []

    def set_port(self, port: str) -> StitchedPulseBuilder:
        """
        Set the port for all parts of the StitchedPulse.

        Parameters
        ----------
        port : str
            Port of the stitched pulse.

        Returns
        -------
        StitchedPulseBuilder
        """
        self._port = port
        return self

    def set_clock(self, clock: str) -> StitchedPulseBuilder:
        """
        Set the clock for all parts of the StitchedPulse.

        Parameters
        ----------
        clock : str
            Clock used to modulate the stitched pulse.

        Returns
        -------
        StitchedPulseBuilder
        """
        self._clock = clock
        return self

    def set_t0(self, t0: float) -> StitchedPulseBuilder:
        """
        Set the start time of the whole StitchedPulse.

        Parameters
        ----------
        t0 : float
            Time in seconds when to start the pulses relative to the start time
            of the Operation in the Schedule.

        Returns
        -------
        StitchedPulseBuilder
        """
        self._t0 = t0
        return self

    def add_pulse(
        self,
        pulse: Operation,
        append: bool = True,
    ) -> StitchedPulseBuilder:
        """
        Add an Operation to the StitchedPulse that is a valid pulse.

        Parameters
        ----------
        pulse : Operation
            The Operation to add.
        append : bool, optional
            Specifies whether to append the operation to the end of the StitchedPulse,
            or to insert it at a time relative to the start of the StitchedPulse,
            specified by the pulse's t0 attribute. By default True.

        Returns
        -------
        StitchedPulseBuilder

        Raises
        ------
        RuntimeError
            If the Operation is not a pulse.
        """
        if pulse.valid_acquisition:
            raise RuntimeError(
                "Cannot add acquisition to StitchedPulse. Please add it directly to "
                "the schedule instead."
            )
        if pulse.valid_gate:
            raise RuntimeError(
                "Cannot add gate to StitchedPulse. Please add it directly to the "
                "schedule instead."
            )
        if len(pulse["logic_info"]) > 0:
            raise RuntimeError(
                "Cannot add logic element to StitchedPulse. Please add it directly to "
                "the schedule instead."
            )
        if pulse.has_voltage_offset:
            raise RuntimeError(
                "Cannot use this method to add a voltage offset. Please use "
                "`add_voltage_offset` instead."
            )

        pulse = deepcopy(pulse)  # we will modify it
        if append:
            for pulse_info in pulse["pulse_info"]:
                pulse_info["t0"] += self.operation_end
        self._pulses.append(pulse)
        return self

    def add_voltage_offset(
        self,
        path_0: float,
        path_1: float,
        duration: float | None = None,
        rel_time: float = 0.0,
        append: bool = True,
        min_duration: float = qblox_constants.GRID_TIME * 1e-9,
    ) -> StitchedPulseBuilder:
        """
        Add a DC voltage offset to the StitchedPulse.

        Parameters
        ----------
        path_0 : float
            The offset on path 0 of the sequencer.
        path_1 : float
            The offset on path 1 of the sequencer.
        duration : float or None, optional
            Specifies how long to maintain the offset. If set to None, the offset
            voltage offset will hold until the end of the StitchedPulse. By default None.
        rel_time : float, optional
            Specifies when to set the offset, relative to the current end of the
            StitchedPulse (if ``append = True``), or to the start of the StitchedPulse
            (if ``append = False``). By default 0.0.
        append : bool, optional
            Specifies whether to append the operation to the end of the StitchedPulse,
            or to insert it at a time relative to the start of the StitchedPulse,
            specified by the the rel_time argument. By default True.
        min_duration : float, optional
            The minimal duration of the voltage offset. By default equal to the grid
            time of Qblox modules.

        Returns
        -------
        StitchedPulseBuilder

        Raises
        ------
        ValueError
            If the duration is not at least ``min_duration``.
        RuntimeError
            If the offset overlaps in time with a previously added offset.
        """
        if append:
            rel_time += self.operation_end

        if duration is not None and duration < min_duration:
            raise ValueError(
                f"Minimum duration of a voltage offset is {min_duration} ns"
            )

        offset = _VoltageOffsetInfo(
            path_0=path_0, path_1=path_1, t0=rel_time, duration=duration
        )
        if self._overlaps_with_existing_offsets(offset):
            raise RuntimeError(
                "Tried to add offset that overlaps with existing offsets in the "
                "StitchedPulse."
            )

        self._offsets.append(offset)
        return self

    @property
    def operation_end(self) -> float:
        max_from_pulses = (
            0.0
            if len(self._pulses) == 0
            else max(
                pulse_info["t0"] + pulse_info["duration"]
                for op in self._pulses
                for pulse_info in op.data["pulse_info"]
            )
        )
        max_from_offsets = (
            0.0
            if len(self._offsets) == 0
            else max(offs.t0 + (offs.duration or 0.0) for offs in self._offsets)
        )
        return max(max_from_pulses, max_from_offsets)

    def _distribute_port_clock(self) -> None:
        if self._port is None:
            raise RuntimeError("No port is defined.")
        if self._clock is None:
            raise RuntimeError("No clock is defined.")
        for op in self._pulses:
            for pulse_info in op.data["pulse_info"]:
                pulse_info["port"] = self._port
                pulse_info["clock"] = self._clock

    def _distribute_t0(self) -> None:
        for op in self._pulses:
            for pulse_info in op.data["pulse_info"]:
                pulse_info["t0"] += self._t0

    def _build_voltage_offset_operations(self) -> List[VoltageOffset]:
        """
        Add offset instructions that reset any offset that had a specified duration.

        If an offset was added without a duration, it is assumed that its duration
        should be until the end of the StitchedPulse, and any following offsets that
        _do_ have a duration will be reset to this value. Otherwise, offsets with a
        duration will be reset to 0.

        At the end of the StitchedPulse, the offset will be reset to 0.

        An offset does not need to be reset, if at the end of its duration, another
        offset instruction starts.
        """
        if len(self._offsets) == 0:
            return []

        def create_operation_from_info(info: _VoltageOffsetInfo) -> VoltageOffset:
            return VoltageOffset(
                offset_path_0=info.path_0,
                offset_path_1=info.path_1,
                duration=info.duration or 0.0,
                port=self._port,
                clock=self._clock,
                t0=info.t0,
            )

        offset_ops: List[VoltageOffset] = []
        offset_infos = sorted(
            self._offsets,
            key=lambda op: op.t0,
        )
        background = (0.0, 0.0)
        for i, offset_info in enumerate(offset_infos):
            offset_ops.append(create_operation_from_info(offset_info))

            if offset_info.duration is None:
                # If no duration was specified, this offset should hold until the end of
                # the StitchedPulse.
                background = (
                    offset_info.path_0,
                    offset_info.path_1,
                )
                continue

            this_end = offset_info.t0 + (offset_info.duration or 0.0)
            if isclose(this_end, self.operation_end):
                background = (0.0, 0.0)
            # Reset if the next offset's start does not overlap with the current
            # offset's end, or if the current offset is the last one
            if i + 1 >= len(self._offsets) or not isclose(
                self._offsets[i + 1].t0, this_end
            ):
                offset_ops.append(
                    create_operation_from_info(
                        _VoltageOffsetInfo(background[0], background[1], t0=this_end)
                    )
                )

        # If this wasn't done yet, add a reset to 0 at the end of the StitchedPulse
        if not (isclose(background[0], 0) and isclose(background[1], 0)):
            offset_ops.append(
                create_operation_from_info(
                    _VoltageOffsetInfo(0.0, 0.0, t0=self.operation_end)
                )
            )

        return offset_ops

    def _overlaps_with_existing_offsets(self, offset: _VoltageOffsetInfo) -> bool:
        offsets = self._offsets[:]
        offsets.append(offset)
        offsets.sort(key=lambda op: op.t0)
        for i, offs in enumerate(offsets[:-1]):
            next_start = offsets[i + 1].t0
            this_end = offs.t0 + (offs.duration or 0.0)
            if next_start < this_end:
                return True
        return False

    def build(self) -> StitchedPulse:
        """
        Build the StitchedPulse.

        Returns
        -------
        StitchedPulse
        """
        offsets = self._build_voltage_offset_operations()
        self._distribute_port_clock()
        self._distribute_t0()
        stitched_pulse = StitchedPulse()
        for op in self._pulses + offsets:
            stitched_pulse.add_pulse(op)
        return stitched_pulse
