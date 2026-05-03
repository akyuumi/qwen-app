import unittest

from app.execution_manager import CodeValidationError, validate_python


class ValidatePythonTests(unittest.TestCase):
    def test_allows_simple_python(self) -> None:
        validate_python("print(sum([1, 2, 3]))")

    def test_rejects_empty_code(self) -> None:
        with self.assertRaises(CodeValidationError):
            validate_python("  ")

    def test_rejects_forbidden_import(self) -> None:
        with self.assertRaises(CodeValidationError):
            validate_python("import subprocess\nprint('x')")

    def test_rejects_forbidden_call(self) -> None:
        with self.assertRaises(CodeValidationError):
            validate_python("eval('1 + 1')")

    def test_rejects_forbidden_attribute_call(self) -> None:
        with self.assertRaises(CodeValidationError):
            validate_python("runner.system('echo no')")


if __name__ == "__main__":
    unittest.main()
