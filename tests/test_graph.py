import unittest
from mock import patch
from mock import Mock
from threaded_order.graph import DAGraph, log_candidates

class TestDAGraph(unittest.TestCase):

    def setUp(self):
        self.graph = DAGraph()
        self.graph.add('a')
        self.graph.add('b')
        self.graph.add('c', after=['a'])
        self.graph.add('d', after=['a'])
        self.graph.add('e', after=['b'])
        self.graph.add('f', after=['d', 'e'])
    
    def test_add_Should_RaiseValueError_When_ParentAlreadyAdded(self, *patches):
        with self.assertRaises(ValueError):
            self.graph.add('a')
    
    def test_add_Should_RaiseValueError_When_DependsOnUnknown(self, *patches):
        with self.assertRaises(ValueError):
            self.graph.add('g', after=['h'])

    @patch('threaded_order.graph.DAGraph._has_cycle', return_value=True)
    def test_add_Should_RaiseValueError_When_CreatesCycle(self, *patches):
        with self.assertRaises(ValueError) as error:
            self.graph.add('g', after=['f'])
        self.assertEqual(str(error.exception), 'adding g will create a cycle')

    def test_remove(self, *patches):
        self.assertIn('c', self.graph.children_of('a'))
        self.assertIn('d', self.graph.children_of('a'))
        self.graph.remove('a')
        self.assertNotIn('a', self.graph.nodes())
        self.assertTrue(self.graph.children_of('a') == [])
        self.assertTrue(self.graph.parents_of('c') == [])
        self.assertTrue(self.graph.parents_of('d') == [])

    def test_remove_partial(self, *patches):
        g = DAGraph()
        g._children['a'] = ('b',)
        g._parents['b'] = []
        g.remove('a')
        self.assertNotIn('a', g.nodes())

    def test_is_empty(self, *patches):
        self.assertFalse(self.graph.is_empty())
        self.graph.remove('a')
        self.graph.remove('b')
        self.graph.remove('c')
        self.graph.remove('d')
        self.graph.remove('e')
        self.graph.remove('f')
        self.assertTrue(self.graph.is_empty())

    def test_ready_When_ActiveNodes(self, *patches):
        ready_nodes = self.graph.ready()
        self.assertEqual(set(ready_nodes), {'a', 'b'})
        ready_nodes = self.graph.ready(active=['a'])
        self.assertEqual(set(ready_nodes), {'b'})
        ready_nodes = self.graph.ready(active=['a', 'b'])
        self.assertEqual(set(ready_nodes), set([]))

    def test_get_candidates(self, *patches):
        candidates = self.graph.get_candidates(['a'], 2)
        self.assertEqual(candidates, ['b'])
        candidates = self.graph.get_candidates(['a', 'b'], 4, sort=True)
        self.assertEqual(candidates, [])

    @patch('builtins.print')
    def test_repr(self, *patches):
        print(repr(self.graph))
        self.assertEqual(set(self.graph.original_parents_of('f')), set(['d', 'e']))

    @patch('threaded_order.graph.logging')
    def test_log_candidates_When_NoCandidates(self, logging_patch, *patches):
        logger_mock = Mock()
        logging_patch.getLogger.return_value = logger_mock
        log_candidates([], 3)
        logger_mock.debug.assert_called_with('requested 3 but found no candidates eligible for submission')

    @patch('threaded_order.graph.logging')
    def test_log_candidates_When_Candidates(self, logging_patch, *patches):
        logger_mock = Mock()
        logging_patch.getLogger.return_value = logger_mock
        log_candidates(['a', 'b'], 3)
        logger_mock.debug.assert_called_with('requested 3 and found 2 candidates eligible for submission a, b')

    @patch('threaded_order.graph.logging')
    def test_log_candidates_When_SingleCandidate(self, logging_patch, *patches):
        logger_mock = Mock()
        logging_patch.getLogger.return_value = logger_mock
        log_candidates(['a'], 3)
        logger_mock.debug.assert_called_with('requested 3 and found 1 candidate eligible for submission a')

    def test_has_cycle_returns_false_for_acyclic_graph(self):
        g = DAGraph()
        # A -> B -> C (meaning: A depends on B, B depends on C)
        g._parents = {
            'A': ['B'],
            'B': ['C'],
            'C': [],
        }
        self.assertFalse(g._has_cycle())

    def test_has_cycle_returns_true_for_simple_cycle(self):
        g = DAGraph()
        # A <-> B cycle
        g._parents = {
            'A': ['B'],
            'B': ['A'],
        }
        self.assertTrue(g._has_cycle())

    def test_has_cycle_returns_true_for_self_loop(self):
        g = DAGraph()
        # A depends on itself
        g._parents = {
            'A': ['A'],
        }
        self.assertTrue(g._has_cycle())

    def test_has_cycle_returns_true_for_cycle_in_subgraph(self):
        g = DAGraph()
        # Component 1 (acyclic): X -> Y
        # Component 2 (cyclic):  A -> B -> C -> A
        g._parents = {
            'X': ['Y'],
            'Y': [],
            'A': ['B'],
            'B': ['C'],
            'C': ['A'],
        }
        self.assertTrue(g._has_cycle())
