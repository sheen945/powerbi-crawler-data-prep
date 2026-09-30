# -*- coding: utf-8 -*-
"""通过 TOM 连到本机 Power BI Desktop 实例（AS 引擎），触发全量刷新并等结果"""
import os, sys, time, clr

DLL = os.path.join(os.environ.get('POWERBI_MCP_DIR', r'%USERPROFILE%/WorkBuddy/tools/powerbi-mcp'), 'adomd')
sys.path.append(DLL)
clr.AddReference('Microsoft.AnalysisServices.Tabular')
clr.AddReference('Microsoft.AnalysisServices.Core')
clr.AddReference('Microsoft.AnalysisServices.AdomdClient')

from Microsoft.AnalysisServices.Tabular import Server, RefreshType
from Microsoft.AnalysisServices.AdomdClient import AdomdConnection, AdomdCommand

PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 12702
CONN = f'localhost:{PORT}'

print(f'连接 {CONN} ...')
srv = Server()
srv.Connect(CONN)
db = srv.Databases[0]
print('已连接，模型表:', ', '.join(t.Name for t in db.Model.Tables))

print('请求全量刷新 ...')
db.Model.RequestRefresh(RefreshType.Full)
db.Model.SaveChanges()
print('刷新已提交，等待完成 ...')

def dax(expr, timeout=180):
    """用 ADOMD 执行 DAX，返回解析后的文本"""
    end = time.time() + timeout
    while True:
        try:
            cn = AdomdConnection(f'Provider=MSOLAP;Data Source={CONN};')
            cn.Open()
            cmd = AdomdCommand(expr, cn)
            rd = cmd.ExecuteReader()
            rows = []
            while rd.Read():
                rows.append([rd.GetValue(i) for i in range(rd.FieldCount)])
            cn.Close()
            return rows
        except Exception as e:
            if time.time() > end:
                raise
            time.sleep(3)

ok = False
for attempt in range(1, 16):
    time.sleep(4)
    try:
        r = dax('EVALUATE ROW("比赛", COUNTROWS(\'比赛数据\'), "首发", COUNTROWS(\'首发名单\'))', timeout=10)
        games, starters = r[0][0], r[0][1]
        print(f'  第{attempt}次查询: 比赛数据={games} 行, 首发名单={starters} 行')
        if games and games > 0:
            ok = True
            break
    except Exception as e:
        print(f'  第{attempt}次查询异常（可能在刷新中）: {str(e)[:120]}')

if ok:
    print()
    print('=== 刷新成功，取前 5 场样例 ===')
    rows = dax("""
EVALUATE TOPN(5, SUMMARIZECOLUMNS('比赛数据'[比赛日期], '比赛数据'[联赛], '比赛数据'[主队], '比赛数据'[主队比分], '比赛数据'[客队比分], '比赛数据'[客队], '比赛数据'[数据完整性]))
""", timeout=30)
    for r in rows:
        print('  ', r)
    print()
    print('=== 勾稽校验：四节加总 vs 全场（应为 0 条不符）===')
    rows = dax("""
EVALUATE FILTER(
    SUMMARIZECOLUMNS('比赛数据'[编号], "四节主", SUM('比赛数据'[一节主])+SUM('比赛数据'[二节主])+SUM('比赛数据'[三节主])+SUM('比赛数据'[四节主]), "全场主", SUM('比赛数据'[主队比分])),
    [四节主] <> [全场主])
""", timeout=30)
    print('  不符场次:', len(rows))
else:
    print()
    print('!! 刷新后仍无数据，需排查 M 管道或参数值')
