import os
from ._julia_project import project
project.ensure_init()

Main = project.simple_import("Main")
QuantumOps = project.simple_import("QuantumOps")
QiskitQuantumInfo = project.simple_import("QiskitQuantumInfo")

# import julia
# from julia import QuantumOps
# from julia import QiskitQuantumInfo
# from julia import Main

from qiskit.quantum_info import Pauli, SparsePauliOp, PauliList


def jlPauli(data):
    """
    Convert a QiskitQuantumInfo.Pauli to a qiskit.quantum_info.Pauli
    """
    if isinstance(data, str):
        data = QiskitQuantumInfo.Pauli(data)
    return Pauli((data.x, data.z, data.phase))


def jlPauliList(pauli_list):
    """
    Convert a QiskitQuantumInfo.PauliList to a qiskit.quantum_info.PauliList
    """
    return PauliList.from_symplectic(pauli_list.z, pauli_list.x)


def jlSparsePauliOp(sp):
    pl = PauliList.from_symplectic(sp.pauli_list.z, sp.pauli_list.x)
    return SparsePauliOp(pl, sp.coeffs)


def PauliSum_to_SparsePauliOp(ps):
    """
    Convert a QuantumOps.PauliSum to a qiskit.quantum_info.SparsePauliOp
    """
    spop_jl = QiskitQuantumInfo.SparsePauliOp(ps) # Convert to QiskitQuantumInfo.SparsePauliOp
    spop = jlSparsePauliOp(spop_jl)  # Convert to qisit.quantum_info.SparsePauliOp
    return spop
