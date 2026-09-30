# -*- coding: utf-8 -*-
"""Desktop Bridge 操作：热重载 + 截图（纯 Python，参数按 args 包装）

用法: python 桥接.py <pid> [pageId] [输出png] [--reload]
"""
import os, sys, base64, os
MCP_DIR = os.environ.get('POWERBI_MCP_DIR', r'%USERPROFILE%/WorkBuddy/tools/powerbi-mcp')
sys.path.insert(0, os.path.join(MCP_DIR, 'src'))
from desktop_bridge import DesktopBridgeClient

PID = int(sys.argv[1])
PIPE = rf'\\.\pipe\pbi-desktop-bridge-{PID}'
c = DesktopBridgeClient(PIPE, timeout=120)

if '--reload' in sys.argv:
    try:
        r = c.call('file.reload/v1', {'args': {'reloadModelDefinition': True}})
        print('热重载结果:', r)
    except Exception as e:
        print('热重载失败:', e)

if len(sys.argv) > 3 and sys.argv[2] and sys.argv[3]:
    page_id, out = sys.argv[2], sys.argv[3]
    os.makedirs(os.path.dirname(out), exist_ok=True)
    snap = c.call('report.snapshot.capture/v2', {'args': {'pageId': page_id, 'scale': 1.5}})
    data = base64.b64decode(snap['payload'])
    open(out, 'wb').write(data)
    print(f"截图: {snap.get('pageDisplayName')} -> {out} ({len(data):,} 字节)")
