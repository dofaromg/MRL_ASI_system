"""Verify a pending grant cannot activate runtime authorization; synthetic trees only."""
import importlib.util
import json
import pathlib
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
REQUEST = 'config/MRL_STRUCTURE_INDEX_GRANT_REQUEST_20261101.json'
REPOSITORY = 'dofaromg/MRL_ASI_system'

class PendingGrantTests(unittest.TestCase):
    def test_request_is_scoped_and_unapproved(self):
        """Keep all operational terms explicit and approval absent."""
        request = json.loads((ROOT / REQUEST).read_text())
        self.assertEqual(request['state'], 'PENDING_ROOT_APPROVAL')
        self.assertEqual(request['canonical_authority'], 'Mr.liou')
        self.assertTrue(all(v is None for v in request['approval'].values()))
        grant = request['proposed_grant']
        self.assertEqual(grant['status'], 'pending')
        for key in ('issued_by', 'issued_at', 'expires_at', 'evidence_reference'):
            self.assertIsNone(grant[key])
        self.assertEqual(grant['scope'], {'repository': REPOSITORY, 'assets': ['.'],
            'max_depth': 8, 'destination': 'github-actions-artifact:' + REPOSITORY,
            'events': ['workflow_dispatch'], 'ref': 'refs/heads/main'})
        self.assertEqual(grant['grantee'], {'actor': 'dofaromg', 'triggering_actor': 'dofaromg'})
        self.assertEqual(set(grant['actions']), {'structure.scan', 'structure.generate', 'structure.upload'})

    def test_pending_request_is_ignored_and_outputs_untouched(self):
        """A complete proposal next to an empty registry remains fail closed."""
        spec = importlib.util.spec_from_file_location('pending_guard', ROOT / '.copilot/Mrliou_structure_authorization.py')
        guard = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(guard)
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            (root / 'config').mkdir()
            registry = json.loads((ROOT / 'config/MRL_AUTHORIZATION_REGISTRY_v1.json').read_text())
            registry['active_grants'] = []
            registry_path = root / 'config/MRL_AUTHORIZATION_REGISTRY_v1.json'
            registry_path.write_text(json.dumps(registry))
            (root / REQUEST).write_bytes((ROOT / REQUEST).read_bytes())
            guard.ROOT, guard.REGISTRY = root, registry_path
            before = registry_path.read_bytes()
            for relative in guard.ARTIFACTS:
                target = root / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(b'HISTORICAL_EVIDENCE')
            for actions in (guard.ACTIONS, {'structure.upload'}):
                with self.assertRaisesRegex(guard.AuthorizationDenied, 'NO_RECORDED_GRANT'):
                    guard.authorize(actions)
            self.assertEqual(registry_path.read_bytes(), before)
            for relative in guard.ARTIFACTS:
                self.assertEqual((root / relative).read_bytes(), b'HISTORICAL_EVIDENCE')

if __name__ == '__main__':
    unittest.main()
