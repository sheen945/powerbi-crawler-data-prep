# -*- coding: utf-8 -*-
"""把本仓库的 3 处补丁应用到一份 powerbi-mcp 源码上（幂等，可重复执行）

用法:
    python apply_patches.py --mcp-dir <powerbi-mcp 目录>
    python apply_patches.py --mcp-dir <powerbi-mcp 目录> --check     # 只检查不修改

补丁（详见 README.md）:
    1. desktop_bridge.py            — 桥接参数契约 {"args": {...}} 兼容 + 截图优先 v2
    2. powerbi_pbip_connector.py    — _write_text 加进程级锁 + 唯一临时文件名
    3. powerbi_pbip_connector.py    — create_backup 改到系统临时目录
"""
import argparse
import os
import sys

BRIDGE = 'src/desktop_bridge.py'
CONNECTOR = 'src/powerbi_pbip_connector.py'

# ---------------------------------------------------------------- 补丁定义

P_BRIDGE_STATE_OLD = '''    def get_state(self) -> Dict[str, Any]:
        return self.call("application.state.get/v1")

    def capture_snapshot(self, page_id: str, scale: Optional[float] = None) -> Dict[str, Any]:
        # The manifest marks BOTH pageId and scale as required (scale is nullable but the key
        # must be present; omitting it null-refs inside Desktop). Learn's doc says optional -
        # trust the manifest.
        params: Dict[str, Any] = {"pageId": page_id,
                                  "scale": float(scale) if scale is not None else 1.0}
        return self.call("report.snapshot.capture/v1", params)

    def reload_file(self, reload_model_definition: bool = True) -> Dict[str, Any]:
        return self.call("file.reload/v1", {"reloadModelDefinition": bool(reload_model_definition)})'''

P_BRIDGE_STATE_NEW = '''    def call_with_args(self, method: str, args: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Call a bridge method honouring the build's parameter contract.

        Desktop builds >= 26.07 declare `params.required = ["args"]` in bridge.manifest, so the
        business parameters must be nested under an "args" key (``{"args": {...}}``). Older builds
        (and the published Learn docs) accept the flat form. Try nested first, fall back to flat
        when the bridge answers -32602 ("Request arguments are required")."""
        payload = dict(args or {})
        try:
            return self.call(method, {"args": payload})
        except BridgeError as e:
            if e.code != -32602:
                raise
            return self.call(method, payload)

    def get_state(self) -> Dict[str, Any]:
        return self.call_with_args("application.state.get/v1")

    def capture_snapshot(self, page_id: str, scale: Optional[float] = None) -> Dict[str, Any]:
        # The manifest marks BOTH pageId and scale as required (scale is nullable but the key
        # must be present; omitting it null-refs inside Desktop). Learn's doc says optional -
        # trust the manifest.
        args: Dict[str, Any] = {"pageId": page_id,
                                "scale": float(scale) if scale is not None else 1.0}
        # v2 adds an optional capture region; prefer it when the build advertises it.
        try:
            return self.call_with_args("report.snapshot.capture/v2", args)
        except BridgeError as e:
            if e.code not in (-32601, -32602):
                raise
            return self.call_with_args("report.snapshot.capture/v1", args)

    def reload_file(self, reload_model_definition: bool = True) -> Dict[str, Any]:
        return self.call_with_args("file.reload/v1",
                                   {"reloadModelDefinition": bool(reload_model_definition)})'''

P_CONN_IMPORTS_OLD = '''import shutil
from datetime import datetime'''

P_CONN_IMPORTS_NEW = '''import shutil
import tempfile
import threading
from datetime import datetime'''

P_CONN_LOCK_OLD = '''logger = logging.getLogger(__name__)
'''

P_CONN_LOCK_NEW = '''logger = logging.getLogger(__name__)

# Serialises atomic file writes: the MCP server can run several tool calls concurrently in one
# process, and two writers sharing "<name>.tmp" collide (WinError 32, seen on pages.json).
_WRITE_LOCK = threading.RLock()
'''

P_CONN_WRITE_OLD = '''    def _write_text(self, file_path, content: str) -> None:
        """Atomically write text (temp file + os.replace) using the file's remembered
        encoding and without translating newlines, so a crash mid-write cannot corrupt
        the original and CRLF/LF and BOM are preserved."""
        encoding = self._file_encodings.get(str(file_path), 'utf-8')
        path = Path(file_path)
        tmp = path.with_name(path.name + '.tmp')
        with open(tmp, 'w', encoding=encoding, newline='') as f:
            f.write(content)
        os.replace(tmp, path)'''

P_CONN_WRITE_NEW = '''    def _write_text(self, file_path, content: str) -> None:
        """Atomically write text (temp file + os.replace) using the file's remembered
        encoding and without translating newlines, so a crash mid-write cannot corrupt
        the original and CRLF/LF and BOM are preserved.

        Serialised with a process-wide lock and a unique temp name: concurrent tool calls used
        to share "<name>.tmp" and fail with WinError 32 (seen on definition/pages/pages.json
        when two pbir_add_page calls raced)."""
        encoding = self._file_encodings.get(str(file_path), 'utf-8')
        path = Path(file_path)
        with _WRITE_LOCK:
            tmp = path.with_name(f"{path.name}.{os.getpid()}.{threading.get_ident()}.tmp")
            with open(tmp, 'w', encoding=encoding, newline='') as f:
                f.write(content)
            os.replace(tmp, path)'''

P_CONN_BACKUP_OLD = '''            backup_name = f"{self.current_project.pbip_file.stem}_backup_{timestamp}"
            backup_path = self.current_project.root_path.parent / backup_name'''

P_CONN_BACKUP_NEW = '''            backup_name = f"{self.current_project.pbip_file.stem}_backup_{timestamp}"
            # Backups go to the system temp dir, NOT next to the user's project: they used to
            # land in the project's parent folder and clutter the user's workspace.
            backup_root = Path(tempfile.gettempdir()) / "powerbi-mcp-backups"
            backup_root.mkdir(parents=True, exist_ok=True)
            backup_path = backup_root / backup_name'''

PATCHES = [
    (BRIDGE, '桥接参数契约 + 截图优先 v2', 'call_with_args', [(P_BRIDGE_STATE_OLD, P_BRIDGE_STATE_NEW)]),
    (CONNECTOR, '写文件加锁（并发安全）', '_WRITE_LOCK', [(P_CONN_IMPORTS_OLD, P_CONN_IMPORTS_NEW),
                                                          (P_CONN_LOCK_OLD, P_CONN_LOCK_NEW),
                                                          (P_CONN_WRITE_OLD, P_CONN_WRITE_NEW)]),
    (CONNECTOR, '备份改到系统临时目录', 'powerbi-mcp-backups', [(P_CONN_BACKUP_OLD, P_CONN_BACKUP_NEW)]),
]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--mcp-dir', required=True, help='powerbi-mcp 源码目录')
    ap.add_argument('--check', action='store_true', help='只检查不修改')
    a = ap.parse_args()

    ok = True
    for rel, title, marker, edits in PATCHES:
        p = os.path.join(a.mcp_dir, rel)
        if not os.path.isfile(p):
            print(f'❌ 找不到文件: {p}')
            ok = False
            continue
        text = open(p, encoding='utf-8').read()
        if marker in text:
            print(f'✅ 已应用，跳过：{title}  ({rel})')
            continue
        new = text
        applied = 0
        for old, rep in edits:
            if old in new:
                new = new.replace(old, rep, 1)
                applied += 1
        if applied == len(edits):
            if a.check:
                print(f'🔎 需要打补丁：{title}  ({rel})')
            else:
                open(p, 'w', encoding='utf-8', newline='\n').write(new)
                print(f'🔧 已打补丁：{title}  ({rel})')
        else:
            print(f'⚠️ 跳过（源码与预期不符，可能上游已改动）：{title}  ({rel}) '
                  f'匹配 {applied}/{len(edits)} 处')
            ok = False

    print()
    print('完成。改完记得重启 MCP 服务（常驻进程）才生效。' if not a.check else '检查模式，未修改任何文件。')
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())
