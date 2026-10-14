"""DWG Pipeline Runner - Автономный конвейер прогрессивной обработки DWG-чертежей.

Архитектура «Не ждать полного файла»:
1. Фаза 0 (< 5 мс): Мгновенное извлечение растрового превью из заголовка DWG.
2. Фаза 1: Открытие DWG в изолированном процессе AutoCAD COM, получение структуры всех листов.
3. Фаза 2 (High-Priority): Немедленная печать первого листа (page_0001.pdf) и нарезка в 150 DPI PNG.
   Пользователь видит готовый первый лист сразу, не дожидаясь остальных!
4. Фаза 3 (Progressive Streaming): Последовательная допечка остальных листов в фоне.
   Каждый лист сохраняется независимо, прогресс транслируется в реальном времени.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from app.backend.dwg_engine import extract_raw_thumbnail_from_dwg, _generate_placeholder_png

try:
    import fitz  # PyMuPDF
except ImportError:
    fitz = None


def calc_file_id(path: Path) -> str:
    return hashlib.sha1(str(path.resolve()).casefold().encode("utf-8")).hexdigest()[:12]


def run_pipeline(
    input_dwg: Path,
    output_dir: Optional[Path] = None,
    priority_tab: int = 1,
    dpi: int = 150,
    list_only: bool = False,
) -> Dict[str, Any]:
    t_global_start = time.perf_counter()
    input_dwg = input_dwg.resolve()
    if not input_dwg.is_file():
        raise FileNotFoundError(f"Файл DWG не найден: {input_dwg}")

    file_id = calc_file_id(input_dwg)
    if output_dir is None:
        output_dir = REPO_ROOT / "runtime" / "cache" / "dwg" / "autonomous" / f"{input_dwg.stem}_{file_id}"
    output_dir.mkdir(parents=True, exist_ok=True)

    print("=" * 70)
    print("  DWG PIPELINE RUNNER v1.0 (Autonomous On-Demand Engine)")
    print("=" * 70)
    print(f"[*] Файл: {input_dwg.name}")
    print(f"[*] Размер: {input_dwg.stat().st_size:,} байт ({input_dwg.stat().st_size / (1024*1024):.2f} МБ)")
    print(f"[*] Выходной кэш: {output_dir}\n")

    manifest_path = output_dir / "manifest.json"
    manifest: Dict[str, Any] = {
        "sourcePath": str(input_dwg),
        "sourceName": input_dwg.name,
        "sourceSize": input_dwg.stat().st_size,
        "sourceMtimeNs": input_dwg.stat().st_mtime_ns,
        "outputDir": str(output_dir),
        "fileId": file_id,
        "phase0_thumb": None,
        "layouts": [],
        "completedPages": {},
        "isComplete": False,
        "startedAt": time.strftime("%Y-%m-%dT%H:%M:%S"),
    }

    # =========================================================================
    # ФАЗА 0: Мгновенное извлечение растрового превью из заголовка DWG (< 5 мс)
    # =========================================================================
    t0 = time.perf_counter()
    thumb_res = extract_raw_thumbnail_from_dwg(input_dwg)
    t_phase0 = (time.perf_counter() - t0) * 1000.0

    thumb_png_path = output_dir / "header_thumb.png"
    if thumb_res:
        raw_bytes, img_fmt = thumb_res
        thumb_png_path.write_bytes(raw_bytes)
        print(f"[Фаза 0: Превью заголовка] УСПЕХ: извлечен {img_fmt} ({len(raw_bytes):,} байт) за {t_phase0:.2f} мс")
        manifest["phase0_thumb"] = {"path": str(thumb_png_path), "format": img_fmt, "elapsedMs": round(t_phase0, 2)}
    else:
        dummy = _generate_placeholder_png(input_dwg.name, "Model")
        thumb_png_path.write_bytes(dummy)
        print(f"[Фаза 0: Превью заголовка] Заголовочный растр не найден, создан плейсхолдер за {t_phase0:.2f} мс")
        manifest["phase0_thumb"] = {"path": str(thumb_png_path), "format": "PNG", "elapsedMs": round(t_phase0, 2), "isPlaceholder": True}

    # =========================================================================
    # ФАЗА 1 & 2: Запуск прогрессивного AutoCAD COM воркера
    # =========================================================================
    worker_script = REPO_ROOT / "scripts" / "dwg_plot_worker.ps1"
    if not worker_script.is_file():
        raise FileNotFoundError(f"Скрипт воркера не найден: {worker_script}")

    cmd = [
        "powershell",
        "-NoProfile",
        "-ExecutionPolicy", "Bypass",
        "-File", str(worker_script),
        "-InputPath", str(input_dwg),
        "-OutputDir", str(output_dir),
        "-PriorityTabOrder", str(priority_tab),
    ]
    if list_only:
        cmd.append("-ListOnly")

    print("\n[Фаза 1: Запуск AutoCAD воркера] Открытие файла и подготовка очереди печати...")
    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
        bufsize=1,
    )

    first_sheet_delivered = False
    layouts_discovered = []
    completed_sheets: List[Dict[str, Any]] = []

    # Чтение событий воркера в реальном времени
    if proc.stdout:
        for line in proc.stdout:
            line_str = line.strip()
            if not line_str or not (line_str.startswith("{") and line_str.endswith("}")):
                continue
            try:
                event = json.loads(line_str)
            except Exception:
                continue

            event_type = event.get("event")

            # 1. Документ открыт в AutoCAD, структура листов прочитана
            if event_type == "doc_opened":
                open_ms = event.get("openMs", 0)
                layouts_discovered = event.get("layouts", [])
                valid_count = event.get("validLayouts", 0)
                print(f" -> База чертежа открыта в CAD за {open_ms/1000.0:.2f} сек. Найдено печатаемых листов: {valid_count}")
                for idx, lay in enumerate(layouts_discovered[:5], 1):
                    print(f"    [{lay.get('tabOrder')}] '{lay.get('name')}' (Media: {lay.get('canonicalMediaName')})")
                if len(layouts_discovered) > 5:
                    print(f"    ... и ещё {len(layouts_discovered) - 5} листов")
                manifest["layouts"] = layouts_discovered
                manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

            # 2. Лист отпечатан в PDF -> мгновенная нарезка в 150 DPI PNG
            elif event_type == "sheet_ready":
                tab_order = event.get("tabOrder", 0)
                sheet_name = event.get("name", "")
                pdf_path_str = event.get("pdfPath", "")
                elapsed_ms = event.get("elapsedMs", 0)
                from_cache = event.get("fromCache", False)

                pdf_p = Path(pdf_path_str) if pdf_path_str else None
                png_p = output_dir / f"page_{tab_order:04d}.png"
                img_dims = ""

                # Растеризация в PNG через PyMuPDF (fitz)
                if pdf_p and pdf_p.is_file() and fitz:
                    try:
                        t_fitz0 = time.perf_counter()
                        with fitz.open(pdf_p) as doc:
                            if len(doc) > 0:
                                page = doc[0]
                                pix = page.get_pixmap(dpi=dpi)
                                pix.save(str(png_p))
                                img_dims = f"{pix.width}x{pix.height} px"
                        t_fitz_ms = (time.perf_counter() - t_fitz0) * 1000.0
                    except Exception as fe:
                        img_dims = f"fitz_err: {fe}"

                cache_label = "[КЭШ]" if from_cache else f"[{elapsed_ms/1000.0:.1f}с]"
                print(f"  [+] Лист {tab_order:2d} ('{sheet_name}') {cache_label} -> PNG: {png_p.name} ({img_dims})")

                sheet_entry = {
                    "tabOrder": tab_order,
                    "name": sheet_name,
                    "pdf": str(pdf_p) if pdf_p else "",
                    "png": str(png_p),
                    "dims": img_dims,
                    "elapsedMs": elapsed_ms,
                    "readyAt": time.strftime("%H:%M:%S"),
                }
                completed_sheets.append(sheet_entry)
                manifest["completedPages"][str(tab_order)] = sheet_entry
                manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

                # Фиксация ключевого момента: выдача первого готового листа пользователю
                if not first_sheet_delivered:
                    first_sheet_delivered = True
                    t_first_deliv = time.perf_counter() - t_global_start
                    print("=" * 70)
                    print(f"  >>> ПЕРВЫЙ ГОТОВЫЙ ЛИСТ ВЫДАН НА СЦЕНУ ЗА: {t_first_deliv:.2f} СЕК! <<<")
                    print(f"  Файл для экрана: {png_p}")
                    print("=" * 70)
                    print("  (Остальные листы продолжают допекаться в фоновом режиме...)\n")

            # 3. Ошибка на отдельном листе
            elif event_type == "sheet_error":
                tab_order = event.get("tabOrder", 0)
                sheet_name = event.get("name", "")
                err_msg = event.get("message", "")
                print(f"  [!] Ошибка листа {tab_order} ('{sheet_name}'): {err_msg}")

            # 4. Завершение всех листов
            elif event_type == "complete":
                tot_ms = event.get("totalTimeMs", 0)
                print(f"\n[*] Все доступные листы отпечатаны за {tot_ms/1000.0:.1f} сек.")

    proc.wait()
    t_global_total = time.perf_counter() - t_global_start

    manifest["isComplete"] = True
    manifest["totalDurationSec"] = round(t_global_total, 2)
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    print("\n" + "=" * 70)
    print("  ИТОГИ ВЫПОЛНЕНИЯ КОНВЕЙЕРА:")
    print(f"  - Всего листов обработано: {len(completed_sheets)}")
    print(f"  - Полное время конвейера: {t_global_total:.2f} сек ({t_global_total/60.0:.2f} мин)")
    print(f"  - Директория с готовыми PNG/PDF: {output_dir}")
    print("=" * 70)

    return manifest


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Автономный запуск прогрессивного DWG конвейера")
    parser.add_argument("--input", "-i", required=True, help="Путь к файлу .dwg")
    parser.add_argument("--output-dir", "-o", default=None, help="Выходная папка для кэша листов")
    parser.add_argument("--priority", "-p", type=int, default=1, help="Приоритетный лист для немедленной выдачи (default 1)")
    parser.add_argument("--dpi", type=int, default=150, help="DPI нарезки PNG (default 150)")
    parser.add_argument("--list-only", action="store_true", help="Только список листов без печати")

    args = parser.parse_args()
    run_pipeline(
        input_dwg=Path(args.input),
        output_dir=Path(args.output_dir) if args.output_dir else None,
        priority_tab=args.priority,
        dpi=args.dpi,
        list_only=args.list_only,
    )
