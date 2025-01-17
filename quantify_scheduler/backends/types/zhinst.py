# Repository: https://gitlab.com/quantify-os/quantify-scheduler
# Licensed according to the LICENCE file on the main branch
"""Python dataclasses for quantify-scheduler json-schemas."""
from dataclasses import dataclass, field
from enum import Enum, unique
from typing import Dict, List, Literal, Optional, Union

from pydantic.v1 import Field, validator
from typing_extensions import Annotated

from quantify_scheduler.backends.types import common
from quantify_scheduler.structure.model import DataStructure


@unique
class DeviceType(str, Enum):
    """Enum of device types."""

    HDAWG = "HDAWG"
    UHFQA = "UHFQA"
    UHFLI = "UHFLI"
    MFLI = "MFLI"
    PQSC = "PQSC"
    NONE = "none"


@unique
class ModulationModeType(str, Enum):

    """
    The modulation mode enum type.

    Used to set the modulation type to

    1. no modulation. ('none')
    2. Software premodulation applied in the numerical waveforms. ('premod')
    3. Hardware real-time modulation. ('modulate')

    See also :class:`~quantify_scheduler.backends.types.zhinst.Modulation` for the use.
    """

    NONE = "none"
    PREMODULATE = "premod"
    MODULATE = "modulate"


@unique
class SignalModeType(str, Enum):

    """
    The signal output enum type.

    Used to set the output signal type to a
    modulated or real respectively.
    """

    COMPLEX = "complex"
    REAL = "real"


@unique
class ReferenceSourceType(str, Enum):

    """
    The reference source enum type.

    Used to set the source trigger type to
    internal or external respectively.
    """

    NONE = "none"
    INTERNAL = "int"
    EXTERNAL = "ext"


@unique
class InstrumentOperationMode(str, Enum):
    """
    The InstrumentOperationMode enum defines in what operational mode an instrument is
    in.

    OPERATING mode sets the Instrument in its default operation mode.
    CALIBRATING mode sets the Instrument in calibration mode in which for example the
    numeric pulses generated by a backend for an AWG are set to np.ones.
    """

    OPERATING = "operate"
    CALIBRATING = "calibrate"


class Modulation(DataStructure):
    """The backend Modulation record type."""

    type: ModulationModeType = ModulationModeType.NONE
    """
    The modulation mode type select. Allows
    to choose between. (default = ModulationModeType.NONE)

    1. no modulation. ('none')
    2. Software premodulation applied in the numerical waveforms. ('premod')
    3. Hardware real-time modulation. ('modulate')
    """
    interm_freq: float = 0.0
    """The inter-modulation frequency (IF) in Hz. (default = 0.0)."""
    phase_shift: float = 0.0
    """The IQ modulation phase shift in Degrees. (default = 0.0)."""


class LocalOscillator(DataStructure):
    """The backend LocalOscillator record type."""

    unique_name: str
    """The unique name identifying the combination of instrument and channel/parameters."""
    instrument_name: str
    """The QCodes name of the LocalOscillator."""
    generic_icc_name: Optional[str] = None
    """The name of the GenericInstrumentCoordinatorComponent attached to this device."""
    frequency: Optional[dict] = None
    """A dict which tells the generic icc what parameter maps to the local oscillator (LO) frequency in Hz."""
    frequency_param: Optional[str] = None
    """The parameter on the LO instrument used to control the frequency."""
    power: Optional[dict] = None
    """A dict which tells the generic icc what parameter maps to the local oscillator (LO) power in dBm."""
    phase: Optional[dict] = None
    """A dict which tells the generic icc what parameter maps to the local oscillator (LO) phase in radians."""
    parameters: Optional[dict] = None
    """
    A dict which allows setting of channel specific parameters of the device. Cannot
    be used together with frequency and power.
    """


class Output(DataStructure):
    """
    The definition class for zhinst channel properties.

    This class maps to the zhinst backend JSON "channel"
    properties defined in the hardware mapping.
    """

    port: str
    """The port resource."""
    clock: str
    """The Clock resource."""
    mode: SignalModeType
    """The output mode type."""
    modulation: Modulation
    """The modulation settings."""
    local_oscillator: str
    """The LocalOscillator name."""
    clock_frequency: Optional[float] = None
    """The frequency for the clock resource (AKA RF/signal frequency)."""
    gain1: int = 0
    """The output1 IQ modulation gain. Accepted value between -1 and + 1. (default = 1.0)"""
    gain2: int = 0
    """The output2 IQ modulation gain. Accepted value between -1 and + 1. (default = 1.0)"""
    trigger: Optional[int] = None
    """
    The ZI Instrument input trigger. (default = None)
    Setting this will declare the device secondary.
    """
    markers: List[Union[str, int]] = []
    """The ZI Instrument output triggers. (default = [])"""
    mixer_corrections: Optional[common.MixerCorrections] = None
    """The output mixer corrections."""

    @validator("mixer_corrections", pre=True, always=True)
    def decapitalize_dc_mixer_offsets(cls, v):
        """
        Decapitalize the DC mixer offsets.

        This is required because the old-style hardare config used capitalized
        keys for the DC mixer offsets, while the new-style hardware config uses
        lower-case keys.
        """
        if isinstance(v, dict):
            if "dc_offset_I" in v:
                v["dc_offset_i"] = v.pop("dc_offset_I")
            if "dc_offset_Q" in v:
                v["dc_offset_q"] = v.pop("dc_offset_Q")
        return v


class Device(DataStructure):
    """
    The device definition class for zhinst devices.

    This class maps to the zhinst backend JSON "devices"
    properties defined in the hardware mapping.
    """

    name: str
    """The QCodes Instrument name."""
    type: str
    """The instrument model type. For example, 'UHFQA', 'HDAWG4', 'HDAWG8'."""
    ref: ReferenceSourceType
    """The reference source type."""
    channel_0: Output
    """The first physical channel properties."""
    channel_1: Optional[Output] = None
    """The second physical channel properties."""
    channel_2: Optional[Output] = None
    """The third physical channel properties."""
    channel_3: Optional[Output] = None
    """The fourth physical channel properties."""
    channels: Optional[List[Output]]
    """The list of channels. (auto generated)"""
    clock_select: Optional[int] = 0
    """
    The clock rate divisor which will be used to get
    the instruments clock rate from the lookup dictionary in
    quantify_scheduler.backends.zhinst_backend.DEVICE_CLOCK_RATES.

    For information see zhinst User manuals, section /DEV..../AWGS/n/TIME
    Examples: base sampling rate (1.8 GHz) divided by 2^clock_select. (default = 0)
    """
    channelgrouping: int = 0
    """
    The HDAWG channelgrouping property. (default = 0) corresponding to a single
    sequencer controlling a pair (2) awg outputs.
    """
    mode: InstrumentOperationMode = InstrumentOperationMode.OPERATING
    """
    The Instruments operation mode.
    (default = zhinst.InstrumentOperationMode.OPERATING)
    """
    device_type: DeviceType = DeviceType.NONE
    """
    The Zurich Instruments hardware type. (default = DeviceType.NONE)
    This field is automatically populated.
    """
    sample_rate: Optional[int]
    """
    The Instruments sampling clock rate.
    This field is automatically populated.
    """
    n_channels: Optional[int]
    """
    The number of physical channels of this ZI Instrument.
    This field is automatically populated.
    """

    @validator("channels", pre=True, always=True)
    def generate_channel_list(cls, v, values):
        if v is not None:
            raise ValueError(
                f"Trying to set 'channels' to {v}, while it is an auto-generated field."
            )
        v = [values["channel_0"]]
        if values["channel_1"] is not None:
            v.append(values["channel_1"])
        if values["channel_2"] is not None:
            v.append(values["channel_2"])
        if values["channel_3"] is not None:
            v.append(values["channel_3"])
        return v

    @validator("n_channels", pre=True, always=True)
    def calculate_n_channels(cls, v, values):
        if v is not None:
            raise ValueError(
                f"Trying to set 'n_channels' to {v}, while it is an auto-generated field."
            )
        if values["type"][-1].isdigit():
            digit = int(values["type"][-1])
            v = digit
        else:
            v = 1
        return v

    @validator("device_type", pre=True, always=True)
    def determine_device_type(cls, v, values):
        if v is not DeviceType.NONE:
            raise ValueError(
                f"Trying to set 'device_type' to {v}, while it is an auto-generated field."
            )
        if values["type"][-1].isdigit():
            v = DeviceType(values["type"][:-1])
        else:
            v = DeviceType(values["type"])
        return v


class CommandTableHeader(DataStructure):
    """
    The CommandTable header definition.
    """

    version: str = "0.2"
    partial: bool = False


class CommandTableEntryValue(DataStructure):
    """
    A CommandTable entry definition with a value.
    """

    value: int


class CommandTableWaveform(DataStructure):
    """
    The command table waveform properties.
    """

    index: int
    length: int


class CommandTableEntry(DataStructure):
    """
    The definition of a single CommandTable entry.
    """

    index: int
    waveform: "CommandTableWaveform"


class CommandTable(DataStructure):
    """
    The CommandTable definition for ZI HDAWG.
    """

    header: Optional["CommandTableHeader"]
    table: List["CommandTableEntry"]

    @validator("header", pre=True, always=True)
    def generate_command_table_header(cls, v, values):
        if v is not None:
            raise ValueError(
                f"Trying to set 'header' to {v}, while it is an auto-generated field."
            )
        return CommandTableHeader()


@unique
class QasIntegrationMode(Enum):
    """
    Operation mode of all weighted integration units.

    NORMAL: Normal mode. The integration weights are given
    by the user-programmed filter memory.

    SPECTROSCOPY:  Spectroscopy mode. The integration weights
    are generated by a digital oscillator. This mode offers
    enhanced frequency resolution.
    """

    NORMAL = 0
    SPECTROSCOPY = 1


@unique
class QasResultMode(Enum):
    """UHFQA QAS result mode."""

    CYCLIC = 0
    SEQUENTIAL = 1


@unique
class QasResultSource(Enum):
    """UHFQA QAS result source."""

    CROSSTALK = 0
    THRESHOLD = 1
    ROTATION = 3
    CROSSTALK_CORRELATION = 4
    THRESHOLD_CORRELATION = 5
    INTEGRATION = 7


class WaveformDestination(Enum):
    """The waveform destination enum type."""

    CSV = 0
    WAVEFORM_TABLE = 1


@dataclass
class InstrumentInfo:
    """Instrument information record type."""

    sample_rate: int

    num_samples_per_clock: int  # number of samples per clock cycle (sequencer_rate)
    granularity: int  # waveforms need to be a multiple of this many samples.
    mode: InstrumentOperationMode = InstrumentOperationMode.OPERATING
    sequencer_rate: float = field(init=False)

    def __post_init__(self):
        """Initializes fields after initializing object."""
        self.sequencer_rate = self.num_samples_per_clock / self.sample_rate


@dataclass(frozen=True)
class Instruction:
    """Sequence base instruction record type."""

    waveform_id: str
    abs_time: float
    clock_cycle_start: int

    duration: float

    @staticmethod
    def default():
        """
        Returns a default Instruction instance.

        Returns
        -------
        Instruction :
        """
        return Instruction("None", 0, 0, 0)


@dataclass(frozen=True)
class Acquisition(Instruction):
    """
    This instruction indicates that an acquisition is to be triggered in the UHFQA.
    If a waveform_id is specified, this waveform will be used as the integration weight.
    """

    def __repr__(self):
        return (
            f"Acquisition(waveform_id: {self.waveform_id}"
            f"|abs_time: {self.abs_time * 1e9} ns"
            f"|dt: {self.duration * 1e9} ns"
            f"|c0: {self.clock_cycle_start}"
        )


@dataclass(frozen=True)
class Wave(Instruction):
    """
    This instruction indicates that a waveform  should be played.
    """

    def __repr__(self):
        return (
            f"Wave(waveform_id: {self.waveform_id}"
            f"|abs_time: {self.abs_time * 1e9} ns"
            f"|dt: {self.duration * 1e9} ns"
            f"|c0: {self.clock_cycle_start}"
        )


class ZIChannelDescription(DataStructure):
    """
    Information needed to specify a ZI Channel in the :class:`~.CompilationConfig`.

    A single 'channel' represents a complex output, consisting of two physical I/O channels on
    the Instrument.
    """

    mode: Union[Literal["real"], Literal["complex"]]
    """The output mode type."""
    markers: List[str] = []
    """
    Property that specifies which markers to trigger on each sequencer iteration.
    The values are used as input for the `setTrigger` sequencer instruction.
    """
    trigger: Optional[int]
    """
    The `trigger` property specifies for a sequencer which digital trigger to wait for.
    This value is used as the input parameter for the `waitDigTrigger` sequencer instruction.
    Setting this will declare the device secondary.
    """


class ZIBaseDescription(common.HardwareDescription):
    """Base class for a Zurich Instrument hardware description."""

    ref: Union[Literal["int"], Literal["ext"], None]
    """
    Property that describes if the instrument uses Markers or Triggers.
    - `int` Enables sending Marker
    - `ext` Enables waiting for Marker
    - `none` Ignores waiting for Marker
    """


class ZIHDAWG4Description(ZIBaseDescription):
    """Information needed to specify a HDAWG4 in the :class:`~.CompilationConfig`."""

    instrument_type: Literal["HDAWG4"]
    """The instrument type, used to select this datastructure when parsing a :class:`~.CompilationConfig`."""
    channelgrouping: int
    """
    The HDAWG channelgrouping property impacting the amount of HDAWG channels per AWG
    that must be used.. (default = 0) corresponding to a single sequencer controlling 
    a pair (2) awg outputs.
    """
    clock_select: int
    """
    The clock rate divisor which will be used to get
    the instruments clock rate from the lookup dictionary in
    quantify_scheduler.backends.zhinst_backend.DEVICE_CLOCK_RATES.

    For information see zhinst User manuals, section /DEV..../AWGS/n/TIME
    Examples: base sampling rate (1.8 GHz) divided by 2^clock_select. (default = 0)
    """
    channel_0: Optional[ZIChannelDescription]
    """Description of the first channel on this HDAWG (corresponding to 1 or 2 physical output ports)."""
    channel_1: Optional[ZIChannelDescription]
    """Description of the second channel on this HDAWG (corresponding to 1 or 2 physical output ports)."""


class ZIHDAWG8Description(ZIHDAWG4Description):
    """Information needed to specify a HDAWG8 in the :class:`~.CompilationConfig`."""

    instrument_type: Literal["HDAWG8"]
    """The instrument type, used to select this datastructure when parsing a :class:`~.CompilationConfig`."""
    channel_2: Optional[ZIChannelDescription]
    """Description of the third channel on this HDAWG (corresponding to 1 or 2 physical output ports)."""
    channel_3: Optional[ZIChannelDescription]
    """Description of the fourth channel on this HDAWG (corresponding to 1 or 2 physical output ports)."""


class ZIUHFQADescription(ZIBaseDescription):
    """Information needed to specify a UHFQA in the :class:`~.CompilationConfig`."""

    instrument_type: Literal["UHFQA"]
    """The instrument type, used to select this datastructure when parsing a :class:`~.CompilationConfig`."""
    channel_0: Optional[ZIChannelDescription]
    """Description of the readout channel on this UHFQA."""


ZIHardwareDescription = Annotated[
    Union[
        ZIHDAWG4Description,
        ZIHDAWG8Description,
        ZIUHFQADescription,
        common.LocalOscillatorDescription,
    ],
    Field(discriminator="instrument_type"),
]
"""
Specifies a piece of Zurich Instruments hardware and its instrument-specific settings.

Currently, the supported instrument types are:
:class:`~.ZIHDAWG4Description`,
:class:`~.ZIHDAWG8Description`,
:class:`~.ZIUHFQADescription`
"""


class OutputGain(DataStructure):
    """
    Gain settings for a port-clock combination.

    These gain values will be set on each control-hardware output
    port that is used for this port-clock combination.

    .. admonition:: Example
        :class: dropdown

        .. code-block:: python

            hardware_compilation_config.hardware_options.gain = {
                "q0:res-q0.ro": Gain(
                    output_1 = 1,
                    output_2 = 1
                ),
            }
    """

    gain_I: float = 0
    """The output 1 IQ modulation gain. Accepted value between -1 and + 1. (default = 1.0)."""
    gain_Q: float = 0
    """The output 2 IQ modulation gain. Accepted value between -1 and + 1. (default = 1.0)."""


class ZIHardwareOptions(common.HardwareOptions):
    """
    Datastructure containing the hardware options for each port-clock combination.

    .. admonition:: Example
        :class: dropdown

        Here, the HardwareOptions datastructure is created by parsing a
        dictionary containing the relevant information.

        .. jupyter-execute::

            import pprint
            from quantify_scheduler.schemas.examples.utils import (
                load_json_example_scheme
            )

        .. jupyter-execute::

            from quantify_scheduler.backends.types.zhinst import (
                ZIHardwareOptions
            )
            zi_hw_options_dict = load_json_example_scheme(
                "zhinst_hardware_compilation_config.json")["hardware_options"]
            pprint.pprint(zi_hw_options_dict)
            zi_hw_options = ZIHardwareOptions.parse_obj(zi_hw_options_dict)
            zi_hw_options
    """

    output_gain: Optional[Dict[str, OutputGain]]
    """
    Dictionary containing the gain settings (values) that should be applied
    to the outputs that are connected to a certain port-clock combination (keys).
    """
