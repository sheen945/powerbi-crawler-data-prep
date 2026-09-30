# -*- coding: utf-8 -*-
"""验证对 powerbi-mcp 的三处补丁：
1) desktop_bridge 的 args 包装（26.07+ 的参数契约）
2) _write_text 的并发锁（原来会 WinError 32）
3) create_backup 落到系统 temp
"""
import sys, os, threading, tempfile, traceback

SRC = os.environ.get('POWERBI_MCP_DIR', r'%USERPROFILE%/WorkBuddy/tools/powerbi-mcp/src'
sys.path.insert(0, SRC)
SRC_ADOMD = os.environ.get('POWERBI_MCP_DIR', r'%USERPROFILE%/WorkBuddy/tools/powerbi-mcp/adomd'

print('=== 0. 补丁 2：并发写锁 ===')
try:
    import powerbi_pbip_connector as pc
    conn = pc.PowerBIPBIPConnector(auto_backup=False)
    target = os.path.join(tempfile.gettempdir(), 'mcp_lock_test.json')
    errors = []

    def writer(n):
        try:
            for i in range(150):
                conn._write_text(target, '{"n": %d, "writer": %d}' % (i, n))
        except Exception as e:
            errors.append(f'writer{n}: {type(e).__name__}: {e}')

    ts = [threading.Thread(target=writer, args=(i,)) for i in range(4)]
    [t.start() for t in ts]
    [t.join() for t in ts]
    print('  4 线程 × 150 次并发写同一文件 ->', '无异常 ✅' if not errors else f'异常 ❌ {errors[:3]}')
    print('  模块级锁存在:', hasattr(pc, '_WRITE_LOCK'), '| tempfile 已导入:', hasattr(pc, 'tempfile'))
    import inspect
    src = inspect.getsource(pc.PowerBIPBIPConnector.create_backup)
    print('  备份目录改到 temp:', 'powerbi-mcp-backups' in src and 'root_path.parent' not in src)
    os.remove(target)
except Exception:
    traceback.print_exc()

print()
print('=== 1. 补丁 1：桥接 args 包装（真机调用）===')
try:
    import desktop_bridge as db
    bridges = db.discover_bridges()
    print('  发现桥接实例:', bridges)
    if bridges:
        pid, pipe = bridges[0]['pid'], bridges[0]['pipe']
        print('  使用:', pid, pipe)
        c = db.DesktopBridgeClient(pipe, timeout=90)
        st = c.get_state()                      # 走 call_with_args
        print('  get_state() ->', {k: (v if k == "hasUnsavedChanges" else str(v)[-50:]) for k, v in st.items()})
        pages = db.pages_for_file(st.get('currentFilePath') or '')
        print('  PBIR 页面:', [(p['id'], p['display_name']) for p in pages])
        if pages:
            snap = c.capture_snapshot(pages[0]['id'], 1.0)   # 走 call_with_args + v2
            import base64
            data = base64.b64decode(snap['payload'])
            out = os.path.join(tempfile.gettempdir(), 'mcp_bridge_patch_test.png')
            open(out, 'wb').write(data)
            print(f"  capture_snapshot(直接调用，无需手工包 args) -> {snap.get('pageDisplayName')} "
                  f"{len(data):,} 字节, 存 {out} ✅")
    else:
        print('  当前没有运行中的 Power BI Desktop（桥接不可用），跳过真机验证')
except Exception:
    traceback.print_exc()
