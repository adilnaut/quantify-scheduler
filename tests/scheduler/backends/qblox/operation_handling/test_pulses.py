import pytest
import numpy as np

from quantify_scheduler import waveforms

from quantify_scheduler.helpers.waveforms import normalize_waveform_data
from quantify_scheduler.backends.types import qblox as types
from quantify_scheduler.backends.qblox import constants
from quantify_scheduler.backends.qblox.qasm_program import QASMProgram
from quantify_scheduler.backends.qblox.register_manager import RegisterManager
from quantify_scheduler.backends.qblox.operation_handling import pulses


@pytest.fixture(name="empty_qasm_program")
def fixture_empty_qasm_program():
    static_hw_properties = types.StaticHardwareProperties(
        instrument_type="QCM",
        max_sequencers=constants.NUMBER_OF_SEQUENCERS_QCM,
        max_awg_output_voltage=2.5,
        marker_configuration=types.MarkerConfiguration(start=0b1111, end=0b0000),
        mixer_dc_offset_range=types.BoundedParameter(
            min_val=-2.5, max_val=2.5, units="V"
        ),
    )
    yield QASMProgram(static_hw_properties, RegisterManager())


class TestGenericPulseStrategy:
    def test_constructor(self):
        pulses.GenericPulseStrategy(
            types.OpInfo(name="", data={}, timing=0), output_mode="real"
        )

    def test_operation_info_property(self):
        # arrange
        op_info = types.OpInfo(name="", data={}, timing=0)
        strategy = pulses.GenericPulseStrategy(op_info, output_mode="real")

        # act
        from_property = strategy.operation_info

        # assert
        assert op_info == from_property

    @pytest.mark.parametrize(
        "wf_func, wf_func_path, wf_kwargs",
        [
            (
                waveforms.square,
                "quantify_scheduler.waveforms.square",
                {"amp": 1},
            ),
            (
                waveforms.ramp,
                "quantify_scheduler.waveforms.ramp",
                {"amp": 0.1234},
            ),
            (
                waveforms.soft_square,
                "quantify_scheduler.waveforms.soft_square",
                {"amp": -0.1234},
            ),
        ],
    )
    def test_generate_data_real(self, wf_func, wf_func_path, wf_kwargs):
        # arrange
        duration = 24e-9
        data = {"wf_func": wf_func_path, "duration": duration, **wf_kwargs}

        op_info = types.OpInfo(name="", data=data, timing=0)
        strategy = pulses.GenericPulseStrategy(op_info, output_mode="real")
        wf_dict = {}
        t_test = np.linspace(0, duration, int(duration * constants.SAMPLING_RATE))

        # act
        strategy.generate_data(wf_dict=wf_dict)

        # assert
        waveforms_generated = list(wf_dict.values())
        waveform0_data = waveforms_generated[0]["data"]
        waveform1_data = waveforms_generated[1]["data"]
        normalized_data, amp_real, amp_imag = normalize_waveform_data(
            wf_func(t=t_test, **wf_kwargs)
        )
        assert waveform0_data == normalized_data.real.tolist()
        assert waveform1_data == normalized_data.imag.tolist()
        assert strategy.amplitude_path0 == amp_real
        assert strategy.amplitude_path1 == amp_imag

    def test_generate_data_complex(self):
        # arrange
        duration = 24e-9
        data = {
            "wf_func": "quantify_scheduler.waveforms.drag",
            "duration": duration,
            "G_amp": 0.1234,
            "D_amp": 1,
            "nr_sigma": 3,
            "phase": 0,
        }

        op_info = types.OpInfo(name="", data=data, timing=0)
        strategy = pulses.GenericPulseStrategy(op_info, output_mode="complex")
        wf_dict = {}
        t_test = np.linspace(0, duration, int(duration * constants.SAMPLING_RATE))

        # act
        strategy.generate_data(wf_dict=wf_dict)

        # assert
        waveforms_generated = list(wf_dict.values())
        waveform0_data = waveforms_generated[0]["data"]
        waveform1_data = waveforms_generated[1]["data"]
        del data["wf_func"]
        normalized_data, amp_real, amp_imag = normalize_waveform_data(
            waveforms.drag(t=t_test, **data)
        )
        assert waveform0_data == normalized_data.real.tolist()
        assert waveform1_data == normalized_data.imag.tolist()
        assert strategy.amplitude_path0 == amp_real
        assert strategy.amplitude_path1 == amp_imag

    @pytest.mark.parametrize(
        "wf_func, wf_func_path, wf_kwargs",
        [
            (
                waveforms.square,
                "quantify_scheduler.waveforms.square",
                {"amp": 1},
            ),
            (
                waveforms.ramp,
                "quantify_scheduler.waveforms.ramp",
                {"amp": 0.1234},
            ),
            (
                waveforms.soft_square,
                "quantify_scheduler.waveforms.soft_square",
                {"amp": -0.1234},
            ),
        ],
    )
    def test_generate_data_imag(self, wf_func, wf_func_path, wf_kwargs):
        # arrange
        duration = 24e-9
        data = {"wf_func": wf_func_path, "duration": duration, **wf_kwargs}

        op_info = types.OpInfo(name="", data=data, timing=0)
        strategy = pulses.GenericPulseStrategy(op_info, output_mode="imag")
        wf_dict = {}
        t_test = np.arange(0, duration, step=1e-9)

        # act
        strategy.generate_data(wf_dict=wf_dict)

        # assert
        waveforms_generated = list(wf_dict.values())
        waveform0_data = waveforms_generated[0]["data"]
        waveform1_data = waveforms_generated[1]["data"]
        normalized_data, amp_real, amp_imag = normalize_waveform_data(
            wf_func(t=t_test, **wf_kwargs)
        )
        assert waveform0_data == normalized_data.real.tolist()
        assert waveform1_data == normalized_data.imag.tolist()
        assert strategy.amplitude_path0 == amp_imag
        assert strategy.amplitude_path1 == amp_real

    @pytest.mark.parametrize(
        "output_mode",
        ["real", "imag"],
    )
    def test_exception_wrong_mode(self, output_mode):
        # arrange
        duration = 24e-9
        data = {
            "wf_func": "quantify_scheduler.waveforms.drag",
            "duration": duration,
            "G_amp": 0.1234,
            "D_amp": 1,
            "nr_sigma": 3,
            "phase": 0,
        }

        op_info = types.OpInfo(name="test_pulse_name", data=data, timing=0)
        strategy = pulses.GenericPulseStrategy(op_info, output_mode=output_mode)
        wf_dict = {}

        # act
        with pytest.raises(ValueError) as error:
            strategy.generate_data(wf_dict=wf_dict)

        # assert
        assert (
            error.value.args[0]
            == 'Complex valued Pulse "test_pulse_name" (t0=0, duration=2.4e-08) '
            "detected but the sequencer is not expecting complex input. This "
            "can be caused by attempting to play complex valued waveforms on "
            "an output marked as real.\n\nException caused by Pulse "
            "test_pulse_name (t=0 to 2.4e-08)\ndata={'wf_func': "
            "'quantify_scheduler.waveforms.drag', 'duration': 2.4e-08, '"
            "G_amp': 0.1234, 'D_amp': 1, 'nr_sigma': 3, 'phase': 0}."
        )

    def test_insert_qasm(self, empty_qasm_program):
        # arrange
        qasm = empty_qasm_program
        duration = 24e-9
        wf_func_path, wf_kwargs = ("quantify_scheduler.waveforms.square", {"amp": 1})
        data = {"wf_func": wf_func_path, "duration": duration, **wf_kwargs}

        op_info = types.OpInfo(name="test_pulse", data=data, timing=0)
        strategy = pulses.GenericPulseStrategy(op_info, output_mode="real")
        strategy.generate_data(wf_dict={})

        # act
        strategy.insert_qasm(qasm)

        # assert
        line0 = ["", "set_awg_gain", "13107,0", "# setting gain for test_pulse"]
        line1 = ["", "play", "0,1,4", "# play test_pulse (24 ns)"]
        assert qasm.instructions[0] == line0
        assert qasm.instructions[1] == line1


class TestStitchedSquarePulseStrategy:
    def test_constructor(self):
        pulses.StitchedSquarePulseStrategy(
            types.OpInfo(name="", data={}, timing=0), output_mode="real"
        )

    def test_operation_info_property(self):
        # arrange
        op_info = types.OpInfo(name="", data={}, timing=0)
        strategy = pulses.StitchedSquarePulseStrategy(op_info, output_mode="real")

        # act
        from_property = strategy.operation_info

        # assert
        assert op_info == from_property

    @pytest.mark.parametrize("duration", [400e-9, 1e-6, 1e-3])
    def test_generate_data(self, duration):
        # arrange
        num_samples = int(constants.PULSE_STITCHING_DURATION * constants.SAMPLING_RATE)
        op_info = types.OpInfo(name="", data={"amp": 0.4}, timing=0)
        strategy = pulses.StitchedSquarePulseStrategy(op_info, output_mode="complex")

        wf_dict = {}

        # act
        strategy.generate_data(wf_dict)

        # assert
        waveforms_generated = list(wf_dict.values())
        waveform0_data = waveforms_generated[0]["data"]
        waveform1_data = waveforms_generated[1]["data"]

        answer_path0 = np.ones(num_samples).tolist()
        answer_path1 = np.zeros(num_samples).tolist()
        assert waveform0_data == answer_path0
        assert waveform1_data == answer_path1

    @pytest.mark.parametrize(
        "duration, output_mode",
        [
            (400e-9, "real"),
            (1e-6, "real"),
            (1e-3, "real"),
            (400e-9, "imag"),
            (1e-6, "imag"),
            (1e-3, "imag"),
        ],
    )
    def test_generate_data_real_or_imag(self, duration, output_mode):
        # arrange
        num_samples = int(constants.PULSE_STITCHING_DURATION * constants.SAMPLING_RATE)
        op_info = types.OpInfo(name="", data={"amp": 0.4}, timing=0)
        strategy = pulses.StitchedSquarePulseStrategy(op_info, output_mode=output_mode)

        wf_dict = {}

        # act
        strategy.generate_data(wf_dict)

        # assert
        waveforms_generated = list(wf_dict.values())
        waveform0_data = waveforms_generated[0]["data"]

        answer_path0 = np.ones(num_samples).tolist()
        assert waveform0_data == answer_path0
        assert len(waveforms_generated) == 1

    @pytest.mark.parametrize(
        "duration, answer",
        [
            (
                400e-9,
                [
                    ["", "set_awg_gain", "13107,0", "# setting gain for test_pulse"],
                    ["", "play", "0,1,400", ""],
                    ["", "set_awg_gain", "0,0", "# set to 0 at end of pulse"],
                ],
            ),
            (
                1e-6,
                [
                    ["", "set_awg_gain", "13107,0", "# setting gain for test_pulse"],
                    ["", "play", "0,1,1000", ""],
                    ["", "set_awg_gain", "0,0", "# set to 0 at end of pulse"],
                ],
            ),
            (
                1.2e-6,
                [
                    ["", "set_awg_gain", "13107,0", "# setting gain for test_pulse"],
                    ["", "play", "0,1,1000", ""],
                    ["", "play", "0,1,200", ""],
                    ["", "set_awg_gain", "0,0", "# set to 0 at end of pulse"],
                ],
            ),
            (
                2e-6,
                [
                    ["", "set_awg_gain", "13107,0", "# setting gain for test_pulse"],
                    ["", "move", "2,R0", "# iterator for loop with label stitch1"],
                    ["stitch1:", "", "", ""],
                    ["", "play", "0,1,1000", ""],
                    ["", "loop", "R0,@stitch1", ""],
                ],
            ),
            (
                2.4e-6,
                [
                    ["", "set_awg_gain", "13107,0", "# setting gain for test_pulse"],
                    ["", "move", "2,R0", "# iterator for loop with label stitch1"],
                    ["stitch1:", "", "", ""],
                    ["", "play", "0,1,1000", ""],
                    ["", "loop", "R0,@stitch1", ""],
                    ["", "play", "0,1,400", ""],
                    ["", "set_awg_gain", "0,0", "# set to 0 at end of pulse"],
                ],
            ),
            (
                1e-3,
                [
                    ["", "set_awg_gain", "13107,0", "# setting gain for test_pulse"],
                    ["", "move", "1000,R0", "# iterator for loop with label stitch1"],
                    ["stitch1:", "", "", ""],
                    ["", "play", "0,1,1000", ""],
                    ["", "loop", "R0,@stitch1", ""],
                ],
            ),
        ],
    )
    def test_insert_qasm(self, empty_qasm_program, duration, answer):
        # arrange
        qasm = empty_qasm_program
        wf_func_path, wf_kwargs = ("quantify_scheduler.waveforms.square", {"amp": 1})
        data = {"wf_func": wf_func_path, "duration": duration, **wf_kwargs}

        op_info = types.OpInfo(name="test_pulse", data=data, timing=0)
        strategy = pulses.StitchedSquarePulseStrategy(op_info, output_mode="complex")
        strategy.generate_data(wf_dict={})

        # act
        strategy.insert_qasm(qasm)

        # assert
        for row_idx, instruction in enumerate(qasm.instructions):
            assert instruction == answer[row_idx]
