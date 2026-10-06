# /// script
# requires-python = ">=3.11"
# dependencies = ["pyyaml", "requests"]
# ///
"""Execute current job adapters and the focused publication regressions."""
import argparse
import hashlib
import hmac
import importlib.util
import json
import os
import shutil
import ssl
import subprocess
import sys
import threading
import time
from datetime import datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import requests
import yaml

ROOT = Path(__file__).resolve().parents[1]


def module(name, file):
    spec = importlib.util.spec_from_file_location(name, ROOT / 'scripts' / file)
    value = importlib.util.module_from_spec(spec)
    sys.modules[name] = value
    spec.loader.exec_module(value)
    return value


reg = module('current_regressions', 'test-review-regressions.py')
builder = module('current_builder', 'build-example-conformance.py')
publication = module('current_publication', 'test-publication-review.py')


def command(args, **kwargs):
    return subprocess.run(args, check=True, capture_output=True, text=True, **kwargs).stdout


class Receiver(BaseHTTPRequestHandler):
    received = []

    def do_POST(self):
        body = self.rfile.read(int(self.headers['Content-Length']))
        self.received.append((self.path, self.headers.get('Authorization'), json.loads(body)))
        self.send_response(200)
        self.end_headers()

    def log_message(self, *_):
        pass


def run_job(suite, directory, name, document):
    path = directory / f'{name}.yaml'
    path.write_text(yaml.safe_dump(document, sort_keys=False))
    ok, _, output = reg.runner.deploy(path, reg.CLI, suite.api)
    assert ok, output
    return document['name']


def jobs(suite, directory, cert, key, receiver_port):
    rows = []
    server = ThreadingHTTPServer(('127.0.0.1', receiver_port), Receiver)
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.load_cert_chain(cert, key)
    server.socket = context.wrap_socket(server.socket, server_side=True)
    thread = threading.Thread(target=server.serve_forever)
    thread.start()
    try:
        path = ROOT / 'skills/jobs/webhook-fan-out/pipeline.yaml'
        document = yaml.safe_load(path.read_text())
        port = reg.runner.free_port()
        document['config']['input']['http_server']['address'] = f'127.0.0.1:{port}'
        for output in document['config']['output']['broker']['outputs']:
            output['http_client']['tls'] = {'enabled': True, 'root_cas_file': str(cert)}
        name = run_job(suite, directory, 'fanout', document)
        try:
            ready, reason = reg.runner.wait_for_execution_running(reg.CLI, name, suite.api)
            assert ready, reason
            payload = b'{"event":"fixture"}'
            signature = hmac.new(b'fixture-secret', payload, hashlib.sha256).hexdigest()
            for signed in ['invalid', signature]:
                response = requests.post(f'http://127.0.0.1:{port}/webhook', data=payload,
                                         headers={'X-Webhook-Signature': signed}, timeout=20)
                if signed == 'invalid':
                    assert response.status_code in (200, 408), response.text
                    assert Receiver.received == [], Receiver.received
                else:
                    assert response.status_code == 200, response.text
            deadline = time.monotonic() + 15
            while len(Receiver.received) < 3 and time.monotonic() < deadline:
                time.sleep(.1)
            assert len(Receiver.received) == 3, Receiver.received
            assert all(route == '/notify' and token == 'Bearer fixture-token' and
                       body['event'] == 'fixture' and body['received_at']
                       for route, token, body in Receiver.received), Receiver.received
            rows.append(reg.runner.base_evidence(path) | {'status': 'pass', 'outputs': Receiver.received})
        finally:
            reg.runner.delete_job(reg.CLI, name, suite.api)
    finally:
        server.shutdown()
        server.server_close()
        thread.join()

    path = ROOT / 'skills/jobs/data-migration-engine/pipeline.yaml'
    if shutil.which('pg_config'):
        os.environ['PATH'] = command(['pg_config', '--bindir']).strip() + os.pathsep + os.environ['PATH']
    required = ['initdb', 'pg_ctl', 'psql']
    missing = [name for name in required if not shutil.which(name)]
    if missing:
        rows.append(reg.runner.base_evidence(path) | {'status': 'skipped', 'reason': 'TLS PostgreSQL fixture unavailable: missing ' + ', '.join(missing)})
        return rows
    data = directory / 'postgres'
    password = directory / 'password'
    password.write_text('fixture-password\n')
    password.chmod(0o600)
    command(['initdb', '-D', str(data), '-U', 'fixture', '--pwfile', str(password), '--auth', 'scram-sha-256', '--no-locale'])
    port = reg.runner.free_port()
    with (data / 'postgresql.conf').open('a') as file:
        file.write(f"\nlisten_addresses='127.0.0.1'\nport={port}\nunix_socket_directories=''\nssl=on\nssl_cert_file='{cert}'\nssl_key_file='{key}'\n")
    command(['pg_ctl', 'start', '-D', str(data), '-l', str(directory / 'postgres.log'), '-w'])
    try:
        dsn = f'postgres://fixture@localhost:{port}/postgres?sslmode=verify-full&sslrootcert={cert}'
        env = os.environ | {'PGPASSWORD': 'fixture-password'}
        def sql(query):
            return command(['psql', '-X', '-d', dsn, '-v', 'ON_ERROR_STOP=1', '-At', '-c', query], env=env)
        sql('CREATE DATABASE source')
        sql('CREATE DATABASE destination')
        source = dsn.replace('/postgres?', '/source?')
        destination = dsn.replace('/postgres?', '/destination?')
        command(['psql', '-X', '-d', source, '-v', 'ON_ERROR_STOP=1', '-c', "CREATE TABLE customers(cust_no int, full_name text, email text, signup text, status_code text, balance_cents int); INSERT INTO customers VALUES(1,'Doe, Jane',' JANE@example.test ','01/02/2026','A',-150),(2,'Doe, Bad','bad','01/02/2026','A',0)"], env=env)
        command(['psql', '-X', '-d', destination, '-v', 'ON_ERROR_STOP=1', '-c', 'CREATE TABLE customers(id int PRIMARY KEY, first_name text, last_name text, email text, signed_up_on date, status text, balance numeric, migrated_from text)'], env=env)
        document = yaml.safe_load(path.read_text())
        document['config']['input']['sql_select']['dsn'] = source.replace('fixture@', 'fixture:fixture-password@')
        cases = document['config']['output']['switch']['cases']
        rejects = directory / 'rejects.jsonl'
        cases[0]['output']['file']['path'] = str(rejects)
        cases[1]['output']['sql_insert']['dsn'] = destination.replace('fixture@', 'fixture:fixture-password@')
        name = run_job(suite, directory, 'migration', document)
        try:
            deadline = time.monotonic() + 30
            output = ''
            while time.monotonic() < deadline:
                output = command(['psql', '-X', '-d', destination, '-At', '-c', 'SELECT row_to_json(customers) FROM customers'], env=env).strip()
                if output and rejects.exists():
                    break
                time.sleep(.2)
            result = json.loads(output)
            assert result == {'id': 1, 'first_name': 'Jane', 'last_name': 'Doe', 'email': 'jane@example.test', 'signed_up_on': '2026-01-02', 'status': 'active', 'balance': -1.5, 'migrated_from': 'legacy.customers'}, result
            rejected = [json.loads(line) for line in rejects.read_text().splitlines()]
            assert len(rejected) == 1 and rejected[0]['reject_reason'] == 'invalid email', rejected
            rows.append(reg.runner.base_evidence(path) | {'status': 'pass', 'outputs': [result], 'rejects': rejected})
        finally:
            reg.runner.delete_job(reg.CLI, name, suite.api)
    finally:
        command(['pg_ctl', 'stop', '-D', str(data), '-m', 'fast', '-w'])
    return rows


def archive_keys(suite, directory):
    sweep = []
    def outputs(value):
        if isinstance(value, dict):
            for key, child in value.items():
                if key in ('aws_s3', 'gcp_cloud_storage', 'azure_blob_storage') and isinstance(child, dict) and 'path' in child:
                    yield child['path']
                else:
                    yield from outputs(child)
        elif isinstance(value, list):
            for child in value:
                yield from outputs(child)
    for path in sorted((ROOT / 'skills').glob('*/*/pipeline*.yaml')):
        document = yaml.safe_load(path.read_text())
        cfg = document.get('config', {})
        for index, key in enumerate(outputs(cfg.get('output', {}))):
            destination = directory / 'objects' / path.parent.name / str(index)
            processors = [{'unarchive': {'format': 'json_array'}}]
            if path.parent.name == 'nightly-backup':
                processors += cfg['pipeline']['processors']
            processors += [{'mapping': 'root = this\nroot.fixture_second = now().ts_unix()'}]
            fixture = {
                '_source_pipeline': str(path.relative_to(ROOT)),
                'pipeline': {'processors': processors},
                'output': {'file': {'path': str(destination) + '/' + key, 'codec': 'lines'}},
            }
            payload = [{'id': value, '_table': 'orders', '_kafka_topic': 'fixture',
                        '_partition_day': '2026-10-06', '_partition_hour': '22'} for value in (1, 2)]
            suite.execute(fixture, payload, retain_output=True, decode_json=False)
            files = list(destination.rglob('*'))
            files = [file for file in files if file.is_file()]
            assert len(files) == 2, (path, key, files)
            records = [json.loads(file.read_text()) for file in files]
            assert {record['id'] for record in records} == {1, 2}, records
            assert len({record['fixture_second'] for record in records}) == 1, records
            sweep.append({'pipeline': str(path.relative_to(ROOT)), 'sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
                          'key': key, 'objects': [str(file.relative_to(directory)) for file in files]})
    (ROOT / '.conformance/object-key-sweep.json').write_text(json.dumps({'status': 'pass', 'outputs': sweep}, indent=2) + '\n')
    print(f'PASS {len(sweep)} object outputs retain two records in one second')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--jobs-only', action='store_true')
    args = parser.parse_args()
    directory = ROOT / '.conformance' / f'current-review-{time.time_ns()}'
    directory.mkdir(parents=True)
    cert, key = directory / 'cert.pem', directory / 'private.key'
    command(['openssl', 'req', '-x509', '-newkey', 'rsa:2048', '-nodes', '-keyout', str(key), '-out', str(cert), '-days', '1', '-subj', '/CN=localhost', '-addext', 'subjectAltName=DNS:localhost'])
    key.chmod(0o600)
    version = command(['expanso-edge', 'version']).strip()
    env = {'WEBHOOK_SECRET': 'fixture-secret', 'PLACEHOLDER': '[HIDDEN]'}
    for receiver in 'ABC':
        env[f'RECEIVER_{receiver}_TOKEN'] = 'fixture-token'
    receiver_port = reg.runner.free_port()
    for receiver in 'ABC':
        env[f'RECEIVER_{receiver}_HOST'] = f'localhost:{receiver_port}'
    suite = reg.Suite(directory, env)
    try:
        rows = jobs(suite, directory, cert, key, receiver_port)
        report = {'generated': datetime.now(timezone.utc).isoformat(), 'expanso_edge': version, 'scope': 'local Edge; published adapters and processors, fixture connection details only', 'jobs': rows}
        (ROOT / '.conformance/job-execution.json').write_text(json.dumps(report, indent=2) + '\n')
        for row in rows:
            path = ROOT / row['pipeline']
            evidence = builder.execution_evidence(path, 'job', {}, {}, {}, {})
            assert evidence['status'] == row['status'], evidence
        stale = json.loads(json.dumps(report))
        stale['jobs'][0]['sha256'] = 'stale'
        report_path = ROOT / '.conformance/job-execution.json'
        report_path.write_text(json.dumps(stale))
        try:
            assert builder.execution_evidence(ROOT / rows[0]['pipeline'], 'job', {}, {}, {}, {})['status'] == 'failing'
        finally:
            report_path.write_text(json.dumps(report, indent=2) + '\n')
        if args.jobs_only:
            print('PASS current-hash job execution evidence')
            return
        publication.workflow_contract()
        for variant in ['cli', 'mcp']:
            cfg = reg.config('workflows/seo-pipeline', variant)
            html = '<title>Chart</title><meta name="description" content="Summary"><h1>Chart</h1><img alt="Chart"><meta name="viewport">'
            for extra in ['<!-- <img src=x> -->', '<script>"<img src=x>"</script>', '<style>x{content:"<img>"}</style>', '<textarea><img></textarea>', '<script>const x="</style><img src=x>";</script>', '<style>x{content:"</script><img>"}</style>']:
                result = suite.execute(cfg, {'html': html + extra})
                assert result['analysis']['score'] == 100 and result['analysis']['image_count'] == 1, result
            result = suite.execute(cfg, {'html': '<!-- ' + html + ' --><script>' + html + '</script>'})
            assert result['analysis']['score'] == 15 and result['analysis']['image_count'] == 0, result
            cfg = reg.config('security/pii-redact', variant)
            cfg['pipeline']['processors'][2] = {'mapping': 'meta delivered_prompt = this.messages.0.content\nroot = {"choices": [{"message": {"content": "{\\"redacted_text\\":\\"[HIDDEN]\\",\\"redaction_count\\":1,\\"redacted_types\\":[\\"email\\"]}"}}]}'}
            cfg['pipeline']['processors'].append({'mapping': 'root = this\nroot.delivered_prompt = meta("delivered_prompt")'})
            payload = 'Contact a@example.test' if variant == 'cli' else {'text': 'Contact a@example.test', 'placeholder': '[HIDDEN]'}
            result = suite.execute(cfg, payload, raw=variant == 'cli')
            assert "'[HIDDEN]'" in result['delivered_prompt'] and result['metadata']['placeholder'] == '[HIDDEN]' and result['redacted_text'] == '[HIDDEN]', result
        cfg = reg.config('recipes/priority-queues', 'recipe')
        cfg['pipeline']['processors'] = cfg['pipeline']['processors'][-1:]
        result = suite.execute(cfg, {'priority_score': 100, 'timestamp': (datetime.now(timezone.utc) + timedelta(seconds=30)).strftime('%Y-%m-%dT%H:%M:%SZ')})
        assert result['age_boost_applied'] == 0 and result['priority_queue'] == 'high', result
        cfg = reg.config('recipes/priority-queues', 'recipe')
        result = suite.execute(cfg, {'severity': 'INFO', 'timestamp': (datetime.now(timezone.utc) + timedelta(seconds=30)).strftime('%Y-%m-%dT%H:%M:%SZ')})
        assert result['age_boost_applied'] == 0 and result['final_score'] == 30 and result['priority_queue'] == 'low', result
        archive_keys(suite, directory)
        reg.write_evidence()
        print('PASS current job execution, stale evidence rejection, SEO contexts, placeholder, and future priority')
    finally:
        suite.close()


if __name__ == '__main__':
    main()
