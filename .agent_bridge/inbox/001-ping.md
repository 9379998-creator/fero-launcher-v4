# Task 001 - ping (проверка канала)
mode: read-only
push: no

Цель: убедиться, что агент видит ветку bridge, умеет в неё писать и корректно выводит текст.

Выполни и приложи вывод дословно:
1. `git rev-parse --abbrev-ref HEAD` (в рабочей папке main)
2. `git status -sb` (в рабочей папке main)
3. `git log -3 --oneline` (в рабочей папке main)
4. `C:\Python314\python.exe --version`
5. `C:\Python314\python.exe -c "import numpy; print(numpy.__version__)"` (если не установлен - покажи ошибку)
6. Содержимое `.agent_bridge/PROTOCOL.md` в worktree bridge: первые 5 строк с номерами.
7. Контрольная строка кириллицы и скобок для проверки кодировки: выведи её как есть - `Проверка: {("лист №1")} - ok`.

Запиши результат в `.agent_bridge/outbox/001-ping.md` по формату из PROTOCOL.md и запушь в `origin bridge`.
