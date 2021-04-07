# -----------------------------------------------------------------------------
# Description:    Tests for Zurich Instruments backend.
# Repository:     https://gitlab.com/quantify-os/quantify-scheduler
# Copyright (C) Qblox BV & Orange Quantum Systems Holding BV (2020-2021)
# -----------------------------------------------------------------------------
from textwrap import dedent

import pytest

from quantify.scheduler.backends.zhinst.seqc_il_generator import (
    SEQC_INSTR_CLOCKS,
    SeqcILGenerator,
    SeqcInstructions,
    add_wait,
)


def test___declare_local():
    # Arrange
    gen = SeqcILGenerator()

    # Act
    gen._declare_local("wave", "w0")

    with pytest.raises(ValueError) as execinfo:
        gen._declare_local("wave", "w0")

    # Assert
    assert "Duplicate local variable 'w0'!" == str(execinfo.value)
    assert gen._variables["w0"] == ("wave w0", None)


def test___assign_local():
    # Arrange
    gen = SeqcILGenerator()

    # Act
    with pytest.raises(ValueError) as execinfo:
        gen._assign_local("w0", "custom_wave")

    gen.declare_wave("w0")
    gen._assign_local("w0", "custom_wave")

    # Assert
    assert "Undefined reference 'w0'!" == str(execinfo.value)
    assert gen._variables["w0"] == ("wave w0", "custom_wave")


def test__scope():
    # Arrange
    gen = SeqcILGenerator()

    # Act
    level0 = gen._level
    gen._begin_scope()
    level1 = gen._level

    gen._begin_scope()
    level2 = gen._level

    gen._end_scope()
    level3 = gen._level

    gen._end_scope()
    level4 = gen._level

    with pytest.raises(ValueError) as execinfo:
        gen._end_scope()

    # Assert
    assert level0 == 0
    assert level1 == 1
    assert level2 == 2
    assert level3 == 1
    assert level4 == 0
    assert "SeqcILGenerator scope level is to low!" == str(execinfo.value)


def test_declare_var_and_assign():
    # Arrange
    gen = SeqcILGenerator()
    name: str = "foo"
    value: int = 1

    # Act
    gen.declare_var(name, value)

    # Assert
    assert gen._variables[name] == (f"var {name}", f"{value};")


def test_declare_wave_and_assign():
    # Arrange
    gen = SeqcILGenerator()
    name: str = "foo"
    value: str = "dev_1234_wave0"

    # Act
    gen.declare_wave(name, value)

    # Assert
    assert gen._variables[name] == (f"wave {name}", f'"{value}";')


@pytest.mark.parametrize(
    "index,expected",
    [
        (0, "waitDigTrigger(1);"),
        (1, "waitDigTrigger(1, 1);"),
    ],
)
def test_emit_wait_dig_trigger(index: int, expected: str):
    # Arrange
    gen = SeqcILGenerator()

    # Act
    gen.emit_wait_dig_trigger(index)

    # Assert
    assert gen._program[-1] == (0, expected)


def test__generate():
    # Arrange
    gen = SeqcILGenerator()

    # Act
    gen.declare_var("__repetitions__")
    gen.assign_get_user_reg("__repetitions__", 0)

    custom_wave = "custom_wave"
    gen.declare_wave("w0")
    gen.assign_var("w0", custom_wave)

    command_table_index = 0
    gen.declare_wave("w1")
    gen.assign_placeholder("w1", size=48)
    gen.emit_assign_wave_index("w1", "w1", index=command_table_index)

    gen.emit_set_trigger(0)
    gen.emit_begin_repeat("__repetitions__")

    gen.emit_set_trigger("AWG_MARKER0 + AWG_MARKER1")

    gen.emit_start_qa_monitor()
    gen.emit_start_qa_result("0b0000000001", "AWG_INTEGRATION_TRIGGER")

    gen.emit_execute_table_entry(index=command_table_index)
    gen.emit_play_wave("w0")
    gen.emit_wait(0)

    gen.emit_end_repeat()

    gen.emit_begin_while()
    gen.emit_set_trigger(0)
    gen.emit_end_while()

    # Assert
    expected = dedent(
        """
    // Generated by quantify-scheduler.
    // Variables
    var __repetitions__ = getUserReg(0);
    wave w0 = "custom_wave";
    wave w1 = placeholder(48);

    // Operations
    assignWaveIndex(w1, w1, 0);
    setTrigger(0);
    repeat(__repetitions__)
    {
      setTrigger(AWG_MARKER0 + AWG_MARKER1);
      startQAMonitor();
      startQAResult(0b0000000001, AWG_INTEGRATION_TRIGGER);
      executeTableEntry(0);
      playWave(w0);
      wait(0);
    }
    while(true)
    {
      setTrigger(0);
    }
    """
    ).lstrip("\n")
    program = gen.generate()
    assert program == expected


def test_generate_uninitalized_var():
    # Arrange
    gen = SeqcILGenerator()
    expected = dedent(
        """
    // Generated by quantify-scheduler.
    // Variables
    var empty_var;
    """
    ).lstrip("\n")

    # Act
    gen.declare_var("empty_var")

    # Assert
    program = gen.generate()
    assert program == expected


@pytest.mark.parametrize(
    "delay,expected_wait,expected_elapsed",
    [
        (0, 0, SEQC_INSTR_CLOCKS[SeqcInstructions.WAIT]),
        (3, 0, 3),
        (6, 3, 6),
    ],
)
def test_add_wait(delay: int, expected_wait: int, expected_elapsed: int):
    # Arrange
    gen = SeqcILGenerator()
    if delay - SEQC_INSTR_CLOCKS[SeqcInstructions.WAIT] < 0:
        expected_instruction = f"wait({expected_wait});\t//  n_instr=3 <--"
    else:
        expected_instruction = f"wait({expected_wait});\t//  n_instr=3"

    # Act
    elapsed_clocks = add_wait(gen, delay)

    # Assert
    assert elapsed_clocks == expected_elapsed
    assert gen._program[-1] == (0, expected_instruction)
