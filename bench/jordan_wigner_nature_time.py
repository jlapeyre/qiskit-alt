# Benchmark qiskit-nature peforming the Jordan-Wigner transform on a Fermi operator.
import timeit

def make_setup_code(basis, geometry):
    return f"""
from qiskit_nature.drivers import UnitsType, Molecule
from qiskit_nature.drivers.second_quantization import ElectronicStructureDriverType, ElectronicStructureMoleculeDriver

h2_geometry = [['H', [0., 0., 0.]],
            ['H', [0., 0., 0.735]]]

h2o_geometry = [['O', [0., 0., 0.]],
            ['H', [0.757, 0.586, 0.]],
            ['H', [-0.757, 0.586, 0.]]]

basis = {basis}

molecule = Molecule(geometry={geometry},
                     charge=0, multiplicity=1)
driver = ElectronicStructureMoleculeDriver(molecule, basis=basis, driver_type=ElectronicStructureDriverType.PYSCF)

from qiskit_nature.problems.second_quantization import ElectronicStructureProblem
from qiskit_nature.converters.second_quantization import QubitConverter
from qiskit_nature.mappers.second_quantization import JordanWignerMapper

es_problem = ElectronicStructureProblem(driver)
second_q_op = es_problem.second_q_ops()

qubit_converter = QubitConverter(mapper=JordanWignerMapper())

hamiltonian = second_q_op[0]
"""

def run_one_basis(basis, geometry, num_repetitions):
    setup_code = make_setup_code(basis, geometry)
    bench_code = "qubit_converter.convert(hamiltonian)"
    time = timeit.timeit(stmt=bench_code, setup=setup_code, number=num_repetitions)
    t = 1000 * time / num_repetitions
    print(f"geometry={geometry}, basis={basis} {t:0.2f}", "ms")
    return t

nature_times = []

for basis, geometry, num_repetitions in (("'sto3g'", "h2_geometry", 10), ("'631g'", "h2_geometry", 10),
                                         ("'631++g'", "h2_geometry", 5),
                                         ("'sto3g'", "h2o_geometry", 5), ("'631g'", "h2o_geometry", 1)):
    t = run_one_basis(basis, geometry, num_repetitions)
    nature_times.append(t)
