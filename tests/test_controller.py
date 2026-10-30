from dataclasses import FrozenInstanceError
from pathlib import Path
import sys
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from igris.controller import MissionController, MissionError, State, TaskOutcome


class ControllerTests(unittest.TestCase):
    def test_creation_and_success_transitions(self):
        controller = MissionController('owner', {'inspect': lambda ctx: TaskOutcome('success', 'checked fixture', 'simulated', True)})
        first = controller.create('inspect fixture', 'inspect')
        second = controller.create('inspect fixture', 'inspect')
        self.assertNotEqual(first.id, second.id)
        mission = controller.run(first.id)
        self.assertEqual(mission.state, State.SUCCEEDED)
        self.assertEqual(mission.history, (State.REQUESTED, State.PLANNED, State.READY, State.RUNNING, State.VERIFYING, State.SUCCEEDED))
        self.assertEqual(controller.report(first.id)['evidence_origin'], 'simulated')
        with self.assertRaises(FrozenInstanceError):
            mission.state = State.READY

    def test_unknown_route_input_and_transitions(self):
        controller = MissionController('owner', {})
        for text, route in (('', 'unknown'), ('data', 'shell'), ('x' * 8193, 'unknown')):
            with self.assertRaises(MissionError):
                controller.create(text, route)
        with self.assertRaises(MissionError):
            controller.get('missing')
        other = MissionController('owner', {'r': lambda c: TaskOutcome('blocked', 'missing access')})
        mission = other.create('do task', 'r')
        with self.assertRaises(MissionError):
            other._move(mission.id, State.SUCCEEDED)
        self.assertEqual(other.run(mission.id).state, State.BLOCKED)
        with self.assertRaises(MissionError):
            other.run(mission.id)

    def test_approval_is_requested_and_reference_only_resumes_handler(self):
        seen = []
        def handler(ctx):
            seen.append(ctx.approval_id)
            if ctx.approval_id is None:
                return TaskOutcome('approval_required', 'Owner review needed.', approval_request_id='a' * 32)
            # A forged reference must still fail at the executor, not succeed here.
            return TaskOutcome('failed', 'Executor rejected reference.')
        controller = MissionController('owner', {'r': handler})
        mission = controller.create('create approved fixture', 'r')
        self.assertEqual(controller.run(mission.id).state, State.AWAITING_APPROVAL)
        with self.assertRaises(MissionError):
            controller.run(mission.id)
        self.assertEqual(controller.run(mission.id, approval_id='x' * 32).state, State.FAILED)
        self.assertEqual(seen, [None, 'x' * 32])

    def test_invalid_outcomes_and_exceptions_never_succeed(self):
        def broken(ctx):
            raise RuntimeError('sensitive synthetic detail')
        for handler in (broken, lambda c: {'status': 'success'},
                        lambda c: TaskOutcome('success', 'asserted only'),
                        lambda c: TaskOutcome('approval_required', 'missing reference')):
            controller = MissionController('owner', {'r': handler})
            mission = controller.create('request', 'r')
            self.assertEqual(controller.run(mission.id).state, State.FAILED)
            self.assertNotIn('sensitive synthetic detail', str(controller.report(mission.id)))

    def test_input_and_result_sanitized_and_routes_copied(self):
        routes = {'r': lambda c: TaskOutcome('success', 'password: synthetic fixture', 'local', True)}
        controller = MissionController('owner', routes)
        routes.clear()
        mission = controller.create('token: synthetic fixture', 'r')
        self.assertEqual(mission.prompt, '[REDACTED]')
        self.assertEqual(controller.run(mission.id).message, '[REDACTED]')
