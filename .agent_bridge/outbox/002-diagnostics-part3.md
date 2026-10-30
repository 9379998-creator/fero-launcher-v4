# Result 002 - Part 3 (Разделы E, F, G: Объект, Точки запуска CAD, Код воркера)
status: ok
branch/commit: e2d15f1 (bridge) / 4f44ce1 (main)

## Что выполнено
- E1. Состав папки объекта (расширения и количество): ok
- E1b. Тип диска H: и атрибуты файлов: ok
- E1c. 15 самых больших файлов DWG/PDF объекта: ok
- E2. Настройки нативных приложений (runtime\native_apps.json): ok
- E3. Установленные версии AutoCAD в Program Files: ok
- F. Поиск в коде мест запуска AutoCAD: ok
- G. Скрипт воркера (dwg_plot_worker.ps1, строки 1-250 с номерами): ok

## Вывод команд

### E1. Состав папки объекта (расширения и количество)
```text
exists=True

Name Count
---- -----
.dwg    21
.pdf     2
.zip     1
```

### E1b. Тип диска H: и состояние файлов (атрибуты)
```text
Name     : H
Provider : Microsoft.PowerShell.Core\FileSystem
Root     : H:\
Used     : 445269004288
Free     : 65325699072






Name          Count
----          -----
.pdf | Normal     2
.zip | Normal     1
.dwg | Normal    21
```

### E1c. 15 самых больших файлов DWG/PDF объекта
```text
Name                                                                                                      MB LastWriteTime       
----                                                                                                      -- -------------       
2026-04-21_АР выше 0.000.zip                                                                             8.1 10/9/2026 4:23:26 PM
U2601-002 ОПР_2026-04-14.pdf                                                                             7.2 10/9/2026 4:23:28 PM
U2601-002 ОПР_2026-04-14.dwg                                                                             4.2 10/9/2026 4:23:28 PM
АР0 - _8 - Узлы и детали устройства кровли автостоянки.dwg                                               1.4 4/21/2026 3:04:16 PM
_АР0 - 06 - Кровля автостоянки- Разуклонка в уровне гидроизоляции- Сечение 1-1-1-1 _Сечение 1_3_1_13.dwg 1.1 4/21/2026 3:04:16 PM
АР3 - 4 - Фасад в осях И-В, В-И.dwg                                                                      0.9 4/22/2026 8:09:56 AM
Задание.dwg                                                                                              0.8 4/22/2026 8:09:54 AM
АР3 - 2 - Фасад в осях 3-17.dwg                                                                          0.8 4/22/2026 8:09:54 AM
АР0 - _7 - Сечения 2-1-2-1  -  2-15-2-15.dwg                                                             0.7 4/21/2026 3:04:16 PM
АР3 - 5 - Фасад в осях В-И, И-В.dwg                                                                      0.6 4/22/2026 8:09:56 AM
АР3 - 3 - Фасад в осях 17-3.dwg                                                                          0.6 4/22/2026 8:09:58 AM
2024_03_26_Larta_Санкт_Петербург_Офис_Спич_В2.pdf                                                        0.4 10/9/2026 4:23:26 PM
АР1 - __14 - Секция 1- Маркировочный план на отм- 0-000.dwg                                              0.4 4/21/2026 3:04:16 PM
АР1 - __15 - Секция 2- Маркировочный план на отм- 0-000.dwg                                              0.4 4/21/2026 3:04:16 PM
АР1 - __24 - Секция 1- Маркировочный план на отм- + 16-500.dwg                                           0.3 4/21/2026 3:04:16 PM
```

### E2. Настройки нативных приложений (runtime\native_apps.json)
```text
{
  "useNativeApps": true,
  "defaultAction": "explorer",
  "firstRunCompleted": true,
  "version": 2,
  ".dwg": {
    "path": "C:\\Program Files\\Common Files\\Autodesk Shared\\AcShellEx\\AcLauncher.exe",
    "source": "windows_import",
    "updated_at": "2026-10-15T10:43:41",
    "valid_at_save": true
  },
  ".dxf": {
    "path": "C:\\Program Files\\Common Files\\Autodesk Shared\\AcShellEx\\AcLauncher.exe",
    "source": "windows_import",
    "updated_at": "2026-10-15T10:43:41",
    "valid_at_save": true
  },
  ".pdf": {
    "path": "C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe",
    "source": "windows_import",
    "updated_at": "2026-10-15T10:43:41",
    "valid_at_save": true
  },
  ".doc": {
    "path": "C:\\Program Files\\Microsoft Office\\Root\\Office16\\WINWORD.EXE",
    "source": "windows_import",
    "updated_at": "2026-10-15T10:43:41",
    "valid_at_save": true
  },
  ".docx": {
    "path": "C:\\Program Files\\Microsoft Office\\Root\\Office16\\WINWORD.EXE",
    "source": "windows_import",
    "updated_at": "2026-10-15T10:43:41",
    "valid_at_save": true
  },
  ".rtf": {
    "path": "C:\\Program Files\\Microsoft Office\\Root\\Office16\\WINWORD.EXE",
    "source": "windows_import",
    "updated_at": "2026-10-15T10:43:41",
    "valid_at_save": true
  },
  ".odt": {
    "path": "C:\\Program Files\\Microsoft Office\\Root\\Office16\\WINWORD.EXE",
    "source": "windows_import",
    "updated_at": "2026-10-15T10:43:41",
    "valid_at_save": true
  },
  ".xls": {
    "path": "C:\\Program Files\\Microsoft Office\\Root\\Office16\\EXCEL.EXE",
    "source": "windows_import",
    "updated_at": "2026-10-15T10:43:41",
    "valid_at_save": true
  },
  ".xlsx": {
    "path": "C:\\Program Files\\Microsoft Office\\Root\\Office16\\EXCEL.EXE",
    "source": "windows_import",
    "updated_at": "2026-10-15T10:43:41",
    "valid_at_save": true
  },
  ".xlsm": {
    "path": "C:\\Program Files\\Microsoft Office\\Root\\Office16\\EXCEL.EXE",
    "source": "windows_import",
    "updated_at": "2026-10-15T10:43:41",
    "valid_at_save": true
  },
  ".csv": {
    "path": "C:\\Program Files\\Microsoft Office\\Root\\Office16\\EXCEL.EXE",
    "source": "windows_import",
    "updated_at": "2026-10-15T10:43:41",
    "valid_at_save": true
  },
  ".ods": {
    "path": "C:\\Program Files\\Microsoft Office\\Root\\Office16\\EXCEL.EXE",
    "source": "windows_import",
    "updated_at": "2026-10-15T10:43:41",
    "valid_at_save": true
  },
  ".ppt": {
    "path": "C:\\Program Files\\Microsoft Office\\Root\\Office16\\POWERPNT.EXE",
    "source": "windows_import",
    "updated_at": "2026-10-15T10:43:41",
    "valid_at_save": true
  },
  ".pptx": {
    "path": "C:\\Program Files\\Microsoft Office\\Root\\Office16\\POWERPNT.EXE",
    "source": "windows_import",
    "updated_at": "2026-10-15T10:43:41",
    "valid_at_save": true
  },
  ".odp": {
    "path": "C:\\Program Files\\Microsoft Office\\Root\\Office16\\POWERPNT.EXE",
    "source": "windows_import",
    "updated_at": "2026-10-15T10:43:41",
    "valid_at_save": true
  },
  ".jpg": {
    "path": "",
    "source": "manual",
    "updated_at": "2026-10-15T10:43:41",
    "valid_at_save": false
  },
  ".jpeg": {
    "path": "",
    "source": "manual",
    "updated_at": "2026-10-15T10:43:41",
    "valid_at_save": false
  },
  ".png": {
    "path": "C:\\Users\\a9379\\AppData\\Local\\SumatraPDF\\SumatraPDF.exe",
    "source": "windows_import",
    "updated_at": "2026-10-15T10:43:41",
    "valid_at_save": true
  },
  ".bmp": {
    "path": "",
    "source": "manual",
    "updated_at": "2026-10-15T10:43:41",
    "valid_at_save": false
  },
  ".gif": {
    "path": "",
    "source": "manual",
    "updated_at": "2026-10-15T10:43:41",
    "valid_at_save": false
  },
  ".webp": {
    "path": "",
    "source": "manual",
    "updated_at": "2026-10-15T10:43:41",
    "valid_at_save": false
  },
  ".tif": {
    "path": "",
    "source": "manual",
    "updated_at": "2026-10-15T10:43:41",
    "valid_at_save": false
  },
  ".tiff": {
    "path": "",
    "source": "manual",
    "updated_at": "2026-10-15T10:43:41",
    "valid_at_save": false
  },
  ".ico": {
    "path": "",
    "source": "manual",
    "updated_at": "2026-10-15T10:43:41",
    "valid_at_save": false
  },
  ".svg": {
    "path": "C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe",
    "source": "windows_import",
    "updated_at": "2026-10-15T10:43:41",
    "valid_at_save": true
  },
  ".zip": {
    "path": "C:\\Program Files\\WindowsApps\\WuhanNetPowerTechnologyCo.ZipX_8.6.8.0_x64__63m8b6nby1dvp\\NetPowerZip\\NetPowerZip.exe",
    "source": "windows_import",
    "updated_at": "2026-10-15T10:43:41",
    "valid_at_save": true
  },
  ".rar": {
    "path": "C:\\Program Files\\WindowsApps\\WuhanNetPowerTechnologyCo.ZipX_8.6.8.0_x64__63m8b6nby1dvp\\NetPowerZip\\NetPowerZip.exe",
    "source": "windows_import",
    "updated_at": "2026-10-15T10:43:41",
    "valid_at_save": true
  },
  ".7z": {
    "path": "C:\\Program Files\\WindowsApps\\WuhanNetPowerTechnologyCo.ZipX_8.6.8.0_x64__63m8b6nby1dvp\\NetPowerZip\\NetPowerZip.exe",
    "source": "windows_import",
    "updated_at": "2026-10-15T10:43:41",
    "valid_at_save": true
  },
  ".tar": {
    "path": "C:\\Program Files\\WindowsApps\\WuhanNetPowerTechnologyCo.ZipX_8.6.8.0_x64__63m8b6nby1dvp\\NetPowerZip\\NetPowerZip.exe",
    "source": "windows_import",
    "updated_at": "2026-10-15T10:43:41",
    "valid_at_save": true
  },
  ".gz": {
    "path": "C:\\Program Files\\WindowsApps\\WuhanNetPowerTechnologyCo.ZipX_8.6.8.0_x64__63m8b6nby1dvp\\NetPowerZip\\NetPowerZip.exe",
    "source": "windows_import",
    "updated_at": "2026-10-15T10:43:41",
    "valid_at_save": true
  },
  ".txt": {
    "path": "C:\\Users\\a9379\\AppData\\Local\\Programs\\Microsoft VS Code\\Code.exe",
    "source": "windows_import",
    "updated_at": "2026-10-15T10:43:41",
    "valid_at_save": true
  },
  ".log": {
    "path": "C:\\Program Files\\WindowsApps\\Microsoft.WindowsNotepad_11.2607.14.0_x64__8wekyb3d8bbwe\\Notepad\\Notepad.exe",
    "source": "windows_import",
    "updated_at": "2026-10-15T10:43:41",
    "valid_at_save": true
  },
  ".ini": {
    "path": "C:\\Program Files\\WindowsApps\\Microsoft.WindowsNotepad_11.2607.14.0_x64__8wekyb3d8bbwe\\Notepad\\Notepad.exe",
    "source": "windows_import",
    "updated_at": "2026-10-15T10:43:41",
    "valid_at_save": true
  },
  ".cfg": {
    "path": "",
    "source": "manual",
    "updated_at": "2026-10-15T10:43:41",
    "valid_at_save": false
  },
  ".json": {
    "path": "",
    "source": "manual",
    "updated_at": "2026-10-15T10:43:41",
    "valid_at_save": false
  },
  ".xml": {
    "path": "C:\\Program Files\\Microsoft Office\\Root\\VFS\\ProgramFilesCommonX64\\Microsoft Shared\\Office16\\MSOXMLED.EXE",
    "source": "windows_import",
    "updated_at": "2026-10-15T10:43:41",
    "valid_at_save": true
  },
  ".yaml": {
    "path": "",
    "source": "manual",
    "updated_at": "2026-10-15T10:43:41",
    "valid_at_save": false
  },
  ".yml": {
    "path": "",
    "source": "manual",
    "updated_at": "2026-10-15T10:43:41",
    "valid_at_save": false
  },
  ".mp4": {
    "path": "C:\\Program Files\\VideoLAN\\VLC\\vlc.exe",
    "source": "windows_import",
    "updated_at": "2026-10-15T10:43:41",
    "valid_at_save": true
  },
  ".avi": {
    "path": "C:\\Program Files\\VideoLAN\\VLC\\vlc.exe",
    "source": "windows_import",
    "updated_at": "2026-10-15T10:43:41",
    "valid_at_save": true
  },
  ".mov": {
    "path": "C:\\Program Files\\VideoLAN\\VLC\\vlc.exe",
    "source": "windows_import",
    "updated_at": "2026-10-15T10:43:41",
    "valid_at_save": true
  },
  ".mkv": {
    "path": "C:\\Program Files\\VideoLAN\\VLC\\vlc.exe",
    "source": "windows_import",
    "updated_at": "2026-10-15T10:43:41",
    "valid_at_save": true
  },
  ".mp3": {
    "path": "C:\\Program Files\\VideoLAN\\VLC\\vlc.exe",
    "source": "windows_import",
    "updated_at": "2026-10-15T10:43:41",
    "valid_at_save": true
  },
  ".wav": {
    "path": "C:\\Program Files\\VideoLAN\\VLC\\vlc.exe",
    "source": "windows_import",
    "updated_at": "2026-10-15T10:43:41",
    "valid_at_save": true
  }
}
```

### E3. Установленные версии AutoCAD в C:\Program Files\Autodesk
```text
Name        
----        
AdODIS      
AutoCAD 2024
```

### F. Места запуска AutoCAD в кодовой базе проекта
```text
C:\Users\a9379\.gemini\antigravity\scratch\fero-launcher-v4\app\backend\analytics_parser.py:135: acad = win32com.client.Dispatch("AutoCAD.Application")
C:\Users\a9379\.gemini\antigravity\scratch\fero-launcher-v4\app\backend\server.py:791: ["taskkill", "/F", "/FI", "WINDOWTITLE eq ", "/IM", "acad.exe"],
C:\Users\a9379\.gemini\antigravity\scratch\fero-launcher-v4\app\backend\server.py:1305: # Для DWG/DXF приоритетно используем официальный AcLauncher
C:\Users\a9379\.gemini\antigravity\scratch\fero-launcher-v4\app\backend\server.py:1340: # ВАЖНО: Если ассоциация непригодна (например, AcLauncher), НЕ очищаем и НЕ заменяем существующее!
C:\Users\a9379\.gemini\antigravity\scratch\fero-launcher-v4\app\backend\server.py:1643: """Убивает только висящие скрытые/фоновые COM-сессии AutoCAD (/Automation),
C:\Users\a9379\.gemini\antigravity\scratch\fero-launcher-v4\app\backend\server.py:1649: "Get-CimInstance Win32_Process -Filter \"Name='acad.exe'\" -ErrorAction SilentlyContinue | "
C:\Users\a9379\.gemini\antigravity\scratch\fero-launcher-v4\app\backend\server.py:1666: """Возвращает путь к официальному AcLauncher.exe (AutoCAD DWG Launcher), если он есть на машине."""
C:\Users\a9379\.gemini\antigravity\scratch\fero-launcher-v4\app\backend\server.py:1670: r"C:\Program Files\Common Files\Autodesk Shared\AcShellEx\AcLauncher.exe",
C:\Users\a9379\.gemini\antigravity\scratch\fero-launcher-v4\app\backend\server.py:1671: r"C:\Program Files (x86)\Common Files\Autodesk Shared\AcShellEx\AcLauncher.exe",
C:\Users\a9379\.gemini\antigravity\scratch\fero-launcher-v4\app\backend\server.py:1700: target_img = "acad.exe"
C:\Users\a9379\.gemini\antigravity\scratch\fero-launcher-v4\app\backend\server.py:1747: if img == target_img or img in ("acad.exe", "zwcad.exe"):
C:\Users\a9379\.gemini\antigravity\scratch\fero-launcher-v4\app\backend\server.py:1776: "AutoCAD.Application",
C:\Users\a9379\.gemini\antigravity\scratch\fero-launcher-v4\app\backend\server.py:1777: "AutoCAD.Application.25",
C:\Users\a9379\.gemini\antigravity\scratch\fero-launcher-v4\app\backend\server.py:1778: "AutoCAD.Application.24.3",
C:\Users\a9379\.gemini\antigravity\scratch\fero-launcher-v4\app\backend\server.py:1779: "AutoCAD.Application.24.2",
C:\Users\a9379\.gemini\antigravity\scratch\fero-launcher-v4\app\backend\server.py:1780: "AutoCAD.Application.24.1",
C:\Users\a9379\.gemini\antigravity\scratch\fero-launcher-v4\app\backend\server.py:1781: "AutoCAD.Application.24.0",
C:\Users\a9379\.gemini\antigravity\scratch\fero-launcher-v4\app\backend\server.py:1782: "AutoCAD.Application.24",
C:\Users\a9379\.gemini\antigravity\scratch\fero-launcher-v4\app\backend\server.py:1783: "AutoCAD.Application.23.1",
C:\Users\a9379\.gemini\antigravity\scratch\fero-launcher-v4\app\backend\server.py:1784: "AutoCAD.Application.23",
C:\Users\a9379\.gemini\antigravity\scratch\fero-launcher-v4\app\backend\server.py:1785: "AutoCAD.Application.22",
C:\Users\a9379\.gemini\antigravity\scratch\fero-launcher-v4\app\backend\server.py:2109: # Для DWG/DXF или если указан AutoCAD (acad.exe / AcLauncher.exe):
C:\Users\a9379\.gemini\antigravity\scratch\fero-launcher-v4\app\backend\server.py:2110: # Прямой запуск acad.exe из командной строки порождает 2 копии процесса (вторую создаёт DDE-интеграция).
C:\Users\a9379\.gemini\antigravity\scratch\fero-launcher-v4\app\backend\server.py:2111: # Для AutoCAD ВСЕГДА следует использовать официальный AcLauncher.exe с ключом /O.
C:\Users\a9379\.gemini\antigravity\scratch\fero-launcher-v4\app\backend\server.py:2113: if norm_ext in (".dwg", ".dxf") or exe_name in ("acad.exe", "aclauncher.exe"):
C:\Users\a9379\.gemini\antigravity\scratch\fero-launcher-v4\app\backend\server.py:2119: bring_native_window_to_front(0, "acad.exe")
C:\Users\a9379\.gemini\antigravity\scratch\fero-launcher-v4\app\backend\server.py:2121: return "custom-app:AcLauncher.exe"
C:\Users\a9379\.gemini\antigravity\scratch\fero-launcher-v4\app\backend\server.py:2130: bring_native_window_to_front(proc.pid, "acad.exe")
C:\Users\a9379\.gemini\antigravity\scratch\fero-launcher-v4\app\backend\server.py:2132: return "custom-app:AcLauncher.exe"
C:\Users\a9379\.gemini\antigravity\scratch\fero-launcher-v4\app\backend\server.py:2181: # Для DWG/DXF на Windows приоритетно используем официальный AcLauncher.exe
C:\Users\a9379\.gemini\antigravity\scratch\fero-launcher-v4\app\backend\server.py:2187: bring_native_window_to_front(0, "acad.exe")
C:\Users\a9379\.gemini\antigravity\scratch\fero-launcher-v4\app\backend\server.py:2189: return "custom-app:AcLauncher.exe"
C:\Users\a9379\.gemini\antigravity\scratch\fero-launcher-v4\app\backend\server.py:3777: bring_native_window_to_front(user_pid, "acad.exe")
C:\Users\a9379\.gemini\antigravity\scratch\fero-launcher-v4\app\backend\server.py:3834: bring_native_window_to_front(0, "acad.exe")
C:\Users\a9379\.gemini\antigravity\scratch\fero-launcher-v4\app\flauncher.pyw:282: ["taskkill", "/F", "/FI", "WINDOWTITLE eq ", "/IM", "acad.exe"],
C:\Users\a9379\.gemini\antigravity\scratch\fero-launcher-v4\app\flauncher.pyw:392: # 3. Гарантированно гасим accoreconsole.exe и фоновые acad.exe (/Automation)
C:\Users\a9379\.gemini\antigravity\scratch\fero-launcher-v4\app\flauncher.pyw:396: ["taskkill", "/F", "/FI", "WINDOWTITLE eq ", "/IM", "acad.exe"],
C:\Users\a9379\.gemini\antigravity\scratch\fero-launcher-v4\scripts\convert_excel_to_pdf.ps1:22: $excel = New-Object -ComObject Excel.Application
C:\Users\a9379\.gemini\antigravity\scratch\fero-launcher-v4\scripts\convert_excel_to_pdf.ps1:76: try { [System.Runtime.InteropServices.Marshal]::ReleaseComObject($workbook) | Out-Null } catch {}
C:\Users\a9379\.gemini\antigravity\scratch\fero-launcher-v4\scripts\convert_excel_to_pdf.ps1:80: try { [System.Runtime.InteropServices.Marshal]::ReleaseComObject($excel) | Out-Null } catch {}
C:\Users\a9379\.gemini\antigravity\scratch\fero-launcher-v4\scripts\convert_word_to_pdf.ps1:24: $word = New-Object -ComObject Word.Application
C:\Users\a9379\.gemini\antigravity\scratch\fero-launcher-v4\scripts\convert_word_to_pdf.ps1:39: try { [System.Runtime.InteropServices.Marshal]::ReleaseComObject($document) | Out-Null } catch {}
C:\Users\a9379\.gemini\antigravity\scratch\fero-launcher-v4\scripts\convert_word_to_pdf.ps1:43: try { [System.Runtime.InteropServices.Marshal]::ReleaseComObject($word) | Out-Null } catch {}
C:\Users\a9379\.gemini\antigravity\scratch\fero-launcher-v4\scripts\convert_xls_to_xlsx.ps1:24: $excel = New-Object -ComObject Excel.Application
C:\Users\a9379\.gemini\antigravity\scratch\fero-launcher-v4\scripts\convert_xls_to_xlsx.ps1:80: try { [System.Runtime.InteropServices.Marshal]::ReleaseComObject($workbook) | Out-Null } catch {}
C:\Users\a9379\.gemini\antigravity\scratch\fero-launcher-v4\scripts\convert_xls_to_xlsx.ps1:84: try { [System.Runtime.InteropServices.Marshal]::ReleaseComObject($excel) | Out-Null } catch {}
C:\Users\a9379\.gemini\antigravity\scratch\fero-launcher-v4\scripts\dwg_plot_worker.ps1:74: "AutoCAD.Application.25",
C:\Users\a9379\.gemini\antigravity\scratch\fero-launcher-v4\scripts\dwg_plot_worker.ps1:75: "AutoCAD.Application.24.3",
C:\Users\a9379\.gemini\antigravity\scratch\fero-launcher-v4\scripts\dwg_plot_worker.ps1:76: "AutoCAD.Application.24.2",
C:\Users\a9379\.gemini\antigravity\scratch\fero-launcher-v4\scripts\dwg_plot_worker.ps1:77: "AutoCAD.Application.24.1",
C:\Users\a9379\.gemini\antigravity\scratch\fero-launcher-v4\scripts\dwg_plot_worker.ps1:78: "AutoCAD.Application.24.0",
C:\Users\a9379\.gemini\antigravity\scratch\fero-launcher-v4\scripts\dwg_plot_worker.ps1:79: "AutoCAD.Application.24",
C:\Users\a9379\.gemini\antigravity\scratch\fero-launcher-v4\scripts\dwg_plot_worker.ps1:80: "AutoCAD.Application.23.1",
C:\Users\a9379\.gemini\antigravity\scratch\fero-launcher-v4\scripts\dwg_plot_worker.ps1:81: "AutoCAD.Application.23",
C:\Users\a9379\.gemini\antigravity\scratch\fero-launcher-v4\scripts\dwg_plot_worker.ps1:82: "AutoCAD.Application.22",
C:\Users\a9379\.gemini\antigravity\scratch\fero-launcher-v4\scripts\dwg_plot_worker.ps1:83: "AutoCAD.Application"
C:\Users\a9379\.gemini\antigravity\scratch\fero-launcher-v4\scripts\dwg_plot_worker.ps1:422: try { [System.Runtime.InteropServices.Marshal]::ReleaseComObject($document) | Out-Null } catch {}
C:\Users\a9379\.gemini\antigravity\scratch\fero-launcher-v4\scripts\dwg_plot_worker.ps1:426: try { [System.Runtime.InteropServices.Marshal]::ReleaseComObject($app) | Out-Null } catch {}
C:\Users\a9379\.gemini\antigravity\scratch\fero-launcher-v4\scripts\dwg_plot_worker.ps1:435: try { [System.Runtime.InteropServices.Marshal]::ReleaseComObject($app) | Out-Null } catch {}
C:\Users\a9379\.gemini\antigravity\scratch\fero-launcher-v4\scripts\prepare_flash_drive.ps1:114: powershell.exe -NoProfile -ExecutionPolicy Bypass -Command "$wsh = New-Object -ComObject WScript.Shell; $desktop = [Environment]::GetFolderPath('Desktop'); $s = $wsh.CreateShortcut("$desktopF-Engineering Launcher.lnk"); $s.TargetPath = '%TARGET_DIR%
C:\Users\a9379\.gemini\antigravity\scratch\fero-launcher-v4\scripts\setup_pc.ps1:115: $hasAutocad = Test-Path "Registry::HKEY_CLASSES_ROOT\AutoCAD.Application"
C:\Users\a9379\.gemini\antigravity\scratch\fero-launcher-v4\scripts\setup_pc.ps1:183: $wsh = New-Object -ComObject WScript.Shell
C:\Users\a9379\.gemini\antigravity\scratch\fero-launcher-v4\scripts\start_app.ps1:101: $serverProc = Start-Process @startParams
C:\Users\a9379\.gemini\antigravity\scratch\fero-launcher-v4\scripts\start_app.ps1:126: Start-Process $url
C:\Users\a9379\.gemini\antigravity\scratch\fero-launcher-v4\scripts\check_shortcuts.py:4: $sh = New-Object -ComObject WScript.Shell
C:\Users\a9379\.gemini\antigravity\scratch\fero-launcher-v4\scripts\export_usb_package.py:214: "$wsh = New-Object -ComObject WScript.Shell; " ^
C:\Users\a9379\.gemini\antigravity\scratch\fero-launcher-v4\scripts\fix_desktop_shortcut.py:11: $sh = New-Object -ComObject WScript.Shell
C:\Users\a9379\.gemini\antigravity\scratch\fero-launcher-v4\scripts\update_launcher_icons.py:96: $sh = New-Object -ComObject WScript.Shell
```

### G. Скрипт воркера scripts\dwg_plot_worker.ps1 (строки 1-250 с номерами)
```text
1: param(
2:   [Parameter(Mandatory = $true)][string]$InputPath,
3:   [Parameter(Mandatory = $true)][string]$OutputDir,
4:   [Parameter(Mandatory = $false)][int]$PriorityTabOrder = -1,
5:   [Parameter(Mandatory = $false)][switch]$ListOnly,
6:   [Parameter(Mandatory = $false)][string]$LogFile = ""
7: )
8: 
9: $ErrorActionPreference = "Stop"
10: [Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)
11: 
12: if (-not (Test-Path -LiteralPath $InputPath -PathType Leaf)) {
13:   Write-Output (@{ event = "error"; message = "DWG file not found: $InputPath" } | ConvertTo-Json -Compress)
14:   exit 1
15: }
16: 
17: $InputPath = [System.IO.Path]::GetFullPath($InputPath)
18: $OutputDir = [System.IO.Path]::GetFullPath($OutputDir)
19: if ($LogFile) {
20:   $LogFile = [System.IO.Path]::GetFullPath($LogFile)
21: }
22: 
23: if (-not (Test-Path -LiteralPath $OutputDir)) {
24:   New-Item -ItemType Directory -Force -Path $OutputDir | Out-Null
25: }
26: 
27: function Log-Msg([string]$text) {
28:   if ($LogFile) {
29:     try {
30:       $ts = (Get-Date).ToString("yyyy-MM-dd HH:mm:ss.fff")
31:       Add-Content -LiteralPath $LogFile -Value "[$ts] $text" -Encoding UTF8 -ErrorAction SilentlyContinue
32:     } catch {}
33:   }
34: }
35: 
36: # 1. Регистрация IOleMessageFilter для перехвата сообщений COM/RPC (чтобы AutoCAD не отваливался при занятости)
37: if (-not ([System.Management.Automation.PSTypeName]'DwgPlotMessageFilter').Type) {
38:   Add-Type -TypeDefinition @"
39: using System;
40: using System.Runtime.InteropServices;
41: 
42: [ComImport(), InterfaceType(ComInterfaceType.InterfaceIsIUnknown), Guid("00000016-0000-0000-C000-000000000046")]
43: public interface IOleMessageFilter {
44:     [PreserveSig] int HandleInComingCall(int dwCallType, IntPtr hTaskCaller, int dwTickCount, IntPtr lpInterfaceInfo);
45:     [PreserveSig] int RetryRejectedCall(IntPtr hTaskCallee, int dwTickCount, int dwRejectType);
46:     [PreserveSig] int MessagePending(IntPtr hTaskCallee, int dwTickCount, int dwPendingType);
47: }
48: 
49: public class DwgPlotMessageFilter : IOleMessageFilter {
50:     [DllImport("ole32.dll")] private static extern int CoRegisterMessageFilter(IOleMessageFilter newFilter, out IOleMessageFilter oldFilter);
51:     [DllImport("user32.dll")] public static extern uint GetWindowThreadProcessId(IntPtr hWnd, out uint lpdwProcessId);
52:     public static void Register() {
53:         IOleMessageFilter newFilter = new DwgPlotMessageFilter();
54:         IOleMessageFilter oldFilter = null;
55:         CoRegisterMessageFilter(newFilter, out oldFilter);
56:     }
57:     public static void Revoke() {
58:         IOleMessageFilter oldFilter = null;
59:         CoRegisterMessageFilter(null, out oldFilter);
60:     }
61:     public int HandleInComingCall(int dwCallType, IntPtr hTaskCaller, int dwTickCount, IntPtr lpInterfaceInfo) { return 0; }
62:     public int RetryRejectedCall(IntPtr hTaskCallee, int dwTickCount, int dwRejectType) {
63:         if (dwRejectType == 2) return 100;
64:         return -1;
65:     }
66:     public int MessagePending(IntPtr hTaskCallee, int dwTickCount, int dwPendingType) { return 2; }
67: }
68: "@
69: }
70: [DwgPlotMessageFilter]::Register()
71: 
72: # 2. Подключение к AutoCAD COM
73: $comProgIds = @(
74:   "AutoCAD.Application.25",
75:   "AutoCAD.Application.24.3",
76:   "AutoCAD.Application.24.2",
77:   "AutoCAD.Application.24.1",
78:   "AutoCAD.Application.24.0",
79:   "AutoCAD.Application.24",
80:   "AutoCAD.Application.23.1",
81:   "AutoCAD.Application.23",
82:   "AutoCAD.Application.22",
83:   "AutoCAD.Application"
84: )
85: 
86: $app = $null
87: $usedProgId = ""
88: $isNewInstance = $false
89: $acadPid = 0
90: 
91: # Проверяем, есть ли РЕАЛЬНОЕ открытое видимое окно AutoCAD у пользователя
92: $visibleAcad = Get-Process acad -ErrorAction SilentlyContinue | Where-Object { $_.MainWindowHandle -ne 0 }
93: if ($visibleAcad) {
94:   foreach ($progId in $comProgIds) {
95:     try {
96:       $app = [System.Runtime.InteropServices.Marshal]::GetActiveObject($progId)
97:       if ($app) {
98:         $usedProgId = $progId
99:         $isNewInstance = $false
100:         Log-Msg "Attached to existing active user AutoCAD instance ($progId)"
101:         break
102:       }
103:     } catch {}
104:   }
105: }
106: 
107: if (-not $app) {
108:   Log-Msg "Active AutoCAD not found; background worker will not start a new instance."
109:   Write-Output (@{ event = "error"; message = "AutoCAD is not running" } | ConvertTo-Json -Compress)
110:   exit 0
111: }
112: 
113: $document = $null
114: 
115: try {
116:   Log-Msg "Opening document: $InputPath"
117:   $swOpen = [System.Diagnostics.Stopwatch]::StartNew()
118:   
119:   $openAttempts = 0
120:   while (-not $document -and $openAttempts -lt 3) {
121:     $openAttempts++
122:     try {
123:       $document = $app.Documents.Open($InputPath, $true) # ReadOnly = True
124:     } catch {
125:       if ($openAttempts -ge 3) { throw }
126:       Start-Sleep -Seconds 5
127:     }
128:   }
129:   $openMs = $swOpen.ElapsedMilliseconds
130:   Log-Msg "Opened in $openMs ms"
131: 
132:   # Оптимизация системных переменных чертежа для ускорения печати
133:   try { $app.Preferences.System.DisplayAlerts = $false } catch {}
134:   try { $document.SetVariable("LAYOUTREGENCTL", 2) } catch {}
135:   try { $document.SetVariable("REGENMODE", 0) } catch {}
136:   try { $document.SetVariable("BACKGROUNDPLOT", 0) } catch {}
137:   try { $document.SetVariable("EXPERT", 5) } catch {}
138:   try { $document.SetVariable("FILEDIA", 0) } catch {}
139:   try { $document.SetVariable("CMDDIA", 0) } catch {}
140:   try { $document.SetVariable("NOMUTT", 1) } catch {}
141:   try { $document.SetVariable("PROXYNOTICE", 0) } catch {}
142:   try { $document.SetVariable("DRAWORDERCTL", 0) } catch {}
143: 
144:   # Сбор всех пространств листа (Layouts)
145:   $candidateLayouts = @($document.Layouts | Where-Object { -not $_.ModelType } | Sort-Object TabOrder)
146:   $nonEmptyLayouts = @($candidateLayouts | Where-Object { $_.Block.Count -ge 1 })
147: 
148:   $layoutMetadata = @()
149:   foreach ($l in $nonEmptyLayouts) {
150:     $rot = 0
151:     try { $rot = [int]$l.PlotRotation } catch {}
152:     $layoutMetadata += @{
153:       name = [string]$l.Name
154:       tabOrder = [int]$l.TabOrder
155:       plotRotation = $rot
156:       configName = [string]$l.ConfigName
157:       canonicalMediaName = [string]$l.CanonicalMediaName
158:     }
159:   }
160: 
161:   # Уведомление о структуре листов
162:   $startEvent = @{
163:     event = "doc_opened"
164:     inputPath = $InputPath
165:     progId = $usedProgId
166:     openMs = $openMs
167:     totalLayouts = $candidateLayouts.Count
168:     validLayouts = $nonEmptyLayouts.Count
169:     layouts = $layoutMetadata
170:   }
171:   Write-Output ($startEvent | ConvertTo-Json -Compress -Depth 4)
172: 
173:   # Сохраняем начальный манифест структуры листов
174:   $manifestFile = Join-Path $OutputDir "manifest.json"
175:   try {
176:     $itemStat = Get-Item -LiteralPath $InputPath
177:     $epoch = [datetime]'1970-01-01 00:00:00Z'
178:     $mtimeSec = [int64]($itemStat.LastWriteTimeUtc - $epoch).TotalSeconds
179:     $manifestData = [ordered]@{
180:       sourcePath = $InputPath
181:       sourceName = [System.IO.Path]::GetFileName($InputPath)
182:       sourceSize = $itemStat.Length
183:       sourceMtime = $mtimeSec
184:       outputDir = $OutputDir
185:       isComplete = $false
186:       totalLayouts = $candidateLayouts.Count
187:       validLayouts = $nonEmptyLayouts.Count
188:       layouts = $layoutMetadata
189:       completedPages = @{}
190:     }
191:     $utf8NoBom = [System.Text.UTF8Encoding]::new($false)
192:     [System.IO.File]::WriteAllText($manifestFile, ($manifestData | ConvertTo-Json -Depth 5), $utf8NoBom)
193:   } catch {}
194: 
195:   if ($ListOnly) {
196:     exit 0
197:   }
198: 
199:   # Функция настройки плоттера листа (с кэшированием устройств)
200:   function Prepare-LayoutPlotter($layoutObj) {
201:     # ВСЕГДА проверяем, что выбран именно PDF-плоттер (физические принтеры вызывают E_INVALIDARG в PlotToFile)
202:     $curDev = [string]$layoutObj.ConfigName
203:     $isPdfDev = ($curDev -and ($curDev -match "DWG To PDF" -or $curDev -match "AutoCAD PDF" -or $curDev -match "Microsoft Print to PDF"))
204:     if (-not $isPdfDev) {
205:       $preferred = @(
206:         "DWG To PDF.pc3",
207:         "AutoCAD PDF (General Documentation).pc3",
208:         "AutoCAD PDF (High Quality Print).pc3",
209:         "AutoCAD PDF (Smallest File).pc3",
210:         "Microsoft Print to PDF"
211:       )
212:       foreach ($dev in $preferred) {
213:         try {
214:           $layoutObj.ConfigName = $dev
215:           $layoutObj.RefreshPlotDeviceInfo()
216:           break
217:         } catch {}
218:       }
219:     }
220: 
221:     try {
222:       $allMedia = @($layoutObj.GetCanonicalMediaNames())
223:       $curMedia = [string]$layoutObj.CanonicalMediaName
224:       $hasIsoMedia = ($curMedia -and ($curMedia -match "ISO|A3|A4|A2|A1|A0"))
225:       if (-not $hasIsoMedia -and $allMedia.Count -gt 0) {
226:         $preferredMedia = @(
227:           "ISO_full_bleed_A3_(420.00_x_297.00_MM)",
228:           "ISO_A3_(420.00_x_297.00_MM)",
229:           "ISO_full_bleed_A4_(297.00_x_210.00_MM)",
230:           "ISO_A4_(297.00_x_210.00_MM)"
231:         )
232:         foreach ($pm in $preferredMedia) {
233:           if ($allMedia -contains $pm) {
234:             try { $layoutObj.CanonicalMediaName = $pm; break } catch {}
235:           }
236:         }
237:       }
238:     } catch {}
239: 
240:     try { $layoutObj.PlotType = 5 } catch {} # acLayout (5 is acLayout in AutoCAD COM; 4 is acWindow)
241:     $layoutObj.PlotWithLineweights = $true
242:     $layoutObj.PlotWithPlotStyles = $true
243:   }
244: 
245:   # Функция печати одного листа
246:   function Plot-OneLayout($layoutObj) {
247:     $tabOrder = [int]$layoutObj.TabOrder
248:     $name = [string]$layoutObj.Name
249:     $pdfFile = Join-Path $OutputDir ("page_{0:D4}.pdf" -f $tabOrder)
250:
```

## Расхождения
- Нет. Все команды выполнены дословно в режиме read-only.
- Процессы AutoCAD и лаунчера не завершались, не закрывались и не перезапускались.