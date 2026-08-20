import json
from pathlib import Path
import sqlite3
import subprocess
import tempfile
import unittest
from unittest import mock
from contextlib import closing
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import threading

import tkinter as tk

import codex_switcher

from codex_switcher import (
    BUILTIN_OFFICIAL_ID,
    CheckOption,
    DeepSeekHarnessClient,
    DpapiVault,
    MigrationProject,
    MigrationSession,
    Provider,
    SwitchEngine,
    _codex_history_text,
    _codex_history_messages,
    _dsh_native_events,
    _dsh_runtime_paths,
    _run_dsh_native_bridge,
    _codex_rollout_from_dsh,
    _dsh_event_text,
    _extract_user_request,
    discover_deepseek_harness_url,
    fetch_provider_models,
    merge_toml,
    migration_item_total,
    native_official_config,
    normalize_auth,
    register_codex_imports,
    repair_dsh_import_visibility,
    run_codex_import,
    scan_codex_migration,
    set_language,
    sync_history,
    tr,
)


class CoreTests(unittest.TestCase):
    @staticmethod
    def _create_threads_db(path: Path) -> None:
        with closing(sqlite3.connect(path)) as con:
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

    def test_language_switch_translates_logs_and_prompts(self):
        try:
            set_language("en")
            self.assertEqual(tr("execution_log"), "Execution log")
            self.assertIn("Target: API", tr("confirm_close", name="API"))
            self.assertIn("scanned 3", tr("switch_complete", rollouts=3, changed=2, updated=1, inserted=0))
        finally:
            set_language("zh-CN")

    def test_migration_progress_text_is_localized(self):
        try:
            set_language("en")
            self.assertEqual(tr("migration_progress_title"), "Import progress")
            self.assertIn("2/5", tr("migration_progress_item", current=2, total=5, title="Demo"))
            set_language("zh-CN")
            self.assertIn("正在导入 2/5", tr("migration_progress_item", current=2, total=5, title="演示"))
        finally:
            set_language("zh-CN")

    def test_migration_progress_counts_projects_or_sessions(self):
        projects = [
            (MigrationProject("p1", "One", "C:/one", "codex", 2), [
                MigrationSession("s1", "A", "C:/one", "codex", 1),
                MigrationSession("s2", "B", "C:/one", "codex", 2),
            ]),
            (MigrationProject("p2", "Two", "C:/two", "codex", 1), [
                MigrationSession("s3", "C", "C:/two", "codex", 3),
            ]),
        ]
        self.assertEqual(migration_item_total(projects, "full"), 3)
        self.assertEqual(migration_item_total(projects, "project"), 2)

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
            self._create_threads_db(db)
            stats = sync_history(home, "openai", None)
            self.assertEqual(stats["changed"], 1)
            self.assertEqual(stats["inserted"], 1)
            content = session.read_text(encoding="utf-8")
            self.assertNotIn('"model_provider":"custom"', content)
            with closing(sqlite3.connect(db)) as con:
                row = con.execute("SELECT id,model_provider,title FROM threads").fetchone()
            self.assertEqual(row, ("thread-1", "openai", "hello"))

    def test_codex_migration_scan_groups_projects_and_reads_history(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            session_dir = home / "sessions" / "2026" / "01" / "01"
            session_dir.mkdir(parents=True)
            project_a = home / "project-a"
            project_b = home / "project-b"
            for index, project in enumerate((project_a, project_b), 1):
                records = [
                    {"type": "session_meta", "payload": {"id": f"session-{index}", "cwd": str(project)}},
                    {"type": "response_item", "payload": {"role": "user", "content": [{"type": "input_text", "text": "# AGENTS.md instructions\n<INSTRUCTIONS>workspace rules</INSTRUCTIONS>"}]}},
                    {"type": "response_item", "payload": {"role": "user", "content": [{"type": "input_text", "text": f"request {index}"}]}},
                    {"type": "response_item", "payload": {"role": "assistant", "content": [{"type": "output_text", "text": f"answer {index}"}]}},
                ]
                (session_dir / f"rollout-{index}.jsonl").write_text(
                    "".join(json.dumps(row) + "\n" for row in records), encoding="utf-8"
                )
            projects, sessions = scan_codex_migration(home)
            self.assertEqual(len(projects), 2)
            self.assertEqual(sum(item.session_count for item in projects), 2)
            first_session = sessions[projects[0].id][0]
            self.assertTrue(first_session.title.startswith("request"))
            self.assertIn("answer", first_session.preview)
            history = _codex_history_text(Path(first_session.artifact_path))
            self.assertIn("**user**", history)
            self.assertIn("**assistant**", history)

    def test_codex_history_messages_preserve_native_roles(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "rollout.jsonl"
            path.write_text("".join(json.dumps(row) + "\n" for row in [
                {"type": "response_item", "payload": {"role": "user", "content": [{"text": "# AGENTS.md instructions\n<INSTRUCTIONS>x</INSTRUCTIONS>"}]}},
                {"type": "response_item", "payload": {"role": "user", "content": [{"text": "question"}]}},
                {"type": "response_item", "payload": {"role": "assistant", "content": [{"text": "answer"}]}},
            ]), encoding="utf-8")
            self.assertEqual(_codex_history_messages(path), [("user", "question"), ("assistant", "answer")])

    def test_dsh_native_events_are_contiguous_and_turn_balanced(self):
        events = _dsh_native_events([
            ("user", "first"), ("user", "clarification"), ("assistant", "reply"),
            ("user", "next"), ("assistant", "done"),
        ], now_ms=1000)
        self.assertEqual([event["seq"] for event in events], list(range(len(events))))
        self.assertEqual(events[0]["type"], "turn/start")
        self.assertEqual(events[-1]["type"], "turn/end")
        self.assertEqual([event["data"]["turn"] for event in events if event["type"] == "turn/start"], [1, 2])
        visible = [event for event in events if event["type"] in {"user/message", "assistant/message"}]
        self.assertEqual(len(visible), 5)
        self.assertTrue(all(event["surfaceOp"] == "append" for event in visible))
        assistant = next(event for event in visible if event["type"] == "assistant/message")
        self.assertEqual(assistant["data"]["message"]["source"]["provider"], "codex-import")

    def test_dsh_native_bridge_writes_and_verifies_isolated_session(self):
        try:
            _dsh_runtime_paths()
        except Exception as exc:
            self.skipTest(f"DeepSeek Harness runtime unavailable: {exc}")
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "sessions"
            events = _dsh_native_events([
                ("user", "hello ฅ(๑˃̵ᴗ˂̵)و"), ("assistant", "世界喵~"),
            ], now_ms=1000)
            session_id = "session-native-import-test"
            result = _run_dsh_native_bridge("import", {
                "id": session_id, "createdAt": 1000, "cwd": str(Path(tmp).resolve()),
                "events": events, "visibleCount": 2,
            }, root=root)
            self.assertEqual(result["visibleCount"], 2)
            self.assertTrue(Path(result["artifact"]).is_file())
            removed = _run_dsh_native_bridge("remove", {"id": session_id}, root=root)
            self.assertTrue(removed["removed"])

    def test_dsh_native_bridge_does_not_scan_all_sessions(self):
        self.assertNotIn("sessionPersistence.list()", codex_switcher.DSH_NATIVE_BRIDGE)

    def test_dsh_native_bridge_timeout_is_short_and_does_not_leak_script(self):
        timeout = subprocess.TimeoutExpired(["node", "<large internal script>"], 90)
        with mock.patch.object(codex_switcher, "_dsh_runtime_paths", return_value=(Path("node"), Path.cwd())):
            with mock.patch.object(codex_switcher.subprocess, "run", side_effect=timeout):
                with self.assertRaises(Exception) as caught:
                    _run_dsh_native_bridge("import", {"id": "session-test"}, root=Path.cwd() / "sessions")
        message = str(caught.exception)
        self.assertIn("等待超时", message)
        self.assertNotIn("internal script", message)
        self.assertNotIn("import {", message)

    def test_codex_request_wrapper_is_reduced_to_visible_request(self):
        wrapped = (
            "# Files mentioned by the user:\n\n## image.png\n\n"
            "<environment_context><cwd>C:/project</cwd></environment_context>\n\n"
            "## My request:\n请按项目分类显示会话"
        )
        self.assertEqual(_extract_user_request(wrapped), "请按项目分类显示会话")
        self.assertEqual(_extract_user_request("普通请求"), "普通请求")
        self.assertEqual(_extract_user_request("# AGENTS.md instructions\n<INSTRUCTIONS>x</INSTRUCTIONS>"), "")
        self.assertEqual(_extract_user_request("## My request:\n显示项目 <image name=[Image #1] path=\"C:/tmp/a.png\">"), "显示项目")

    def test_codex_migration_merges_extended_windows_project_paths(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            folder = home / "sessions" / "2026" / "01" / "01"
            folder.mkdir(parents=True)
            normal = r"C:\Users\Example\Project"
            extended = r"\\?\C:\Users\Example\Project"
            for index, cwd in enumerate((normal, extended), 1):
                records = [
                    {"type": "session_meta", "payload": {"id": f"thread-{index}", "cwd": cwd, "thread_source": "user"}},
                    {"type": "response_item", "payload": {"role": "user", "content": [{"text": f"task {index}"}]}},
                ]
                (folder / f"rollout-{index}.jsonl").write_text(
                    "".join(json.dumps(row) + "\n" for row in records), encoding="utf-8"
                )
            projects, sessions = scan_codex_migration(home)
            self.assertEqual(len(projects), 1)
            self.assertEqual(projects[0].name, "Project")
            self.assertEqual(len(sessions[projects[0].id]), 2)

    def test_codex_migration_uses_real_project_assignments_and_recent_section(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            folder = home / "sessions" / "2026" / "01" / "01"
            folder.mkdir(parents=True)
            project_root = home / "real-project"
            standalone_root = home / "generated-chat"
            for thread_id, cwd, title in (
                ("assigned-thread", project_root, "project task"),
                ("recent-thread", standalone_root, "standalone task"),
            ):
                records = [
                    {"type": "session_meta", "payload": {"id": thread_id, "cwd": str(cwd), "thread_source": "user"}},
                    {"type": "response_item", "payload": {"role": "user", "content": [{"text": title}]}},
                ]
                (folder / f"rollout-{thread_id}.jsonl").write_text(
                    "".join(json.dumps(row) + "\n" for row in records), encoding="utf-8"
                )
            (home / ".codex-global-state.json").write_text(json.dumps({
                "local-projects": {
                    "local-project": {"id": "local-project", "name": "Actual Project", "rootPaths": [str(project_root)]}
                },
                "project-order": ["local-project"],
                "thread-project-assignments": {
                    "assigned-thread": {"projectKind": "local", "projectId": "local-project"}
                },
                "projectless-thread-ids": ["recent-thread"],
            }), encoding="utf-8")
            projects, sessions = scan_codex_migration(home)
            self.assertEqual([project.name for project in projects], ["Actual Project", "最近"])
            self.assertEqual(projects[0].source, "codex")
            self.assertEqual(projects[1].source, "codex-recent")
            self.assertEqual(sessions[projects[0].id][0].title, "project task")
            self.assertEqual(sessions[projects[1].id][0].title, "standalone task")

    def test_dsh_event_parser_supports_messages_and_tool_results(self):
        user = {"type": "user/message", "data": {"message": {"content": [{"type": "text", "text": "hello"}]}}}
        assistant = {"type": "assistant/message", "data": {"content": [{"text": "world"}]}}
        tool = {"type": "tool/result", "data": {"content": [{"output": "done"}]}}
        self.assertEqual(_dsh_event_text(user), ("user", "hello"))
        self.assertEqual(_dsh_event_text(assistant), ("assistant", "world"))
        self.assertEqual(_dsh_event_text(tool), ("assistant", "done"))
        self.assertIsNone(_dsh_event_text({"type": "system/status", "data": {}}))

    def test_deepseek_harness_client_uses_json_rpc_envelope(self):
        captured = []

        class Handler(BaseHTTPRequestHandler):
            def do_POST(self):
                length = int(self.headers.get("Content-Length", "0"))
                request = json.loads(self.rfile.read(length))
                captured.append((self.path, request))
                body = json.dumps({"result": {"ok": True, "value": {"items": [{
                    "workspaceId": "workspace-1", "title": "Project", "path": str(Path(tempfile.gettempdir()) / "project"), "sessionIds": []
                }]}}}).encode()
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
            client = DeepSeekHarnessClient(f"http://127.0.0.1:{server.server_address[1]}")
            projects = client.list_projects()
            self.assertEqual(projects[0].workspace_id, "workspace-1")
            path, request = captured[0]
            self.assertEqual(path, "/api/workspace.list")
            self.assertEqual(request["type"], "client-request")
            self.assertEqual(request["method"], "workspace.list")
            self.assertTrue(request["rpcId"])
        finally:
            server.shutdown()
            server.server_close()

    def test_deepseek_harness_session_list_omits_empty_cursor(self):
        captured = []

        class Handler(BaseHTTPRequestHandler):
            def do_POST(self):
                length = int(self.headers.get("Content-Length", "0"))
                request = json.loads(self.rfile.read(length))
                captured.append(request)
                if request["method"] == "workspace.list":
                    value = {"items": [], "archivedSessionIds": []}
                else:
                    value = {"items": []}
                body = json.dumps({"result": {"ok": True, "value": value}}).encode()
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
            DeepSeekHarnessClient(f"http://127.0.0.1:{server.server_address[1]}").list_sessions()
            session_request = next(row for row in captured if row["method"] == "session.list")
            self.assertEqual(session_request["payload"], {})
        finally:
            server.shutdown()
            server.server_close()

    def test_deepseek_harness_dynamic_port_is_discovered(self):
        class Handler(BaseHTTPRequestHandler):
            def do_POST(self):
                body = json.dumps({"result": {"ok": True, "value": {
                    "items": [], "archivedSessionIds": [],
                }}}).encode()
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
            with mock.patch.object(codex_switcher, "_deepseek_harness_listener_ports", return_value={port}):
                detected = discover_deepseek_harness_url("http://127.0.0.1:1")
            self.assertEqual(detected, f"http://127.0.0.1:{port}")
        finally:
            server.shutdown()
            server.server_close()

    def test_deepseek_harness_client_rejects_remote_history_upload(self):
        with self.assertRaises(Exception):
            DeepSeekHarnessClient("https://example.test:3080")

    def test_dsh_history_converts_to_codex_rollout_and_index(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            project_path = home / "project"
            project_path.mkdir()
            project = MigrationProject("project-1", "Project", str(project_path), "dsh", 1, "workspace-1")
            session = MigrationSession("dsh-session", "Fix the bug", str(project_path), "dsh", 1)
            events = [
                {"type": "user/message", "data": {"content": [{"text": "original question"}]}},
                {"type": "assistant/message", "data": {"content": [{"text": "original answer"}]}},
            ]
            path, records = _codex_rollout_from_dsh(home, session, project, events, "openai", "full")
            self.assertTrue(str(path).startswith(str(home / "sessions")))
            self.assertEqual(records[0]["type"], "session_meta")
            self.assertEqual(records[0]["payload"]["cwd"], str(project_path))
            self.assertEqual(records[0]["payload"]["source"], "vscode")
            self.assertEqual(records[0]["payload"]["originator"], "CodexShift")
            self.assertEqual(records[1]["payload"]["role"], "user")
            self.assertEqual(records[1]["payload"]["content"][0]["text"], "original question")
            self.assertEqual(records[2]["type"], "event_msg")
            self.assertEqual(records[2]["payload"]["type"], "user_message")
            self.assertEqual(records[4]["payload"]["type"], "agent_message")
            self.assertNotIn("Imported from DeepSeek Harness", json.dumps(records))
            self.assertEqual(records[-1]["payload"]["type"], "agent_message")
            path.parent.mkdir(parents=True)
            path.write_text("".join(json.dumps(row) + "\n" for row in records), encoding="utf-8")
            self._create_threads_db(home / "state_5.sqlite")
            stats = sync_history(home, "openai", None)
            self.assertEqual(stats["inserted"], 1)
            with closing(sqlite3.connect(home / "state_5.sqlite")) as con:
                row = con.execute("SELECT cwd,title,model_provider FROM threads").fetchone()
            self.assertEqual(row[0], str(project_path))
            self.assertIn("Fix the bug", row[1])
            self.assertEqual(row[2], "openai")

    def test_dsh_handoff_keeps_recent_messages_as_native_roles(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            project_path = home / "project"
            project_path.mkdir()
            project = MigrationProject("project-1", "Project", str(project_path), "dsh", 1)
            session = MigrationSession("session-12345678-abcd", "session-12345678-abcd", str(project_path), "dsh", 1)
            events = [
                {"type": "user/message" if index % 2 == 0 else "assistant/message", "data": {"content": [{"text": f"message {index}"}]}}
                for index in range(14)
            ]
            _path, records = _codex_rollout_from_dsh(home, session, project, events, "openai", "handoff")
            messages = [row for row in records[1:] if row["type"] == "response_item"]
            self.assertEqual(len(messages), 12)
            self.assertEqual(messages[0]["payload"]["content"][0]["text"], "message 2")
            self.assertEqual([row["payload"]["role"] for row in messages[:2]], ["user", "assistant"])
            self.assertEqual(len([row for row in records if row["type"] == "event_msg"]), 12)
            self.assertEqual(records[0]["payload"]["title"], "message 0")

    def test_register_codex_imports_creates_and_reuses_project_assignment(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            project_path = home / "project"
            project_path.mkdir()
            self._create_threads_db(home / "state_5.sqlite")
            with closing(sqlite3.connect(home / "state_5.sqlite")) as con:
                for thread_id in ("thread-1", "thread-2"):
                    con.execute("""INSERT INTO threads
                        (id,rollout_path,created_at,updated_at,source,model_provider,cwd,title,sandbox_policy,
                         approval_mode,has_user_event,archived,cli_version,thread_source,first_user_message,
                         created_at_ms,updated_at_ms,preview,recency_at,recency_at_ms)
                        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                        (thread_id, str(home / f"{thread_id}.jsonl"), 1, 1, "codexshift-dsh-import", "openai",
                         str(project_path), "old", "{}", "on-request", 0, 0, "", "user", "old", 1000,
                         1000, "old", 1, 1000))
                con.commit()
            state_path = home / ".codex-global-state.json"
            state_path.write_text(json.dumps({
                "local-projects": {"existing-project": {
                    "id": "existing-project", "name": "Existing", "rootPaths": [str(project_path)]
                }},
                "project-order": ["existing-project"],
                "thread-project-assignments": {},
                "projectless-thread-ids": ["thread-1", "thread-2"],
            }), encoding="utf-8")
            project = MigrationProject("p", "Project", str(project_path), "dsh", 2)
            register_codex_imports(home, [
                ("thread-1", "Title one", str(project_path)),
                ("thread-2", "Title two", str(project_path)),
            ], [project])
            state = json.loads(state_path.read_text(encoding="utf-8"))
            self.assertEqual(len(state["local-projects"]), 1)
            self.assertEqual(state["thread-project-assignments"]["thread-1"]["projectId"], "existing-project")
            self.assertEqual(state["projectless-thread-ids"], [])
            with closing(sqlite3.connect(home / "state_5.sqlite")) as con:
                rows = list(con.execute("SELECT id,source,title,sandbox_policy,approval_mode FROM threads ORDER BY id"))
            self.assertEqual(rows[0][1:3], ("vscode", "Title one"))
            self.assertEqual(json.loads(rows[0][3]), {"type": "disabled"})
            self.assertEqual(rows[0][4], "never")

    def test_register_project_only_does_not_create_rollout(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            project_path = home / "project"
            project_path.mkdir()
            project = MigrationProject("p", "Project", str(project_path), "dsh", 0)
            stats = register_codex_imports(home, [], [project])
            self.assertEqual(stats, {"projects": 1, "threads": 0})
            self.assertFalse((home / "sessions").exists())
            state = json.loads((home / ".codex-global-state.json").read_text(encoding="utf-8"))
            self.assertEqual(len(state["local-projects"]), 1)

    def test_repair_old_dsh_import_makes_it_visible(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            project_path = home / "project"
            project_path.mkdir()
            rollout = home / "sessions" / "2026" / "01" / "01" / "rollout-old.jsonl"
            rollout.parent.mkdir(parents=True)
            rollout.write_text("".join(json.dumps(row) + "\n" for row in [
                {"type": "session_meta", "payload": {"id": "old-import", "cwd": str(project_path), "source": "codexshift-dsh-import", "model_provider": "openai"}},
                {"type": "response_item", "payload": {"role": "user", "content": [{"text": "Imported from DeepSeek Harness: session-old\nOriginal session ID: session-old"}]}},
                {"type": "response_item", "payload": {"role": "user", "content": [{"text": "real question"}]}},
            ]), encoding="utf-8")
            self._create_threads_db(home / "state_5.sqlite")
            sync_history(home, "openai", None)
            stats = repair_dsh_import_visibility(home)
            self.assertEqual(stats["repaired"], 1)
            self.assertIn('"source":"vscode"', rollout.read_text(encoding="utf-8"))
            self.assertIn('"originator":"CodexShift"', rollout.read_text(encoding="utf-8"))
            repaired_rows = [json.loads(line) for line in rollout.read_text(encoding="utf-8").splitlines()]
            visible = [row["payload"]["type"] for row in repaired_rows if row["type"] == "event_msg"]
            self.assertEqual(visible, ["user_message"])
            state = json.loads((home / ".codex-global-state.json").read_text(encoding="utf-8"))
            self.assertIn("old-import", state["thread-project-assignments"])
            with closing(sqlite3.connect(home / "state_5.sqlite")) as con:
                row = con.execute("SELECT source,title FROM threads WHERE id='old-import'").fetchone()
            self.assertEqual(row, ("vscode", "real question"))

    def test_repair_dsh_import_with_native_source_but_missing_originator(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            project_path = home / "project"
            project_path.mkdir()
            rollout = home / "sessions" / "2026" / "01" / "01" / "rollout-current.jsonl"
            rollout.parent.mkdir(parents=True)
            rollout.write_text("".join(json.dumps(row) + "\n" for row in [
                {"type": "session_meta", "payload": {
                    "id": "current-import", "session_id": "current-import", "cwd": str(project_path),
                    "timestamp": "2026-01-01T00:00:00Z", "source": "vscode", "thread_source": "user",
                    "model_provider": "openai", "cli_version": codex_switcher.APP_VERSION, "title": "Imported title",
                }},
                {"type": "response_item", "payload": {"role": "user", "content": [{"text": "question"}]}},
            ]), encoding="utf-8")
            stats = repair_dsh_import_visibility(home)
            self.assertEqual(stats["repaired"], 1)
            meta = json.loads(rollout.read_text(encoding="utf-8").splitlines()[0])["payload"]
            self.assertEqual(meta["originator"], "CodexShift")
            self.assertEqual(meta["source"], "vscode")
            rows = [json.loads(line) for line in rollout.read_text(encoding="utf-8").splitlines()]
            self.assertIn("user_message", [row["payload"].get("type") for row in rows if row["type"] == "event_msg"])

    def test_codex_import_closes_and_restarts_codex_automatically(self):
        calls = []
        with mock.patch.object(codex_switcher, "running_codex_processes", return_value=["ChatGPT.exe"]), \
             mock.patch.object(codex_switcher, "close_codex_processes", side_effect=lambda _log: calls.append("close")), \
             mock.patch.object(codex_switcher, "restart_codex", side_effect=lambda: calls.append("restart")):
            result = run_codex_import(lambda: calls.append("import") or 3, lambda _message: None)
        self.assertEqual(result, 3)
        self.assertEqual(calls, ["close", "import", "restart"])

    def test_codex_import_restarts_codex_after_failure(self):
        calls = []
        with mock.patch.object(codex_switcher, "running_codex_processes", return_value=[]), \
             mock.patch.object(codex_switcher, "close_codex_processes", side_effect=lambda _log: calls.append("close")), \
             mock.patch.object(codex_switcher, "restart_codex", side_effect=lambda: calls.append("restart")):
            with self.assertRaisesRegex(RuntimeError, "failed"):
                run_codex_import(lambda: (_ for _ in ()).throw(RuntimeError("failed")), lambda _message: None)
        self.assertEqual(calls, ["restart"])

    def test_scoped_history_sync_does_not_rewrite_existing_threads(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            session_dir = home / "sessions" / "2026" / "01" / "01"
            session_dir.mkdir(parents=True)
            existing = session_dir / "rollout-existing.jsonl"
            imported = session_dir / "rollout-imported.jsonl"
            existing.write_text(json.dumps({"type": "session_meta", "payload": {
                "id": "existing", "cwd": str(home), "model_provider": "custom"
            }}) + "\n", encoding="utf-8")
            imported.write_text("".join(json.dumps(row) + "\n" for row in [
                {"type": "session_meta", "payload": {"id": "imported", "cwd": str(home), "model_provider": "openai"}},
                {"type": "response_item", "payload": {"role": "user", "content": [{"text": "imported title"}]}},
            ]), encoding="utf-8")
            self._create_threads_db(home / "state_5.sqlite")
            with closing(sqlite3.connect(home / "state_5.sqlite")) as con:
                con.execute("""INSERT INTO threads
                    (id,rollout_path,created_at,updated_at,source,model_provider,cwd,title,sandbox_policy,
                     approval_mode,has_user_event,archived,cli_version,thread_source,first_user_message,
                     created_at_ms,updated_at_ms,preview,recency_at,recency_at_ms)
                    VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                    ("existing", str(existing), 1, 1, "vscode", "custom", str(home), "existing", "{}",
                     "on-request", 1, 0, "", "user", "existing", 1000, 1000, "existing", 1, 1000))
                con.commit()
            stats = sync_history(home, "openai", None, paths=[imported], rewrite_existing=False)
            self.assertEqual(stats["updated"], 0)
            self.assertEqual(stats["inserted"], 1)
            self.assertIn('"model_provider": "custom"', existing.read_text(encoding="utf-8"))
            with closing(sqlite3.connect(home / "state_5.sqlite")) as con:
                providers = dict(con.execute("SELECT id,model_provider FROM threads"))
            self.assertEqual(providers, {"existing": "custom", "imported": "openai"})


if __name__ == "__main__":
    unittest.main()
