import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import temporary_database_backup as temporary


class Provider:
    def __init__(self):
        self.row = dict(oid=42, rolname=temporary.ROLE, rolsuper=False, rolcreaterole=False,
                        rolcreatedb=False, rolcanlogin=False, rolvaliduntil='1970-01-01 00:00:00+00')
        self.sessions = []
        self.mutations = []

    def query(self, sql, *, mutate=False):
        if mutate:
            self.mutations.append(sql)
            if 'NOLOGIN' in sql:
                self.row['rolcanlogin'] = False
                self.row['rolvaliduntil'] = '1970-01-01 00:00:00+00'
            elif ' LOGIN' in sql:
                self.row['rolcanlogin'] = True
            if 'pg_terminate_backend' in sql:
                self.sessions = []
            return []
        if sql == temporary.ROLE_QUERY:
            return [dict(self.row)]
        return list(self.sessions)

    def request(self, suffix, payload):
        assert suffix == '/cli/login-role' and payload == {'read_only': True}
        return {'role': temporary.ROLE, 'password': 'synthetic-password', 'ttl_seconds': 300}


@pytest.fixture
def config(tmp_path):
    value = dict(project_ref='a' * 20, management_token='synthetic-token', owned_role_oid=42,
                 pooler_host='aws-0-us-east-1.pooler.supabase.com')
    path = tmp_path / 'config.json'
    path.write_text(json.dumps(value)); path.chmod(0o600)
    return path


def test_config_requires_private_owned_file(config):
    assert temporary.config_file(config)['owned_role_oid'] == 42
    config.chmod(0o644)
    with pytest.raises(temporary.ContractError):
        temporary.config_file(config)


@pytest.mark.parametrize('field,value', [('owned_role_oid', True), ('project_ref', '../other'),
                                        ('pooler_host', 'evil.example'), ('management_token', 'x\ny')])
def test_config_rejects_foreign_or_ambiguous_identity(config, field, value):
    data = json.loads(config.read_text()); data[field] = value; config.write_text(json.dumps(data))
    with pytest.raises(temporary.ContractError):
        temporary.config_file(config)


@pytest.mark.parametrize('field,value', [('oid', 43), ('rolsuper', True), ('rolcreaterole', True),
                                        ('rolcreatedb', True), ('rolcanlogin', True)])
def test_preflight_never_adopts_foreign_or_active_role(field, value):
    api = Provider(); api.row[field] = value
    with pytest.raises(temporary.ContractError):
        temporary.owned_role(api, 42, closed=True)
    assert not api.mutations


def test_revoke_checks_exact_backend_identity_and_expires_credential():
    api = Provider(); api.row['rolcanlogin'] = True
    started = datetime.now(timezone.utc) - timedelta(seconds=2)
    api.sessions = [dict(pid=123, application_name='Supavisor', backend_start=datetime.now(timezone.utc).isoformat())]
    result = temporary.revoke_login(api, 42, started, 'own-application')
    assert result['credential_expired'] and result['owned_sessions_removed']
    assert len(api.mutations) == 2
    assert 'oid=42' in api.mutations[0] and 'NOLOGIN' in api.mutations[0]
    assert 'pid=123' in api.mutations[1] and 'backend_start=' in api.mutations[1]
    assert all('DROP' not in sql and 'CASCADE' not in sql for sql in api.mutations)


def test_unexpected_session_disables_login_without_terminating_it():
    api = Provider(); api.sessions = [dict(pid=123, application_name='other', backend_start=datetime.now(timezone.utc).isoformat())]
    with pytest.raises(temporary.ContractError):
        temporary.revoke_login(api, 42, datetime.now(timezone.utc) - timedelta(seconds=2), 'ours')
    assert len(api.mutations) == 1 and 'NOLOGIN' in api.mutations[0]


def test_ambiguous_create_response_still_revokes_owned_role(config, tmp_path, monkeypatch):
    api = Provider()
    def uncertain(*args, **kwargs):
        api.row['rolcanlogin'] = True
        raise temporary.ContractError('uncertain response')
    api.request = uncertain
    monkeypatch.setattr(temporary, 'Management', lambda config: api)
    monkeypatch.setattr(temporary.backup, 'check_identity', lambda *args: None)
    monkeypatch.setattr(temporary.backup, 'run', lambda *args, **kwargs: b'2.75.0\n')
    root = tmp_path / 'archive'
    with pytest.raises(temporary.ContractError):
        temporary.capture(config, 'a' * 40, root, tmp_path / 'key', tmp_path / 'recipients', tmp_path)
    assert api.row['rolcanlogin'] is False
    receipts = list(root.glob('lifecycle-*.json'))
    assert len(receipts) == 1
    evidence = json.loads(receipts[0].read_text())
    assert evidence['production_backup'] is False and evidence['credential_expired'] is True
    assert not list(root.glob('*/database.tar.gz.age'))


def test_failed_dump_revokes_login_and_never_packs(config, tmp_path, monkeypatch):
    api = Provider()
    monkeypatch.setattr(temporary, 'Management', lambda config: api)
    monkeypatch.setattr(temporary.backup, 'check_identity', lambda *args: None)
    def command(args, **kwargs):
        if args[0] == 'supabase': return b'2.75.0\n'
        return ('supabase_read_only_user|' + temporary.ROLE + '|on|t|t|t|t\n').encode()
    monkeypatch.setattr(temporary.backup, 'run', command)
    monkeypatch.setattr(temporary.backup, 'capture_dumps', lambda *args: (_ for _ in ()).throw(temporary.ContractError('dump failed')))
    monkeypatch.setattr(temporary.backup, 'pack', lambda *args, **kwargs: pytest.fail('failed dump published'))
    with pytest.raises(temporary.ContractError):
        temporary.capture(config, 'a' * 40, tmp_path / 'archive', tmp_path / 'key', tmp_path / 'recipients', tmp_path)
    assert api.row['rolcanlogin'] is False
    assert any('NOLOGIN' in statement for statement in api.mutations)
