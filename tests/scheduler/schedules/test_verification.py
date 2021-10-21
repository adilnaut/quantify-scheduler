# pylint: disable=missing-module-docstring
# pylint: disable=missing-class-docstring
# pylint: disable=missing-function-docstring
# pylint: disable=redefined-outer-name

import pytest
import numpy as np
from numpy.testing import assert_array_equal
from quantify_core.data.handling import set_datadir

from quantify_scheduler.schedules.verification import (
    acquisition_staircase_sched,
    awg_staircase_sched,
)
from quantify_scheduler.schemas.examples.utils import load_json_example_scheme
from quantify_scheduler.compilation import qcompile


@pytest.fixture(scope="module", autouse=False)
def gen_acquisition_staircase_sched(tmp_test_data_dir):

    set_datadir(tmp_test_data_dir)
    sched_kwargs = {
        "readout_pulse_amps": np.linspace(0, 0.5, 11),
        "readout_pulse_duration": 1e-6,
        "readout_frequency": 5e9,
        "acquisition_delay": 4e-9,  # delay of 0 gives an invalid timing error in qblox backend
        "integration_time": 2e-6,
        "port": "q0:res",
        "clock": "q0.ro",
        "init_duration": 10e-6,
        "repetitions": 10,
    }
    sched = acquisition_staircase_sched(**sched_kwargs)
    return sched, sched_kwargs


def test_acquisition_staircase_reps(gen_acquisition_staircase_sched):

    sched, sched_kwargs = gen_acquisition_staircase_sched
    assert sched.repetitions == sched_kwargs["repetitions"]


def test_acquisition_staircase_ops(gen_acquisition_staircase_sched):

    sched, sched_kwargs = gen_acquisition_staircase_sched
    # total number of operations
    assert len(sched.timing_constraints) == 3 * len(sched_kwargs["readout_pulse_amps"])
    # number of unique operations
    assert len(sched.operations) == 2 * len(sched_kwargs["readout_pulse_amps"]) + 1


def test_acquisition_staircase_amps(gen_acquisition_staircase_sched):

    sched, sched_kwargs = gen_acquisition_staircase_sched
    amps = []
    for operation_name, operation in sched.operations.items():
        if "amp" in operation_name:
            amp = operation.data["pulse_info"][0]["amp"]
            amps.append(amp)

    assert_array_equal(np.array(amps), sched_kwargs["readout_pulse_amps"])


def test_acq_staircase_comp_transmon(gen_acquisition_staircase_sched):

    device_cfg = load_json_example_scheme("transmon_test_config.json")
    _ = qcompile(gen_acquisition_staircase_sched[0], device_cfg=device_cfg)


def test_acq_staircase_comp_qblox(gen_acquisition_staircase_sched):

    device_cfg = load_json_example_scheme("transmon_test_config.json")
    hw_cfg = load_json_example_scheme("qblox_test_mapping.json")
    _ = qcompile(
        gen_acquisition_staircase_sched[0],
        device_cfg=device_cfg,
        hardware_mapping=hw_cfg,
    )


def test_acq_staircase_comp_zhinst(gen_acquisition_staircase_sched):

    device_cfg = load_json_example_scheme("transmon_test_config.json")
    hw_cfg = load_json_example_scheme("zhinst_test_mapping.json")
    _ = qcompile(
        gen_acquisition_staircase_sched[0],
        device_cfg=device_cfg,
        hardware_mapping=hw_cfg,
    )


@pytest.fixture(scope="module", autouse=False)
def gen_awg_staircase_sched(tmp_test_data_dir):
    set_datadir(tmp_test_data_dir)

    sched_kwargs = {
        "pulse_amps": np.linspace(0, 0.5, 11),
        "pulse_duration": 1e-6,
        "readout_frequency": 5e9,
        "acquisition_delay": 0,
        "integration_time": 2e-6,
        "mw_port": "q0:mw",
        "ro_port": "q0:res",
        "mw_clock": "q0.01",
        "ro_clock": "q0.ro",
        "init_duration": 10e-6,
        "repetitions": 10,
    }
    sched = awg_staircase_sched(**sched_kwargs)

    return sched, sched_kwargs


def test_awg_staircase_sched(gen_awg_staircase_sched):
    sched, sched_kwargs = gen_awg_staircase_sched
    assert sched.repetitions == sched_kwargs["repetitions"]

    assert len(sched.timing_constraints) == 3 * len(sched_kwargs["pulse_amps"])
    # number of unique operations
    assert len(sched.operations) == 2 * len(sched_kwargs["pulse_amps"]) + 1

    amps = []
    for operation_name, operation in sched.operations.items():
        if "amp" in operation_name:
            amp = operation.data["pulse_info"][0]["amp"]
            amps.append(amp)

    assert_array_equal(np.array(amps), sched_kwargs["pulse_amps"])


def test_awg_staircase_comp_transmon(gen_awg_staircase_sched):

    device_cfg = load_json_example_scheme("transmon_test_config.json")
    _ = qcompile(gen_awg_staircase_sched[0], device_cfg=device_cfg)


def test_awg_staircase_comp_qblox(gen_awg_staircase_sched):

    device_cfg = load_json_example_scheme("transmon_test_config.json")
    hw_cfg = load_json_example_scheme("qblox_test_mapping.json")
    _ = qcompile(
        gen_awg_staircase_sched[0], device_cfg=device_cfg, hardware_mapping=hw_cfg
    )


def test_awg_staircase_comp_zhinst(gen_awg_staircase_sched):

    device_cfg = load_json_example_scheme("transmon_test_config.json")
    hw_cfg = load_json_example_scheme("zhinst_test_mapping.json")
    _ = qcompile(
        gen_awg_staircase_sched[0], device_cfg=device_cfg, hardware_mapping=hw_cfg
    )