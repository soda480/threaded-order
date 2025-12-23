import os
import sys
import queue
import unittest
import argparse
from unittest.mock import patch
from unittest.mock import call
from unittest.mock import Mock
from threaded_order.scheduler import Scheduler, dmark, mark

class TestScheduler(unittest.TestCase):

    @patch('threaded_order.scheduler.configure_logging')
    def test_init_setup_logging(self, configure_logging_patch, *patches):
        Scheduler(setup_logging=True)
        configure_logging_patch.assert_called_once()

    def test_register_ValueError(self, *patches):
        s = Scheduler(workers=2)
        with self.assertRaises(ValueError):
            s.register('not_callable', 'not_callable')

    def test_register(self, *patches):
        s = Scheduler(workers=2)

        def sample_task():
            pass

        s.register(sample_task, 'task1')
        self.assertIn('task1', s._callables)
        self.assertIn('task1', s.graph.nodes())

    @patch('threaded_order.scheduler.Scheduler.register')
    def test_dregister_with_state(self, register_patch, *patches):
        mock_function = Mock(__name__='mock_function')
        s = Scheduler()
        decorated_function = s.dregister(with_state=True)(mock_function)
        result = decorated_function()
        register_patch.assert_called_once_with(decorated_function, 'mock_function', after=None, with_state=True)
        self.assertEqual(decorated_function.__original__, mock_function)
        self.assertEqual(result, mock_function.return_value)

    @patch('threaded_order.scheduler.Scheduler.register')
    def test_dregister_defaults(self, register_patch, *patches):
        mock_function = Mock(__name__ = 'mock_function2')
        s = Scheduler()
        decorated_function = s.dregister()(mock_function)
        register_patch.assert_called_once_with(decorated_function, 'mock_function2', after=None, with_state=False)
        self.assertEqual(decorated_function.__original__, mock_function)

    @patch('threaded_order.scheduler.Scheduler.register')
    def test_dregister_with_after(self, register_patch, *patches):
        mock_function = Mock(__name__ = 'mock_function3')
        s = Scheduler()
        decorated_function = s.dregister(after=['dep1'], with_state=True)(mock_function)
        register_patch.assert_called_once_with(decorated_function, 'mock_function3', after=['dep1'], with_state=True)
        self.assertEqual(decorated_function.__original__, mock_function)

    @patch('threaded_order.scheduler.Scheduler._submit')
    def test_maybe_schedule_next_NoFree(self, submit_patch, *patches):
        s = Scheduler(workers=1)
        s._active.add('task')
        s._maybe_schedule_next(Mock())
        self.assertEqual(len(s._active), 1)
        submit_patch.assert_not_called()

    @patch('threaded_order.scheduler.Scheduler._submit')
    def test_maybe_schedule_next_When_NoSkip(self, submit_patch, *patches):
        s = Scheduler(workers=2)
        graph_mock = Mock()
        graph_mock.get_candidates.return_value = ['task1', 'task2']
        s._graph = graph_mock
        s._maybe_schedule_next(Mock())
        submit_patch.assert_has_calls([call('task1'), call('task2')])

    @patch('threaded_order.scheduler.Scheduler._submit')
    def test_maybe_schedule_next_WhenSkip(self, submit_patch,*patches):
        s = Scheduler(workers=2, skip_dependents=True)
        s._failed.append('task1')
        graph_mock = Mock()
        graph_mock.get_candidates.return_value = ['task3', 'task4']
        # original parent of task3 and task4 are task1 and task2 respectively
        # task1 failed, so task3 should be skipped
        # task4 should be scheduled
        graph_mock.original_parents_of.side_effect = [['task1'], ['task2']]
        s._graph = graph_mock
        s._maybe_schedule_next(Mock())
        s._submit.assert_has_calls([call('task4')])

    @patch('threaded_order.scheduler.Scheduler._maybe_schedule_next')
    @patch('threaded_order.scheduler.Scheduler._callback')
    def test_handle_done_When_Ok(self, callback_patch, *patches):
        s = Scheduler()
        graph_mock = Mock()
        graph_mock.is_empty.return_value = False
        s._graph = graph_mock
        function_mock = Mock()
        s.on_task_done(function_mock)
        mock_payload = ('task1', True, '', '')
        s._handle_done(mock_payload, Mock())
        callback_patch.assert_called_once_with((function_mock, (), {}), 'task1', True)

    @patch('threaded_order.scheduler.Scheduler._maybe_schedule_next')
    @patch('threaded_order.scheduler.Scheduler._callback')
    def test_handle_done_When_NotOkDependencyError(self, callback_patch, *patches):
        s = Scheduler()
        graph_mock = Mock()
        graph_mock.is_empty.return_value = True
        s._graph = graph_mock
        function_mock = Mock()
        s.on_task_done(function_mock)
        mock_payload = ('task1', False, 'DependencyError', 'DependencyError')
        s._handle_done(mock_payload, Mock())
        callback_patch.assert_called_once_with((function_mock, (), {}), 'task1', False)
        self.assertIn('task1', s._skipped)

    @patch('threaded_order.scheduler.Scheduler._callback')
    def test_handle_event_When_Start(self, callback_patch, *patches):
        s = Scheduler()
        function_mock = Mock()
        s.on_task_start(function_mock)
        with patch.object(s, '_events') as events_patch:
            events_patch.get_nowait.side_effect = [('start', 'task1'), queue.Empty()]
            s._handle_event()
            callback_patch.assert_called_once_with((function_mock, (), {}), 'task1')

    @patch('threaded_order.scheduler.Scheduler._callback')
    def test_handle_event_When_Run(self, callback_patch, *patches):
        s = Scheduler()
        function_mock = Mock()
        s.on_task_run(function_mock)
        with patch.object(s, '_events') as events_patch:
            events_patch.get_nowait.side_effect = [('run', ('task1', 'thread1')), queue.Empty()]
            s._handle_event()
            callback_patch.assert_called_once_with((function_mock, (), {}), 'task1', 'thread1')

    @patch('threaded_order.scheduler.logging.getLogger')
    @patch('threaded_order.scheduler.Scheduler._handle_done')
    def test_handle_event_When_Done(self, handle_done_patch, get_logger_patch, *patches):
        s = Scheduler()
        function_mock = Mock()
        s.on_task_done(function_mock)
        with patch.object(s, '_events') as events_patch:
            events_patch.get_nowait.side_effect = [('done', ('task1', True, '', '')), queue.Empty()]
            s._handle_event()
            handle_done_patch.assert_called_once_with(('task1', True, '', ''), get_logger_patch.return_value)

    def test_build_summary(self, *patches):
        s = Scheduler()
        s._build_summary()

    def test_handle_interrupt(self, *patches):
        s = Scheduler()
        s._active.add('task1')
        with patch.object(s, '_futures') as futures_patch:
            fmock1 = Mock()
            fmock2 = Mock()
            fmock2.cancel.side_effect = RuntimeError('runtime error')
            futures_patch.keys.return_value = [fmock1, fmock2]
            s._handle_interrupt(Mock())
            fmock1.cancel.assert_called_once()
            fmock2.cancel.assert_called_once()
            self.assertEqual(s._results['task1'], {'ok': False, 'error_type': 'CancelledError', 'error': 'cancelled'})

    def test_prep_start(self, *patches):
        s = Scheduler()
        with patch.object(s, '_events') as events_patch:
            events_patch.get_nowait.side_effect = [('done', ('task1', True, '', '')), queue.Empty()]
            s._prep_start()
            self.assertEqual(s.state['results'], {})

    @patch('threaded_order.scheduler.ThreadPoolExecutor')
    @patch('threaded_order.scheduler.Scheduler._build_summary')
    @patch('threaded_order.scheduler.Scheduler._handle_event')
    @patch('threaded_order.scheduler.Scheduler._submit')
    @patch('threaded_order.scheduler.Scheduler._prep_start')
    @patch('threaded_order.scheduler.Scheduler._callback')
    def test_start(self, callback_patch, prep_start_patch, submit_patch, handle_event_patch, build_summary_patch, *patches):
        s = Scheduler()
        scheduler_start_mock = Mock()
        scheduler_done_mock = Mock()
        s.on_scheduler_start(scheduler_start_mock)
        s.on_scheduler_done(scheduler_done_mock)
        graph_mock = Mock()
        graph_mock.get_candidates.return_value = ['task1', 'task2']
        s._graph = graph_mock
        with patch.object(s, '_completed') as completed_patch:
            completed_patch.wait.side_effect = [False, False, False, True]
            s.start()
        prep_start_patch.assert_called_once()
        submit_patch.assert_has_calls([call('task1'), call('task2')])
        handle_event_patch.assert_called()
        build_summary_patch.assert_called_once()
        callback_patch.assert_called()

    @patch('threaded_order.scheduler.ThreadPoolExecutor')
    @patch('threaded_order.scheduler.Scheduler._build_summary')
    @patch('threaded_order.scheduler.Scheduler._handle_event')
    @patch('threaded_order.scheduler.Scheduler._submit')
    @patch('threaded_order.scheduler.Scheduler._prep_start')
    @patch('threaded_order.scheduler.Scheduler._callback')
    def test_start_When_KeyboardInterrupt(self, callback_patch, prep_start_patch, submit_patch, handle_event_patch, build_summary_patch, *patches):
        s = Scheduler()
        graph_mock = Mock()
        graph_mock.get_candidates.return_value = ['task1', 'task2']
        s._graph = graph_mock
        with patch.object(s, '_completed') as completed_patch:
            completed_patch.wait.side_effect = [False, False, False, KeyboardInterrupt]
            result = s.start()
        self.assertEqual(result, build_summary_patch.return_value)

    def test_submit(self, *patches):
        s = Scheduler()
        with patch.object(s, '_events') as events_patch, \
            patch.object(s, '_executor') as executor_patch:
            future_mock = Mock()
            executor_patch.submit.return_value = future_mock
            s._submit('task1')
            events_patch.put.assert_called_once_with(('start', 'task1'))
            self.assertEqual(s._futures[future_mock], 'task1')
            future_mock.add_done_callback.assert_called_once_with(s._done)

    def test_done(self, *patches):
        s = Scheduler()
        with patch.object(s, '_events') as events_patch, \
            patch.object(s, '_futures') as futures_patch:
            future_mock = Mock()
            future_mock.result.return_value = ('task1', True, '', '')
            s._done(future_mock)
            events_patch.put.assert_called_once_with(('done', ('task1', True, '', '')))

    def test_done_When_Exception(self, *patches):
        s = Scheduler()
        with patch.object(s, '_events') as events_patch, \
            patch.object(s, '_futures') as futures_patch:
            futures_patch.get.return_value = 'task1'
            future_mock = Mock()
            future_mock.result.side_effect = Exception('error')
            s._done(future_mock)
            events_patch.put.assert_called_once_with(('done', ('task1', False, 'Exception', 'error')))

    def test_run_When_WithState(self, *patches):
        s = Scheduler(store_results=True)
        function_mock = Mock(__name__='task1')
        s._callables = {'task1': (function_mock, True)}
        with patch.object(s, '_events') as events_patch:
            result = s._run('task1')
            function_mock.assert_called_once_with(s.state)
            self.assertEqual(s.state['results']['task1'], function_mock.return_value)
            self.assertEqual(result, ('task1', True, None, None))

    def test_run_When_WithNoState(self, *patches):
        s = Scheduler(store_results=False)
        function_mock = Mock(__name__='task1')
        s._callables = {'task1': (function_mock, False)}
        with patch.object(s, '_events') as events_patch:
            result = s._run('task1')
            function_mock.assert_called_once_with()
            self.assertEqual(result, ('task1', True, None, None))

    def test_run_When_Exception(self, *patches):
        s = Scheduler(store_results=True)
        function_mock = Mock(__name__='task1')
        function_mock.side_effect = Exception('error')
        s._callables = {'task1': (function_mock, True)}
        with patch.object(s, '_events') as events_patch:
            result = s._run('task1')
            function_mock.assert_called_once_with(s.state)
            self.assertEqual(result, ('task1', False, 'Exception', 'error'))

    def test_callback_When_NoCallback(self, *patches):
        s = Scheduler()
        s._callback(None, 'task1')

    def test_callback_When_CallbackIsTuple(self, *patches):
        s = Scheduler()
        callback_mock = Mock()
        s._callback((callback_mock, ('arg1', 'arg2'), {'k1': 'v1'}), 'task1')
        callback_mock.assert_called_once_with('task1', 'arg1', 'arg2', k1='v1')

    def test_callback_When_CallbackIsCallable(self, *patches):
        s = Scheduler()
        callback_mock = Mock()
        s._callback(callback_mock, 'task1')
        callback_mock.assert_called_once_with('task1')

    def test_callback_When_CallbackException(self, *patches):
        s = Scheduler()
        callback_mock = Mock(side_effect=Exception('error'))
        s._callback(callback_mock, 'task1')

    def test_mark(self, *patches):
        function_mock = Mock(__name__='task1')
        decorated_function = mark(with_state=True, tags='t1,t2')(function_mock)
        threaded_order = {
            'after': [],
            'with_state': True,
            'orig_name': 'task1',
            'tags': ['t1', 't2']
        }
        self.assertEqual(decorated_function.__threaded_order__, threaded_order)
        decorated_function()

    def test_dmark(self, *patches):
        function_mock = Mock(__name__='task1')
        decorated_function = dmark(with_state=True, tags='t1,t2')(function_mock)
        threaded_order = {
            'after': [],
            'with_state': True,
            'orig_name': 'task1',
            'tags': ['t1', 't2']
        }
        self.assertEqual(decorated_function.__threaded_order__, threaded_order)
        decorated_function()