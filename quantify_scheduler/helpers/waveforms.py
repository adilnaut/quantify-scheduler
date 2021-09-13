# Repository: https://gitlab.com/quantify-os/quantify-scheduler
# Licensed according to the LICENCE file on the master branch
from __future__ import annotations

import inspect
from functools import partial
from typing import Any, Dict, List, Tuple
from abc import ABC

try:
    from typing import Protocol as _Protocol
except ImportError:
    Protocol = ABC
else:
    Protocol = _Protocol

import numpy as np
import quantify_core.utilities.general as general

import quantify_scheduler.waveforms as waveforms
from quantify_scheduler.helpers import schedule as schedule_helpers
from quantify_scheduler import math
from quantify_scheduler import types

# pylint: disable=too-few-public-methods
class GetWaveformPartial(Protocol):  # typing.Protocol
    """
    Protocol type definition class for the get_waveform
    partial function.
    """

    def __call__(self, sampling_rate: int) -> np.ndarray:
        """
        Execute partial get_waveform function.

        Parameters
        ----------
        sampling_rate
            The waveform sampling rate.

        Returns
        -------
        :
            The waveform array.
        """


def get_waveform_size(waveform: np.ndarray, granularity: int) -> int:
    """
    Returns the number of samples required to
    respect the granularity.

    Parameters
    ----------
    waveform

    granularity

    """
    size: int = len(waveform)
    if size % granularity != 0:
        size = math.closest_number_ceil(size, granularity)

    return max(size, granularity)


def resize_waveforms(waveforms_dict: Dict[int, np.ndarray], granularity: int) -> None:
    """
    Resizes the waveforms to a multiple of the given
    granularity.

    Parameters
    ----------
    waveforms_dict
        The waveforms dictionary.
    granularity
        The granularity.
    """
    # Modify the list while iterating to avoid copies
    for pulse_id in waveforms_dict:
        waveforms_dict[pulse_id] = resize_waveform(
            waveforms_dict[pulse_id], granularity
        )


def resize_waveform(waveform: np.ndarray, granularity: int) -> np.ndarray:
    """
    Returns the waveform in a size that is a modulo of the given granularity.

    Parameters
    ----------
    waveform
        The waveform array.
    granularity
        The waveform granularity.

    Returns
    -------
    :
        The resized waveform with a length equal to
        `mod(len(waveform), granularity) == 0`.
    """
    size: int = len(waveform)
    if size == 0:
        return np.zeros(granularity)

    if size % granularity == 0:
        return waveform

    remainder = math.closest_number_ceil(size, granularity) - size

    # Append the waveform with the remainder zeros
    return np.concatenate([waveform, np.zeros(remainder)])


def shift_waveform(
    waveform: np.ndarray, start_in_seconds: float, clock_rate: int, resolution: int
) -> Tuple[int, np.ndarray]:
    """
    Returns the waveform shifted with a number of samples
    to compensate for rounding errors that cause misalignment
    of the waveform in the clock time domain.

    Note: when using this method be sure that the pulse starts
    at a `round(start_in_clocks)`.

    .. code-block::

        waveform = np.ones(32)
        clock_rate = int(2.4e9)
        resolution: int = 8

        t0: float = 16e-9
        #                 4.8 = 16e-9 / (8 / 2.4e9)
        start_in_clocks = (t0 // (resolution / clock_rate))

        start_waveform_at_clock(start_in_clocks, waveform)

    Parameters
    ----------
    waveform
    start_in_seconds
    clock_rate
    resolution
        The sequencer resolution.
    """

    start_in_clocks = round(start_in_seconds * clock_rate)
    samples_shift = start_in_clocks % resolution
    start_in_lowres_clock = start_in_clocks // resolution

    if samples_shift == 0:
        return start_in_lowres_clock, waveform

    return start_in_lowres_clock, np.concatenate([np.zeros(samples_shift), waveform])


def get_waveform(
    pulse_info: Dict[str, Any],
    sampling_rate: int,
) -> np.ndarray:
    """
    Returns the waveform of a pulse_info dictionary.

    Parameters
    ----------
    pulse_info
        The pulse_info dictionary.
    sampling_rate
        The sample rate of the waveform.

    Returns
    -------
    :
        The waveform.
    """
    t: np.ndarray = np.arange(0, 0 + pulse_info["duration"], 1 / sampling_rate)
    wf_func: str = pulse_info["wf_func"]
    waveform: np.ndarray = exec_waveform_function(wf_func, t, pulse_info)

    return waveform


def get_waveform_by_pulseid(
    schedule: types.Schedule,
) -> Dict[int, GetWaveformPartial]:
    """
    Returns a lookup dictionary of pulse_id and
    respectively its partial waveform function.

    The keys are pulse info ids while the values are partial functions. Executing
    the waveform will return a :class:`numpy.ndarray`.

    Parameters
    ----------
    schedule
        The schedule.
    """
    pulseid_waveformfn_dict: Dict[int, GetWaveformPartial] = dict()
    for t_constr in schedule.timing_constraints:
        operation = schedule.operations[t_constr["operation_repr"]]
        for pulse_info in operation["pulse_info"]:
            pulse_id = schedule_helpers.get_pulse_uuid(pulse_info)
            if pulse_id in pulseid_waveformfn_dict:
                # Unique waveform already populated in the dictionary.
                continue

            pulseid_waveformfn_dict[pulse_id] = partial(
                get_waveform, pulse_info=pulse_info
            )

        for acq_info in operation["acquisition_info"]:
            for pulse_info in acq_info["waveforms"]:
                pulse_id = schedule_helpers.get_pulse_uuid(pulse_info)
                pulseid_waveformfn_dict[pulse_id] = partial(
                    get_waveform, pulse_info=pulse_info
                )

    return pulseid_waveformfn_dict


def exec_waveform_partial(
    pulse_id: int,
    pulseid_waveformfn_dict: Dict[int, GetWaveformPartial],
    sampling_rate: int,
) -> np.ndarray:
    """
    Returns the result of the partial waveform function.

    Parameters
    ----------
    pulse_id
        The pulse uuid.
    pulseid_waveformfn_dict
        The partial waveform lookup dictionary.
    sampling_rate
        The sampling rate.

    Returns
    -------
    :
        The waveform array.
    """
    # Execute partial function get_waveform that already has
    # 'pulse_info' assigned. The following method execution
    # adds the missing required parameters.
    waveform_fn: GetWaveformPartial = pulseid_waveformfn_dict[pulse_id]
    waveform: np.ndarray = waveform_fn(
        sampling_rate=sampling_rate,
    )

    return waveform


def exec_waveform_function(wf_func: str, t: np.ndarray, pulse_info: dict) -> np.ndarray:
    """
    Returns the result of the pulse's waveform function.

    If the wf_func is defined outside quantify-scheduler then the
    wf_func is dynamically loaded and executed using
    :func:`~quantify_scheduler.helpers.waveforms.exec_custom_waveform_function`.

    Parameters
    ----------
    wf_func
        The custom waveform function path.
    t
        The linear timespace.
    pulse_info
        The dictionary containing pulse information.

    Returns
    -------
    :
        Returns the computed waveform.
    """
    whitelist: List[str] = ["square", "ramp", "soft_square", "drag"]
    fn_name: str = wf_func.split(".")[-1]
    waveform: np.ndarray = []
    if wf_func.startswith("quantify_scheduler.waveforms") and fn_name in whitelist:
        if fn_name == "square":
            waveform = waveforms.square(t=t, amp=pulse_info["amp"])
        elif fn_name == "ramp":
            waveform = waveforms.ramp(t=t, amp=pulse_info["amp"])
        elif fn_name == "soft_square":
            waveform = waveforms.soft_square(t=t, amp=pulse_info["amp"])
        elif fn_name == "drag":
            waveform = waveforms.drag(
                t=t,
                G_amp=pulse_info["G_amp"],
                D_amp=pulse_info["D_amp"],
                duration=pulse_info["duration"],
                nr_sigma=pulse_info["nr_sigma"],
                phase=pulse_info["phase"],
            )
    else:
        waveform = exec_custom_waveform_function(wf_func, t, pulse_info)

    return waveform


def exec_custom_waveform_function(
    wf_func: str, t: np.ndarray, pulse_info: dict
) -> np.ndarray:
    """
    Load and import an ambiguous waveform function from a module by string.

    The parameters of the dynamically loaded wf_func are extracted using
    :func:`inspect.signature` while the values are extracted from the
    pulse_info dictionary.

    Parameters
    ----------
    wf_func
        The custom waveform function path.
    t
        The linear timespace.
    pulse_info
        The dictionary containing pulse information.

    Returns
    -------
    :
        Returns the computed waveform.
    """
    # Load the waveform function from string
    function = general.import_func_from_string(wf_func)

    # select the arguments for the waveform function that are present
    # in pulse info
    par_map = inspect.signature(function).parameters
    wf_kwargs = {}
    for kw in par_map.keys():
        if kw in pulse_info:
            wf_kwargs[kw] = pulse_info[kw]

    # Calculate the numerical waveform using the wf_func
    return function(t=t, **wf_kwargs)


def apply_mixer_skewness_corrections(
    waveform: np.ndarray, amplitude_ratio: float, phase_shift: float
) -> np.ndarray:
    r"""
    Takes a waveform and applies a correction for amplitude imbalances and
    phase errors when using an IQ mixer from previously calibrated values.

    Phase correction is done using:

    .. math::

        Re(z_{corrected}) (t) = Re(z (t)) + Im(z (t)) \tan(\phi)
        Im(z_{corrected}) (t) = Im(z (t)) / \cos(\phi)

    The amplitude correction is achieved by rescaling the waveforms back to their
    original amplitudes and multiplying or dividing the I and Q signals respectively by
    the square root of the amplitude ratio.

    Parameters
    ----------
    waveform:
        The complex valued waveform on which the correction will be applied.
    amplitude_ratio:
        The ratio between the amplitudes of I and Q that is used to correct
        for amplitude imbalances between the different paths in the IQ mixer.
    phase_shift:
        The phase error (in deg) used to correct the phase between I and Q.

    Returns
    -------
    :
        The complex valued waveform with the applied phase and amplitude
        corrections.
    """

    def skew_real(_waveform: np.ndarray, alpha: float, phi: float):
        original_amp = np.max(np.abs(_waveform.real))
        intermediate_wf = _waveform.real + _waveform.imag * np.tan(phi)
        new_amp = np.max(np.abs(intermediate_wf))
        intermediate_wf = (
            intermediate_wf / new_amp
            if new_amp != 0
            else np.zeros(intermediate_wf.shape)
        )
        return intermediate_wf * original_amp * np.sqrt(alpha)

    def skew_imag(_waveform: np.ndarray, alpha: float, phi: float):
        original_amp = np.max(np.abs(_waveform.imag))
        intermediate_wf = _waveform.imag / np.cos(phi)
        new_amp = np.max(np.abs(intermediate_wf))
        intermediate_wf = (
            intermediate_wf / new_amp
            if new_amp != 0
            else np.zeros(intermediate_wf.shape)
        )
        return intermediate_wf * original_amp / np.sqrt(alpha)

    corrected_re = skew_real(waveform, amplitude_ratio, np.deg2rad(phase_shift))
    corrected_im = skew_imag(waveform, amplitude_ratio, np.deg2rad(phase_shift))

    return corrected_re + 1.0j * corrected_im


def modulate_waveform(
    t: np.ndarray, envelope: np.ndarray, freq: float, t0: float = 0
) -> np.ndarray:
    r"""
    Generates a (single sideband) modulated waveform from a given envelope by
    multiplying it with a complex exponential.

    .. math::

        z_{mod} (t) = z (t) \cdot e^{2\pi i f (t+t_0)}

    The signs are chosen such that the frequencies follow the relation RF = LO + IF for
    LO, IF > 0.

    Parameters
    ----------
    t
        A numpy array with time values
    envelope
        The complex-valued envelope of the modulated waveform
    freq
        The frequency of the modulation
    t0
        Time offset for the modulation

    Returns
    -------
    :
        The modulated waveform
    """
    modulation = np.exp(1.0j * 2 * np.pi * freq * (t + t0))
    return envelope * modulation


def normalize_waveform_data(data: np.ndarray) -> Tuple[np.ndarray, float, float]:
    """
    Rescales the waveform data so that the maximum amplitude is abs(amp) == 1.

    Parameters
    ----------
    data
        The waveform data to rescale.

    Returns
    -------
    rescaled_data
        The rescaled data.
    amp_real
        The original amplitude of the real part.
    amp_imag
        The original amplitude of the imaginary part.
    """
    amp_real, amp_imag = np.max(np.abs(data.real)), np.max(np.abs(data.imag))
    norm_data_re = (
        data.real / amp_real if amp_real != 0.0 else np.zeros(data.real.shape)
    )
    norm_data_im = (
        data.imag / amp_imag if amp_imag != 0.0 else np.zeros(data.imag.shape)
    )
    rescaled_data = norm_data_re + 1.0j * norm_data_im
    return rescaled_data, amp_real, amp_imag


def area_pulses(pulses: List[Dict[str, Any]], sampling_rate: int) -> float:
    """
    Calculates the area of a set of pulses.

    Parameters
    ----------
    pulses
        List of dictinary with information of the pulses
    sampling_rate
        Sampling rate for the pulse

    Returns
    -------
    :
        The area formed by all the pulses
    """
    area: float = 0.0
    for pulse in pulses:
        area += area_pulse(pulse, sampling_rate)
    return area


def area_pulse(pulse: Dict[str, Any], sampling_rate: int) -> float:
    """
    Calculates the area of a set of pulses.

    Parameters
    ----------
    pulse
        The dictionary with information of the pulse
    sampling_rate
        Sampling rate for the pulse

    Returns
    -------

    :
        The area defined by the pulse
    """
    assert sampling_rate > 0
    waveform: np.ndarray = get_waveform(pulse, sampling_rate)
    # Nice to have: Give the user the option to choose integration algorithm
    return waveform.sum() / sampling_rate
