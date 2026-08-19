from __future__ import annotations

import base64
import ctypes
from ctypes import wintypes
import datetime as dt
import getpass
import json
import locale
import os
from pathlib import Path
import re
import shutil
import sqlite3
import subprocess
import sys
import threading
import time
import tomllib
import uuid
from dataclasses import dataclass
from typing import Callable, Iterable
import urllib.error
import urllib.request
from contextlib import closing

import tkinter as tk
from tkinter import filedialog, ttk


APP_NAME = "CodexShift"
APP_VERSION = "1.7.0"
OFFICIAL_PROVIDER = "openai"
BUILTIN_OFFICIAL_ID = "codexshift-native-official"
PROCESS_NAMES = ("ChatGPT.exe", "codex.exe", "codex-code-mode-host.exe")
MAC_PROCESS_NAMES = ("Codex", "ChatGPT", "codex", "codex-code-mode-host")
SECRET_KEYS = {"OPENAI_API_KEY", "access_token", "refresh_token", "id_token"}
IS_WINDOWS = os.name == "nt"
IS_MACOS = sys.platform == "darwin"
UI_FONT = "PingFang SC" if IS_MACOS else "Microsoft YaHei UI"
MONO_FONT = "Menlo" if IS_MACOS else "Cascadia Mono"

LANGUAGE_LABELS = {
    "zh-CN": "简体中文",
    "en": "English",
    "ja": "日本語",
    "ko": "한국어",
}
CURRENT_LANGUAGE = "zh-CN"
TRANSLATIONS = {
    "en": {
        "subtitle": "Provider switching & history sync", "language_label": "Language",
        "current_connection": "Current connection", "refresh": "↻  Refresh", "path_settings": "Path",
        "provider_profiles": "Provider profiles", "profile_count": "{count} profiles",
        "new_profile": "＋  New", "edit": "Edit", "delete": "Delete",
        "type": "Type", "model": "Model", "source": "Source", "status": "Status",
        "official_account": "Official account", "third_party_api": "Third-party API", "current": "●  Active",
        "auto": "Auto", "unknown": "Unknown", "loading": "Loading…", "detecting": "Detecting…",
        "verify_on_switch": "Verify third-party API", "auto_close": "Close Codex automatically",
        "restart_after": "Reopen after switching", "switch_selected": "Switch to selected Provider  →",
        "test_api": "✓  Test API", "repair_history": "Repair history index", "open_backups": "Open backups",
        "execution_log": "Execution log", "select_profile": "Select a Provider first.",
        "builtin_official": "OpenAI official account (native)",
        "builtin_login_needed": "OpenAI official account (sign-in required)",
        "source_saved_login": "Built-in · Login saved", "source_login_needed": "Built-in · Sign-in required",
        "source_local": "Local encrypted profile", "read_profiles": "Loaded {count} local Providers.",
        "validating": "Validating the target API and credentials…", "closing_codex": "Closing Codex to avoid locked databases…",
        "writing_credentials": "Writing configuration and credentials atomically…",
        "syncing_history": "Synchronizing history Provider values and rebuilding indexes…",
        "switch_complete": "Switch complete: scanned {rollouts}, rewrote {changed}, updated {updated}, inserted {inserted}.",
        "official_login_ready": "Native OpenAI mode restored. Sign in to ChatGPT after opening Codex.",
        "rolling_back": "An error occurred. Rolling back automatically…", "restarting_codex": "Reopening Codex…",
        "scan_progress": "Scanned {index}/{total} history files…", "codex_closed": "Codex processes closed safely.",
        "imported_profile": "Encrypted and imported the current API profile “{name}” into CodexShift.",
        "skip_snapshot": "Skipped current profile snapshot: {error}", "operation_failed": "Failed: {error}",
        "testing_profile": "Testing API for “{name}”…", "api_passed": "API test passed: {result}",
        "repair_complete": "Repair complete: {stats}", "profile_deleted": "Deleted local profile “{name}”.",
        "home_changed": "Codex Home changed to: {path}", "home_auto": "Codex Home auto-detection restored: {path}",
        "choose_home": "Choose Codex Home…", "reset_home": "Restore auto-detection",
        "new_dialog": "New third-party API profile", "edit_dialog": "Edit third-party API profile",
        "profile_name": "Profile name", "model_name": "Model", "fetch_models": "Fetch models",
        "cancel": "Cancel", "save_profile": "Save profile", "save_changes": "Save changes",
        "new_hint": "You can test the API before saving. The active Codex configuration will not change.",
        "edit_hint": "Leave API Key blank to keep the current key. Switch again to apply changes.",
        "saved_profile": "{action} third-party profile “{name}”; credentials are encrypted.",
        "created": "Created", "updated_action": "Updated",
    },
    "ja": {
        "subtitle": "プロバイダー切替と履歴同期", "language_label": "言語", "current_connection": "現在の接続", "refresh": "↻  更新", "path_settings": "パス設定",
        "provider_profiles": "プロバイダー設定", "profile_count": "{count} 件", "new_profile": "＋  新規", "edit": "編集", "delete": "削除",
        "type": "種類", "model": "モデル", "source": "保存元", "status": "状態", "official_account": "公式アカウント",
        "third_party_api": "サードパーティ API", "current": "●  使用中", "auto": "自動", "unknown": "未認識",
        "loading": "読み込み中…", "detecting": "確認中…", "verify_on_switch": "切替時に API を確認",
        "auto_close": "Codex を自動終了", "restart_after": "完了後に再起動", "switch_selected": "選択した Provider に切替  →",
        "test_api": "✓  API 確認", "repair_history": "履歴インデックス修復", "open_backups": "バックアップを開く",
        "execution_log": "実行ログ", "select_profile": "Provider を選択してください。", "builtin_official": "OpenAI 公式アカウント（ネイティブ）",
        "builtin_login_needed": "OpenAI 公式アカウント（再ログイン必要）", "source_saved_login": "内蔵 · ログイン保存済み",
        "source_login_needed": "内蔵 · ログイン必要", "source_local": "ローカル暗号化設定", "read_profiles": "ローカル Provider を {count} 件読み込みました。",
        "validating": "接続先と認証情報を確認中…", "closing_codex": "データベース保護のため Codex を終了中…",
        "writing_credentials": "設定と認証情報を安全に書き込み中…", "syncing_history": "履歴とインデックスを同期中…",
        "switch_complete": "切替完了：履歴 {rollouts} 件、書換 {changed} 件、更新 {updated} 件、追加 {inserted} 件。",
        "official_login_ready": "公式モードに戻しました。Codex を開いて ChatGPT にログインしてください。",
        "rolling_back": "エラーが発生したため自動復元しています…", "restarting_codex": "Codex を再起動中…",
        "scan_progress": "履歴ファイル {index}/{total} 件を確認済み…", "codex_closed": "Codex を安全に終了しました。",
        "imported_profile": "現在の API 設定「{name}」を暗号化して取り込みました。", "skip_snapshot": "現在の設定保存をスキップ：{error}",
        "operation_failed": "失敗：{error}", "testing_profile": "「{name}」の API を確認中…", "api_passed": "API 確認成功：{result}",
        "repair_complete": "修復完了：{stats}", "profile_deleted": "ローカル設定「{name}」を削除しました。",
        "home_changed": "Codex Home を変更：{path}", "home_auto": "Codex Home の自動認識に戻しました：{path}",
        "choose_home": "Codex Home を選択…", "reset_home": "自動認識に戻す", "new_dialog": "サードパーティ API 設定を追加",
        "edit_dialog": "サードパーティ API 設定を編集", "profile_name": "設定名", "model_name": "モデル名", "fetch_models": "モデル取得",
        "cancel": "キャンセル", "save_profile": "保存", "save_changes": "変更を保存", "new_hint": "保存前に API を確認できます。現在の設定は変更されません。",
        "edit_hint": "API Key を空欄にすると現在のキーを保持します。", "saved_profile": "サードパーティ設定「{name}」を{action}しました。認証情報は暗号化されています。",
        "created": "追加", "updated_action": "更新",
    },
    "ko": {
        "subtitle": "Provider 전환 및 기록 동기화", "language_label": "언어", "current_connection": "현재 연결", "refresh": "↻  새로고침", "path_settings": "경로 설정",
        "provider_profiles": "Provider 설정", "profile_count": "{count}개 설정", "new_profile": "＋  새 설정", "edit": "수정", "delete": "삭제",
        "type": "유형", "model": "모델", "source": "저장 위치", "status": "상태", "official_account": "공식 계정",
        "third_party_api": "서드파티 API", "current": "●  사용 중", "auto": "자동", "unknown": "알 수 없음",
        "loading": "불러오는 중…", "detecting": "확인 중…", "verify_on_switch": "전환 시 API 확인", "auto_close": "Codex 자동 종료",
        "restart_after": "완료 후 다시 열기", "switch_selected": "선택한 Provider로 전환  →", "test_api": "✓  API 확인",
        "repair_history": "기록 인덱스 복구", "open_backups": "백업 열기", "execution_log": "실행 로그", "select_profile": "Provider를 먼저 선택하세요.",
        "builtin_official": "OpenAI 공식 계정(기본)", "builtin_login_needed": "OpenAI 공식 계정(로그인 필요)",
        "source_saved_login": "기본 · 로그인 저장됨", "source_login_needed": "기본 · 로그인 필요", "source_local": "로컬 암호화 설정",
        "read_profiles": "로컬 Provider {count}개를 불러왔습니다.", "validating": "대상 API와 인증 정보를 확인하는 중…",
        "closing_codex": "데이터베이스 보호를 위해 Codex를 종료하는 중…", "writing_credentials": "설정과 인증 정보를 안전하게 쓰는 중…",
        "syncing_history": "기록 Provider와 인덱스를 동기화하는 중…", "switch_complete": "전환 완료: 기록 {rollouts}, 변경 {changed}, 업데이트 {updated}, 추가 {inserted}.",
        "official_login_ready": "공식 모드로 복원했습니다. Codex에서 ChatGPT에 로그인하세요.", "rolling_back": "오류가 발생해 자동 복원 중…",
        "restarting_codex": "Codex를 다시 여는 중…", "scan_progress": "기록 파일 {index}/{total}개 확인…", "codex_closed": "Codex를 안전하게 종료했습니다.",
        "imported_profile": "현재 API 설정 “{name}”을 암호화해 가져왔습니다.", "skip_snapshot": "현재 설정 저장 건너뜀: {error}",
        "operation_failed": "실패: {error}", "testing_profile": "“{name}” API 확인 중…", "api_passed": "API 확인 성공: {result}",
        "repair_complete": "복구 완료: {stats}", "profile_deleted": "로컬 설정 “{name}”을 삭제했습니다.", "home_changed": "Codex Home 변경: {path}",
        "home_auto": "Codex Home 자동 감지 복원: {path}", "choose_home": "Codex Home 선택…", "reset_home": "자동 감지 복원",
        "new_dialog": "서드파티 API 설정 추가", "edit_dialog": "서드파티 API 설정 수정", "profile_name": "설정 이름", "model_name": "모델 이름",
        "fetch_models": "모델 가져오기", "cancel": "취소", "save_profile": "저장", "save_changes": "변경 저장",
        "new_hint": "저장 전에 API를 확인할 수 있으며 현재 Codex 설정은 바뀌지 않습니다.", "edit_hint": "API Key를 비워 두면 기존 키를 유지합니다.",
        "saved_profile": "서드파티 설정 “{name}”을 {action}했습니다. 인증 정보는 암호화됩니다.", "created": "추가", "updated_action": "업데이트",
    },
}
TRANSLATIONS["zh-CN"] = {
    "ok": "确定", "confirm": "继续", "cancel": "取消", "language_label": "语言",
    "confirm_close": "切换时需要关闭正在运行的 Codex，未发送的输入会丢失。\n\n目标：{name}\n历史会自动备份并统一索引。\n\n继续吗？",
    "confirm_official_login": "没有找到已保存的 ChatGPT 官方登录会话。\n\n继续后会安全备份当前第三方配置，并让 Codex 进入官方登录流程。请在浏览器中选择“使用 ChatGPT 登录”，再使用你原来的 Google 账号。\n\n在完成登录前，CodexShift 不会把它标记为“已保存登录”。",
    "builtin_edit_locked": "内置官方账号配置由 CodexShift 维护，不能修改。", "builtin_delete_locked": "内置官方账号配置不能删除。",
    "confirm_delete": "确定删除本地配置「{name}」吗？\n\n此操作不会删除历史记录，当前配置不能直接删除。",
    "confirm_repair": "将历史统一到「{name}」并自动备份，继续吗？",
    "home_not_detected": "这个目录里暂时没有发现 Codex 配置或历史文件。\n\n仍然将它设为 Codex Home 吗？",
    "test_passed_dialog": "检测通过\n\n{name}\n{result}",
    "official_mode_ready": "原生官方模式已就绪，切换后请在 Codex 中登录 OpenAI 账号",
    "official_credentials_ok": "官方账号凭据结构正常",
    "models_found": "接口连通，自动发现 {count} 个模型",
    "models_unavailable": "接口可达，但无法自动发现模型：{error}",
    "fetching_models": "正在请求 /models 并解析模型列表…",
    "models_ready": "已发现 {count} 个模型，请从下拉列表选择。",
    "models_dialog": "已自动发现 {count} 个模型。",
    "models_failed": "模型发现失败：{error}；仍可手动填写。",
    "testing_api_status": "正在检测接口和 API Key…",
    "test_passed_status": "检测通过：{result}",
    "test_failed_status": "检测失败：{error}",
}
TRANSLATIONS["en"].update({
    "ok": "OK", "confirm": "Continue", "cancel": "Cancel",
    "confirm_close": "Codex must be closed before switching. Unsent input will be lost.\n\nTarget: {name}\nHistory will be backed up and reindexed automatically.\n\nContinue?",
    "confirm_official_login": "No saved ChatGPT sign-in session was found.\n\nCodexShift will back up the current API profile and enter the official sign-in flow. Choose “Sign in with ChatGPT” in your browser, then use your original Google account.\n\nThe login will not be marked as saved until authorization is complete.",
    "builtin_edit_locked": "The built-in official account profile is managed by CodexShift and cannot be edited.",
    "builtin_delete_locked": "The built-in official account profile cannot be deleted.",
    "confirm_delete": "Delete local profile “{name}”?\n\nHistory will not be deleted. The active profile cannot be deleted directly.",
    "confirm_repair": "Rewrite history to “{name}” and create a backup. Continue?",
    "home_not_detected": "No Codex configuration or history was found in this folder.\n\nUse it as Codex Home anyway?",
    "test_passed_dialog": "Test passed\n\n{name}\n{result}",
    "official_mode_ready": "Native OpenAI mode is ready. Sign in after switching.",
    "official_credentials_ok": "Official account credentials are valid",
    "models_found": "API connected; discovered {count} models", "models_unavailable": "API reachable, but models could not be discovered: {error}",
    "fetching_models": "Requesting /models and parsing the model list…", "models_ready": "Found {count} models. Select one from the list.",
    "models_dialog": "Discovered {count} models.", "models_failed": "Model discovery failed: {error}. You can still enter one manually.",
    "testing_api_status": "Testing the API and API Key…", "test_passed_status": "Test passed: {result}", "test_failed_status": "Test failed: {error}",
})
TRANSLATIONS["ja"].update({
    "ok": "OK", "confirm": "続ける", "cancel": "キャンセル",
    "confirm_close": "切替前に実行中の Codex を終了します。未送信の入力は失われます。\n\n切替先：{name}\n履歴は自動的にバックアップして再索引されます。\n\n続けますか？",
    "confirm_official_login": "保存された ChatGPT ログインがありません。\n\n現在の API 設定をバックアップし、公式ログインを開始します。ブラウザーで「ChatGPT でログイン」を選び、以前の Google アカウントを使用してください。",
    "builtin_edit_locked": "内蔵の公式アカウント設定は編集できません。", "builtin_delete_locked": "内蔵の公式アカウント設定は削除できません。",
    "confirm_delete": "ローカル設定「{name}」を削除しますか？\n\n履歴は削除されません。使用中の設定は直接削除できません。",
    "confirm_repair": "履歴を「{name}」に統一してバックアップします。続けますか？",
    "home_not_detected": "このフォルダーに Codex の設定や履歴が見つかりません。\n\nCodex Home として使用しますか？",
    "test_passed_dialog": "確認成功\n\n{name}\n{result}",
    "official_mode_ready": "公式モードの準備ができました。切替後にログインしてください。", "official_credentials_ok": "公式アカウントの認証情報は正常です",
    "models_found": "接続成功、{count} 個のモデルを取得", "models_unavailable": "接続済みですがモデルを取得できません：{error}",
    "fetching_models": "/models からモデル一覧を取得中…", "models_ready": "{count} 個のモデルを取得しました。リストから選択してください。",
    "models_dialog": "{count} 個のモデルを取得しました。", "models_failed": "モデル取得失敗：{error}。手動入力も可能です。",
    "testing_api_status": "API と API Key を確認中…", "test_passed_status": "確認成功：{result}", "test_failed_status": "確認失敗：{error}",
})
TRANSLATIONS["ko"].update({
    "ok": "확인", "confirm": "계속", "cancel": "취소",
    "confirm_close": "전환 전에 실행 중인 Codex를 종료해야 합니다. 전송하지 않은 입력은 사라집니다.\n\n대상: {name}\n기록은 자동으로 백업하고 다시 색인합니다.\n\n계속할까요?",
    "confirm_official_login": "저장된 ChatGPT 로그인 세션이 없습니다.\n\n현재 API 설정을 백업한 후 공식 로그인 절차를 시작합니다. 브라우저에서 ‘ChatGPT로 로그인’을 선택하고 기존 Google 계정을 사용하세요.",
    "builtin_edit_locked": "기본 공식 계정 설정은 수정할 수 없습니다.", "builtin_delete_locked": "기본 공식 계정 설정은 삭제할 수 없습니다.",
    "confirm_delete": "로컬 설정 “{name}”을 삭제할까요?\n\n기록은 삭제되지 않으며 현재 사용 중인 설정은 바로 삭제할 수 없습니다.",
    "confirm_repair": "기록을 “{name}”으로 통일하고 백업할까요?",
    "home_not_detected": "이 폴더에서 Codex 설정이나 기록을 찾지 못했습니다.\n\nCodex Home으로 사용할까요?",
    "test_passed_dialog": "확인 성공\n\n{name}\n{result}",
    "official_mode_ready": "공식 모드가 준비되었습니다. 전환 후 로그인하세요.", "official_credentials_ok": "공식 계정 인증 정보가 정상입니다",
    "models_found": "연결 성공, 모델 {count}개 발견", "models_unavailable": "연결되었지만 모델을 찾지 못했습니다: {error}",
    "fetching_models": "/models에서 모델 목록을 가져오는 중…", "models_ready": "모델 {count}개를 찾았습니다. 목록에서 선택하세요.",
    "models_dialog": "모델 {count}개를 찾았습니다.", "models_failed": "모델 검색 실패: {error}. 직접 입력할 수도 있습니다.",
    "testing_api_status": "API와 API Key 확인 중…", "test_passed_status": "확인 성공: {result}", "test_failed_status": "확인 실패: {error}",
})


def set_language(code: str) -> None:
    global CURRENT_LANGUAGE
    CURRENT_LANGUAGE = code if code in LANGUAGE_LABELS else "zh-CN"


def tr(key: str, **values) -> str:
    text = TRANSLATIONS.get(CURRENT_LANGUAGE, {}).get(key)
    if text is None and CURRENT_LANGUAGE != "zh-CN":
        text = TRANSLATIONS["en"].get(key)
    if text is None:
        text = {
            "subtitle": "Provider switching & history sync", "language_label": "语言", "current_connection": "当前连接", "refresh": "↻  刷新",
            "path_settings": "路径设置", "provider_profiles": "Provider 配置", "profile_count": "{count} 个配置",
            "new_profile": "＋  新建配置", "edit": "编辑", "delete": "删除", "type": "类型", "model": "模型",
            "source": "配置来源", "status": "状态", "official_account": "官方账号", "third_party_api": "第三方 API",
            "current": "●  当前", "auto": "自动", "unknown": "未识别", "loading": "正在读取配置…", "detecting": "正在识别…",
            "verify_on_switch": "切换时验证第三方接口", "auto_close": "自动关闭 Codex", "restart_after": "完成后重新打开",
            "switch_selected": "切换到选中 Provider  →", "test_api": "✓  检测 API", "repair_history": "修复历史索引",
            "open_backups": "打开备份目录", "execution_log": "执行日志", "select_profile": "请先选择一个 Provider。",
            "builtin_official": "OpenAI 官方账号（原生）", "builtin_login_needed": "OpenAI 官方账号（需重新登录）",
            "source_saved_login": "内置 · 已保存登录", "source_login_needed": "内置 · 需要重新登录", "source_local": "本地加密配置",
            "read_profiles": "已读取 {count} 个本地 Provider。", "validating": "正在验证目标接口与凭据…",
            "closing_codex": "正在关闭 Codex，避免数据库被占用…", "writing_credentials": "正在原子写入配置与账号凭据…",
            "syncing_history": "正在统一历史 Provider 并补齐索引…", "switch_complete": "切换完成：扫描 {rollouts} 个历史，改写 {changed} 个，修复 {updated} 条，补回 {inserted} 条。",
            "official_login_ready": "已恢复 Codex 原生官方模式；打开 Codex 后请登录 OpenAI 官方账号。", "rolling_back": "发生错误，正在自动回滚…",
            "restarting_codex": "正在重新打开 Codex…", "scan_progress": "已扫描 {index}/{total} 个历史文件…", "codex_closed": "Codex 相关进程已安全退出。",
            "imported_profile": "已将当前第三方配置「{name}」加密导入 CodexShift。", "skip_snapshot": "跳过当前配置快照：{error}",
            "operation_failed": "失败：{error}", "testing_profile": "正在检测「{name}」的 API…", "api_passed": "API 检测通过：{result}",
            "repair_complete": "修复完成：{stats}", "profile_deleted": "已删除本地配置「{name}」。", "home_changed": "Codex Home 已改为：{path}",
            "home_auto": "已恢复自动识别 Codex Home：{path}", "choose_home": "选择 Codex Home…", "reset_home": "恢复自动识别",
            "new_dialog": "新建第三方 API 配置", "edit_dialog": "修改第三方 API 配置", "profile_name": "配置名称", "model_name": "模型名称",
            "fetch_models": "自动获取模型", "cancel": "取消", "save_profile": "保存配置", "save_changes": "保存修改",
            "new_hint": "填写后可以先检测 API，不会修改当前 Codex 配置。", "edit_hint": "API Key 留空会保留原密钥；保存后重新切换才会应用。",
            "saved_profile": "已{action}第三方配置「{name}」，凭据已加密。", "created": "新建", "updated_action": "更新",
        }.get(key, key)
    try:
        return text.format(**values)
    except (KeyError, ValueError):
        return text


def preferred_language() -> str:
    saved = read_json(app_data_dir() / "settings.json", {}).get("language")
    if saved in LANGUAGE_LABELS:
        return str(saved)
    code = (locale.getlocale()[0] or os.environ.get("LANG") or "").lower()
    if code.startswith("ja"):
        return "ja"
    if code.startswith("ko"):
        return "ko"
    if code.startswith("zh"):
        return "zh-CN"
    return "en"


class SwitchError(RuntimeError):
    pass


class ModelDiscoveryUnavailable(SwitchError):
    pass


def user_home() -> Path:
    return Path(os.environ.get("USERPROFILE") or Path.home())


def resource_path(relative: str) -> Path:
    return Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent)) / relative


def default_codex_home() -> Path:
    return Path(os.environ.get("CODEX_HOME") or user_home() / ".codex")


def configured_codex_home() -> Path:
    state = read_json(app_data_dir() / "settings.json", {})
    saved = state.get("codex_home")
    if state.get("codex_home_manual") and isinstance(saved, str) and saved.strip():
        return Path(saved).expanduser()
    return default_codex_home()


def app_data_dir() -> Path:
    if IS_MACOS:
        root = user_home() / "Library" / "Application Support"
    elif IS_WINDOWS:
        root = Path(os.environ.get("APPDATA") or user_home() / "AppData" / "Roaming")
    else:
        root = Path(os.environ.get("XDG_CONFIG_HOME") or user_home() / ".config")
    target = root / "CodexShift"
    legacy = root / "XuanCodexSwitcher"
    if not target.exists() and legacy.exists():
        try:
            legacy.rename(target)
        except OSError:
            return legacy
    return target


def atomic_write(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(f".{path.name}.codexshift-{os.getpid()}.tmp")
    with temp.open("wb") as fh:
        fh.write(data)
        fh.flush()
        os.fsync(fh.fileno())
    os.replace(temp, path)


def read_json(path: Path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError):
        return default


def write_json(path: Path, value) -> None:
    atomic_write(path, json.dumps(value, ensure_ascii=False, indent=2).encode("utf-8"))


def _split_toml(text: str) -> tuple[list[str], dict[str, list[str]], list[str]]:
    root: list[str] = []
    tables: dict[str, list[str]] = {}
    order: list[str] = []
    current: list[str] = root
    for raw in text.replace("\r\n", "\n").splitlines():
        line = raw.rstrip()
        match = re.match(r"^\s*(\[\[?.+?\]\]?)\s*(?:#.*)?$", line)
        if match:
            header = match.group(1)
            if header not in tables:
                tables[header] = [line]
                order.append(header)
            else:
                # Array-of-table duplicates are kept as one logical segment.
                tables[header].append(line)
            current = tables[header]
        else:
            current.append(line)
    return root, tables, order


def _assignment_key(line: str) -> str | None:
    match = re.match(r'^\s*((?:"[^"]+"|\'[^\']+\'|[A-Za-z0-9_.-])+?)\s*=', line)
    return match.group(1).strip() if match else None


def merge_toml(base: str, overlay: str) -> str:
    """Merge TOML at root-key/table granularity while keeping human formatting."""
    base_root, base_tables, base_order = _split_toml(base)
    over_root, over_tables, over_order = _split_toml(overlay)
    over_keys = {_assignment_key(line) for line in over_root}
    over_keys.discard(None)
    root = [line for line in base_root if _assignment_key(line) not in over_keys]
    if root and any(line.strip() for line in root) and over_root:
        root.append("")
    root.extend(over_root)

    tables = dict(base_tables)
    order = list(base_order)
    for header in over_order:
        tables[header] = over_tables[header]
        if header not in order:
            order.append(header)

    pieces = ["\n".join(root).strip()]
    pieces.extend("\n".join(tables[header]).strip() for header in order)
    result = "\n\n".join(piece for piece in pieces if piece) + "\n"
    tomllib.loads(result)
    return result


def native_official_config(config_text: str) -> str:
    """Keep unrelated Codex preferences while restoring the built-in OpenAI provider."""
    try:
        root, tables, order = _split_toml(config_text)
        remove_root = {"model", "model_provider", "disable_response_storage"}
        root = [line for line in root if _assignment_key(line) not in remove_root]
        root.insert(0, f'model_provider = "{OFFICIAL_PROVIDER}"')

        official_table = re.compile(r"^\[model_providers\.(?:openai|\"openai\"|'openai')\]$")
        order = [header for header in order if not official_table.fullmatch(header.strip())]
        pieces = ["\n".join(root).strip()]
        pieces.extend("\n".join(tables[header]).strip() for header in order)
        result = "\n\n".join(piece for piece in pieces if piece) + "\n"
        tomllib.loads(result)
        return result
    except (ValueError, TypeError, tomllib.TOMLDecodeError):
        return f'model_provider = "{OFFICIAL_PROVIDER}"\n'


def effective_model_provider(config_text: str) -> str:
    data = tomllib.loads(config_text)
    return str(data.get("model_provider") or OFFICIAL_PROVIDER)


def provider_base_url(config_text: str) -> str | None:
    data = tomllib.loads(config_text)
    selected = str(data.get("model_provider") or OFFICIAL_PROVIDER)
    provider = data.get("model_providers", {}).get(selected, {})
    value = provider.get("base_url") if isinstance(provider, dict) else None
    return str(value).strip() if value else None


def provider_model(config_text: str) -> str | None:
    value = tomllib.loads(config_text).get("model")
    return str(value) if value else None


def provider_name_from_config(config_text: str, fallback: str) -> str:
    try:
        data = tomllib.loads(config_text)
        selected = str(data.get("model_provider") or OFFICIAL_PROVIDER)
        provider = data.get("model_providers", {}).get(selected, {})
        name = provider.get("name") if isinstance(provider, dict) else None
        return str(name).strip() if name else fallback
    except (TypeError, tomllib.TOMLDecodeError):
        return fallback


def custom_provider_config(base_config: str, name: str, base_url: str, model: str) -> str:
    q = lambda value: json.dumps(value, ensure_ascii=False)
    overlay = (
        'model_provider = "custom"\n'
        f"model = {q(model)}\n"
        "disable_response_storage = true\n\n"
        "[model_providers.custom]\n"
        f"name = {q(name)}\n"
        f"base_url = {q(base_url)}\n"
        'wire_api = "responses"\n'
        "requires_openai_auth = true\n"
        "request_max_retries = 4\n"
        "stream_max_retries = 5\n"
    )
    return merge_toml(base_config, overlay)


def provider_signature(config_text: str, auth: dict) -> tuple[str, str, str, str] | None:
    try:
        return (
            effective_model_provider(config_text),
            provider_base_url(config_text) or "",
            provider_model(config_text) or "",
            str(auth.get("OPENAI_API_KEY") or ""),
        )
    except (TypeError, tomllib.TOMLDecodeError):
        return None


def normalize_auth(auth: dict, target_provider: str) -> dict:
    result = dict(auth or {})
    is_chatgpt_account = result.get("auth_mode") == "chatgpt" or (
        isinstance(result.get("tokens"), dict) and bool(result["tokens"].get("refresh_token"))
    )
    if is_chatgpt_account:
        if not isinstance(result.get("tokens"), dict) or not result["tokens"].get("refresh_token"):
            raise SwitchError("官方账号凭据不完整，请先在 Codex 中登录一次官方账号。")
        result["auth_mode"] = "chatgpt"
        result["OPENAI_API_KEY"] = None
    else:
        key = result.get("OPENAI_API_KEY")
        if not isinstance(key, str) or not key.strip():
            raise SwitchError("第三方 Provider 没有可用的 OPENAI_API_KEY。")
        # 统一为 Codex 可识别的 API Key 登录结构，避免残留旧账号字段。
        result = {"OPENAI_API_KEY": key.strip(), "auth_mode": "apikey"}
    return result


def redact(value):
    if isinstance(value, dict):
        return {k: ("***" if k in SECRET_KEYS else redact(v)) for k, v in value.items()}
    if isinstance(value, list):
        return [redact(v) for v in value]
    return value


@dataclass
class Provider:
    id: str
    name: str
    config: str
    auth: dict
    is_current: bool = False
    source: str = "本地配置"

    @property
    def model_provider(self) -> str:
        return effective_model_provider(self.config)

    @property
    def is_official(self) -> bool:
        return self.id == BUILTIN_OFFICIAL_ID or (
            self.model_provider == OFFICIAL_PROVIDER and self.auth.get("auth_mode") == "chatgpt"
        )

    @property
    def kind_label(self) -> str:
        return tr("official_account") if self.is_official else tr("third_party_api")


class DpapiVault:
    """Encrypted per-user snapshots: DPAPI on Windows, Keychain on macOS."""

    def __init__(self, path: Path):
        self.path = path

    @staticmethod
    def _crypt(data: bytes, protect: bool) -> bytes:
        if os.name != "nt":
            # Test/development fallback. Production builds target Windows.
            return base64.b64encode(data) if protect else base64.b64decode(data)

        class DATA_BLOB(ctypes.Structure):
            _fields_ = [("cbData", wintypes.DWORD), ("pbData", ctypes.POINTER(ctypes.c_byte))]

        buffer = ctypes.create_string_buffer(data, len(data))
        in_blob = DATA_BLOB(len(data), ctypes.cast(buffer, ctypes.POINTER(ctypes.c_byte)))
        out_blob = DATA_BLOB()
        if protect:
            ok = ctypes.windll.crypt32.CryptProtectData(
                ctypes.byref(in_blob), "CodexShift", None, None, None, 0, ctypes.byref(out_blob)
            )
        else:
            ok = ctypes.windll.crypt32.CryptUnprotectData(
                ctypes.byref(in_blob), None, None, None, None, 0, ctypes.byref(out_blob)
            )
        if not ok:
            raise ctypes.WinError()
        try:
            return ctypes.string_at(out_blob.pbData, out_blob.cbData)
        finally:
            ctypes.windll.kernel32.LocalFree(out_blob.pbData)

    def load(self) -> dict:
        if IS_MACOS:
            try:
                account = f"{getpass.getuser()}:{self.path.name}"
                result = subprocess.run(
                    ["security", "find-generic-password", "-s", APP_NAME, "-a", account, "-w"],
                    capture_output=True, text=True, check=True,
                )
                return json.loads(base64.b64decode(result.stdout.strip()).decode("utf-8"))
            except (OSError, subprocess.CalledProcessError, ValueError, UnicodeDecodeError):
                pass
        if not self.path.exists():
            return {}
        try:
            return json.loads(self._crypt(self.path.read_bytes(), False).decode("utf-8"))
        except Exception:
            return {}

    def save(self, value: dict) -> None:
        raw = json.dumps(value, ensure_ascii=False).encode("utf-8")
        if IS_MACOS:
            account = f"{getpass.getuser()}:{self.path.name}"
            encoded = base64.b64encode(raw).decode("ascii")
            try:
                subprocess.run(
                    ["security", "add-generic-password", "-U", "-s", APP_NAME,
                     "-a", account, "-w", encoded],
                    capture_output=True, text=True, check=True,
                )
                return
            except (OSError, subprocess.CalledProcessError) as exc:
                raise SwitchError(f"无法写入 macOS Keychain：{exc}") from exc
        atomic_write(self.path, self._crypt(raw, True))


class Backup:
    def __init__(self, codex_home: Path):
        stamp = dt.datetime.now().strftime("%Y%m%d-%H%M%S-%f")
        self.codex_home = codex_home.resolve()
        self.root = (self.codex_home / "switcher_backups" / stamp).resolve()
        self.root.mkdir(parents=True, exist_ok=False)
        self.files: list[str] = []

    def save(self, path: Path) -> None:
        path = path.resolve()
        if not path.exists() or path.is_dir():
            return
        try:
            relative = path.relative_to(self.codex_home)
        except ValueError as exc:
            raise SwitchError(f"拒绝备份 Codex Home 之外的文件：{path}") from exc
        key = relative.as_posix()
        if key in self.files:
            return
        target = self.root / "files" / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, target)
        self.files.append(key)

    def finish(self, provider_id: str) -> None:
        write_json(self.root / "manifest.json", {"provider_id": provider_id, "files": self.files})

    def restore(self) -> None:
        # A newer WAL must never be replayed on top of the restored main DB.
        db_key = "state_5.sqlite"
        if db_key in self.files:
            for suffix in ("-wal", "-shm"):
                sidecar = self.codex_home / f"state_5.sqlite{suffix}"
                try:
                    sidecar.unlink(missing_ok=True)
                except OSError:
                    pass
        for key in reversed(self.files):
            source = self.root / "files" / Path(key)
            target = self.codex_home / Path(key)
            if source.exists():
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source, target)


def prune_backups(codex_home: Path, keep: int = 3) -> None:
    root = (codex_home / "switcher_backups").resolve()
    if not root.exists():
        return
    items = sorted((p.resolve() for p in root.iterdir() if p.is_dir()), reverse=True)
    for path in items[keep:]:
        if path.parent == root and (path / "manifest.json").exists():
            shutil.rmtree(path)


def rollout_files(codex_home: Path) -> list[Path]:
    result: list[Path] = []
    for folder in (codex_home / "sessions", codex_home / "archived_sessions"):
        if folder.exists():
            result.extend(path for path in folder.rglob("*.jsonl") if path.is_file())
    return sorted(set(result))


def _rewrite_rollout(path: Path, target_provider: str, backup: Backup | None) -> tuple[bool, dict | None]:
    output: list[bytes] = []
    changed = False
    session_meta = None
    with path.open("rb") as fh:
        for raw in fh:
            try:
                obj = json.loads(raw)
            except (ValueError, UnicodeDecodeError):
                output.append(raw)
                continue
            payload = obj.get("payload")
            if isinstance(payload, dict) and obj.get("type") == "session_meta" and session_meta is None:
                session_meta = dict(payload)
            if isinstance(payload, dict) and "model_provider" in payload:
                if payload["model_provider"] != target_provider:
                    payload["model_provider"] = target_provider
                    changed = True
                    if obj.get("type") == "session_meta" and session_meta is not None:
                        session_meta["model_provider"] = target_provider
                output.append((json.dumps(obj, ensure_ascii=False, separators=(",", ":")) + "\n").encode("utf-8"))
            else:
                output.append(raw)
    if changed:
        if backup:
            backup.save(path)
        atomic_write(path, b"".join(output))
    return changed, session_meta


def _timestamp(value, fallback: float) -> int:
    if isinstance(value, str):
        try:
            return int(dt.datetime.fromisoformat(value.replace("Z", "+00:00")).timestamp())
        except ValueError:
            pass
    return int(fallback)


def _first_user_message(path: Path) -> str:
    try:
        with path.open(encoding="utf-8") as fh:
            for line in fh:
                obj = json.loads(line)
                payload = obj.get("payload", {})
                if obj.get("type") == "response_item" and payload.get("role") == "user":
                    parts = payload.get("content") or []
                    text = " ".join(str(p.get("text", "")) for p in parts if isinstance(p, dict)).strip()
                    if text:
                        return re.sub(r"\s+", " ", text)[:120]
    except Exception:
        pass
    return "已恢复的 Codex 任务"


def sync_history(
    codex_home: Path,
    target_provider: str,
    backup: Backup | None,
    log: Callable[[str], None] = lambda _x: None,
) -> dict:
    paths = rollout_files(codex_home)
    metas: dict[str, tuple[Path, dict, bool]] = {}
    changed = 0
    for index, path in enumerate(paths, 1):
        was_changed, meta = _rewrite_rollout(path, target_provider, backup)
        changed += int(was_changed)
        if meta and not meta.get("parent_thread_id"):
            thread_id = str(meta.get("id") or meta.get("session_id") or "")
            if thread_id:
                archived = "archived_sessions" in path.parts
                metas[thread_id] = (path, meta, archived)
        if index % 50 == 0:
            log(tr("scan_progress", index=index, total=len(paths)))

    db_path = codex_home / "state_5.sqlite"
    updated = inserted = 0
    if db_path.exists():
        if backup:
            backup.save(db_path)
        with closing(sqlite3.connect(db_path, timeout=30)) as con:
            con.execute("PRAGMA busy_timeout=30000")
            check = con.execute("PRAGMA integrity_check").fetchone()
            if not check or check[0] != "ok":
                raise SwitchError(f"历史数据库完整性检查失败：{check[0] if check else 'unknown'}")
            updated = con.execute(
                "UPDATE threads SET model_provider=? WHERE model_provider<>?",
                (target_provider, target_provider),
            ).rowcount
            existing = {str(row[0]) for row in con.execute("SELECT id FROM threads")}
            for thread_id, (path, meta, archived) in metas.items():
                if thread_id in existing:
                    con.execute(
                        "UPDATE threads SET rollout_path=?, model_provider=?, archived=? WHERE id=?",
                        (str(path), target_provider, int(archived), thread_id),
                    )
                    continue
                stat = path.stat()
                created = _timestamp(meta.get("timestamp"), stat.st_ctime)
                updated_at = int(stat.st_mtime)
                title = _first_user_message(path)
                cwd = str(meta.get("cwd") or user_home())
                source = meta.get("source")
                if not isinstance(source, str):
                    source = "vscode"
                con.execute(
                    "INSERT INTO threads "
                    "(id,rollout_path,created_at,updated_at,source,model_provider,cwd,title,"
                    "sandbox_policy,approval_mode,has_user_event,archived,cli_version,thread_source,"
                    "first_user_message,created_at_ms,updated_at_ms,preview,recency_at,recency_at_ms) "
                    "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                    (
                        thread_id, str(path), created, updated_at, source, target_provider, cwd, title,
                        "{}", "on-request", 1, int(archived), str(meta.get("cli_version") or ""),
                        str(meta.get("thread_source") or "user"), title, created * 1000,
                        updated_at * 1000, title, updated_at, updated_at * 1000,
                    ),
                )
                inserted += 1
            con.commit()
            check = con.execute("PRAGMA integrity_check").fetchone()
            if not check or check[0] != "ok":
                raise SwitchError("写入后历史数据库完整性检查失败。")
    return {"rollouts": len(paths), "changed": changed, "updated": updated, "inserted": inserted}


def running_codex_processes() -> list[str]:
    if IS_WINDOWS:
        result = subprocess.run(
            ["tasklist", "/FO", "CSV", "/NH"], capture_output=True, text=True,
            encoding="utf-8", errors="replace",
        )
        text = result.stdout.lower()
        return [name for name in PROCESS_NAMES if f'"{name.lower()}"' in text]
    if IS_MACOS:
        result = subprocess.run(["ps", "-axo", "comm="], capture_output=True, text=True)
        running = {Path(line.strip()).name for line in result.stdout.splitlines() if line.strip()}
        return [name for name in MAC_PROCESS_NAMES if name in running]
    return []


def close_codex_processes(log: Callable[[str], None]) -> None:
    if IS_WINDOWS:
        for name in PROCESS_NAMES:
            subprocess.run(["taskkill", "/F", "/T", "/IM", name], capture_output=True, creationflags=0x08000000)
    elif IS_MACOS:
        for name in MAC_PROCESS_NAMES:
            subprocess.run(["pkill", "-x", name], capture_output=True)
    for _ in range(30):
        if not running_codex_processes():
            return
        time.sleep(0.2)
    remaining = ", ".join(running_codex_processes())
    if remaining:
        raise SwitchError(f"无法关闭这些 Codex 进程：{remaining}")
    log(tr("codex_closed"))


def restart_codex() -> None:
    if IS_WINDOWS:
        subprocess.Popen(
            ["explorer.exe", "shell:AppsFolder\\OpenAI.Codex_2p2nqsd0c76g0!App"],
            creationflags=0x08000000,
        )
    elif IS_MACOS:
        for app in ("Codex", "ChatGPT"):
            result = subprocess.run(["open", "-a", app], capture_output=True)
            if result.returncode == 0:
                break


def fetch_provider_models(provider: Provider, timeout: int = 10) -> list[str]:
    """Return model IDs from an OpenAI-compatible GET /models endpoint."""
    base_url = provider_base_url(provider.config)
    key = provider.auth.get("OPENAI_API_KEY")
    if not base_url:
        raise ModelDiscoveryUnavailable("该 Provider 没有可用于模型发现的 base_url。")
    if not isinstance(key, str) or not key.strip():
        raise SwitchError("第三方 Provider 缺少 API Key。")
    url = base_url.rstrip("/") + "/models"
    request = urllib.request.Request(
        url,
        headers={"Authorization": f"Bearer {key.strip()}", "User-Agent": "CodexShift/1"},
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            if not 200 <= response.status < 300:
                raise SwitchError(f"接口返回 HTTP {response.status}")
            raw = response.read(2 * 1024 * 1024 + 1)
            if len(raw) > 2 * 1024 * 1024:
                raise SwitchError("/models 返回内容超过 2 MB，已停止解析。")
    except urllib.error.HTTPError as exc:
        if exc.code in (400, 404, 405):
            raise ModelDiscoveryUnavailable(f"服务未开放 /models（HTTP {exc.code}）。") from exc
        if exc.code in (401, 403):
            raise SwitchError(f"第三方 API Key 被拒绝（HTTP {exc.code}）。") from exc
        raise SwitchError(f"第三方接口异常（HTTP {exc.code}）。") from exc
    except OSError as exc:
        raise SwitchError(f"无法连接第三方接口：{exc}") from exc

    try:
        payload = json.loads(raw.decode("utf-8-sig"))
    except (UnicodeDecodeError, ValueError) as exc:
        raise ModelDiscoveryUnavailable("/models 已响应，但返回内容不是有效 JSON。") from exc
    candidates = payload
    if isinstance(payload, dict):
        candidates = payload.get("data", payload.get("models", []))
    if not isinstance(candidates, list):
        raise ModelDiscoveryUnavailable("/models 响应中没有 data 或 models 列表。")
    models: set[str] = set()
    for item in candidates:
        if isinstance(item, str) and item.strip():
            models.add(item.strip())
        elif isinstance(item, dict):
            value = item.get("id") or item.get("name") or item.get("model")
            if isinstance(value, str) and value.strip():
                models.add(value.strip())
    if not models:
        raise ModelDiscoveryUnavailable("接口连通，但没有发现可用模型。")
    return sorted(models, key=str.casefold)


def probe_provider(provider: Provider, timeout: int = 10) -> str:
    if provider.id == BUILTIN_OFFICIAL_ID and provider.auth.get("auth_mode") != "chatgpt":
        return tr("official_mode_ready")
    if provider.is_official:
        return tr("official_credentials_ok")
    try:
        models = fetch_provider_models(provider, timeout)
        return tr("models_found", count=len(models))
    except ModelDiscoveryUnavailable as exc:
        return tr("models_unavailable", error=exc)


class SwitchEngine:
    def __init__(self, codex_home: Path, log: Callable[[str], None]):
        self.codex_home = codex_home.resolve()
        self.data_dir = app_data_dir()
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.state_path = self.data_dir / "settings.json"
        self.vault = DpapiVault(self.data_dir / "profiles.dpapi")
        self.log = log

    def state(self) -> dict:
        return read_json(self.state_path, {})

    def providers(self) -> list[Provider]:
        vault = self.vault.load()
        vault = self._import_live_api_profile(vault)
        providers: list[Provider] = []
        for provider_id, saved in vault.items():
            if provider_id == BUILTIN_OFFICIAL_ID or not isinstance(saved, dict):
                continue
            if not saved.get("config") or not isinstance(saved.get("auth"), dict):
                continue
            auth = dict(saved["auth"])
            if auth.get("auth_mode") == "chatgpt":
                continue
            config = str(saved["config"])
            fallback = str(saved.get("name") or provider_id)
            providers.append(
                Provider(
                    id=str(provider_id),
                    name=provider_name_from_config(config, fallback),
                    config=config,
                    auth=auth,
                    source=tr("source_local"),
                )
            )
        providers.sort(key=lambda item: item.name.casefold())
        providers.insert(0, self._builtin_official_provider(providers, vault))
        current_id = self.current_provider_id(providers)
        for provider in providers:
            provider.is_current = provider.id == current_id
        return providers

    def _import_live_api_profile(self, vault: dict) -> dict:
        config_path = self.codex_home / "config.toml"
        auth_path = self.codex_home / "auth.json"
        if not config_path.exists() or not auth_path.exists():
            return vault
        try:
            config = config_path.read_text(encoding="utf-8")
            tomllib.loads(config)
            auth = normalize_auth(read_json(auth_path, {}), effective_model_provider(config))
        except (OSError, SwitchError, tomllib.TOMLDecodeError):
            return vault
        if auth.get("auth_mode") != "apikey":
            return vault
        live_signature = provider_signature(config, auth)
        for saved in vault.values():
            if not isinstance(saved, dict):
                continue
            saved_config = saved.get("config")
            saved_auth = saved.get("auth")
            if isinstance(saved_config, str) and isinstance(saved_auth, dict):
                if provider_signature(saved_config, saved_auth) == live_signature:
                    return vault
        preferred_id = str(self.state().get("active_provider_id") or "")
        if not preferred_id or preferred_id == BUILTIN_OFFICIAL_ID or preferred_id in vault:
            preferred_id = f"imported-{uuid.uuid4()}"
        name = provider_name_from_config(config, "当前 Codex 配置")
        vault[preferred_id] = {
            "name": name,
            "config": config,
            "auth": auth,
            "managed_by": APP_NAME,
            "imported_from_current": True,
        }
        self.vault.save(vault)
        self.log(tr("imported_profile", name=name))
        return vault

    def _builtin_official_provider(self, providers: list[Provider], vault: dict) -> Provider:
        config_path = self.codex_home / "config.toml"
        current_config = config_path.read_text(encoding="utf-8") if config_path.exists() else ""
        config = native_official_config(current_config)
        auth: dict = {"auth_mode": "logged_out"}

        candidates = [vault.get(BUILTIN_OFFICIAL_ID)]
        candidates.extend(vault.values())
        candidates.extend({"auth": provider.auth, "config": provider.config} for provider in providers)
        auth_path = self.codex_home / "auth.json"
        if auth_path.exists():
            candidates.insert(0, {"auth": read_json(auth_path, {})})
        backup_root = self.codex_home / "switcher_backups"
        if backup_root.exists():
            for folder in sorted((path for path in backup_root.iterdir() if path.is_dir()), reverse=True):
                backup_auth = folder / "files" / "auth.json"
                backup_config = folder / "files" / "config.toml"
                if not backup_auth.exists():
                    continue
                saved: dict = {"auth": read_json(backup_auth, {})}
                if backup_config.exists():
                    try:
                        saved["config"] = backup_config.read_text(encoding="utf-8")
                    except OSError:
                        pass
                candidates.append(saved)
        for saved in candidates:
            if not isinstance(saved, dict):
                continue
            candidate_auth = saved.get("auth", saved)
            try:
                normalized = normalize_auth(candidate_auth, OFFICIAL_PROVIDER)
            except SwitchError:
                continue
            if normalized.get("auth_mode") == "chatgpt":
                auth = normalized
                saved_config = saved.get("config")
                if isinstance(saved_config, str) and saved_config.strip():
                    config = native_official_config(saved_config)
                break

        has_login = auth.get("auth_mode") == "chatgpt"
        if has_login:
            saved_official = dict(vault.get(BUILTIN_OFFICIAL_ID) or {})
            updated = {
                "name": "OpenAI 官方账号（原生）",
                "config": config,
                "auth": auth,
                "managed_by": APP_NAME,
            }
            if any(saved_official.get(key) != value for key, value in updated.items()):
                saved_official.update(updated)
                vault[BUILTIN_OFFICIAL_ID] = saved_official
                self.vault.save(vault)
        source = tr("source_saved_login") if has_login else tr("source_login_needed")
        name = tr("builtin_official") if has_login else tr("builtin_login_needed")
        return Provider(BUILTIN_OFFICIAL_ID, name, config, auth, source=source)

    def current_provider_id(self, providers: Iterable[Provider] | None = None) -> str | None:
        value = self.state().get("active_provider_id")
        if value:
            return str(value)
        if providers:
            current = next((p.id for p in providers if p.is_current), None)
            return current
        return None

    def snapshot_current(self, providers: list[Provider]) -> None:
        active_id = self.current_provider_id(providers)
        config_path = self.codex_home / "config.toml"
        auth_path = self.codex_home / "auth.json"
        if not active_id or not config_path.exists() or not auth_path.exists():
            return
        try:
            config = config_path.read_text(encoding="utf-8")
            tomllib.loads(config)
            auth = json.loads(auth_path.read_text(encoding="utf-8"))
            vault = self.vault.load()
            saved = dict(vault.get(active_id) or {})
            active = next((provider for provider in providers if provider.id == active_id), None)
            saved.update({"config": config, "auth": auth})
            if active is not None:
                saved["name"] = active.name
            vault[active_id] = saved
            self.vault.save(vault)
        except Exception as exc:
            self.log(tr("skip_snapshot", error=exc))

    def switch(self, provider: Provider, verify: bool, close: bool, restart: bool) -> dict:
        processes = running_codex_processes()
        if processes and not close:
            raise SwitchError("Codex 仍在运行。请勾选“自动关闭 Codex”，或先手动退出。")
        target = provider.model_provider
        needs_official_login = provider.id == BUILTIN_OFFICIAL_ID and provider.auth.get("auth_mode") != "chatgpt"
        auth = None if needs_official_login else normalize_auth(provider.auth, target)
        tomllib.loads(provider.config)
        if auth is not None and auth.get("auth_mode") != "chatgpt":
            data = tomllib.loads(provider.config)
            selected = data.get("model_providers", {}).get(target)
            if not isinstance(selected, dict) or not selected.get("base_url"):
                raise SwitchError(f"配置里没有 [model_providers.{target}] 或 base_url。")
            if selected.get("wire_api", "responses") != "responses":
                raise SwitchError("当前 Codex 只支持 Responses 协议（wire_api = 'responses'）。")
            if not selected.get("requires_openai_auth", False):
                raise SwitchError("第三方 Provider 必须设置 requires_openai_auth = true 才能使用 auth.json 的 Key。")

        provider = Provider(provider.id, provider.name, provider.config, auth or {"auth_mode": "logged_out"}, provider.is_current, provider.source)
        if verify:
            self.log(tr("validating"))
            self.log(probe_provider(provider))

        providers = self.providers()
        self.snapshot_current(providers)
        if processes:
            self.log(tr("closing_codex"))
            close_codex_processes(self.log)

        backup = Backup(self.codex_home)
        for name in (
            "config.toml", "auth.json", "state_5.sqlite", "state_5.sqlite-wal", "state_5.sqlite-shm",
            "session_index.jsonl", ".codex-global-state.json",
        ):
            backup.save(self.codex_home / name)
        try:
            self.log(tr("writing_credentials"))
            atomic_write(self.codex_home / "config.toml", provider.config.encode("utf-8"))
            if auth is None:
                (self.codex_home / "auth.json").unlink(missing_ok=True)
            else:
                write_json(self.codex_home / "auth.json", auth)
            # Read back what was written; this catches antivirus/filesystem interference too.
            if effective_model_provider((self.codex_home / "config.toml").read_text(encoding="utf-8")) != target:
                raise SwitchError("配置回读校验不一致。")
            if auth is not None:
                readback_auth = json.loads((self.codex_home / "auth.json").read_text(encoding="utf-8"))
                if readback_auth.get("auth_mode") != auth.get("auth_mode"):
                    raise SwitchError("账号凭据回读校验不一致。")

            self.log(tr("syncing_history"))
            stats = sync_history(self.codex_home, target, backup, self.log)
            backup.finish(provider.id)

            vault = self.vault.load()
            saved = dict(vault.get(provider.id) or {})
            saved.update({"name": provider.name, "config": provider.config})
            if auth is not None:
                saved["auth"] = auth
            vault[provider.id] = saved
            self.vault.save(vault)
            state = self.state()
            state.update({"active_provider_id": provider.id, "codex_home": str(self.codex_home)})
            write_json(self.state_path, state)
            prune_backups(self.codex_home)
            self.log(tr("switch_complete", **stats))
            if needs_official_login:
                self.log(tr("official_login_ready"))
        except Exception:
            self.log(tr("rolling_back"))
            backup.restore()
            backup.finish("ROLLBACK")
            if restart:
                restart_codex()
            raise

        if restart:
            self.log(tr("restarting_codex"))
            restart_codex()
        return stats

    def add_custom_provider(self, name: str, base_url: str, api_key: str, model: str) -> Provider:
        return self.save_custom_provider(None, name, base_url, api_key, model)

    def save_custom_provider(
        self,
        provider: Provider | None,
        name: str,
        base_url: str,
        api_key: str,
        model: str,
    ) -> Provider:
        name, base_url, api_key, model = (
            name.strip(), base_url.strip().rstrip("/"), api_key.strip(), model.strip()
        )
        if not name:
            raise SwitchError("请填写配置名称。")
        if not re.match(r"^https?://", base_url, re.I):
            raise SwitchError("Base URL 必须以 http:// 或 https:// 开头。")
        if provider is not None and provider.id == BUILTIN_OFFICIAL_ID:
            raise SwitchError("内置官方账号配置不能修改。")
        if not api_key and provider is not None:
            api_key = str(provider.auth.get("OPENAI_API_KEY") or "").strip()
        if not api_key:
            raise SwitchError("请填写 API Key。")
        if not model:
            raise SwitchError("请填写模型名称。")
        if provider is None:
            config_path = self.codex_home / "config.toml"
            base_config = config_path.read_text(encoding="utf-8") if config_path.exists() else ""
            provider_id = f"user-{uuid.uuid4()}"
        else:
            base_config = provider.config
            provider_id = provider.id
        config = custom_provider_config(base_config, name, base_url, model)
        auth = {"OPENAI_API_KEY": api_key, "auth_mode": "apikey"}
        result = Provider(provider_id, name, config, auth, source=tr("source_local"))
        vault = self.vault.load()
        vault[provider_id] = {
            "name": name,
            "config": config,
            "auth": auth,
            "managed_by": APP_NAME,
        }
        self.vault.save(vault)
        return result

    def delete_provider(self, provider: Provider) -> None:
        if provider.id == BUILTIN_OFFICIAL_ID:
            raise SwitchError("内置官方账号配置不能删除。")
        vault = self.vault.load()
        saved = vault.get(provider.id)
        if not isinstance(saved, dict):
            raise SwitchError("没有找到这个本地配置。")
        if provider.id == self.current_provider_id():
            raise SwitchError("当前正在使用这个配置，请先切换到其他 Provider。")
        del vault[provider.id]
        self.vault.save(vault)

    def repair_history(self, provider: Provider, close: bool) -> dict:
        if running_codex_processes():
            if not close:
                raise SwitchError("修复历史前必须退出 Codex。")
            close_codex_processes(self.log)
        backup = Backup(self.codex_home)
        try:
            stats = sync_history(self.codex_home, provider.model_provider, backup, self.log)
            backup.finish(provider.id)
            prune_backups(self.codex_home)
            return stats
        except Exception:
            backup.restore()
            raise


class CheckOption(tk.Checkbutton):
    """A clear check-mark option; avoids the clam theme's misleading X indicator."""

    def __init__(self, master, text: str, variable: tk.BooleanVar):
        self.label_text = text
        self.variable = variable
        super().__init__(
            master,
            variable=variable,
            indicatoron=False,
            command=self._refresh,
            relief="flat",
            offrelief="flat",
            overrelief="flat",
            borderwidth=0,
            highlightthickness=0,
            background="#ffffff",
            activebackground="#ffffff",
            foreground="#475569",
            activeforeground="#24324a",
            selectcolor="#ffffff",
            font=(UI_FONT, 9),
            cursor="hand2",
            padx=2,
            pady=2,
        )
        self._refresh()

    def _refresh(self) -> None:
        self.configure(text=f"{'☑' if self.variable.get() else '☐'} {self.label_text}")


def app_dialog(parent, message: str, *, kind: str = "info", confirm: bool = False) -> bool:
    """Language-aware modal dialog; avoids OS-localized messagebox buttons."""
    dialog = tk.Toplevel(parent)
    dialog.title(APP_NAME)
    dialog.resizable(False, False)
    dialog.transient(parent)
    dialog.configure(bg="#ffffff")
    result = {"value": False}

    body = tk.Frame(dialog, bg="#ffffff", padx=24, pady=22)
    body.pack(fill="both", expand=True)
    icons = {"info": ("i", "#6257e8"), "warning": ("!", "#e39a2f"), "error": ("×", "#d84a5b"), "question": ("?", "#2684d8")}
    symbol, color = icons.get(kind, icons["info"])
    tk.Label(
        body, text=symbol, bg=color, fg="#ffffff", width=2, height=1,
        font=("Segoe UI", 18, "bold"),
    ).pack(side="left", anchor="n", padx=(0, 18))
    tk.Label(
        body, text=message, bg="#ffffff", fg="#111827", justify="left",
        wraplength=430, font=(UI_FONT, 10),
    ).pack(side="left", fill="both", expand=True)

    footer = tk.Frame(dialog, bg="#f5f6f9", padx=18, pady=12)
    footer.pack(fill="x")

    def finish(value: bool) -> None:
        result["value"] = value
        dialog.destroy()

    def dialog_button(text: str, command, *, primary: bool = False) -> tk.Button:
        """Use a native Tk button so Windows ttk themes cannot hide its text."""
        colors = {
            "bg": "#6257e8" if primary else "#ffffff",
            "fg": "#ffffff" if primary else "#374151",
            "activebackground": "#5146d7" if primary else "#eef0f5",
            "activeforeground": "#ffffff" if primary else "#111827",
            "highlightbackground": "#6257e8" if primary else "#d7dbe5",
        }
        return tk.Button(
            footer,
            text=text,
            command=command,
            width=12,
            padx=8,
            pady=7,
            relief="flat",
            borderwidth=0,
            highlightthickness=1,
            cursor="hand2",
            font=(UI_FONT, 9, "bold" if primary else "normal"),
            takefocus=True,
            **colors,
        )

    if confirm:
        dialog_button(tr("cancel"), lambda: finish(False)).pack(side="right")
        dialog_button(tr("confirm"), lambda: finish(True), primary=True).pack(side="right", padx=(0, 10))
    else:
        dialog_button(tr("ok"), lambda: finish(True), primary=True).pack(side="right")

    dialog.protocol("WM_DELETE_WINDOW", lambda: finish(False))
    dialog.bind("<Escape>", lambda _event: finish(False))
    dialog.bind("<Return>", lambda _event: finish(True))
    dialog.update_idletasks()
    # CJK languages wrap at different positions. Size from Tk's actual layout
    # instead of estimating from Python character counts, which could crop the
    # footer buttons for Korean and Japanese messages.
    screen_width = dialog.winfo_screenwidth()
    screen_height = dialog.winfo_screenheight()
    width = min(max(540, dialog.winfo_reqwidth() + 4), max(540, screen_width - 80))
    height = min(max(220, dialog.winfo_reqheight() + 8), max(220, screen_height - 100))
    x = parent.winfo_rootx() + max(0, (parent.winfo_width() - width) // 2)
    y = parent.winfo_rooty() + max(0, (parent.winfo_height() - height) // 2)
    dialog.geometry(f"{width}x{height}+{x}+{y}")
    dialog.grab_set()
    dialog.wait_window()
    return result["value"]


class NewProviderDialog(tk.Toplevel):
    def __init__(self, parent: "App", provider: Provider | None = None):
        super().__init__(parent)
        self.parent = parent
        self.engine = parent.engine
        self.provider = provider
        editing = provider is not None
        self.title(tr("edit_dialog") if editing else tr("new_dialog"))
        self.geometry("600x430")
        self.resizable(False, False)
        self.configure(bg="#f5f7fb")
        self.transient(parent)
        self.grab_set()
        self.name_var = tk.StringVar(value=provider.name if provider else "")
        self.url_var = tk.StringVar(value=provider_base_url(provider.config) or "" if provider else "")
        self.key_var = tk.StringVar()
        self.model_var = tk.StringVar(value=(provider_model(provider.config) or "") if provider else "gpt-5.6-terra")
        hint = tr("edit_hint") if editing else tr("new_hint")
        self.status_var = tk.StringVar(value=hint)
        self._build()
        self.protocol("WM_DELETE_WINDOW", self.destroy)

    def _build(self) -> None:
        frame = ttk.Frame(self, padding=24)
        frame.pack(fill="both", expand=True)
        title = tr("edit_dialog") if self.provider else tr("new_dialog")
        ttk.Label(frame, text=title, style="Title.TLabel").grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 16))
        fields = ((tr("profile_name"), self.name_var, False), ("Base URL", self.url_var, False), ("API Key", self.key_var, True))
        for row, (label, variable, secret) in enumerate(fields, 1):
            ttk.Label(frame, text=label).grid(row=row, column=0, sticky="w", padx=(0, 14), pady=7)
            entry = ttk.Entry(frame, textvariable=variable, width=49, show="●" if secret else "")
            entry.grid(row=row, column=1, sticky="ew", pady=7)
            if row == 1:
                entry.focus_set()
        ttk.Label(frame, text=tr("model_name")).grid(row=4, column=0, sticky="w", padx=(0, 14), pady=7)
        self.model_combo = ttk.Combobox(frame, textvariable=self.model_var, width=47, state="normal")
        self.model_combo.grid(row=4, column=1, sticky="ew", pady=7)
        ttk.Label(frame, textvariable=self.status_var, style="Sub.TLabel", wraplength=500).grid(
            row=5, column=0, columnspan=2, sticky="w", pady=(12, 16)
        )
        buttons = ttk.Frame(frame)
        buttons.grid(row=6, column=0, columnspan=2, sticky="ew")
        self.models_button = ttk.Button(buttons, text=tr("fetch_models"), command=self.detect_models)
        self.models_button.pack(side="left")
        self.test_button = ttk.Button(buttons, text=tr("test_api").replace("✓  ", ""), command=self.test_api)
        self.test_button.pack(side="left", padx=(10, 0))
        ttk.Button(buttons, text=tr("cancel"), command=self.destroy).pack(side="right")
        self.save_button = ttk.Button(buttons, text=tr("save_changes") if self.provider else tr("save_profile"), style="Primary.TButton", command=self.save)
        self.save_button.pack(side="right", padx=10)
        frame.columnconfigure(1, weight=1)

    def values(self) -> tuple[str, str, str, str]:
        return self.name_var.get(), self.url_var.get(), self.key_var.get(), self.model_var.get()

    def temporary_provider(self, require_model: bool = True) -> Provider:
        name, base_url, api_key, model = (v.strip() for v in self.values())
        if not api_key and self.provider is not None:
            api_key = str(self.provider.auth.get("OPENAI_API_KEY") or "").strip()
        if not base_url or not api_key:
            raise SwitchError("请先填写 Base URL 和 API Key。")
        if require_model and (not name or not model):
            raise SwitchError("检测 API 前还需要填写配置名称和模型。")
        if not re.match(r"^https?://", base_url, re.I):
            raise SwitchError("Base URL 必须以 http:// 或 https:// 开头。")
        name = name or "待检测 Provider"
        model = model or "auto-detect"
        q = lambda value: json.dumps(value, ensure_ascii=False)
        config = (
            f"model_provider = \"custom\"\nmodel = {q(model)}\n"
            "[model_providers.custom]\n"
            f"name = {q(name)}\nbase_url = {q(base_url.rstrip('/'))}\n"
            "wire_api = \"responses\"\nrequires_openai_auth = true\n"
        )
        return Provider("temporary", name, config, {"OPENAI_API_KEY": api_key, "auth_mode": "apikey"}, source="待保存")

    def _set_detecting(self, detecting: bool) -> None:
        state = "disabled" if detecting else "normal"
        self.models_button.configure(state=state)
        self.test_button.configure(state=state)
        self.save_button.configure(state=state)

    def _apply_models(self, models: list[str]) -> None:
        self.model_combo.configure(values=models)
        current = self.model_var.get().strip()
        if current not in models:
            preferred = next((m for m in models if "gpt-5.6-terra" in m.lower()), None)
            self.model_var.set(preferred or models[0])

    def detect_models(self, show_dialog: bool = True) -> None:
        try:
            provider = self.temporary_provider(require_model=False)
        except Exception as exc:
            app_dialog(self, str(exc), kind="error")
            return
        self._set_detecting(True)
        self.status_var.set(tr("fetching_models"))

        def work():
            try:
                models = fetch_provider_models(provider)
                self.after(0, lambda: self._apply_models(models))
                self.after(0, lambda: self.status_var.set(tr("models_ready", count=len(models))))
                if show_dialog:
                    self.after(0, lambda: app_dialog(self, tr("models_dialog", count=len(models))))
            except Exception as exc:
                self.after(0, lambda e=exc: self.status_var.set(tr("models_failed", error=e)))
                if show_dialog:
                    self.after(0, lambda e=exc: app_dialog(self, tr("models_failed", error=e), kind="error"))
            finally:
                self.after(0, lambda: self._set_detecting(False))
        threading.Thread(target=work, daemon=True).start()

    def test_api(self) -> None:
        try:
            provider = self.temporary_provider()
        except Exception as exc:
            app_dialog(self, str(exc), kind="error")
            return
        self._set_detecting(True)
        self.status_var.set(tr("testing_api_status"))

        def work():
            try:
                try:
                    models = fetch_provider_models(provider)
                    self.after(0, lambda: self._apply_models(models))
                    result = tr("models_found", count=len(models))
                except ModelDiscoveryUnavailable as unavailable:
                    result = tr("models_unavailable", error=unavailable)
                self.after(0, lambda: self.status_var.set(tr("test_passed_status", result=result)))
                self.after(0, lambda: app_dialog(self, tr("test_passed_status", result=result)))
            except Exception as exc:
                self.after(0, lambda e=exc: self.status_var.set(tr("test_failed_status", error=e)))
                self.after(0, lambda e=exc: app_dialog(self, str(e), kind="error"))
            finally:
                self.after(0, lambda: self._set_detecting(False))
        threading.Thread(target=work, daemon=True).start()

    def save(self) -> None:
        try:
            provider = self.engine.save_custom_provider(self.provider, *self.values())
        except Exception as exc:
            app_dialog(self, str(exc), kind="error")
            return
        action = tr("updated_action") if self.provider else tr("created")
        self.parent.log(tr("saved_profile", action=action, name=provider.name))
        self.parent.refresh(select_id=provider.id)
        self.destroy()

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        set_language(preferred_language())
        self.title(f"{APP_NAME}  {APP_VERSION}")
        icon_png = resource_path("assets/codexshift-logo.png")
        icon_ico = resource_path("assets/codexshift.ico")
        if icon_png.exists():
            self._icon_image = tk.PhotoImage(file=str(icon_png))
            self.iconphoto(True, self._icon_image)
        if IS_WINDOWS and icon_ico.exists():
            self.iconbitmap(str(icon_ico))
        self.geometry("1040x820")
        self.minsize(920, 720)
        self.configure(bg="#f3f5fa")
        self.engine = SwitchEngine(configured_codex_home(), self.log)
        self.providers_cache: list[Provider] = []
        self.verify_var = tk.BooleanVar(value=True)
        self.close_var = tk.BooleanVar(value=True)
        self.restart_var = tk.BooleanVar(value=True)
        self.status_var = tk.StringVar(value=tr("loading"))
        self.current_name_var = tk.StringVar(value=tr("detecting"))
        self.provider_count_var = tk.StringVar(value=tr("profile_count", count=0))
        self.language_var = tk.StringVar(value=LANGUAGE_LABELS[CURRENT_LANGUAGE])
        self._build_style()
        self._build_ui()
        self.after(100, self.refresh)

    def _build_style(self) -> None:
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure("TFrame", background="#f3f5fa")
        style.configure("Card.TFrame", background="#ffffff")
        style.configure("Topbar.TFrame", background="#11152c")
        style.configure("TLabel", background="#f3f5fa", foreground="#111827", font=(UI_FONT, 10))
        style.configure("Card.TLabel", background="#ffffff", foreground="#111827", font=(UI_FONT, 10))
        style.configure("Title.TLabel", background="#f3f5fa", foreground="#111827", font=(UI_FONT, 20, "bold"))
        style.configure("Sub.TLabel", background="#f3f5fa", foreground="#7c8799", font=(UI_FONT, 9))
        style.configure("CardTitle.TLabel", background="#ffffff", foreground="#111827", font=(UI_FONT, 12, "bold"))
        style.configure("CardSub.TLabel", background="#ffffff", foreground="#7c8799", font=(UI_FONT, 9))
        style.configure("Current.TLabel", background="#ffffff", foreground="#111827", font=(UI_FONT, 16, "bold"))
        style.configure("Primary.TButton", font=(UI_FONT, 10, "bold"), padding=(18, 11), background="#6257e8", foreground="#ffffff", borderwidth=0)
        style.map("Primary.TButton", background=[("active", "#5146d7"), ("disabled", "#b9b5e8")], foreground=[("disabled", "#f4f3ff")])
        style.configure("Secondary.TButton", font=(UI_FONT, 10, "bold"), padding=(15, 10), background="#eeecff", foreground="#4d43c7", borderwidth=0)
        style.map("Secondary.TButton", background=[("active", "#dedaff"), ("disabled", "#f3f2fa")], foreground=[("disabled", "#aaa6c9")])
        style.configure("Ghost.TButton", font=(UI_FONT, 9), padding=(13, 9), background="#ffffff", foreground="#4b5565", bordercolor="#dfe3eb", lightcolor="#dfe3eb", darkcolor="#dfe3eb", borderwidth=1)
        style.map("Ghost.TButton", background=[("active", "#f6f7fb"), ("disabled", "#f6f7f9")], foreground=[("disabled", "#adb3bd")])
        style.configure("Danger.TButton", font=(UI_FONT, 9), padding=(13, 9), background="#fff1f2", foreground="#be3447", borderwidth=0)
        style.map("Danger.TButton", background=[("active", "#ffe3e6"), ("disabled", "#f7f3f4")], foreground=[("disabled", "#c9aeb2")])
        style.configure("TButton", font=(UI_FONT, 10), padding=(13, 8))
        style.configure("Treeview", rowheight=44, font=(UI_FONT, 10), background="#ffffff", fieldbackground="#ffffff", foreground="#263247", borderwidth=0)
        style.configure("Treeview.Heading", font=(UI_FONT, 9, "bold"), padding=(10, 10), background="#f7f8fb", foreground="#6b7585", relief="flat")
        style.map("Treeview.Heading", background=[("active", "#f1f2f7")])
        style.map("Treeview", background=[("selected", "#e9e7ff")], foreground=[("selected", "#302878")])
        style.configure("TCheckbutton", background="#ffffff", font=(UI_FONT, 9), foreground="#475569")

    def _build_ui(self) -> None:
        topbar = tk.Frame(self, bg="#11152c", height=126)
        topbar.pack(fill="x")
        topbar.pack_propagate(False)
        topbar_inner = tk.Frame(topbar, bg="#11152c")
        topbar_inner.pack(fill="both", expand=True, padx=34, pady=25)
        if hasattr(self, "_icon_image"):
            self._header_logo = self._icon_image.subsample(16, 16)
            tk.Label(topbar_inner, image=self._header_logo, bg="#11152c", borderwidth=0).pack(side="left", padx=(0, 17))
        heading = tk.Frame(topbar_inner, bg="#11152c")
        heading.pack(side="left", fill="y")
        tk.Label(heading, text="CodexShift", bg="#11152c", fg="#ffffff", font=(UI_FONT, 22, "bold")).pack(anchor="w")
        tk.Label(
            heading,
            text=tr("subtitle"),
            bg="#11152c",
            fg="#aeb5d1",
            font=("Segoe UI", 10),
        ).pack(anchor="w", pady=(3, 0))
        tk.Label(
            topbar_inner,
            text=f"v{APP_VERSION}",
            bg="#292e51",
            fg="#dfe2ff",
            font=("Segoe UI", 9, "bold"),
            padx=12,
            pady=6,
        ).pack(side="right", anchor="n", pady=4)
        language_text = f"🌐  {tr('language_label')} · {self.language_var.get()}  ▾"
        self.language_button = tk.Menubutton(
            topbar_inner,
            text=language_text,
            bg="#292e51",
            fg="#ffffff",
            activebackground="#353b64",
            activeforeground="#ffffff",
            relief="flat",
            borderwidth=0,
            highlightthickness=0,
            cursor="hand2",
            font=(UI_FONT, 9),
            padx=13,
            pady=6,
            direction="below",
        )
        language_menu = tk.Menu(
            self.language_button,
            tearoff=False,
            bg="#ffffff",
            fg="#263247",
            activebackground="#e9e7ff",
            activeforeground="#302878",
            font=(UI_FONT, 9),
            borderwidth=1,
            relief="solid",
        )
        for code, label in LANGUAGE_LABELS.items():
            marker = "✓  " if code == CURRENT_LANGUAGE else "    "
            language_menu.add_command(label=marker + label, command=lambda selected=code: self.select_language(selected))
        self.language_button.configure(menu=language_menu)
        self.language_button.pack(side="right", anchor="n", padx=(0, 10), pady=4)

        outer = ttk.Frame(self, padding=(28, 20, 28, 24))
        outer.pack(fill="both", expand=True)

        status_border = tk.Frame(outer, bg="#e4e7ef", highlightthickness=0)
        status_border.pack(fill="x", pady=(0, 14))
        status = tk.Frame(status_border, bg="#ffffff")
        status.pack(fill="both", padx=1, pady=1)
        tk.Frame(status, bg="#6257e8", width=5).pack(side="left", fill="y")
        status_text = tk.Frame(status, bg="#ffffff")
        status_text.pack(side="left", fill="both", expand=True, padx=18, pady=13)
        tk.Label(status_text, text=tr("current_connection"), bg="#ffffff", fg="#7c8799", font=(UI_FONT, 9)).pack(anchor="w")
        ttk.Label(status_text, textvariable=self.current_name_var, style="Current.TLabel").pack(anchor="w", pady=(2, 0))
        status_right = tk.Frame(status, bg="#ffffff")
        status_right.pack(side="right", padx=14, pady=13)
        ttk.Button(status_right, text=tr("refresh"), style="Ghost.TButton", command=self.refresh).pack(side="right")
        self.home_button = ttk.Button(
            status_right, text=tr("path_settings"), style="Ghost.TButton", command=self.show_home_menu
        )
        self.home_button.pack(side="right", padx=(0, 8))
        tk.Label(
            status_right,
            textvariable=self.status_var,
            bg="#ffffff",
            fg="#7c8799",
            font=(UI_FONT, 9),
        ).pack(side="right", padx=(0, 16))

        provider_border = tk.Frame(outer, bg="#e4e7ef")
        provider_border.pack(fill="x", pady=(0, 14))
        provider_card = ttk.Frame(provider_border, style="Card.TFrame", padding=(18, 15, 18, 17))
        provider_card.pack(fill="both", padx=1, pady=1)
        table_header = ttk.Frame(provider_card, style="Card.TFrame")
        table_header.pack(fill="x", pady=(0, 12))
        table_title = ttk.Frame(table_header, style="Card.TFrame")
        table_title.pack(side="left")
        ttk.Label(table_title, text=tr("provider_profiles"), style="CardTitle.TLabel").pack(side="left")
        ttk.Label(table_title, textvariable=self.provider_count_var, style="CardSub.TLabel").pack(side="left", padx=(10, 0), pady=(3, 0))
        self.new_button = ttk.Button(table_header, text=tr("new_profile"), style="Secondary.TButton", command=self.new_provider)
        self.new_button.pack(side="right")
        self.delete_button = ttk.Button(table_header, text=tr("delete"), style="Danger.TButton", command=self.delete_selected)
        self.delete_button.pack(side="right", padx=(8, 0))
        self.edit_button = ttk.Button(table_header, text=tr("edit"), style="Ghost.TButton", command=self.edit_selected)
        self.edit_button.pack(side="right", padx=(8, 0))

        columns = ("name", "kind", "model", "source", "current")
        self.tree = ttk.Treeview(provider_card, columns=columns, show="headings", height=5, selectmode="browse")
        headings = {"name": "PROVIDER", "kind": tr("type"), "model": tr("model"), "source": tr("source"), "current": tr("status")}
        widths = {"name": 250, "kind": 125, "model": 170, "source": 120, "current": 90}
        for key in columns:
            self.tree.heading(key, text=headings[key])
            self.tree.column(key, width=widths[key], anchor="w" if key in ("name", "model") else "center")
        self.tree.pack(fill="x")
        self.tree.bind("<<TreeviewSelect>>", lambda _event: self.update_provider_actions())
        self.tree.bind("<Double-1>", lambda _event: self.edit_selected())
        self.tree.tag_configure("current", background="#f3f1ff", foreground="#302878")
        self.tree.tag_configure("official", foreground="#245c4a")
        self.tree.tag_configure("custom", foreground="#263247")

        options = ttk.Frame(provider_card, style="Card.TFrame")
        options.pack(fill="x", pady=(13, 1))
        CheckOption(options, tr("verify_on_switch"), self.verify_var).pack(side="left", padx=(0, 18))
        CheckOption(options, tr("auto_close"), self.close_var).pack(side="left", padx=(0, 18))
        CheckOption(options, tr("restart_after"), self.restart_var).pack(side="left")

        actions = ttk.Frame(outer)
        actions.pack(fill="x", pady=(0, 14))
        self.switch_button = ttk.Button(actions, text=tr("switch_selected"), style="Primary.TButton", command=self.start_switch)
        self.switch_button.pack(side="left")
        self.test_button = ttk.Button(actions, text=tr("test_api"), style="Secondary.TButton", command=self.test_selected)
        self.test_button.pack(side="left", padx=(10, 0))
        self.repair_button = ttk.Button(actions, text=tr("repair_history"), style="Ghost.TButton", command=self.start_repair)
        self.repair_button.pack(side="left", padx=(10, 0))
        ttk.Button(actions, text=tr("open_backups"), style="Ghost.TButton", command=self.open_backups).pack(side="right")

        log_border = tk.Frame(outer, bg="#1b2437")
        log_border.pack(fill="both", expand=True)
        log_header = tk.Frame(log_border, bg="#151c2b", height=38)
        log_header.pack(fill="x")
        log_header.pack_propagate(False)
        tk.Label(log_header, text=tr("execution_log"), bg="#151c2b", fg="#f2f5fb", font=(UI_FONT, 9, "bold")).pack(side="left", padx=14)
        tk.Label(log_header, text="●  LIVE", bg="#151c2b", fg="#54d89b", font=("Segoe UI", 8, "bold")).pack(side="right", padx=14)
        self.log_box = tk.Text(
            log_border,
            height=8,
            bg="#0c1220",
            fg="#cbd5e1",
            insertbackground="#ffffff",
            selectbackground="#363f68",
            relief="flat",
            font=(MONO_FONT, 9),
            padx=14,
            pady=11,
            state="disabled",
            wrap="word",
        )
        self.log_box.pack(fill="both", expand=True, padx=1, pady=(0, 1))

    def log(self, message: str) -> None:
        def append():
            stamp = dt.datetime.now().strftime("%H:%M:%S")
            self.log_box.configure(state="normal")
            self.log_box.insert("end", f"[{stamp}] {message}\n")
            self.log_box.see("end")
            self.log_box.configure(state="disabled")
        if threading.current_thread() is threading.main_thread():
            append()
        else:
            self.after(0, append)

    def change_language(self, _event=None) -> None:
        code = next((key for key, label in LANGUAGE_LABELS.items() if label == self.language_var.get()), "zh-CN")
        if code == CURRENT_LANGUAGE:
            return
        old_log = self.log_box.get("1.0", "end-1c") if hasattr(self, "log_box") else ""
        set_language(code)
        state = self.engine.state()
        state["language"] = code
        write_json(self.engine.state_path, state)
        self.status_var.set(tr("loading"))
        self.current_name_var.set(tr("detecting"))
        for child in self.winfo_children():
            child.destroy()
        self._build_style()
        self._build_ui()
        if old_log:
            self.log_box.configure(state="normal")
            self.log_box.insert("end", old_log + "\n")
            self.log_box.configure(state="disabled")
        self.refresh()

    def select_language(self, code: str) -> None:
        self.language_var.set(LANGUAGE_LABELS.get(code, LANGUAGE_LABELS["zh-CN"]))
        self.change_language()

    def refresh(self, select_id: str | None = None) -> None:
        try:
            self.providers_cache = self.engine.providers()
            self.tree.delete(*self.tree.get_children())
            selected = None
            for provider in self.providers_cache:
                model = provider_model(provider.config) or tr("auto")
                tag = "current" if provider.is_current else ("official" if provider.is_official else "custom")
                status = tr("current") if provider.is_current else ""
                item = self.tree.insert(
                    "",
                    "end",
                    iid=provider.id,
                    values=(provider.name, provider.kind_label, model, provider.source, status),
                    tags=(tag,),
                )
                if provider.is_current:
                    selected = item
            if select_id and self.tree.exists(select_id):
                selected = select_id
            if selected:
                self.tree.selection_set(selected)
                self.tree.focus(selected)
            elif self.providers_cache:
                self.tree.selection_set(self.providers_cache[0].id)
            current = next((p for p in self.providers_cache if p.is_current), None)
            self.current_name_var.set(current.name if current else tr("unknown"))
            self.provider_count_var.set(tr("profile_count", count=len(self.providers_cache)))
            self.status_var.set(f"Codex Home  ·  {self.engine.codex_home}")
            self.update_provider_actions()
            self.log(tr("read_profiles", count=len(self.providers_cache)))
        except Exception as exc:
            self.current_name_var.set("读取失败")
            self.status_var.set("读取失败")
            self.log(str(exc))
            app_dialog(self, str(exc), kind="error")

    def selected_provider(self) -> Provider | None:
        chosen = self.tree.selection()
        if not chosen:
            app_dialog(self, tr("select_profile"))
            return None
        return next((p for p in self.providers_cache if p.id == chosen[0]), None)

    def set_busy(self, busy: bool) -> None:
        state = "disabled" if busy else "normal"
        self.switch_button.configure(state=state)
        self.test_button.configure(state=state)
        self.new_button.configure(state=state)
        self.repair_button.configure(state=state)
        if busy:
            self.edit_button.configure(state="disabled")
            self.delete_button.configure(state="disabled")
        else:
            self.update_provider_actions()

    def update_provider_actions(self) -> None:
        chosen = self.tree.selection() if hasattr(self, "tree") else ()
        provider = next((p for p in self.providers_cache if chosen and p.id == chosen[0]), None)
        state = "normal" if provider and provider.id != BUILTIN_OFFICIAL_ID else "disabled"
        self.edit_button.configure(state=state)
        self.delete_button.configure(state=state)

    def _run(self, work: Callable[[], None]) -> None:
        self.set_busy(True)
        def target():
            try:
                work()
            except Exception as exc:
                self.log(tr("operation_failed", error=exc))
                self.after(0, lambda: app_dialog(self, str(exc), kind="error"))
            finally:
                self.after(0, lambda: self.set_busy(False))
                self.after(0, self.refresh)
        threading.Thread(target=target, daemon=True).start()

    def start_switch(self) -> None:
        provider = self.selected_provider()
        if not provider:
            return
        if provider.id == BUILTIN_OFFICIAL_ID and provider.auth.get("auth_mode") != "chatgpt":
            answer = app_dialog(self, tr("confirm_official_login"), kind="question", confirm=True)
            if not answer:
                return
        running = running_codex_processes()
        if running and self.close_var.get():
            answer = app_dialog(self, tr("confirm_close", name=provider.name), kind="question", confirm=True)
            if not answer:
                return
        self._run(lambda: self.engine.switch(provider, self.verify_var.get(), self.close_var.get(), self.restart_var.get()))

    def new_provider(self) -> None:
        NewProviderDialog(self)

    def edit_selected(self) -> None:
        provider = self.selected_provider()
        if not provider:
            return
        if provider.id == BUILTIN_OFFICIAL_ID:
            app_dialog(self, tr("builtin_edit_locked"))
            return
        NewProviderDialog(self, provider)

    def delete_selected(self) -> None:
        provider = self.selected_provider()
        if not provider:
            return
        if provider.id == BUILTIN_OFFICIAL_ID:
            app_dialog(self, tr("builtin_delete_locked"))
            return
        if not app_dialog(self, tr("confirm_delete", name=provider.name), kind="warning", confirm=True):
            return
        try:
            self.engine.delete_provider(provider)
        except Exception as exc:
            app_dialog(self, str(exc), kind="error")
            return
        self.log(tr("profile_deleted", name=provider.name))
        self.refresh()

    def test_selected(self) -> None:
        provider = self.selected_provider()
        if not provider:
            return

        def work():
            self.log(tr("testing_profile", name=provider.name))
            result = probe_provider(provider)
            self.log(tr("api_passed", result=result))
            self.after(0, lambda: app_dialog(self, tr("test_passed_dialog", name=provider.name, result=result)))

        self._run(work)

    def start_repair(self) -> None:
        provider = self.selected_provider()
        if not provider:
            return
        if not app_dialog(self, tr("confirm_repair", name=provider.name), kind="question", confirm=True):
            return
        self._run(lambda: self._repair(provider))

    def _repair(self, provider: Provider) -> None:
        stats = self.engine.repair_history(provider, self.close_var.get())
        self.log(tr("repair_complete", stats=stats))

    def open_backups(self) -> None:
        path = self.engine.codex_home / "switcher_backups"
        path.mkdir(parents=True, exist_ok=True)
        if IS_WINDOWS:
            os.startfile(path)
        elif IS_MACOS:
            subprocess.Popen(["open", str(path)])
        else:
            subprocess.Popen(["xdg-open", str(path)])

    def show_home_menu(self) -> None:
        menu = tk.Menu(self, tearoff=False, font=(UI_FONT, 9))
        menu.add_command(label=tr("choose_home"), command=self.choose_codex_home)
        menu.add_command(label=tr("reset_home"), command=self.reset_codex_home)
        try:
            x = self.home_button.winfo_rootx()
            y = self.home_button.winfo_rooty() + self.home_button.winfo_height()
            menu.tk_popup(x, y)
        finally:
            menu.grab_release()

    def choose_codex_home(self) -> None:
        selected = filedialog.askdirectory(
            title="选择 Codex Home",
            initialdir=str(self.engine.codex_home),
            mustexist=True,
            parent=self,
        )
        if not selected:
            return
        path = Path(selected).expanduser().resolve()
        markers = ("config.toml", "auth.json", "state_5.sqlite", "sessions")
        if not any((path / marker).exists() for marker in markers):
            if not app_dialog(self, tr("home_not_detected"), kind="warning", confirm=True):
                return
        state = self.engine.state()
        state.update({"codex_home": str(path), "codex_home_manual": True})
        write_json(self.engine.state_path, state)
        self.engine.codex_home = path
        self.log(tr("home_changed", path=path))
        self.refresh()

    def reset_codex_home(self) -> None:
        path = default_codex_home().expanduser().resolve()
        state = self.engine.state()
        state.update({"codex_home": str(path), "codex_home_manual": False})
        write_json(self.engine.state_path, state)
        self.engine.codex_home = path
        self.log(tr("home_auto", path=path))
        self.refresh()


def main() -> int:
    if "--diagnose" in sys.argv:
        engine = SwitchEngine(configured_codex_home(), print)
        providers = engine.providers()
        print(json.dumps([
            {"id": p.id, "name": p.name, "kind": p.kind_label, "model_provider": p.model_provider, "source": p.source}
            for p in providers
        ], ensure_ascii=False, indent=2))
        return 0
    App().mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
