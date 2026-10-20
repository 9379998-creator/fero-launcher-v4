# Result 002
status: ok
branch/commit: e2d15f1 (bridge) / 4f44ce1 (main)

## Что выполнено
- A. Процессы (A1, A2, A3): ok
- B. Порты (B1, B2, B3): ok
- C. Логи (150 строк launcher_gui, server_startup, server, native-front): ok
- D. Кэш DWG и PDF (D1, D2, D3, D4): ok
- E. Объект и настройки (E1, E1b, E1c, E2, E3): ok
- F. Кто запускает AutoCAD в коде: ok
- G. Скрипт воркера dwg_plot_worker.ps1 (строки 1-250 с номерами): ok

Полный детальный вывод разбит на 3 части согласно правилу ограничения длины файлов (>250 строк):
1. [.agent_bridge/outbox/002-diagnostics-part1.md](002-diagnostics-part1.md) — Разделы A, B, C (Процессы, Порты, Логи)
2. [.agent_bridge/outbox/002-diagnostics-part2.md](002-diagnostics-part2.md) — Раздел D (Кэш DWG и PDF, размеры pt/px, манифесты)
3. [.agent_bridge/outbox/002-diagnostics-part3.md](002-diagnostics-part3.md) — Разделы E, F, G (Папка объекта, точки запуска AutoCAD, строки 1-250 dwg_plot_worker.ps1)

## Сводка ключевых находок диагностики
- **Процессы**: активен `pythonw.exe` PID 32432 (порт 8780), родитель `pythonw.exe` PID 26668. Присутствует старый зомби PID 15128 (от 18.10). Запущен пользовательский `acad.exe` PID 26832 (без видимого заголовка, hwnd=0).
- **Порты**: `127.0.0.1:8780` в состоянии Listen (1 соединение, процесс 32432). `/api/health` отвечает 200 OK.
- **Кэш DWG**: 21ffad6742142c12f679 (`Сечение 2-2_Секция 2.dwg`) имеет `page_0000.pdf` размером `792x612 pt` (ANSI Letter / A4) и `page-0.png` 792x612 px, тогда как остальные чертежи имеют `size_pt=842x1191` (формат А3).
- **Кэш PDF**: многостраничный PDF `U2601-002 ОПР_2026-04-14.pdf` (9 страниц) в кэше 150 DPI имеет только 1 отрендеренную страницу (`complete: false`), а в кэше 72 DPI отрендерен полностью (`complete: true`, 9 страниц).
- **Объект Попова**: путь `H:\Общие диски\007_Коммерческий отдел\ОБЪЕКТЫ 2026\13_Попова_38_Стройтрест\Попова АР` доступен (`exists=True`), содержит 21 файл DWG, 2 файла PDF, 1 файл ZIP. Все файлы имеют атрибут `Normal` (скачаны на локальный диск).
- **Точки запуска AutoCAD**: найден вызов COM `AutoCAD.Application` в `app/backend/server.py` и `scripts/dwg_plot_worker.ps1`, а также запуск `accoreconsole.exe` в `scripts/Invoke-NativeDwgPdfExport.ps1`.

## Расхождения
- Нет. Все пункты задания 002 выполнены штатно и дословно.