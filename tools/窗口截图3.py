# -*- coding: utf-8 -*-
"""按 pid 找到窗口 → PrintWindow 抓取内容（无需前台）→ 保存 PNG
用法: python 窗口截图3.py <pid> <输出png>
"""
import ctypes, ctypes.wintypes as w, sys
from PIL import Image

user32 = ctypes.windll.user32
gdi32 = ctypes.windll.gdi32
TARGET_PID = int(sys.argv[1])
OUT = sys.argv[2]

found = []
@ctypes.WINFUNCTYPE(ctypes.c_bool, w.HWND, w.LPARAM)
def cb(hwnd, lparam):
    pid = w.DWORD()
    user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
    if pid.value == TARGET_PID and user32.IsWindowVisible(hwnd):
        n = user32.GetWindowTextLengthW(hwnd)
        buf = ctypes.create_unicode_buffer(n + 1)
        user32.GetWindowTextW(hwnd, buf, n + 1)
        rect = w.RECT()
        user32.GetWindowRect(hwnd, ctypes.byref(rect))
        if buf.value and (rect.right - rect.left) > 400:
            found.append((hwnd, buf.value, rect.right - rect.left, rect.bottom - rect.top))
    return True
user32.EnumWindows(cb, 0)
print('候选窗口:', found)
if not found:
    sys.exit('未找到目标窗口')

hwnd, title, W, H = found[0]
print(f'抓取: hwnd={hwnd} 标题={title!r} 尺寸={W}x{H}')
hwndDC = user32.GetWindowDC(hwnd)
mfcDC = gdi32.CreateCompatibleDC(hwndDC)
bmp = gdi32.CreateCompatibleBitmap(hwndDC, W, H)
gdi32.SelectObject(mfcDC, bmp)
user32.PrintWindow(hwnd, mfcDC, 0x00000002)

class BIH(ctypes.Structure):
    _fields_ = [('biSize', w.DWORD), ('biWidth', ctypes.c_long), ('biHeight', ctypes.c_long),
                ('biPlanes', w.WORD), ('biBitCount', w.WORD), ('biCompression', w.DWORD),
                ('biSizeImage', w.DWORD), ('biXPelsPerMeter', ctypes.c_long),
                ('biYPelsPerMeter', ctypes.c_long), ('biClrUsed', w.DWORD), ('biClrImportant', w.DWORD)]
bi = BIH(); bi.biSize = ctypes.sizeof(BIH); bi.biWidth = W; bi.biHeight = -H
bi.biPlanes = 1; bi.biBitCount = 32; bi.biCompression = 0
buf = ctypes.create_string_buffer(W * H * 4)
gdi32.GetDIBits(mfcDC, bmp, 0, H, buf, ctypes.byref(bi), 0)
Image.frombuffer('RGBA', (W, H), buf, 'raw', 'BGRA', 0, 1).convert('RGB').save(OUT)
print('已保存:', OUT)
gdi32.DeleteObject(bmp); gdi32.DeleteDC(mfcDC); user32.ReleaseDC(hwnd, hwndDC)
