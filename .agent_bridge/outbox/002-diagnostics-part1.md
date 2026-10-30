# Result 002 - Part 1 (Разделы A, B, C: Процессы, Порты, Логи)
status: ok
branch/commit: e2d15f1 (bridge) / 4f44ce1 (main)

## Что выполнено
- A1. Количество процессов по имени: ok
- A2. Полный список процессов (PID, родитель, старт, cmd): ok
- A3. Окна AutoCAD (видимые, заголовки): ok
- B1. Порты 8700-8899 в состоянии Listen: ok
- B2. Состояния соединений на порту 8780: ok
- B3. Health check (GET /api/health): ok
- C. Логи (последние 150 строк): ok

## Вывод команд

### A1. Количество процессов по имени
```text
Name           Count
----           -----
acad               1
conhost            5
GoogleDriveFS      2
msedgewebview2    33
powershell         2
python             1
pythonw            3
```

### A2. Полный список процессов (PID, родитель, старт, командная строка)
```text
ProcessId       : 26832
ParentProcessId : 17252
Name            : acad.exe
Start           : 10/20/2026 10:36:29 AM
Cmd             : "C:\Program Files\Autodesk\AutoCAD 2024\acad.exe" "C:\Users\a9379\Downloads\ФП-007- КМ1 ИЗМ3 от 19.10.2026.dwg"

ProcessId       : 16068
ParentProcessId : 17984
Name            : powershell.exe
Start           : 10/20/2026 12:11:30 PM
Cmd             : powershell -Command "python \"C:\Users\a9379\.gemini\antigravity\brain\4b9b761e-6b93-432a-8701-6e8e129b1518\scratch\generate_diag_report.py\""

ProcessId       : 30052
ParentProcessId : 30876
Name            : powershell.exe
Start           : 10/20/2026 12:11:32 PM
Cmd             : powershell -NoProfile -ExecutionPolicy Bypass -Command "$ErrorActionPreference = \"Continue\"; Get-CimInstance Win32_Process | Where-Object { $_.Name -match '^(acad|accoreconsole|AcLauncher|python|pythonw|powershell|pwsh|FEngineeringLauncher)\.exe$' } | Sort-Object Name,CreationDate | Select-Object 

ProcessId       : 30876
ParentProcessId : 16068
Name            : python.exe
Start           : 10/20/2026 12:11:31 PM
Cmd             : "C:\Python314\python.exe" C:\Users\a9379\.gemini\antigravity\brain\4b9b761e-6b93-432a-8701-6e8e129b1518\scratch\generate_diag_report.py

ProcessId       : 15128
ParentProcessId : 10768
Name            : pythonw.exe
Start           : 10/18/2026 11:43:42 AM
Cmd             : C:\Python314\pythonw.exe C:\Users\a9379\.gemini\antigravity\scratch\fero-launcher-v4\app\backend\server.py --port 8780

ProcessId       : 26668
ParentProcessId : 2540
Name            : pythonw.exe
Start           : 10/20/2026 11:30:35 AM
Cmd             : "C:\Python314\pythonw.exe"  "C:\Users\a9379\.gemini\antigravity\scratch\fero-launcher-v4\app\flauncher.pyw"

ProcessId       : 32432
ParentProcessId : 26668
Name            : pythonw.exe
Start           : 10/20/2026 11:30:38 AM
Cmd             : C:\Python314\pythonw.exe C:\Users\a9379\.gemini\antigravity\scratch\fero-launcher-v4\app\backend\server.py --port 8780
```

### A3. Окна AutoCAD (видимые, заголовки)
```text
Id MainWindowHandle Title StartTime             
   -- ---------------- ----- ---------             
26832                0       10/20/2026 10:36:29 AM
```

### B1. Порты 8700–8899 в состоянии Listen с владельцем-процессом
```text
LocalAddress LocalPort OwningProcess Proc   
------------ --------- ------------- ----   
127.0.0.1         8780         32432 pythonw
```

### B2. Состояния соединений на порту 8780
```text
Name     Count
----     -----
TimeWait     2
Listen       1
```

### B3. Health check (GET /api/health)
```text
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

### C. Логи (последние 150 строк launcher_gui, server_startup, server, native-front)
```text
### runtime\logs\launcher_gui.log
Length LastWriteTime         
------ -------------         
140187 10/20/2026 11:30:50 AM
[2026-10-20 02:47:33] Reaped stale launcher server pid 15128 on port 8780
[2026-10-20 02:47:33] Port 8780 is still busy after 3s reaping; scanning fallback ports 8781-8789...
[2026-10-20 02:47:34] Selected free fallback port 8781
[2026-10-20 02:47:34] Starting backend on port 8781
[2026-10-20 02:47:34] Successfully created Windows Job Object with KILL_ON_JOB_CLOSE
[2026-10-20 02:47:34] Assigned process pid 19440 to Job Object: True
[2026-10-20 02:47:36] Server on port 8781 became healthy (pid 19440)
[2026-10-20 02:47:36] Readiness: backend healthy, objects ready (14 items)
[2026-10-20 02:47:39] Readiness gates passed (health+objects+loaded); showing window once
[2026-10-20 02:48:14] Mutex busy and existing window could not be focused; checking for stale lock...
[2026-10-20 02:48:15] Mutex port still busy after reaping attempt: [WinError 10048] Обычно разрешается только одно использование адреса сокета (протокол/сетевой адрес/порт), exiting
[2026-10-20 02:48:42] Mutex busy and existing window could not be focused; checking for stale lock...
[2026-10-20 02:48:42] Mutex port still busy after reaping attempt: [WinError 10048] Обычно разрешается только одно использование адреса сокета (протокол/сетевой адрес/порт), exiting
[2026-10-20 02:48:52] Mutex busy and existing window could not be focused; checking for stale lock...
[2026-10-20 02:48:53] Mutex port still busy after reaping attempt: [WinError 10048] Обычно разрешается только одно использование адреса сокета (протокол/сетевой адрес/порт), exiting
[2026-10-20 02:50:43] Port 8780 is occupied but unhealthy; reaping stale server process tree...
[2026-10-20 02:50:43] Reaped stale launcher server pid 15128 on port 8780
[2026-10-20 02:50:43] Reaped stale launcher server pid 15128 on port 8780
[2026-10-20 02:50:44] Reaped stale launcher server pid 15128 on port 8780
[2026-10-20 02:50:44] Reaped stale launcher server pid 15128 on port 8780
[2026-10-20 02:50:44] Reaped stale launcher server pid 15128 on port 8780
[2026-10-20 02:51:56] Port 8780 is occupied but unhealthy; reaping stale server process tree...
[2026-10-20 02:51:56] Reaped stale launcher server pid 15128 on port 8780
[2026-10-20 02:51:57] Reaped stale launcher server pid 15128 on port 8780
[2026-10-20 02:51:57] Reaped stale launcher server pid 15128 on port 8780
[2026-10-20 02:51:58] Reaped stale launcher server pid 15128 on port 8780
[2026-10-20 02:51:58] Reaped stale launcher server pid 15128 on port 8780
[2026-10-20 02:51:58] Reaped stale launcher server pid 15128 on port 8780
[2026-10-20 02:51:59] Reaped stale launcher server pid 15128 on port 8780
[2026-10-20 02:51:59] Reaped stale launcher server pid 15128 on port 8780
[2026-10-20 02:51:59] Reaped stale launcher server pid 15128 on port 8780
[2026-10-20 02:51:59] Port 8780 is still busy after 3s reaping; scanning fallback ports 8781-8789...
[2026-10-20 02:52:00] Selected free fallback port 8781
[2026-10-20 02:52:00] Starting backend on port 8781
[2026-10-20 02:52:00] Successfully created Windows Job Object with KILL_ON_JOB_CLOSE
[2026-10-20 02:52:00] Assigned process pid 12504 to Job Object: True
[2026-10-20 02:52:01] Server on port 8781 became healthy (pid 12504)
[2026-10-20 02:52:02] Readiness: backend healthy, objects ready (14 items)
[2026-10-20 02:52:04] Readiness gates passed (health+objects+loaded); showing window once
[2026-10-20 02:53:34] Port 8780 is occupied but unhealthy; reaping stale server process tree...
[2026-10-20 02:53:34] Reaped stale launcher server pid 15128 on port 8780
[2026-10-20 02:53:35] Reaped stale launcher server pid 15128 on port 8780
[2026-10-20 02:53:35] Reaped stale launcher server pid 15128 on port 8780
[2026-10-20 02:53:35] Reaped stale launcher server pid 15128 on port 8780
[2026-10-20 02:53:36] Reaped stale launcher server pid 15128 on port 8780
[2026-10-20 02:53:36] Reaped stale launcher server pid 15128 on port 8780
[2026-10-20 02:53:37] Reaped stale launcher server pid 15128 on port 8780
[2026-10-20 02:53:37] Reaped stale launcher server pid 15128 on port 8780
[2026-10-20 02:53:37] Reaped stale launcher server pid 15128 on port 8780
[2026-10-20 02:53:38] Reaped stale launcher server pid 15128 on port 8780
[2026-10-20 02:53:38] Port 8780 is still busy after 3s reaping; scanning fallback ports 8781-8789...
[2026-10-20 02:53:38] Selected free fallback port 8781
[2026-10-20 02:53:38] Starting backend on port 8781
[2026-10-20 02:53:38] Successfully created Windows Job Object with KILL_ON_JOB_CLOSE
[2026-10-20 02:53:38] Assigned process pid 27728 to Job Object: True
[2026-10-20 02:54:33] Port 8780 is occupied but unhealthy; reaping stale server process tree...
[2026-10-20 02:54:33] Reaped stale launcher server pid 15128 on port 8780
[2026-10-20 02:54:33] Reaped stale launcher server pid 15128 on port 8780
[2026-10-20 02:54:34] Reaped stale launcher server pid 15128 on port 8780
[2026-10-20 02:54:34] Reaped stale launcher server pid 15128 on port 8780
[2026-10-20 02:54:35] Reaped stale launcher server pid 15128 on port 8780
[2026-10-20 02:54:35] Reaped stale launcher server pid 15128 on port 8780
[2026-10-20 02:54:35] Reaped stale launcher server pid 15128 on port 8780
[2026-10-20 02:54:36] Reaped stale launcher server pid 15128 on port 8780
[2026-10-20 02:54:36] Reaped stale launcher server pid 15128 on port 8780
[2026-10-20 02:54:36] Port 8780 is still busy after 3s reaping; scanning fallback ports 8781-8789...
[2026-10-20 02:54:37] Selected free fallback port 8781
[2026-10-20 02:54:37] Starting backend on port 8781
[2026-10-20 02:54:37] Successfully created Windows Job Object with KILL_ON_JOB_CLOSE
[2026-10-20 02:54:37] Assigned process pid 16684 to Job Object: True
[2026-10-20 02:54:38] Server on port 8781 became healthy (pid 16684)
[2026-10-20 02:54:38] Readiness: backend healthy, objects ready (14 items)
[2026-10-20 02:54:41] Readiness gates passed (health+objects+loaded); showing window once
[2026-10-20 02:57:25] Port 8780 is occupied but unhealthy; reaping stale server process tree...
[2026-10-20 02:57:25] Reaped stale launcher server pid 15128 on port 8780
[2026-10-20 02:57:25] Reaped stale launcher server pid 15128 on port 8780
[2026-10-20 02:57:25] Reaped stale launcher server pid 15128 on port 8780
[2026-10-20 02:57:26] Reaped stale launcher server pid 15128 on port 8780
[2026-10-20 02:57:26] Reaped stale launcher server pid 15128 on port 8780
[2026-10-20 02:57:27] Reaped stale launcher server pid 15128 on port 8780
[2026-10-20 02:57:27] Reaped stale launcher server pid 15128 on port 8780
[2026-10-20 02:57:27] Reaped stale launcher server pid 15128 on port 8780
[2026-10-20 02:57:28] Reaped stale launcher server pid 15128 on port 8780
[2026-10-20 02:57:28] Reaped stale launcher server pid 15128 on port 8780
[2026-10-20 02:57:28] Port 8780 is still busy after 3s reaping; scanning fallback ports 8781-8789...
[2026-10-20 02:57:29] Selected free fallback port 8781
[2026-10-20 02:57:29] Starting backend on port 8781
[2026-10-20 02:57:29] Successfully created Windows Job Object with KILL_ON_JOB_CLOSE
[2026-10-20 02:57:29] Assigned process pid 17232 to Job Object: True
[2026-10-20 02:57:30] Server on port 8781 became healthy (pid 17232)
[2026-10-20 02:57:30] Readiness: backend healthy, objects ready (14 items)
[2026-10-20 02:57:33] Readiness gates passed (health+objects+loaded); showing window once
[2026-10-20 03:28:51] Port 8780 is occupied or unhealthy; reaping stale server process tree...
[2026-10-20 03:28:51] Reaped stale server.py process pid 15128
[2026-10-20 03:28:52] Starting backend on port 8780
[2026-10-20 03:28:52] Successfully created Windows Job Object with KILL_ON_JOB_CLOSE
[2026-10-20 03:28:52] Assigned process pid 28824 to Job Object: True
[2026-10-20 03:28:55] Backend process pid 28824 exited prematurely with return code 1!
[2026-10-20 03:28:55] Warning: server on port 8780 health check timed out, attempting to use it anyway
[2026-10-20 03:29:16] Objects readiness failed: URLError: <urlopen error [WinError 10061] Подключение не установлено, т.к. конечный компьютер отверг запрос на подключение>
[2026-10-20 03:30:11] Mutex busy and existing window could not be focused; checking for stale lock...
[2026-10-20 03:30:13] Mutex port still busy after reaping attempt, exiting
[2026-10-20 03:30:31] Mutex busy and existing window could not be focused; checking for stale lock...
[2026-10-20 03:30:33] Mutex port still busy after reaping attempt, exiting
[2026-10-20 03:31:29] Port 8780 is occupied or unhealthy; reaping stale server process tree...
[2026-10-20 03:31:30] Reaped stale server.py process pid 15128
[2026-10-20 03:31:30] Starting backend on port 8780
[2026-10-20 03:31:30] Successfully created Windows Job Object with KILL_ON_JOB_CLOSE
[2026-10-20 03:31:30] Assigned process pid 23028 to Job Object: True
[2026-10-20 03:31:32] Server on port 8780 became healthy (pid 23028)
[2026-10-20 03:31:32] Readiness: backend healthy, objects ready (14 items)
[2026-10-20 03:31:35] Readiness gates passed (health+objects+loaded); showing window once
[2026-10-20 03:42:05] Port 8780 is occupied or unhealthy; reaping stale server process tree...
[2026-10-20 03:42:05] Reaped stale server.py process pid 15128
[2026-10-20 03:42:05] Starting backend on port 8780
[2026-10-20 03:42:05] Successfully created Windows Job Object with KILL_ON_JOB_CLOSE
[2026-10-20 03:42:05] Assigned process pid 18228 to Job Object: True
[2026-10-20 03:42:07] Server on port 8780 became healthy (pid 18228)
[2026-10-20 03:42:08] Readiness: backend healthy, objects ready (14 items)
[2026-10-20 03:42:10] Readiness gates passed (health+objects+loaded); showing window once
[2026-10-20 03:57:07] Port 8780 is occupied or unhealthy; reaping stale server process tree...
[2026-10-20 03:57:07] Reaped stale server.py process pid 15128
[2026-10-20 03:57:07] Starting backend on port 8780
[2026-10-20 03:57:07] Successfully created Windows Job Object with KILL_ON_JOB_CLOSE
[2026-10-20 03:57:07] Assigned process pid 27244 to Job Object: True
[2026-10-20 03:57:14] Server on port 8780 became healthy (pid 27244)
[2026-10-20 03:57:15] Readiness: backend healthy, objects ready (13 items)
[2026-10-20 03:57:18] Readiness gates passed (health+objects+loaded); showing window once
[2026-10-20 05:29:42] Window closed event received, stopping server...
[2026-10-20 05:29:42] Shutting down server pid 27244...
[2026-10-20 05:29:42] Server pid 27244 stopped successfully
[2026-10-20 05:43:37] Port 8780 is occupied or unhealthy; reaping stale server process tree...
[2026-10-20 05:43:38] Reaped stale server.py process pid 15128
[2026-10-20 05:43:38] Starting backend on port 8780
[2026-10-20 05:43:38] Successfully created Windows Job Object with KILL_ON_JOB_CLOSE
[2026-10-20 05:43:38] Assigned process pid 23960 to Job Object: True
[2026-10-20 05:43:39] Server on port 8780 became healthy (pid 23960)
[2026-10-20 05:43:39] Readiness: backend healthy, objects ready (14 items)
[2026-10-20 05:43:42] Readiness gates passed (health+objects+loaded); showing window once
[2026-10-20 06:36:26] Window closed event received, stopping server...
[2026-10-20 06:36:26] Shutting down server pid 23960...
[2026-10-20 06:36:26] Server pid 23960 stopped successfully
[2026-10-20 11:30:38] Port 8780 is occupied or unhealthy; reaping stale server process tree...
[2026-10-20 11:30:38] Reaped stale server.py process pid 15128
[2026-10-20 11:30:38] Starting backend on port 8780
[2026-10-20 11:30:38] Successfully created Windows Job Object with KILL_ON_JOB_CLOSE
[2026-10-20 11:30:38] Assigned process pid 32432 to Job Object: True
[2026-10-20 11:30:45] Server on port 8780 became healthy (pid 32432)
[2026-10-20 11:30:46] Readiness: backend healthy, objects ready (15 items)
[2026-10-20 11:30:50] Readiness gates passed (health+objects+loaded); showing window once
### runtime\logs\server_startup.log
Length LastWriteTime         
------ -------------         
 10561 10/20/2026 11:35:52 AM

--- [2026-10-20 02:47:34] Starting backend on port 8781 ---
F-Engineering Launcher v3: http://127.0.0.1:8781/

--- [2026-10-20 02:52:00] Starting backend on port 8781 ---
F-Engineering Launcher v3: http://127.0.0.1:8781/

--- [2026-10-20 02:53:38] Starting backend on port 8781 ---

--- [2026-10-20 02:54:37] Starting backend on port 8781 ---
F-Engineering Launcher v3: http://127.0.0.1:8781/

--- [2026-10-20 02:57:29] Starting backend on port 8781 ---
F-Engineering Launcher v3: http://127.0.0.1:8781/
accoreconsole export incomplete for 03_����������� ��������.dwg: stdout=ity\scratch\fero-launcher-v4\runtime\cache\dwg\87cab0e...
exportMs                       6776                                                                                    
pageCount                      1                                                                                       


 stderr=
Background AutoCAD open failed: <unknown>.Open
������ ��������� ������������ C:\Users\a9379\.gemini\antigravity\scratch\fero-launcher-v4\runtime\cache\dwg\3e3d98c9eb49492c7241\page_0001.pdf � C:\Users\a9379\.gemini\antigravity\scratch\fero-launcher-v4\runtime\cache\dwg\3e3d98c9eb49492c7241\page-1.png: [WinError 5] �������� � �������: 'C:\\Users\\a9379\\.gemini\\antigravity\\scratch\\fero-launcher-v4\\runtime\\cache\\dwg\\3e3d98c9eb49492c7241\\page-1.tmp.17232_1792454515970.png' -> 'C:\\Users\\a9379\\.gemini\\antigravity\\scratch\\fero-launcher-v4\\runtime\\cache\\dwg\\3e3d98c9eb49492c7241\\page-1.png'
������ ��������� ������������ C:\Users\a9379\.gemini\antigravity\scratch\fero-launcher-v4\runtime\cache\dwg\b4f122f628a178293173\page_0001.pdf � C:\Users\a9379\.gemini\antigravity\scratch\fero-launcher-v4\runtime\cache\dwg\b4f122f628a178293173\page-1.png: [WinError 5] �������� � �������: 'C:\\Users\\a9379\\.gemini\\antigravity\\scratch\\fero-launcher-v4\\runtime\\cache\\dwg\\b4f122f628a178293173\\page-1.tmp.17232_1792454543452.png' -> 'C:\\Users\\a9379\\.gemini\\antigravity\\scratch\\fero-launcher-v4\\runtime\\cache\\dwg\\b4f122f628a178293173\\page-1.png'
������ ��������� ������������ C:\Users\a9379\.gemini\antigravity\scratch\fero-launcher-v4\runtime\cache\dwg\1c2331fb5f97a16e1ea2\page_0001.pdf � C:\Users\a9379\.gemini\antigravity\scratch\fero-launcher-v4\runtime\cache\dwg\1c2331fb5f97a16e1ea2\page-1.png: Failed to open file 'C:\\Users\\a9379\\.gemini\\antigravity\\scratch\\fero-launcher-v4\\runtime\\cache\\dwg\\1c2331fb5f97a16e1ea2\\page_0001.pdf'.
������ ��������� ������������ C:\Users\a9379\.gemini\antigravity\scratch\fero-launcher-v4\runtime\cache\dwg\1c2331fb5f97a16e1ea2\page_0001.pdf � C:\Users\a9379\.gemini\antigravity\scratch\fero-launcher-v4\runtime\cache\dwg\1c2331fb5f97a16e1ea2\page-1.png: Failed to open file 'C:\\Users\\a9379\\.gemini\\antigravity\\scratch\\fero-launcher-v4\\runtime\\cache\\dwg\\1c2331fb5f97a16e1ea2\\page_0001.pdf'.
������ ��������� ������������ C:\Users\a9379\.gemini\antigravity\scratch\fero-launcher-v4\runtime\cache\dwg\7aaa13c9cac8acaf34c7\page_0001.pdf � C:\Users\a9379\.gemini\antigravity\scratch\fero-launcher-v4\runtime\cache\dwg\7aaa13c9cac8acaf34c7\page-1.png: Failed to open file 'C:\\Users\\a9379\\.gemini\\antigravity\\scratch\\fero-launcher-v4\\runtime\\cache\\dwg\\7aaa13c9cac8acaf34c7\\page_0001.pdf'.
������ ��������� ������������ C:\Users\a9379\.gemini\antigravity\scratch\fero-launcher-v4\runtime\cache\dwg\7aaa13c9cac8acaf34c7\page_0001.pdf � C:\Users\a9379\.gemini\antigravity\scratch\fero-launcher-v4\runtime\cache\dwg\7aaa13c9cac8acaf34c7\page-1.png: Failed to open file 'C:\\Users\\a9379\\.gemini\\antigravity\\scratch\\fero-launcher-v4\\runtime\\cache\\dwg\\7aaa13c9cac8acaf34c7\\page_0001.pdf'.
������ ��������� ������������ C:\Users\a9379\.gemini\antigravity\scratch\fero-launcher-v4\runtime\cache\dwg\7aaa13c9cac8acaf34c7\page_0001.pdf � C:\Users\a9379\.gemini\antigravity\scratch\fero-launcher-v4\runtime\cache\dwg\7aaa13c9cac8acaf34c7\page-1.png: Failed to open file 'C:\\Users\\a9379\\.gemini\\antigravity\\scratch\\fero-launcher-v4\\runtime\\cache\\dwg\\7aaa13c9cac8acaf34c7\\page_0001.pdf'.
������ ��������� ������������ C:\Users\a9379\.gemini\antigravity\scratch\fero-launcher-v4\runtime\cache\dwg\7aaa13c9cac8acaf34c7\page_0001.pdf � C:\Users\a9379\.gemini\antigravity\scratch\fero-launcher-v4\runtime\cache\dwg\7aaa13c9cac8acaf34c7\page-1.png: Failed to open file 'C:\\Users\\a9379\\.gemini\\antigravity\\scratch\\fero-launcher-v4\\runtime\\cache\\dwg\\7aaa13c9cac8acaf34c7\\page_0001.pdf'.
������ ��������� ������������ C:\Users\a9379\.gemini\antigravity\scratch\fero-launcher-v4\runtime\cache\dwg\7aaa13c9cac8acaf34c7\page_0001.pdf � C:\Users\a9379\.gemini\antigravity\scratch\fero-launcher-v4\runtime\cache\dwg\7aaa13c9cac8acaf34c7\page-1.png: Failed to open file 'C:\\Users\\a9379\\.gemini\\antigravity\\scratch\\fero-launcher-v4\\runtime\\cache\\dwg\\7aaa13c9cac8acaf34c7\\page_0001.pdf'.
accoreconsole export incomplete for 2020_05_27_�����_recover.dwg: stdout= stderr=finished but PDF was not created"
+     ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    + CategoryInfo          : OperationStopped: (AutoCAD Core Co...was not created:String) [], RuntimeException
    + FullyQualifiedErrorId : AutoCAD Core Console finished but PDF was not created
 

accoreconsole export incomplete for 2020_05_27_�����_recover000.dwg: stdout= stderr=finished but PDF was not created"
+     ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    + CategoryInfo          : OperationStopped: (AutoCAD Core Co...was not created:String) [], RuntimeException
    + FullyQualifiedErrorId : AutoCAD Core Console finished but PDF was not created
 

accoreconsole export incomplete for �����������_recover.dwg: stdout= stderr=finished but PDF was not created"
+     ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    + CategoryInfo          : OperationStopped: (AutoCAD Core Co...was not created:String) [], RuntimeException
    + FullyQualifiedErrorId : AutoCAD Core Console finished but PDF was not created
 


--- [2026-10-20 03:28:52] Starting backend on port 8780 ---
Traceback (most recent call last):
  File "C:\Users\a9379\.gemini\antigravity\scratch\fero-launcher-v4\app\backend\server.py", line 4144, in <module>
    main()
    ~~~~^^
  File "C:\Users\a9379\.gemini\antigravity\scratch\fero-launcher-v4\app\backend\server.py", line 4118, in main
    db.init_db()
    ~~~~~~~~~~^^
  File "C:\Users\a9379\.gemini\antigravity\scratch\fero-launcher-v4\app\backend\db.py", line 20, in init_db
    conn = get_connection()
  File "C:\Users\a9379\.gemini\antigravity\scratch\fero-launcher-v4\app\backend\db.py", line 14, in get_connection
    conn.execute("PRAGMA journal_mode=WAL;")
    ~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^
sqlite3.OperationalError: disk I/O error

--- [2026-10-20 03:31:30] Starting backend on port 8780 ---
Could not set socket non-inheritable: [Errno 9] Bad file descriptor
F-Engineering Launcher v3: http://127.0.0.1:8780/

--- [2026-10-20 03:42:05] Starting backend on port 8780 ---
Could not set socket non-inheritable: [Errno 9] Bad file descriptor
F-Engineering Launcher v3: http://127.0.0.1:8780/

--- [2026-10-20 03:57:07] Starting backend on port 8780 ---
Could not set socket non-inheritable: [Errno 9] Bad file descriptor
F-Engineering Launcher v3: http://127.0.0.1:8780/

--- [2026-10-20 05:43:38] Starting backend on port 8780 ---
Could not set socket non-inheritable: [Errno 9] Bad file descriptor
F-Engineering Launcher v3: http://127.0.0.1:8780/
C:\Users\a9379\AppData\Roaming\Python\Python314\site-packages\openpyxl\reader\drawings.py:67: UserWarning: wmf image format is not supported so the image is being dropped
  warn(msg)

--- [2026-10-20 11:30:38] Starting backend on port 8780 ---
Could not set socket non-inheritable: [Errno 9] Bad file descriptor
F-Engineering Launcher v3: http://127.0.0.1:8780/
������ ��������� ������������ C:\Users\a9379\.gemini\antigravity\scratch\fero-launcher-v4\runtime\cache\dwg\586c4edacae3d9f92611\page_0001.pdf � C:\Users\a9379\.gemini\antigravity\scratch\fero-launcher-v4\runtime\cache\dwg\586c4edacae3d9f92611\page-1.png: [WinError 5] �������� � �������: 'C:\\Users\\a9379\\.gemini\\antigravity\\scratch\\fero-launcher-v4\\runtime\\cache\\dwg\\586c4edacae3d9f92611\\page-1.tmp.32432_1792485186728.png' -> 'C:\\Users\\a9379\\.gemini\\antigravity\\scratch\\fero-launcher-v4\\runtime\\cache\\dwg\\586c4edacae3d9f92611\\page-1.png'
������ ��������� ������������ C:\Users\a9379\.gemini\antigravity\scratch\fero-launcher-v4\runtime\cache\dwg\aed7bdf56fc0455a2e44\page_0001.pdf � C:\Users\a9379\.gemini\antigravity\scratch\fero-launcher-v4\runtime\cache\dwg\aed7bdf56fc0455a2e44\page-1.png: [WinError 5] �������� � �������: 'C:\\Users\\a9379\\.gemini\\antigravity\\scratch\\fero-launcher-v4\\runtime\\cache\\dwg\\aed7bdf56fc0455a2e44\\page-1.tmp.32432_1792485316461.png' -> 'C:\\Users\\a9379\\.gemini\\antigravity\\scratch\\fero-launcher-v4\\runtime\\cache\\dwg\\aed7bdf56fc0455a2e44\\page-1.png'
----------------------------------------
Exception occurred during processing of request from ('127.0.0.1', 62589)
Traceback (most recent call last):
  File "C:\Python314\Lib\socketserver.py", line 697, in process_request_thread
    self.finish_request(request, client_address)
    ~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\Python314\Lib\socketserver.py", line 362, in finish_request
    self.RequestHandlerClass(request, client_address, self)
    ~~~~~~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\Python314\Lib\socketserver.py", line 766, in __init__
    self.handle()
    ~~~~~~~~~~~^^
  File "C:\Python314\Lib\http\server.py", line 496, in handle
    self.handle_one_request()
    ~~~~~~~~~~~~~~~~~~~~~~~^^
  File "C:\Python314\Lib\http\server.py", line 484, in handle_one_request
    method()
    ~~~~~~^^
  File "C:\Users\a9379\.gemini\antigravity\scratch\fero-launcher-v4\app\backend\server.py", line 3139, in do_GET
    self.serve_cache(parsed.path)
    ~~~~~~~~~~~~~~~~^^^^^^^^^^^^^
  File "C:\Users\a9379\.gemini\antigravity\scratch\fero-launcher-v4\app\backend\server.py", line 4053, in serve_cache
    self.wfile.write(body)
    ~~~~~~~~~~~~~~~~^^^^^^
  File "C:\Python314\Lib\socketserver.py", line 845, in write
    self._sock.sendall(b)
    ~~~~~~~~~~~~~~~~~~^^^
ConnectionAbortedError: [WinError 10053] ��������� �� ����� ����-���������� ��������� ������������� �����������
----------------------------------------
### runtime\logs\server.log
Length LastWriteTime         
 ------ -------------         
4434221 10/20/2026 12:11:38 PM
20/Oct/2026 11:34:08 - "GET /cache/dwg/91ea19382e35fd9e8957/header_thumb.png HTTP/1.1" 200 -
20/Oct/2026 11:34:10 - "POST /api/dwg/model-render HTTP/1.1" 200 -
20/Oct/2026 11:34:10 - "POST /api/dwg/model-render HTTP/1.1" 200 -
20/Oct/2026 11:34:10 - "GET /cache/dwg/a3a869f9b933d941ae52/page-1.png HTTP/1.1" 200 -
20/Oct/2026 11:34:12 - "POST /api/dwg/status HTTP/1.1" 200 -
20/Oct/2026 11:34:12 - "GET /cache/dwg/a3a869f9b933d941ae52/page-1.png?v=1792485252165 HTTP/1.1" 200 -
20/Oct/2026 11:34:12 - "POST /api/dwg/model-render HTTP/1.1" 200 -
20/Oct/2026 11:34:12 - "GET /cache/dwg/a9a821a284a6f3df18c0/page-1.png HTTP/1.1" 200 -
20/Oct/2026 11:34:14 - "POST /api/dwg/status HTTP/1.1" 200 -
20/Oct/2026 11:34:15 - "POST /api/dwg/status HTTP/1.1" 200 -
20/Oct/2026 11:34:16 - "POST /api/dwg/status HTTP/1.1" 200 -
20/Oct/2026 11:34:17 - "POST /api/dwg/status HTTP/1.1" 200 -
20/Oct/2026 11:34:19 - "POST /api/dwg/status HTTP/1.1" 200 -
20/Oct/2026 11:34:20 - "POST /api/dwg/status HTTP/1.1" 200 -
20/Oct/2026 11:34:22 - "POST /api/dwg/status HTTP/1.1" 200 -
20/Oct/2026 11:34:22 - "POST /api/dwg/model-render HTTP/1.1" 200 -
20/Oct/2026 11:34:24 - "POST /api/dwg/status HTTP/1.1" 200 -
20/Oct/2026 11:34:24 - "GET /cache/dwg/dea84820925c5b0e1c86/page-1.png?v=1792485264575 HTTP/1.1" 200 -
20/Oct/2026 11:34:24 - "POST /api/dwg/model-render HTTP/1.1" 200 -
20/Oct/2026 11:34:24 - "GET /cache/dwg/487a9f5f9425a671cc69/page-1.png HTTP/1.1" 200 -
20/Oct/2026 11:34:25 - "POST /api/dwg/status HTTP/1.1" 200 -
20/Oct/2026 11:34:26 - "POST /api/dwg/model-render HTTP/1.1" 200 -
20/Oct/2026 11:34:26 - "GET /cache/dwg/4701ea50fbef22db2c0e/page-1.png HTTP/1.1" 200 -
20/Oct/2026 11:34:27 - "POST /api/dwg/status HTTP/1.1" 200 -
20/Oct/2026 11:34:27 - "POST /api/dwg/model-render HTTP/1.1" 200 -
20/Oct/2026 11:34:28 - "POST /api/dwg/status HTTP/1.1" 200 -
20/Oct/2026 11:34:29 - "POST /api/dwg/model-render HTTP/1.1" 200 -
20/Oct/2026 11:34:30 - "POST /api/dwg/status HTTP/1.1" 200 -
20/Oct/2026 11:34:31 - "POST /api/dwg/model-render HTTP/1.1" 200 -
20/Oct/2026 11:34:31 - "GET /cache/dwg/91ea19382e35fd9e8957/page-1.png HTTP/1.1" 200 -
20/Oct/2026 11:34:32 - "POST /api/dwg/status HTTP/1.1" 200 -
20/Oct/2026 11:34:33 - "POST /api/dwg/status HTTP/1.1" 200 -
20/Oct/2026 11:34:34 - "POST /api/dwg/status HTTP/1.1" 200 -
20/Oct/2026 11:34:36 - "POST /api/dwg/status HTTP/1.1" 200 -
20/Oct/2026 11:34:37 - "POST /api/dwg/status HTTP/1.1" 200 -
20/Oct/2026 11:34:37 - "POST /api/dwg/model-render HTTP/1.1" 200 -
20/Oct/2026 11:34:38 - "GET /cache/dwg/26c3a3712b4570cd7758/header_thumb.png HTTP/1.1" 200 -
20/Oct/2026 11:34:39 - "POST /api/dwg/status HTTP/1.1" 200 -
20/Oct/2026 11:34:39 - "GET /cache/dwg/26c3a3712b4570cd7758/page-1.png?v=1792485279593 HTTP/1.1" 200 -
20/Oct/2026 11:34:41 - "POST /api/dwg/status HTTP/1.1" 200 -
20/Oct/2026 11:34:42 - "POST /api/dwg/status HTTP/1.1" 200 -
20/Oct/2026 11:34:44 - "POST /api/dwg/status HTTP/1.1" 200 -
20/Oct/2026 11:34:45 - "POST /api/dwg/model-render HTTP/1.1" 200 -
20/Oct/2026 11:34:45 - "POST /api/dwg/status HTTP/1.1" 200 -
20/Oct/2026 11:34:45 - "GET /cache/dwg/62b81e7c55e52988ba37/header_thumb.png HTTP/1.1" 200 -
20/Oct/2026 11:34:47 - "POST /api/dwg/status HTTP/1.1" 200 -
20/Oct/2026 11:34:47 - "GET /cache/dwg/62b81e7c55e52988ba37/page-1.png?v=1792485287153 HTTP/1.1" 200 -
20/Oct/2026 11:34:48 - "POST /api/dwg/status HTTP/1.1" 200 -
20/Oct/2026 11:34:50 - "POST /api/dwg/status HTTP/1.1" 200 -
20/Oct/2026 11:34:51 - "POST /api/dwg/status HTTP/1.1" 200 -
20/Oct/2026 11:34:52 - "POST /api/dwg/model-render HTTP/1.1" 200 -
20/Oct/2026 11:34:52 - "GET /cache/dwg/a0ed0b131404bf4a4d66/header_thumb.png HTTP/1.1" 200 -
20/Oct/2026 11:34:54 - "POST /api/dwg/status HTTP/1.1" 200 -
20/Oct/2026 11:34:54 - "GET /cache/dwg/a0ed0b131404bf4a4d66/page-1.png?v=1792485294140 HTTP/1.1" 200 -
20/Oct/2026 11:34:55 - "POST /api/dwg/status HTTP/1.1" 200 -
20/Oct/2026 11:34:57 - "POST /api/dwg/status HTTP/1.1" 200 -
20/Oct/2026 11:34:58 - "POST /api/dwg/status HTTP/1.1" 200 -
20/Oct/2026 11:35:00 - "POST /api/dwg/model-render HTTP/1.1" 200 -
20/Oct/2026 11:35:00 - "GET /cache/dwg/2ae4918a7ed1aad666f0/header_thumb.png HTTP/1.1" 200 -
20/Oct/2026 11:35:01 - "POST /api/dwg/status HTTP/1.1" 200 -
20/Oct/2026 11:35:01 - "GET /cache/dwg/2ae4918a7ed1aad666f0/page-1.png?v=1792485301621 HTTP/1.1" 200 -
20/Oct/2026 11:35:03 - "POST /api/dwg/status HTTP/1.1" 200 -
20/Oct/2026 11:35:04 - "POST /api/dwg/status HTTP/1.1" 200 -
20/Oct/2026 11:35:06 - "POST /api/dwg/status HTTP/1.1" 200 -
20/Oct/2026 11:35:07 - "POST /api/dwg/model-render HTTP/1.1" 200 -
20/Oct/2026 11:35:07 - "GET /cache/dwg/7058fa9525fbda867427/header_thumb.png HTTP/1.1" 200 -
20/Oct/2026 11:35:09 - "POST /api/dwg/status HTTP/1.1" 200 -
20/Oct/2026 11:35:09 - "GET /cache/dwg/7058fa9525fbda867427/page-1.png?v=1792485309122 HTTP/1.1" 200 -
20/Oct/2026 11:35:10 - "POST /api/dwg/status HTTP/1.1" 200 -
20/Oct/2026 11:35:12 - "POST /api/dwg/status HTTP/1.1" 200 -
20/Oct/2026 11:35:13 - "POST /api/dwg/status HTTP/1.1" 200 -
20/Oct/2026 11:35:15 - "POST /api/dwg/status HTTP/1.1" 200 -
20/Oct/2026 11:35:16 - "POST /api/dwg/model-render HTTP/1.1" 200 -
20/Oct/2026 11:35:16 - "POST /api/dwg/status HTTP/1.1" 200 -
20/Oct/2026 11:35:16 - "GET /cache/dwg/aed7bdf56fc0455a2e44/page-1.png HTTP/1.1" 200 -
20/Oct/2026 11:35:18 - "POST /api/dwg/status HTTP/1.1" 200 -
20/Oct/2026 11:35:19 - "POST /api/dwg/status HTTP/1.1" 200 -
20/Oct/2026 11:35:21 - "POST /api/dwg/status HTTP/1.1" 200 -
20/Oct/2026 11:35:22 - "POST /api/dwg/status HTTP/1.1" 200 -
20/Oct/2026 11:35:24 - "POST /api/dwg/status HTTP/1.1" 200 -
20/Oct/2026 11:35:25 - "POST /api/dwg/status HTTP/1.1" 200 -
20/Oct/2026 11:35:26 - "POST /api/dwg/model-render HTTP/1.1" 200 -
20/Oct/2026 11:35:26 - "GET /cache/dwg/3194160218ac19a02039/header_thumb.png HTTP/1.1" 200 -
20/Oct/2026 11:35:27 - "POST /api/dwg/status HTTP/1.1" 200 -
20/Oct/2026 11:35:27 - "GET /cache/dwg/3194160218ac19a02039/page-1.png?v=1792485327704 HTTP/1.1" 200 -
20/Oct/2026 11:35:29 - "POST /api/dwg/status HTTP/1.1" 200 -
20/Oct/2026 11:35:30 - "POST /api/dwg/status HTTP/1.1" 200 -
20/Oct/2026 11:35:32 - "POST /api/dwg/status HTTP/1.1" 200 -
20/Oct/2026 11:35:33 - "POST /api/dwg/status HTTP/1.1" 200 -
20/Oct/2026 11:35:35 - "POST /api/dwg/status HTTP/1.1" 200 -
20/Oct/2026 11:35:35 - "POST /api/dwg/model-render HTTP/1.1" 200 -
20/Oct/2026 11:35:35 - "GET /cache/dwg/27f45b60cd43b5dffacd/page-1.png HTTP/1.1" 200 -
20/Oct/2026 11:35:36 - "POST /api/dwg/status HTTP/1.1" 200 -
20/Oct/2026 11:35:38 - "POST /api/dwg/status HTTP/1.1" 200 -
20/Oct/2026 11:35:40 - "POST /api/dwg/status HTTP/1.1" 200 -
20/Oct/2026 11:35:40 - "POST /api/dwg/model-render HTTP/1.1" 200 -
20/Oct/2026 11:35:40 - "GET /cache/dwg/a014022f49f4ed6294f3/header_thumb.png HTTP/1.1" 200 -
20/Oct/2026 11:35:41 - "POST /api/open-file HTTP/1.1" 200 -
20/Oct/2026 11:35:42 - "POST /api/dwg/status HTTP/1.1" 200 -
20/Oct/2026 11:35:43 - "POST /api/dwg/status HTTP/1.1" 200 -
20/Oct/2026 11:35:45 - "POST /api/dwg/status HTTP/1.1" 200 -
20/Oct/2026 11:35:46 - "POST /api/dwg/status HTTP/1.1" 200 -
20/Oct/2026 11:35:48 - "POST /api/dwg/status HTTP/1.1" 200 -
20/Oct/2026 11:35:48 - "POST /api/dwg/model-render HTTP/1.1" 200 -
20/Oct/2026 11:35:48 - "GET /cache/dwg/7527d659dd6bda383f30/header_thumb.png HTTP/1.1" 200 -
20/Oct/2026 11:35:49 - "POST /api/pdf/render HTTP/1.1" 200 -
20/Oct/2026 11:35:52 - "POST /api/dwg/status HTTP/1.1" 200 -
20/Oct/2026 11:35:52 - "POST /api/dwg/status HTTP/1.1" 200 -
20/Oct/2026 11:35:52 - "GET /cache/dwg/7527d659dd6bda383f30/page-1.png?v=1792485352625 HTTP/1.1" 200 -
20/Oct/2026 11:35:52 - "GET /cache/dwg/7527d659dd6bda383f30/page-1.png?v=1792485352627 HTTP/1.1" 200 -
20/Oct/2026 11:35:53 - "POST /api/dwg/status HTTP/1.1" 200 -
20/Oct/2026 11:36:00 - "POST /api/dwg/model-render HTTP/1.1" 200 -
20/Oct/2026 11:36:00 - "GET /cache/dwg/51e92e87ce00d59ff30d/header_thumb.png HTTP/1.1" 200 -
20/Oct/2026 11:36:03 - "POST /api/dwg/status HTTP/1.1" 200 -
20/Oct/2026 11:36:03 - "POST /api/dwg/status HTTP/1.1" 200 -
20/Oct/2026 11:36:03 - "GET /cache/dwg/51e92e87ce00d59ff30d/page-1.png?v=1792485363930 HTTP/1.1" 200 -
20/Oct/2026 11:36:12 - "POST /api/dwg/model-render HTTP/1.1" 200 -
20/Oct/2026 11:36:12 - "GET /cache/dwg/21ffad6742142c12f679/header_thumb.png HTTP/1.1" 200 -
20/Oct/2026 11:36:14 - "POST /api/dwg/status HTTP/1.1" 200 -
20/Oct/2026 11:36:15 - "POST /api/dwg/status HTTP/1.1" 200 -
20/Oct/2026 11:36:15 - "GET /cache/dwg/21ffad6742142c12f679/page-1.png?v=1792485375575 HTTP/1.1" 200 -
20/Oct/2026 11:36:52 - "POST /api/dwg/model-page HTTP/1.1" 200 -
20/Oct/2026 11:36:52 - "GET /cache/dwg/44be7e8b1a0a22a3d377/page-1.png?v=1792485412987 HTTP/1.1" 200 -
20/Oct/2026 11:36:59 - "GET /cache/dwg/62b81e7c55e52988ba37/page-1.png HTTP/1.1" 200 -
20/Oct/2026 11:36:59 - "POST /api/dwg/model-page HTTP/1.1" 200 -
20/Oct/2026 11:36:59 - "GET /cache/dwg/62b81e7c55e52988ba37/page-1.png?v=1792485419140 HTTP/1.1" 200 -
20/Oct/2026 11:37:00 - "POST /api/dwg/status HTTP/1.1" 200 -
20/Oct/2026 11:37:00 - "GET /cache/dwg/62b81e7c55e52988ba37/page-1.png?v=1792485420647 HTTP/1.1" 200 -
20/Oct/2026 11:37:02 - "POST /api/dwg/status HTTP/1.1" 200 -
20/Oct/2026 11:37:03 - "POST /api/dwg/status HTTP/1.1" 200 -
20/Oct/2026 11:37:05 - "POST /api/dwg/status HTTP/1.1" 200 -
20/Oct/2026 11:37:06 - "POST /api/dwg/status HTTP/1.1" 200 -
20/Oct/2026 11:37:08 - "POST /api/dwg/status HTTP/1.1" 200 -
20/Oct/2026 11:37:09 - "POST /api/dwg/status HTTP/1.1" 200 -
20/Oct/2026 11:37:11 - "POST /api/dwg/status HTTP/1.1" 200 -
20/Oct/2026 11:37:13 - "POST /api/dwg/status HTTP/1.1" 200 -
20/Oct/2026 11:37:14 - "POST /api/dwg/status HTTP/1.1" 200 -
20/Oct/2026 11:37:16 - "POST /api/dwg/status HTTP/1.1" 200 -
20/Oct/2026 11:37:17 - "POST /api/dwg/status HTTP/1.1" 200 -
20/Oct/2026 11:39:40 - "GET /cache/pdf/3d8ec1e00add0d0d46ad/page-1.png HTTP/1.1" 200 -
20/Oct/2026 11:39:46 - "POST /api/pdf/render HTTP/1.1" 200 -
20/Oct/2026 11:39:52 - "POST /api/pdf/render HTTP/1.1" 200 -
20/Oct/2026 11:40:00 - "POST /api/pdf/render HTTP/1.1" 200 -
20/Oct/2026 11:40:02 - "POST /api/pdf/render HTTP/1.1" 200 -
20/Oct/2026 11:41:22 - "POST /api/objects/diff HTTP/1.1" 400 -
20/Oct/2026 11:51:22 - "POST /api/objects/diff HTTP/1.1" 400 -
20/Oct/2026 12:01:22 - "POST /api/objects/diff HTTP/1.1" 400 -
20/Oct/2026 12:09:45 - "GET /api/health HTTP/1.1" 200 -
20/Oct/2026 12:11:22 - "POST /api/objects/diff HTTP/1.1" 400 -
20/Oct/2026 12:11:38 - "GET /api/health HTTP/1.1" 200 -
### runtime\logs\native-front.log
Length LastWriteTime        
------ -------------        
 16204 10/20/2026 4:20:43 AM
07:31:42 pid=0 target hwnd=3803978
07:31:42 pid=0 centered-before=False
07:31:42 pid=0 target hwnd=3803978
07:31:42 pid=0 centered-before=False
07:31:42 pid=0 target hwnd=3803978
07:31:42 pid=0 centered-before=False
07:31:43 pid=0 try fg=3803978 zoomed=True
07:31:43 pid=0 centered-after=False
07:31:43 pid=0 try fg=3803978 zoomed=True
07:31:43 pid=0 centered-after=False
07:31:43 pid=0 try fg=3803978 zoomed=True
07:31:43 pid=0 centered-after=False
08:03:27 pid=0 watch start exe=acad.exe
08:03:27 pid=0 watch start exe=acad.exe
08:03:27 pid=0 watch start exe=acad.exe
08:03:27 pid=0 watch start exe=acad.exe
08:03:27 pid=0 watch start exe=acad.exe
08:03:27 pid=0 watch start exe=acad.exe
08:03:27 pid=0 target hwnd=134206
08:03:27 pid=0 centered-before=True
08:03:27 pid=0 target hwnd=134206
08:03:27 pid=0 centered-before=False
08:03:27 pid=0 target hwnd=134206
08:03:27 pid=0 centered-before=False
08:03:27 pid=0 target hwnd=134206
08:03:27 pid=0 centered-before=False
08:03:28 pid=0 target hwnd=134206
08:03:28 pid=0 centered-before=False
08:03:28 pid=0 target hwnd=134206
08:03:28 pid=0 centered-before=False
08:17:59 pid=0 watch start exe=acad.exe
08:17:59 pid=0 watch start exe=acad.exe
08:17:59 pid=0 watch start exe=acad.exe
08:17:59 pid=0 watch start exe=acad.exe
08:18:00 pid=0 watch start exe=acad.exe
08:18:00 pid=0 watch start exe=acad.exe
08:18:00 pid=0 target hwnd=789576
08:18:00 pid=0 target hwnd=789576
08:18:00 pid=0 centered-before=True
08:18:00 pid=0 centered-before=True
08:18:00 pid=0 target hwnd=789576
08:18:00 pid=0 centered-before=False
08:18:00 pid=0 target hwnd=789576
08:18:00 pid=0 centered-before=False
08:18:00 pid=0 target hwnd=789576
08:18:00 pid=0 centered-before=False
08:18:00 pid=0 target hwnd=789576
08:18:00 pid=0 centered-before=False
08:18:01 pid=0 try fg=0 zoomed=True
08:18:01 pid=0 try fg=0 zoomed=True
08:18:01 pid=0 try fg=0 zoomed=True
08:18:01 pid=0 try fg=0 zoomed=True
08:32:52 pid=0 watch start exe=msedge.exe
08:32:54 pid=0 target hwnd=2165240
08:32:55 pid=0 try fg=2165240 zoomed=True
08:36:09 pid=0 watch start exe=excel.exe
08:36:10 pid=0 target hwnd=200006
08:36:11 pid=0 try fg=200028 zoomed=True
08:36:12 pid=0 try fg=200028 zoomed=False
08:36:13 pid=0 try fg=200028 zoomed=False
08:36:32 pid=0 watch start exe=winword.exe
08:36:33 pid=0 target hwnd=200162
08:36:34 pid=0 try fg=200162 zoomed=True
08:52:00 pid=0 watch start exe=acad.exe
08:52:01 pid=0 target hwnd=1705476
08:52:01 pid=0 centered-before=True
08:52:02 pid=0 try fg=1705476 zoomed=True
08:52:02 pid=0 centered-after=False
08:58:00 pid=0 watch start exe=acad.exe
08:58:00 pid=0 watch start exe=acad.exe
08:58:00 pid=0 watch start exe=acad.exe
08:58:00 pid=0 watch start exe=acad.exe
08:58:00 pid=0 watch start exe=acad.exe
08:58:00 pid=0 watch start exe=acad.exe
08:58:00 pid=0 target hwnd=3869972
08:58:00 pid=0 centered-before=True
08:58:01 pid=0 target hwnd=3869972
08:58:01 pid=0 centered-before=False
08:58:01 pid=0 target hwnd=3869972
08:58:01 pid=0 centered-before=False
08:58:01 pid=0 target hwnd=3869972
08:58:01 pid=0 centered-before=False
08:58:01 pid=0 target hwnd=3869972
08:58:01 pid=0 centered-before=False
08:58:01 pid=0 target hwnd=3869972
08:58:01 pid=0 centered-before=False
08:58:02 pid=0 try fg=0 zoomed=True
08:58:02 pid=0 try fg=0 zoomed=True
08:58:02 pid=0 try fg=0 zoomed=True
08:58:02 pid=0 try fg=0 zoomed=True
08:58:02 pid=0 try fg=0 zoomed=True
08:58:02 pid=0 try fg=0 zoomed=True
09:23:35 pid=0 watch start exe=acad.exe
09:23:35 pid=0 target hwnd=3017206
09:23:35 pid=0 centered-before=True
09:23:36 pid=0 try fg=3017206 zoomed=True
09:23:36 pid=0 centered-after=False
09:38:45 pid=0 watch start exe=acad.exe
09:38:45 pid=0 target hwnd=6425120
09:38:46 pid=0 centered-before=True
09:38:47 pid=0 try fg=6425120 zoomed=True
09:38:47 pid=0 centered-after=False
09:42:11 pid=0 watch start exe=acad.exe
09:42:11 pid=0 target hwnd=1313796
09:42:11 pid=0 centered-before=True
09:42:12 pid=0 try fg=1313796 zoomed=True
09:42:12 pid=0 centered-after=False
10:23:29 pid=0 watch start exe=acad.exe
10:23:30 pid=0 target hwnd=724478
10:23:30 pid=0 centered-before=True
10:23:31 pid=0 try fg=724478 zoomed=True
10:23:31 pid=0 centered-after=False
13:58:17 pid=0 watch start exe=acad.exe
13:58:18 pid=0 target hwnd=4985098
13:58:18 pid=0 centered-before=True
13:58:19 pid=0 try fg=4985098 zoomed=True
13:58:19 pid=0 centered-after=False
11:05:06 pid=0 watch start exe=acad.exe
11:05:07 pid=0 target hwnd=395312
11:05:07 pid=0 centered-before=True
11:05:08 pid=0 try fg=395312 zoomed=True
11:05:08 pid=0 centered-after=False
16:32:22 pid=0 watch start exe=winword.exe
16:32:23 pid=0 target hwnd=7606244
16:32:24 pid=0 try fg=7606244 zoomed=True
20:30:23 pid=0 watch start exe=acad.exe
20:30:24 pid=0 target hwnd=85592068
20:30:24 pid=0 centered-before=True
20:30:25 pid=0 try fg=85592068 zoomed=True
20:30:25 pid=0 centered-after=False
23:51:10 pid=0 watch start exe=acad.exe
23:51:11 pid=0 target hwnd=5178378
23:51:11 pid=0 centered-before=True
23:51:12 pid=0 try fg=5178378 zoomed=True
23:51:12 pid=0 centered-after=False
02:58:17 pid=0 watch start exe=acad.exe
02:58:18 pid=0 target hwnd=13701344
02:58:18 pid=0 centered-before=True
02:58:19 pid=0 try fg=13701344 zoomed=True
02:58:19 pid=0 centered-after=False
03:11:16 pid=0 watch start exe=acad.exe
03:11:17 pid=0 target hwnd=4590442
03:11:17 pid=0 centered-before=True
03:11:18 pid=0 try fg=4590442 zoomed=True
03:11:18 pid=0 centered-after=False
04:20:41 pid=0 watch start exe=acad.exe
04:20:42 pid=0 target hwnd=1249752
04:20:42 pid=0 centered-before=True
04:20:43 pid=0 try fg=1249752 zoomed=True
04:20:43 pid=0 centered-after=False
```