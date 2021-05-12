# Repository: https://gitlab.com/quantify-os/quantify-scheduler
# Licensed according to the LICENCE file on the master branch
"""Module for handling special pulses that get special treatment in the backend."""

from typing import Optional, Tuple, Callable

import numpy as np

from quantify.scheduler.resources import BasebandClockResource

from quantify.scheduler.helpers.waveforms import (
    exec_waveform_function,
    normalize_waveform_data,
)

from quantify.scheduler.backends.types.qblox import OpInfo
from quantify.scheduler.backends.qblox.constants import PULSE_STITCHING_DURATION


def check_reserved_pulse_id(pulse: OpInfo) -> Optional[str]:
    """
    Checks whether the function should be evaluated generically or has special
    treatment.

    Parameters
    ----------
    pulse
        The pulse to check

    Returns
    -------
        A str with a special identifier representing which pulse behavior to use
    """

    reserved_pulse_mapping = {
        "stitched_square_pulse": _check_square_pulse_stitching,
        "staircase": _check_staircase,
    }
    for key, checking_func in reserved_pulse_mapping.items():
        if checking_func(pulse):
            return key
    return None


def generate_reserved_waveform_data(
    reserved_pulse_id: str, data_dict: dict, sampling_rate: float
) -> np.ndarray:
    func_mapping = {
        "stitched_square_pulse": _stitched_square_pulse_waveform_data,
        "staircase": _staircase_waveform_data,
    }
    func: Callable = func_mapping[reserved_pulse_id]

    return func(data_dict, sampling_rate)


def _check_square_pulse_stitching(pulse: OpInfo) -> bool:
    reserved_wf_func = "quantify.scheduler.waveforms.square"
    if pulse.data["clock"] == BasebandClockResource.IDENTITY:
        return pulse.data["wf_func"] == reserved_wf_func


def _check_staircase(pulse: OpInfo) -> bool:
    reserved_wf_func = "quantify.scheduler.waveforms.staircase"
    if pulse.data["clock"] == BasebandClockResource.IDENTITY:
        return pulse.data["wf_func"] == reserved_wf_func


def _staircase_waveform_data(
    data_dict: dict, sampling_rate: float
) -> Tuple[None, float, float]:
    time_duration = PULSE_STITCHING_DURATION
    t = np.linspace(0, time_duration, int(time_duration * sampling_rate))
    wf_data = exec_waveform_function(data_dict["wf_func"], t, data_dict)
    wf_data, amp_i, amp_q = normalize_waveform_data(wf_data)

    return None, amp_i, amp_q


def _stitched_square_pulse_waveform_data(
    data_dict: dict, sampling_rate: float
) -> Tuple[np.ndarray, float, float]:
    time_duration = PULSE_STITCHING_DURATION
    t = np.linspace(0, time_duration, int(time_duration * sampling_rate))
    wf_data = exec_waveform_function(data_dict["wf_func"], t, data_dict)
    wf_data, amp_i, amp_q = normalize_waveform_data(wf_data)
    if np.sum(wf_data) < 0:
        wf_data, amp_i, amp_q = -wf_data, -amp_i, -amp_q
    return wf_data, amp_i, amp_q
