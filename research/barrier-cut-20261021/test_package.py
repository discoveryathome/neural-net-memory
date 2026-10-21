"""The seeded selection and the auxiliary witness must not change challenge identity."""
import copy
from pathlib import Path
import sys
import unittest

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(HERE))
from verifier import Invalid, load, verify
import verify_result


class PackageTests(unittest.TestCase):
    def test_selection_reproduces_and_wrong_row_is_rejected(self):
        self.assertTrue(hasattr(verify_result, 'validate_selection'))
        task = load(HERE / 'TASK.json')
        verify_result.validate_selection(task, ROOT)
        for key, value in (('selected_budget', 0), ('graph', 'mlp-b8'),
                           ('seed', '0' * 32), ('starting_peak_bytes', 2359296),
                           ('graph_path', '../outside.json')):
            bad = copy.deepcopy(task)
            bad[key] = value
            with self.assertRaises(Invalid):
                verify_result.validate_selection(bad, ROOT)

    def test_auxiliary_witness_is_not_a_selected_budget_result(self):
        g = load(ROOT / 'benchmarks/graphs/transformer-b4-t128.json')
        c = load(HERE / 'certificates/auxiliary-budget.json')
        with self.assertRaisesRegex(Invalid, 'challenge budget mismatch'):
            verify(g, c, 956301312)
        c['budget'] = 956301312
        with self.assertRaisesRegex(Invalid, 'recomputation budget exceeded'):
            verify(g, c, 956301312)


if __name__ == '__main__':
    unittest.main()
