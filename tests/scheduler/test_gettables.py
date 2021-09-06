# Repository: https://gitlab.com/quantify-os/quantify-scheduler
# Licensed according to the LICENCE file on the master branch
# pylint: disable=missing-class-docstring
# pylint: disable=missing-function-docstring
# pylint: disable=too-many-locals
# pylint: disable=invalid-name

from collections import namedtuple
from typing import Dict, Tuple, Any
import numpy as np
from qcodes.instrument.parameter import ManualParameter
from quantify_scheduler.compilation import qcompile
from quantify_scheduler.schedules.timedomain_schedules import allxy_sched
from quantify_scheduler.gettables import ScheduleGettableSingleChannel
from quantify_scheduler.helpers.schedule import (
    extract_acquisition_metadata_from_schedule,
)
from quantify_scheduler.types import AcquisitionMetadata

# this is taken from the qblox backend and is used to make the tuple indexing of
# acquisitions more explicit. See also #179 of quantify-scheduler
AcquisitionIndexing = namedtuple("AcquisitionIndexing", "acq_channel acq_index")

# test a batched case
def test_ScheduleGettableSingleChannel_batched_allxy(mock_setup, mocker):
    meas_ctrl = mock_setup["meas_ctrl"]
    quantum_device = mock_setup["quantum_device"]

    qubit = quantum_device.get_component("q0")

    index_par = ManualParameter("index", initial_value=0, unit="#")
    index_par.batched = True

    sched_kwargs = {
        "element_select_idx": index_par,
        "qubit": qubit.name,
        "repetitions": 256,
    }
    indices = np.repeat(np.arange(21), 2)
    # Prepare the mock data the ideal AllXY data

    sched = allxy_sched("q0", element_select_idx=indices, repetitions=256)
    comp_allxy_sched = qcompile(sched, quantum_device.generate_device_config())
    data = (
        np.concatenate(
            (
                0 * np.ones(5 * 2),
                0.5 * np.ones(12 * 2),
                np.ones(4 * 2),
            )
        )
        * np.exp(1j * np.deg2rad(45))
    )

    acq_indices_data = _reshape_array_into_acq_return_type(
        data, extract_acquisition_metadata_from_schedule(comp_allxy_sched)
    )

    mocker.patch.object(
        mock_setup["instrument_coordinator"],
        "retrieve_acquisition",
        return_value=acq_indices_data,
    )

    # Configure the gettable

    allxy_gettable = ScheduleGettableSingleChannel(
        quantum_device=quantum_device,
        schedule_function=allxy_sched,
        schedule_kwargs=sched_kwargs,
        real_imag=True,
        batched=True,
        max_batch_size=1024,
    )

    meas_ctrl.settables(index_par)
    meas_ctrl.setpoints(indices)
    meas_ctrl.gettables([allxy_gettable])
    label = f"AllXY {qubit.name}"
    dset = meas_ctrl.run(label)

    # Assert that the data is coming out correctly.
    np.testing.assert_array_equal(dset.x0, indices)
    np.testing.assert_array_equal(dset.y0 + 1j * dset.y1, data)


# test a batched case


# test an append mode case


# this is probably useful somewhere, it kind of illustrates the weir reshaping in the
# instrument coordinator
def _reshape_array_into_acq_return_type(
    data: np.ndarray, acq_metadata: AcquisitionMetadata
) -> Dict[Tuple[int, int], Any]:
    """
    Takes one ore more complex valued arrays and reshapes the data into a dictionary
    with AcquisitionIndexing
    """

    # Temporary. Will probably be replaced by an xarray object
    # See quantify-core#187, quantify-core#233, quantify-scheduler#36
    acquisitions = dict()

    # if len is 1, we have only 1 channel in the retrieved data
    if len(np.shape(data)) == 0:
        for acq_channel, acq_indices in acq_metadata.acq_indices.items():
            for acq_index in acq_indices:
                acqs = {
                    AcquisitionIndexing(acq_channel, acq_index): (
                        data.real,
                        data.imag,
                    )
                }
                acquisitions.update(acqs)
    elif len(np.shape(data)) == 1:
        for acq_channel, acq_indices in acq_metadata.acq_indices.items():
            for acq_index in acq_indices:
                acqs = {
                    AcquisitionIndexing(acq_channel, acq_index): (
                        data[acq_index].real,
                        data[acq_index].imag,
                    )
                }
                acquisitions.update(acqs)
    else:
        for acq_channel, acq_indices in acq_metadata.acq_indices.items():
            for acq_index in acq_indices:
                acqs = {
                    AcquisitionIndexing(acq_channel, acq_index): (
                        data[acq_channel, acq_index].real,
                        data[acq_channel, acq_index].imag,
                    )
                }
                acquisitions.update(acqs)
    return acquisitions
