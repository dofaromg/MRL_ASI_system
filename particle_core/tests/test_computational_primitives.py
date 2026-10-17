import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from computational_primitives import MatrixOperations


@pytest.mark.parametrize(
    ("matrix", "expected"),
    [
        ([[1, 2, 3], [4, 5, 6]], [[1, 4], [2, 5], [3, 6]]),
        ([[1]], [[1]]),
    ],
)
def test_transpose_accepts_rectangular_matrices(matrix, expected):
    assert MatrixOperations.transpose(matrix) == expected


@pytest.mark.parametrize(
    ("operation", "matrix"),
    [
        (MatrixOperations.transpose, []),
        (MatrixOperations.transpose, [[], []]),
        (MatrixOperations.transpose, [[1, 2], [3]]),
        (MatrixOperations.add, [[1, 2], [3]]),
        (MatrixOperations.multiply, [[1, 2], [3]]),
        (MatrixOperations.determinant, [[1, 2], [3]]),
        (MatrixOperations.determinant, [[1, 2, 3], [4, 5, 6]]),
    ],
)
def test_matrix_operations_reject_malformed_shapes(operation, matrix):
    with pytest.raises(ValueError):
        if operation is MatrixOperations.add:
            operation(matrix, [[1, 2], [3, 4]])
        elif operation is MatrixOperations.multiply:
            operation(matrix, [[1], [2]])
        else:
            operation(matrix)


def test_matrix_addition_rejects_different_shapes():
    with pytest.raises(ValueError, match="dimensions must match"):
        MatrixOperations.add([[1, 2]], [[1], [2]])


def test_matrix_multiplication_rejects_incompatible_shapes():
    with pytest.raises(ValueError, match="Invalid matrix dimensions"):
        MatrixOperations.multiply([[1, 2]], [[1, 2]])


def test_matrix_multiplication_supports_rectangular_matrices():
    assert MatrixOperations.multiply([[1, 2, 3]], [[1], [2], [3]]) == [[14]]
