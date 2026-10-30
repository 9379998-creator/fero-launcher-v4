# Task 005 - сбор данных ПОСЛЕ теста этапа 1 (Part 1)

## A. Процессы и окна
### A1. Количество по имени [status: ok]
```
Name           Count
----           -----
conhost            5
GoogleDriveFS      2
msedgewebview2    26
powershell         1
pythonw            3
```

### A2. Полный список (PID, родитель, старт, Cmd) [status: ok]
```
ProcessId       : 32608
ParentProcessId : 17984
Name            : powershell.exe
Start           : 10/20/2026 3:59:47 PM
Cmd             : powershell -Command "cd \"C:\Users\a9379\.gemini\antigravity\scratch\fero-launcher-v4\" ...

ProcessId       : 15128
ParentProcessId : 10768
Name            : pythonw.exe
Start           : 10/18/2026 11:43:42 AM
Cmd             : C:\Python314\pythonw.exe C:\Users\a9379\.gemini\antigravity\scratch\fero-launcher-v4\app\backend\server.py --port 8780

ProcessId       : 4196
ParentProcessId : 16232
Name            : pythonw.exe
Start           : 10/20/2026 3:51:54 PM
Cmd             : "C:\Python314\pythonw.exe"  "C:\Users\a9379\.gemini\antigravity\scratch\fero-launcher-v4\app\flauncher.pyw"

ProcessId       : 28744
ParentProcessId : 4196
Name            : pythonw.exe
Start           : 10/20/2026 3:51:57 PM
Cmd             : C:\Python314\pythonw.exe C:\Users\a9379\.gemini\antigravity\scratch\fero-launcher-v4\app\backend\server.py --port 8780
```

### A3. Количество открытых документов в AutoCAD [status: ok]
```
no active AutoCAD COM: Exception calling "GetActiveObject" with "1" argument(s): "Operation unavailable (Exception from HRESULT: 0x800401E3 (MK_E_UNAVAILABLE))"
```

### A4. Окна AutoCAD [status: ok]
```
(no acad processes found)
```

## B. Порты и здоровье
### B1. Слушающие порты 8700-8899 [status: ok]
```
LocalAddress LocalPort OwningProcess Proc   
------------ --------- ------------- ----   
127.0.0.1         8780         28744 pythonw
```

### B2. GET /api/health [status: ok]
```
{
  "status": "ok",
  "service": "F.E.R.O. Launcher v4",
  "version": "0.4.0-v3-pdf-render",
  "repoRoot": "C:\\Users\\a9379\\.gemini\\antigravity\\scratch\\fero-launcher-v4",
  "runtime": "C:\\Users\\a9379\\.gemini\\antigravity\\scratch\\fero-launcher-v4\\runtime",
  "wordPreview": true,
  "excelPreview": true
}
```

### B3. dwg_engine.py USE_GUI_WORKER [status: ok]
```
39: USE_GUI_WORKER = False
674: if not USE_GUI_WORKER:
```

### B4. git log -4 --oneline [status: ok]
```
cf7faf6 fix(ui): DWG page readiness without size heuristic, poll in-flight guard and deadline
5088447 fix(server): DWG always 150 DPI, status by real files, socket inheritable fix, cache purpose v4
2792c8f fix(dwg): headless-only rendering (GUI worker off), paths via env, escape layout name, atomic manifests, readiness by file presence
4f44ce1 fix(dwg): init total_layouts, harden DWG status polling, ready-check by file size, and update .gitignore
```