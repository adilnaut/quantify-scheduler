# Repository: https://gitlab.com/quantify-os/quantify-scheduler
# Licensed according to the LICENCE file on the master branch
"""Helpers for Zurich Instruments."""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Union

import numpy as np
from zhinst import qcodes

from quantify.scheduler.backends.types import zhinst as types

logger = logging.getLogger()


def get_value(instrument: qcodes.ZIBaseInstrument, node: str) -> str:
    """
    Gets the value of a ZI node.

    Parameters
    ----------
    instrument :
    node :

    Returns
    -------
    str
        The node value.
    """
    path = f"/{instrument._serial}/{node}"
    logger.debug(path)
    return instrument._controller._get(path)


def set_value(
    instrument: qcodes.ZIBaseInstrument,
    node: str,
    value,
) -> None:
    """
    Sets the value of a ZI node.

    Parameters
    ----------
    instrument :
        The instrument.
    path :
        The node path.
    value :
        The new node value.
    """
    path = f"/{instrument._serial}/{node}"
    logger.debug(path)
    instrument._controller._set(path, value)


def set_vector(
    instrument: qcodes.ZIBaseInstrument,
    node: str,
    vector: Union[List, str],
) -> None:
    """
    Sets the vector value of a ZI node.

    Parameters
    ----------
    instrument :
        The instrument.
    node :
        The node path.
    vector :
        The new node vector value.
    """
    path = f"/{instrument._serial}/{node}"
    logger.debug(path)
    instrument._controller._controller._connection._daq.setVector(path, vector)


def set_wave_vector(
    instrument: qcodes.ZIBaseInstrument,
    awg_index: int,
    wave_index: int,
    vector: Union[List, str],
) -> None:
    """
    Sets the command table wave vector for an awg of an instrument.

    Parameters
    ----------
    instrument :
        The instrument.
    awg_index :
        The index of an AWG
    wave_index :
        The wave index.
    vector :
        The vector value.
    """
    path: str = f"awgs/{awg_index:d}/waveform/waves/{wave_index:d}"
    set_vector(instrument, path, vector)


def set_commandtable_data(
    instrument: qcodes.ZIBaseInstrument,
    awg_index: int,
    json_data: Union[Dict[str, Any], str],
) -> None:
    """
    Sets the commandtable JSON for an AWG.

    Parameters
    ----------
    instrument :
        The instrument
    awg_index :
        The awg index.
    json_data :
        The json data.
    """
    if not isinstance(json_data, str):
        json_data = json.dumps(json_data)

    path = f"awgs/{awg_index:d}/commandtable/data"
    set_vector(instrument, path, str(json_data))


def get_directory(awg: qcodes.hdawg.AWG) -> Path:
    """
    Returns the LabOne directory of an AWG.

    Parameters
    ----------
    awg :
        The HDAWG AWG object.

    Returns
    -------
    Path
        The path of this directory.
    """
    return Path(awg._awg._module.get_string("directory"))


def get_src_directory(awg: qcodes.hdawg.AWG) -> Path:
    """
    Returns the source directory of an AWG.

    Parameters
    ----------
    awg :
        The HDAWG AWG object.

    Returns
    -------
    Path
        The path to the source directory.
    """
    return get_directory(awg).joinpath("awg", "src")


def get_waves_directory(awg: qcodes.hdawg.AWG) -> Path:
    """
    Returns the waves directory of an AWG.

    Parameters
    ----------
    awg :
        The HDAWG AWG object.

    Returns
    -------
    Path
        The path to the waves directory.
    """
    return get_directory(awg).joinpath("awg", "waves")


def get_clock_rate(device_type: types.DeviceType) -> int:
    """
    Returns the clock rate of a Device.

    Parameters
    ----------
    device_type :
        The type of device.

    Returns
    -------
    int
        The number of clocks (GSa/s).
    """
    # clock_rate = awg._awg.sequence_params["sequence_parameters"]["clock_rate"]
    clock_rate = 0
    if device_type == types.DeviceType.HDAWG:
        clock_rate = 2400000000  # 2.4e9 GSa/s
    elif device_type == types.DeviceType.UHFQA:
        clock_rate = 1800000000  # 1.8e9 GSa/s
    return clock_rate


def write_seqc_file(awg: qcodes.hdawg.AWG, contents: str, filename: str) -> Path:
    """
    Writes the contents of to the source directory
    of LabOne.

    Parameters
    ----------
    awg :
        The HDAWG AWG instance.
    contents :
        The content to write.
    filename :
        The name of the file.

    Returns
    -------
    Path
        Returns the path which was written.
    """
    path = get_src_directory(awg).joinpath(filename)
    path.write_text(contents)

    return path


def get_commandtable_map(
    pulse_ids: List[int], pulseid_pulseinfo_dict: Dict[int, Dict[str, Any]]
) -> Dict[int, int]:
    """
    Returns a dictionary that contains the locations of
    pulses in the AWG waveform table.

    Parameters
    ----------
    pulse_ids :
        The list of pulse ids.
    pulseid_pulseinfo_dict :
        The info lookup dictionary.

    Returns
    -------
    Dict[int, int]
        The command table map.
    """
    commandtable_map: Dict[int, int] = dict()
    index = 0
    for pulse_id in pulse_ids:
        if pulse_id in commandtable_map:
            # Skip duplicate pulses.
            continue

        pulse_info = pulseid_pulseinfo_dict[pulse_id]
        if pulse_info["port"] is None:
            # Skip pulses without a port. Such as the IdlePulse.
            continue

        commandtable_map[pulse_id] = index
        index += 1

    return commandtable_map


def set_qas_parameters(
    instrument: qcodes.ZIBaseInstrument,
    integration_length: int,
    mode: types.QAS_IntegrationMode = types.QAS_IntegrationMode.NORMAL,
    delay: int = 0,
):
    assert integration_length <= 4096

    node = "qas/0/integration/length"
    set_value(instrument, node, integration_length)

    node = "qas/0/integration/mode"
    set_value(instrument, node, mode.value)

    node = "qas/0/delay"
    set_value(instrument, node, delay)


def set_integration_weights(
    instrument: qcodes.ZIBaseInstrument,
    channel_index: int,
    weights_i: List[int],
    weights_q: List[int],
):
    assert channel_index < 10
    assert len(weights_i) <= 4096
    assert len(weights_q) <= 4096

    node = "qas/0/integration/weights/"

    set_vector(instrument, f"{node}{channel_index}/real", np.array(weights_i))
    set_vector(instrument, f"{node}{channel_index}/imag", np.array(weights_q))


def get_readout_channel_bitmask(readout_channels_count: int) -> str:
    """
    Returns a bitmask to enable readout channels.
    The bitmask can be used to turn on QA for
    induvidual channels in startQAResult.

    Parameters
    ----------
    readout_channels_count :
        The amount of readout channels to enable.
        Maximum readout channels for UHFQA is 10.

    Returns
    -------
    str
        The channel bitmask.
    """
    assert readout_channels_count <= 10

    mask: int = 0
    for i in range(readout_channels_count):
        mask += 1 << i

    bitmask = format(mask, "b").zfill(10)

    return f"0b{bitmask}"