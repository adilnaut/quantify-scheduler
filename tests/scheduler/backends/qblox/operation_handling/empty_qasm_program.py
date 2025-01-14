"""Empty QASM program fixture."""
import pytest

from quantify_scheduler.backends.qblox.instrument_compilers import QcmModule
from quantify_scheduler.backends.qblox.qasm_program import QASMProgram
from quantify_scheduler.backends.qblox.register_manager import RegisterManager


@pytest.fixture(name="empty_qasm_program_qcm")
def fixture_empty_qasm_program():
    """Empty QASMProgram object."""
    yield QASMProgram(
        static_hw_properties=QcmModule.static_hw_properties,
        register_manager=RegisterManager(),
        align_fields=True,
    )
