import json
from pathlib import Path
import sqlite3
import tempfile
import unittest
from contextlib import closing
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import threading

import tkinter as tk

from codex_switcher import (
    BUILTIN_OFFICIAL_ID,
    CheckOption,
    DpapiVault,
    Provider,
    SwitchEngine,
    fetch_provider_models,
    merge_toml,
    native_official_config,
    normalize_auth,
    set_language,
    sync_history,
    tr,
)


class CoreTests(unittest.TestCase):
    def test_language_switch_translates_logs_and_prompts(self):
        try:
            set_language("en")
            self.assertEqual(tr("execution_log"), "Execution log")
            self.assertIn("Target: API", tr("confirm_close", name="API"))
            self.assertIn("scanned 3", tr("switch_complete", rollouts=3, changed=2, updated=1, inserted=0))
        finally:
            set_language("zh-CN")

    def test_native_official_config_removes_api_override(self):
        config = (
            'model_provider = "openai"\nmodel = "third-party-model"\n'
            '[model_providers.openai]\nbase_url = "https://api.example.test/v1"\n'
            '[features]\napps = true\n'
        )
        restored = native_official_config(config)
        self.assertIn('model_provider = "openai"', restored)
        self.assertNotIn('third-party-model', restored)
        self.assertNotIn('[model_providers.openai]', restored)
        self.assertIn('[features]', restored)

    def test_builtin_official_provider_is_always_available(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            (home / "config.toml").write_text('model_provider = "custom"\n', encoding="utf-8")
            engine = SwitchEngine(home, lambda _message: None)
            engine.vault = DpapiVault(home / "profiles.dpapi")
            engine.vault.save({
                "third-party": {
                    "name": "API",
                    "config": (
                        'model_provider = "custom"\n'
                        '[model_providers.custom]\nname = "API"\nbase_url = "https://example.test/v1"\n'
                    ),
                    "auth": {"OPENAI_API_KEY": "key", "auth_mode": "apikey"},
                }
            })
            providers = engine.providers()
            self.assertEqual(providers[0].id, BUILTIN_OFFICIAL_ID)
            self.assertEqual(providers[1].name, "API")
            self.assertTrue(providers[0].is_official)
            self.assertEqual(providers[0].kind_label, "官方账号")

    def test_official_login_is_recovered_from_backup_and_encrypted(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            backup = home / "switcher_backups" / "backup-1" / "files"
            backup.mkdir(parents=True)
            official_auth = {
                "auth_mode": "chatgpt",
                "OPENAI_API_KEY": None,
                "tokens": {"refresh_token": "refresh", "access_token": "access"},
            }
            (backup / "auth.json").write_text(json.dumps(official_auth), encoding="utf-8")
            (backup / "config.toml").write_text('model_provider = "openai"\n', encoding="utf-8")
            engine = SwitchEngine(home, lambda _message: None)
            engine.vault = DpapiVault(home / "profiles.dpapi")
            official = engine.providers()[0]
            self.assertEqual(official.auth["auth_mode"], "chatgpt")
            self.assertEqual(official.source, "内置 · 已保存登录")
            saved = engine.vault.load()[BUILTIN_OFFICIAL_ID]
            self.assertEqual(saved["auth"]["tokens"]["refresh_token"], "refresh")

    def test_merge_toml_provider_overrides_common(self):
        base = 'model = "official"\n[desktop]\nfont = 12\n[features]\nx = true\n'
        overlay = 'model = "third"\nmodel_provider = "custom"\n[model_providers.custom]\nbase_url = "https://example.test/v1"\nwire_api = "responses"\nrequires_openai_auth = true\n'
        merged = merge_toml(base, overlay)
        self.assertIn('model = "third"', merged)
        self.assertNotIn('model = "official"', merged)
        self.assertIn('[desktop]', merged)
        self.assertIn('[model_providers.custom]', merged)

    def test_custom_auth_is_normalized(self):
        result = normalize_auth({"OPENAI_API_KEY": " secret ", "tokens": {"access_token": "old"}}, "custom")
        self.assertEqual(result, {"OPENAI_API_KEY": "secret", "auth_mode": "apikey"})

    def test_check_option_uses_tick_not_x(self):
        root = tk.Tk()
        root.withdraw()
        try:
            value = tk.BooleanVar(root, value=True)
            option = CheckOption(root, "检测 API", value)
            self.assertEqual(option.cget("text"), "☑ 检测 API")
            option.invoke()
            self.assertEqual(option.cget("text"), "☐ 检测 API")
        finally:
            root.destroy()

    def test_new_provider_is_saved_encrypted_without_switching(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            original = 'model = "official"\n'
            (home / "config.toml").write_text(original, encoding="utf-8")
            engine = SwitchEngine(home, lambda _message: None)
            engine.vault = DpapiVault(home / "profiles.dpapi")
            provider = engine.add_custom_provider(
                "My API", "https://example.test/v1/", "secret-key", "model-x"
            )
            self.assertEqual((home / "config.toml").read_text(encoding="utf-8"), original)
            self.assertEqual(provider.name, "My API")
            saved = engine.vault.load()[provider.id]
            self.assertEqual(saved["managed_by"], "CodexShift")
            self.assertEqual(saved["auth"]["OPENAI_API_KEY"], "secret-key")
            self.assertIn('base_url = "https://example.test/v1"', saved["config"])

    def test_vaults_at_different_paths_are_isolated(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            first = DpapiVault(root / "first" / "profiles.dpapi")
            second = DpapiVault(root / "second" / "profiles.dpapi")
            first.save({"provider": {"name": "First"}})
            second.save({"provider": {"name": "Second"}})
            self.assertEqual(first.load()["provider"]["name"], "First")
            self.assertEqual(second.load()["provider"]["name"], "Second")

    def test_provider_can_be_edited_and_deleted(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            engine = SwitchEngine(home, lambda _message: None)
            engine.vault = DpapiVault(home / "profiles.dpapi")
            provider = engine.add_custom_provider("Old", "https://old.test/v1", "key-1", "model-a")
            updated = engine.save_custom_provider(
                provider, "New", "https://new.test/v1", "", "model-b"
            )
            self.assertEqual(updated.id, provider.id)
            self.assertEqual(updated.name, "New")
            saved = engine.vault.load()[provider.id]
            self.assertEqual(saved["auth"]["OPENAI_API_KEY"], "key-1")
            self.assertIn('base_url = "https://new.test/v1"', saved["config"])
            engine.delete_provider(updated)
            self.assertNotIn(provider.id, engine.vault.load())

    def test_current_api_profile_is_imported_without_external_store(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            config = (
                'model_provider = "custom"\nmodel = "model-a"\n'
                '[model_providers.custom]\nname = "Current API"\n'
                'base_url = "https://current.test/v1"\n'
            )
            (home / "config.toml").write_text(config, encoding="utf-8")
            (home / "auth.json").write_text(
                json.dumps({"OPENAI_API_KEY": "current-key", "auth_mode": "apikey"}),
                encoding="utf-8",
            )
            engine = SwitchEngine(home, lambda _message: None)
            engine.vault = DpapiVault(home / "profiles.dpapi")
            providers = engine.providers()
            self.assertEqual(providers[1].name, "Current API")
            saved = engine.vault.load()
            self.assertEqual(len(saved), 1)
            self.assertTrue(next(iter(saved.values()))["imported_from_current"])

    def test_model_discovery_parses_openai_compatible_response(self):
        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                if self.path != "/v1/models" or self.headers.get("Authorization") != "Bearer key-1":
                    self.send_response(401)
                    self.end_headers()
                    return
                body = json.dumps({"data": [{"id": "model-b"}, {"id": "model-a"}, {"id": "model-a"}]}).encode()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, *_args):
                pass

        server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            port = server.server_address[1]
            config = (
                'model_provider = "custom"\nmodel = "model-a"\n'
                '[model_providers.custom]\n'
                f'base_url = "http://127.0.0.1:{port}/v1"\n'
            )
            provider = Provider("test", "Test", config, {"OPENAI_API_KEY": "key-1"})
            self.assertEqual(fetch_provider_models(provider), ["model-a", "model-b"])
        finally:
            server.shutdown()
            server.server_close()

    def test_sync_history_rewrites_and_inserts_root_thread(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            session = home / "sessions" / "2026" / "01" / "01" / "rollout-test.jsonl"
            session.parent.mkdir(parents=True)
            records = [
                {"timestamp": "2026-01-01T00:00:00Z", "type": "session_meta", "payload": {
                    "id": "thread-1", "timestamp": "2026-01-01T00:00:00Z", "cwd": str(home),
                    "source": "vscode", "thread_source": "user", "model_provider": "custom"
                }},
                {"timestamp": "2026-01-01T00:00:01Z", "type": "turn_context", "payload": {"model_provider": "custom"}},
                {"timestamp": "2026-01-01T00:00:02Z", "type": "response_item", "payload": {
                    "role": "user", "content": [{"type": "input_text", "text": "hello"}]
                }},
            ]
            session.write_text("".join(json.dumps(x) + "\n" for x in records), encoding="utf-8")
            db = home / "state_5.sqlite"
            with closing(sqlite3.connect(db)) as con:
                con.execute("""CREATE TABLE threads (
                    id TEXT PRIMARY KEY, rollout_path TEXT NOT NULL, created_at INTEGER NOT NULL,
                    updated_at INTEGER NOT NULL, source TEXT NOT NULL, model_provider TEXT NOT NULL,
                    cwd TEXT NOT NULL, title TEXT NOT NULL, sandbox_policy TEXT NOT NULL,
                    approval_mode TEXT NOT NULL, has_user_event INTEGER NOT NULL DEFAULT 0,
                    archived INTEGER NOT NULL DEFAULT 0, cli_version TEXT NOT NULL DEFAULT '',
                    thread_source TEXT, first_user_message TEXT NOT NULL DEFAULT '',
                    created_at_ms INTEGER, updated_at_ms INTEGER, preview TEXT NOT NULL DEFAULT '',
                    recency_at INTEGER NOT NULL DEFAULT 0, recency_at_ms INTEGER NOT NULL DEFAULT 0
                )""")
                con.commit()
            stats = sync_history(home, "openai", None)
            self.assertEqual(stats["changed"], 1)
            self.assertEqual(stats["inserted"], 1)
            content = session.read_text(encoding="utf-8")
            self.assertNotIn('"model_provider":"custom"', content)
            with closing(sqlite3.connect(db)) as con:
                row = con.execute("SELECT id,model_provider,title FROM threads").fetchone()
            self.assertEqual(row, ("thread-1", "openai", "hello"))


if __name__ == "__main__":
    unittest.main()
