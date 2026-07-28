# -*- coding: utf-8 -*-
# !/bin/python
from __future__ import annotations

import os
import re
import subprocess
import time
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from urllib.parse import quote, unquote, urlsplit, urlunsplit

import yaml

from ..integrations.diagnostics import log_exception_event, log_task_event, log_warning_event
from ..shared.path_export import get_export_base
from app.db.config_paths import DEFAULT_SVN_CONFIG
from app.config.audit_rules import get_audit_rules

# SVN credentials and connection settings are deployment configuration, not package resources.
CONFIG_PATH = DEFAULT_SVN_CONFIG
DEFAULT_SVN_BIN = 'svn'
SENSITIVE_URL_QUERY_KEYS = {
    'access_token', 'apikey', 'api_key', 'authorization', 'credential',
    'password', 'passwd', 'secret', 'token',
}


class SvnCliNotFoundError(RuntimeError):
    """Raised only when the configured SVN executable cannot be started."""


def sanitize_svn_url_for_log(value: str) -> str:
    """Return a diagnostic-safe view of an SVN URL without changing its path."""
    if not isinstance(value, str):
        return value
    try:
        parsed = urlsplit(value)
    except ValueError:
        return value
    if parsed.scheme.lower() not in {'http', 'https', 'svn', 'svn+ssh', 'file'}:
        return value

    netloc = parsed.netloc
    if '@' in netloc:
        userinfo, host = netloc.rsplit('@', 1)
        username, separator, _password = userinfo.partition(':')
        netloc = f'{username}:***@{host}' if separator else f'{username}@{host}'

    query_parts = []
    for part in parsed.query.split('&'):
        key, separator, value_part = part.partition('=')
        if separator and unquote(key).lower() in SENSITIVE_URL_QUERY_KEYS:
            query_parts.append(f'{key}=***')
        else:
            query_parts.append(part)
    return urlunsplit((parsed.scheme, netloc, parsed.path, '&'.join(query_parts), parsed.fragment))


def sanitize_svn_command_for_log(command) -> list[str]:
    """Copy an SVN command for logs, redacting password arguments and URL secrets."""
    if not command:
        return []

    safe_command = []
    redact_next = False
    for argument in command:
        value = str(argument)
        if redact_next:
            safe_command.append('***')
            redact_next = False
        elif value == '--password':
            safe_command.append(value)
            redact_next = True
        elif value.startswith('--password='):
            safe_command.append('--password=***')
        else:
            safe_command.append(sanitize_svn_url_for_log(value))
    return safe_command


def _sanitize_svn_text_for_log(value, command=()) -> str:
    """Redact command-derived credentials when SVN or its exceptions echo them."""
    safe_text = str(value)
    command_values = list(command or ())
    for index, argument in enumerate(command_values):
        argument = str(argument)
        if argument == '--password' and index + 1 < len(command_values):
            password = str(command_values[index + 1])
            if password:
                safe_text = safe_text.replace(password, '***')
        elif argument.startswith('--password='):
            password = argument.split('=', 1)[1]
            if password:
                safe_text = safe_text.replace(password, '***')
        sanitized_argument = sanitize_svn_url_for_log(argument)
        if sanitized_argument != argument:
            safe_text = safe_text.replace(argument, sanitized_argument)
    return re.sub(
        r"(?:https?|svn(?:\+ssh)?|file)://[^\s'\"\]\)]+",
        lambda match: sanitize_svn_url_for_log(match.group(0)),
        safe_text,
    )


def _svn_output_summary(value: str, command) -> str:
    return _sanitize_svn_text_for_log(value, command)[:500]


def _log_svn_exception(event: str, exc: BaseException, command=(), **fields) -> None:
    """Keep diagnostic detail without allowing exception formatting to expose a command."""
    safe_command = sanitize_svn_command_for_log(command)
    safe_fields = {
        key: sanitize_svn_url_for_log(value) if key.endswith('url') else value
        for key, value in fields.items()
    }
    safe_fields.update(
        exception_type=type(exc).__name__,
        exception_message=_sanitize_svn_text_for_log(exc, command),
    )
    if command:
        safe_fields['command'] = safe_command
    log_exception_event(event, RuntimeError('SVN command failed; see sanitized fields'), **safe_fields)


def build_compare_url(base_url: str, revision: str | None = None) -> str:
    plain_url = strip_peg_revision(base_url)
    if revision:
        return f'{plain_url}@{revision}'
    return plain_url


def expand_env_value(value):
    if not isinstance(value, str):
        return value
    if value.startswith('${') and value.endswith('}'):
        return os.getenv(value[2:-1], '')
    return value


def expand_env_config(config):
    return {key: expand_env_value(value) for key, value in config.items()}


def load_svn_config() -> dict:
    if not Path(CONFIG_PATH).is_file():
        raise FileNotFoundError(f'SVN 配置文件不存在: {CONFIG_PATH}')
    with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
        data = yaml.safe_load(f) or {}
    defaults = expand_env_config(data.get('defaults', {}))
    projects = data.get('projects', {})
    merged_projects = {}
    for name, project in projects.items():
        config = dict(defaults)
        config.update(expand_env_config(project or {}))
        merged_projects[name] = config
    return {'defaults': defaults, 'projects': merged_projects}


def get_project_config(project: str) -> dict:
    config = load_svn_config()
    projects = config.get('projects', {})
    if project not in projects:
        normalized_project = str(project).lower()
        for project_name, project_config in projects.items():
            if str(project_name).lower() == normalized_project:
                return project_config
        raise KeyError(f'svn project not found: {project}, config: {CONFIG_PATH}, projects: {list(projects)}')
    return projects[project]


def decode_svn_output(data: bytes) -> str:
    for encoding in ('gbk', 'utf-8'):
        try:
            return data.decode(encoding)
        except UnicodeDecodeError:
            pass
    return data.decode('utf-8', errors='replace')


def build_svn_command(project_config: dict, *args: str) -> list[str]:
    command = [project_config.get('svn_bin', DEFAULT_SVN_BIN), *args]
    if project_config.get('non_interactive', True):
        command.append('--non-interactive')
    if project_config.get('trust_server_cert', True):
        command.append('--trust-server-cert')

    username = str(project_config.get('username', '') or '').strip()
    password = str(project_config.get('password', '') or '').strip()
    if username:
        command.extend(['--username', username])
    if password:
        command.extend(['--password', password])
    return command


def run_svn_text(project_config: dict, *args: str) -> tuple[int, str, str]:
    command = build_svn_command(project_config, *args)
    safe_command = sanitize_svn_command_for_log(command)
    start_ts = time.time()
    log_task_event(
        "svn_command",
        "start",
        command=safe_command,
    )
    timeout = int(project_config.get('timeout', 120))
    try:
        result = subprocess.run(command, capture_output=True, timeout=timeout)
    except FileNotFoundError as exc:
        _log_svn_exception("SVN_COMMAND_EXCEPTION", exc, command=command)
        raise SvnCliNotFoundError(str(exc)) from exc
    except Exception as exc:
        _log_svn_exception("SVN_COMMAND_EXCEPTION", exc, command=command)
        raise

    elapsed_seconds = round(time.time() - start_ts, 3)
    stdout = decode_svn_output(result.stdout)
    stderr = decode_svn_output(result.stderr)
    log_task_event(
        "svn_command",
        "end",
        command=safe_command,
        returncode=result.returncode,
        elapsed_seconds=elapsed_seconds,
        stdout_length=len(stdout),
        stderr_length=len(stderr),
    )
    if elapsed_seconds >= 10:
        log_warning_event(
            "SVN_COMMAND_SLOW",
            command=safe_command,
            returncode=result.returncode,
            elapsed_seconds=elapsed_seconds,
        )
    if result.returncode != 0:
        log_warning_event(
            "SVN_COMMAND_FAILED",
            command=safe_command,
            returncode=result.returncode,
            stdout_summary=_svn_output_summary(stdout, command),
            stderr_summary=_svn_output_summary(stderr, command),
        )
    return result.returncode, stdout, stderr


def strip_peg_revision(url: str) -> str:
    return url.split('@', 1)[0]


def get_repo_root(project_config: dict, url: str) -> str:
    code, stdout, stderr = run_svn_text(project_config, 'info', '--xml', strip_peg_revision(url))
    if code != 0:
        raise RuntimeError(f'svn info 执行失败:\n{_sanitize_svn_text_for_log(stderr, build_svn_command(project_config))}')
    root = ET.fromstring(stdout).findtext('.//repository/root')
    if not root:
        raise RuntimeError('未找到 SVN repository root')
    return root.rstrip('/')


def to_repo_path(url: str, repo_root: str) -> str:
    plain_url = strip_peg_revision(url).rstrip('/')
    if not plain_url.startswith(repo_root):
        raise RuntimeError(f'URL 不在仓库根路径下: {plain_url}')
    return '/' + plain_url[len(repo_root):].lstrip('/')


def get_branch_origin(project_config: dict, branch_url: str) -> tuple[str, str]:
    repo_root = get_repo_root(project_config, branch_url)

    def resolve_origin(url: str, peg_revision: str | None = None) -> tuple[str, str]:
        target_url = strip_peg_revision(url)
        current_repo_path = to_repo_path(target_url, repo_root)
        log_target = f'{target_url}@{peg_revision}' if peg_revision else target_url

        code, stdout, stderr = run_svn_text(project_config, 'log', '--xml', '--verbose', '--stop-on-copy', log_target)
        if code != 0:
            raise RuntimeError(f'svn log 执行失败:\n{_sanitize_svn_text_for_log(stderr, build_svn_command(project_config))}')

        root = ET.fromstring(stdout)
        entries = root.findall('./logentry')
        if not entries:
            raise RuntimeError(f'未找到分支日志: {log_target}')

        oldest_entry = entries[-1]
        copy_path = None
        copy_rev = None
        for path_node in oldest_entry.findall('./paths/path'):
            if (path_node.text or '').strip() != current_repo_path:
                continue
            if path_node.attrib.get('action') != 'A':
                continue
            copy_path = path_node.attrib.get('copyfrom-path')
            copy_rev = path_node.attrib.get('copyfrom-rev')
            if copy_path and copy_rev:
                break

        if not copy_path or not copy_rev:
            revision = oldest_entry.attrib.get('revision')
            if not revision:
                raise RuntimeError(f'未找到分支创建 revision: {log_target}')
            return target_url, revision

        source_url = f'{repo_root}{copy_path}'
        if '/branches/' in copy_path:
            return resolve_origin(source_url, copy_rev)
        return source_url, copy_rev

    origin_url, origin_revision = resolve_origin(branch_url)
    log_task_event(
        "svn_branch_origin",
        "resolved",
        revision=origin_revision,
        origin=sanitize_svn_url_for_log(origin_url),
    )
    return origin_url, origin_revision


def diff_between_urls(project_config: dict, left_url: str, right_url: str) -> str:
    code, stdout, stderr = run_svn_text(project_config, 'diff', '--summarize', left_url, right_url)
    if code != 0:
        raise RuntimeError(f'svn diff 执行失败:\n{_sanitize_svn_text_for_log(stderr, build_svn_command(project_config))}')
    log_task_event(
        "svn_diff",
        "resolved",
        left=sanitize_svn_url_for_log(left_url),
        right=sanitize_svn_url_for_log(right_url),
    )
    return stdout


def summarize_diff(diff_text: str):
    counts = {'A': 0, 'M': 0, 'D': 0, 'OTHER': 0}
    for line in diff_text.splitlines():
        line = line.strip()
        if not line:
            continue
        status = line[0]
        counts[status if status in counts else 'OTHER'] += 1
    log_task_event("svn_diff", "summary", counts=counts)


def diff_url_to_repo_rel_path(marker: str, path: str) -> str:
    idx = path.find(marker)
    if idx == -1:
        raise ValueError(f'无法定位仓库相对路径: {path}')
    rel = path[idx + len(marker):]
    parts = rel.split('/')
    if parts[0] == 'trunk':
        rel = '/'.join(parts[1:])
    elif parts[0] == 'branches':
        if len(parts) >= 3 and parts[1] == 'history':
            rel = '/'.join(parts[3:])
        else:
            rel = '/'.join(parts[2:])
    return unquote(rel)


def extract_active_files(marker: str, diff_text: str) -> list[str]:
    result = []
    for line in diff_text.splitlines():
        line = line.strip()
        if not line:
            continue
        status = line[0]
        path = line[1:].strip()
        if status not in ('A', 'M'):
            continue
        if not path.lower().endswith(tuple(get_audit_rules()["audit_input"]["included_extensions"])):
            continue
        result.append(diff_url_to_repo_rel_path(marker, path))
    return sorted(set(result))


def build_branch_file_url(branch_url: str, repo_rel_path: str) -> str:
    repo_rel_path = repo_rel_path.strip('/')
    encoded_rel = '/'.join(quote(part) for part in repo_rel_path.split('/'))
    return f"{branch_url.rstrip('/')}/{encoded_rel}"


def export_svn_file(project_config: dict, repo_rel_path: str, branch_url: str, local_root: Path) -> str:
    file_url = build_branch_file_url(branch_url, repo_rel_path)
    local_path = Path(local_root) / Path(repo_rel_path)
    local_path.parent.mkdir(parents=True, exist_ok=True)

    code, _, stderr = run_svn_text(project_config, 'export', '--force', file_url, str(local_path))
    if code != 0:
        safe_stderr = _sanitize_svn_text_for_log(stderr, build_svn_command(project_config))
        raise RuntimeError(f'export 失败:\n{safe_stderr}\nURL: {sanitize_svn_url_for_log(file_url)}')
    return str(local_path)


def svn_main(project: str, branch_url: str):
    safe_branch_url = sanitize_svn_url_for_log(branch_url)
    log_task_event("svn_main", "start", project=project, branch_url=safe_branch_url)
    project_config = get_project_config(project)
    marker = project_config['marker']
    branch_name = branch_url.rstrip('/').rsplit('/', 1)[-1]
    local_export_root = get_export_base() / branch_name

    try:
        log_task_event("svn_main.resolve_origin", "start", project=project, branch_url=safe_branch_url)
        resolve_started = time.perf_counter()
        base_source_url, create_revision = get_branch_origin(project_config, branch_url)
        log_task_event(
            "svn_main.resolve_origin",
            "end",
            base_source_url=sanitize_svn_url_for_log(base_source_url),
            create_revision=create_revision,
            elapsed_seconds=round(time.perf_counter() - resolve_started, 3),
        )

        base_compare_url = build_compare_url(base_source_url, create_revision)
        latest_trunk_url = build_compare_url(base_source_url)

        log_task_event(
            "svn_main.diff", "start", branch_url=safe_branch_url,
            base_compare_url=sanitize_svn_url_for_log(base_compare_url),
        )
        diff_started = time.perf_counter()
        branch_diff_text = diff_between_urls(project_config, base_compare_url, branch_url)
        trunk_diff_text = diff_between_urls(project_config, base_compare_url, latest_trunk_url)
        log_task_event(
            "svn_main.diff",
            "end",
            branch_diff_length=len(branch_diff_text),
            trunk_diff_length=len(trunk_diff_text),
            elapsed_seconds=round(time.perf_counter() - diff_started, 3),
        )
        summarize_diff(branch_diff_text)
        summarize_diff(trunk_diff_text)

        branch_changed_files = extract_active_files(marker, branch_diff_text)
        trunk_changed_files = extract_active_files(marker, trunk_diff_text)
        trunk_conflict_files = sorted(set(branch_changed_files) & set(trunk_changed_files))

        log_task_event("svn_export", "start", file_count=len(branch_changed_files))
        log_task_event(
            "svn_main.export",
            "start",
            file_count=len(branch_changed_files),
            local_export_root=str(local_export_root),
        )
        export_started = time.perf_counter()
        result_paths = []
        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = {
                executor.submit(export_svn_file, project_config, file_path, branch_url, local_export_root): file_path
                for file_path in branch_changed_files
            }
            for future in as_completed(futures):
                repo_rel_path = futures[future]
                try:
                    result_paths.append(future.result())
                except Exception as exc:
                    safe_message = _sanitize_svn_text_for_log(exc, build_svn_command(project_config))
                    log_warning_event(
                        "SVN_EXPORT_FAILED",
                        path=repo_rel_path,
                        error=safe_message,
                    )
                    _log_svn_exception(
                        "SVN_EXPORT_EXCEPTION", exc,
                        command=build_svn_command(project_config),
                        repo_rel_path=repo_rel_path,
                        branch_url=safe_branch_url,
                    )
        result_paths.sort()
        log_task_event(
            "svn_main.export",
            "end",
            exported_count=len(result_paths),
            requested_count=len(branch_changed_files),
            elapsed_seconds=round(time.perf_counter() - export_started, 3),
        )
        log_task_event(
            "svn_main",
            "end",
            project=project,
            branch_url=safe_branch_url,
            exported_count=len(result_paths),
            branch_changed_count=len(branch_changed_files),
            trunk_changed_count=len(trunk_changed_files),
            trunk_conflict_count=len(trunk_conflict_files),
        )
        return {
            'exported_paths': result_paths,
            'branch_changed_files': branch_changed_files,
            'trunk_changed_files': trunk_changed_files,
            'trunk_conflict_files': trunk_conflict_files,
            'base_source_url': base_source_url,
            'create_revision': create_revision,
            'latest_trunk_url': latest_trunk_url,
        }
    except Exception as exc:
        _log_svn_exception(
            "SVN_MAIN_EXCEPTION", exc, project=project, branch_url=safe_branch_url,
            command=build_svn_command(project_config),
        )
        raise


if __name__ == '__main__':
    raise SystemExit("Configure SVN in configs/svn.yaml and invoke svn_main from the application.")
