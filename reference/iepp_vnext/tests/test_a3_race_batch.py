import copy
from concurrent.futures import ThreadPoolExecutor
import json
import os
import socket
import subprocess
from pathlib import Path
import sys
import tempfile
import threading
import unittest
import zipfile
from urllib.error import HTTPError

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import a3_race_batch as race


class BatchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.root = Path(cls.temp.name) / 'batch'
        manifest = race.prepare(cls.root, 'http://127.0.0.1:0', 1)
        cls.batch = race.Batch(cls.root, lead_seconds=.3, allow_same_host=True)
        cls.server = race.BatchServer(('127.0.0.1', 0), cls.batch)
        url = f'http://127.0.0.1:{cls.server.server_address[1]}'
        cls.manifest = manifest
        manifest['url'] = url
        race.write_json(cls.root / 'public/manifest.json', manifest)
        for b in 'AB':
            path = cls.root / 'private' / f'worker-{b}.private.json'
            config = race.read(path)
            config['manifest']['url'] = url
            path.write_text(json.dumps(config))
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        try:
            with ThreadPoolExecutor(max_workers=2) as pool:
                jobs = [pool.submit(race.worker, cls.root / 'private' / f'worker-{b}.private.json',
                                    Path(cls.temp.name) / f'worker-{b}') for b in 'AB']
                for job in jobs:
                    job.result(timeout=60)
        finally:
            cls.server.shutdown()
            cls.server.server_close()
            cls.thread.join(timeout=5)
            if cls.batch.engine:
                cls.batch.engine.close()

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def test_22_real_http_trials_are_isolated_and_audited(self):
        summary = race.audit_batch(self.root / 'public')
        self.assertTrue(summary['passed'], summary)
        self.assertEqual(summary['planned'], 22)
        self.assertEqual(summary['passed_trials'], 22)
        self.assertEqual(summary['schedule_quality_ok_trials'], 22)
        self.assertFalse(summary['actual_vm_restore_per_trial'])
        specs = self.manifest['specs']
        self.assertEqual({(s['mode'], *s['delay_ms'].values()) for s in specs},
                         {(m, *d) for m in ('fresh', 'shared') for d in race.DELAYS})
        keys, initial = set(), set()
        for spec in specs:
            folder = self.root / 'public' / spec['trial_id']
            e = race.read(folder / 'enrollment.json')
            keys.add(e['public_key'])
            initial.add(e['initial_state'])
            a, b = [race.read(folder / f'candidate-{x}.json') for x in 'AB']
            self.assertEqual(a['evidence']['challenge_id'] == b['evidence']['challenge_id'],
                             spec['mode'] == 'shared')
            self.assertFalse(a['actual_vm_restore'])
        self.assertEqual(len(keys), 22)
        self.assertEqual(len(initial), 22)

    def test_public_outputs_exclude_private_keys_and_tokens(self):
        config = race.read(self.root / 'private/worker-A.private.json')
        text = '\n'.join(p.read_text() for p in (self.root / 'public').rglob('*') if p.is_file())
        self.assertNotIn(config['token'], text)
        for snapshot in config['snapshots'].values():
            self.assertNotIn(snapshot['private_key'], text)
        if os.name != 'nt':
            self.assertEqual((self.root / 'private/worker-A.private.json').stat().st_mode & 0o777, 0o600)

    def test_auditor_rejects_mismatch_duplicate_expiry_missing_and_bad_signature(self):
        import shutil
        spec = self.manifest['specs'][0]
        original = self.root / 'public' / spec['trial_id']
        cases = ('mismatch', 'duplicate', 'expired', 'missing', 'signature', 'schedule')
        for case in cases:
            with self.subTest(case=case), tempfile.TemporaryDirectory() as tmp:
                folder = Path(tmp) / 'trial'
                shutil.copytree(original, folder)
                if case == 'mismatch':
                    p = folder / 'result-A.json'
                    row = race.read(p)
                    row['canonical_head_after'] = '00' * 32
                    race.write_json(p, row)
                elif case == 'duplicate':
                    events = race.lines(folder / 'registry-events.jsonl')
                    race.append_jsonl(folder / 'registry-events.jsonl', events[-1])
                elif case == 'expired':
                    p = folder / 'registry-events.jsonl'
                    events = race.lines(p)
                    events[0]['challenge']['expires_at'] = 0
                    p.write_text('\n'.join(json.dumps(e) for e in events))
                elif case == 'missing':
                    (folder / 'result-A.json').unlink()
                elif case == 'signature':
                    p = folder / 'candidate-A.json'
                    row = race.read(p)
                    row['evidence']['signature'] = '00' * 64
                    race.write_json(p, row)
                else:
                    p = folder / 'result-A.json'
                    row = race.read(p)
                    row['configured_delay_ms'] = 999
                    race.write_json(p, row)
                self.assertFalse(race.audit_trial(folder, spec)['passed'])

    def test_reject_existing_workspace_and_incomplete_batch(self):
        with self.assertRaises(FileExistsError):
            race.prepare(self.root, 'http://127.0.0.1:1', 1)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / 'new'
            race.prepare(root, 'http://127.0.0.1:1', 1)
            summary = race.audit_batch(root / 'public')
            self.assertFalse(summary['passed'])
            self.assertEqual(summary['passed_trials'], 0)

    def test_authentication_duplicate_worker_and_code_mismatch(self):
        # A separate controller before any task; tests must not mutate evidence above.
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / 'new'
            race.prepare(root, 'http://127.0.0.1:0', 1)
            batch = race.Batch(root)
            server = race.BatchServer(('127.0.0.1', 0), batch)
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            cfg = race.read(root / 'private/worker-A.private.json')
            cfg['manifest']['url'] = f'http://127.0.0.1:{server.server_address[1]}'
            try:
                bad = copy.deepcopy(cfg)
                bad['token'] = 'wrong'
                with self.assertRaises(HTTPError) as cm:
                    race.rpc(bad, {'op': 'clock'})
                self.assertEqual(cm.exception.code, 403)
                hello = {'op': 'hello', 'source_hashes': race.source_hashes(), 'host': 'test', 'runtime': 'test'}
                with self.assertRaises(HTTPError):
                    race.rpc(cfg, {**hello, 'source_hashes': {}})
                self.assertTrue(race.rpc(cfg, hello)['ok'])
                with self.assertRaises(HTTPError):
                    race.rpc(cfg, hello)
                other = race.read(root / 'private/worker-B.private.json')
                other['manifest']['url'] = cfg['manifest']['url']
                with self.assertRaises(HTTPError):
                    race.rpc(other, hello)  # same observed IP, production guard
            finally:
                server.shutdown()
                server.server_close()
                thread.join(timeout=5)

    def test_cli_process_lifecycle_and_public_archive(self):
        # Two representative trials exercise the real CLI process lifecycle;
        # the complete 22-case matrix is exercised above through real HTTP.
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / 'cli'
            with socket.socket() as sock:
                sock.bind(('127.0.0.1', 0))
                port = sock.getsockname()[1]
            manifest = race.prepare(root, f'http://127.0.0.1:{port}', 1)
            manifest['specs'] = [manifest['specs'][0], manifest['specs'][11]]
            manifest['specs'][1]['index'] = 1
            race.write_json(root / 'public/manifest.json', manifest)
            for b in 'AB':
                path = root / 'private' / f'worker-{b}.private.json'
                cfg = race.read(path)
                cfg['manifest'] = manifest
                path.write_text(json.dumps(cfg))
            script = str(Path(race.__file__).resolve())
            processes = []
            controller = subprocess.Popen([sys.executable, '-u', script, 'serve',
                '--workspace', str(root), '--bind', '127.0.0.1', '--port', str(port),
                '--allow-same-host'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            processes.append(controller)
            try:
                self.assertTrue(json.loads(controller.stdout.readline())['ready'])
                for b in 'AB':
                    processes.append(subprocess.Popen([sys.executable, script, 'worker',
                        '--config', str(root / 'private' / f'worker-{b}.private.json'),
                        '--output', str(Path(tmp) / b)], stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE, text=True))
                for proc in processes[1:]:
                    out, err = proc.communicate(timeout=30)
                    self.assertEqual(proc.returncode, 0, (out, err))
                out, err = controller.communicate(timeout=30)
                self.assertEqual(controller.returncode, 0, (out, err))
                self.assertTrue(race.read(root / 'public/summary.json')['passed'])
                with zipfile.ZipFile(root / 'public-results.zip') as archive:
                    self.assertTrue(all(n.startswith('public/') for n in archive.namelist()))
                    self.assertIn('public/summary.json', archive.namelist())
                    text = '\n'.join(archive.read(n).decode() for n in archive.namelist())
                    cfg = race.read(root / 'private/worker-A.private.json')
                    self.assertNotIn(cfg['token'], text)
                    for snapshot in cfg['snapshots'].values():
                        self.assertNotIn(snapshot['private_key'], text)
                rerun = subprocess.run([sys.executable, script, 'serve', '--workspace', str(root),
                    '--bind', '127.0.0.1', '--port', str(port), '--allow-same-host'],
                    capture_output=True, text=True, timeout=10)
                self.assertNotEqual(rerun.returncode, 0)
            finally:
                for proc in processes:
                    if proc.poll() is None:
                        proc.kill()
                    proc.communicate()


if __name__ == '__main__':
    unittest.main()
