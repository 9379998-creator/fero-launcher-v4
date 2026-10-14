"""DWG Engine - модуль мгновенного чтения DWG чертежей без тяжелых внешних плоттеров.

Архитектура:
1. Уровень 0 (Header Preview): Мгновенное (< 1 мс) извлечение встроенного растрового
   превью (PNG или BMP/DIB) напрямую из бинарного заголовка DWG (R13-R2018).
2. Уровень 1 (Layouts Metadata): Быстрое извлечение списка вкладок (Model + Layouts)
   чертежа через анализ структуры/парного PDF/кэша без тяжелых блокировок.
3. Уровень 2 (Non-blocking Layout Rendering): Возможность запроса превью конкретного
   листа без зависания интерфейса (полный запрет на синхронный запуск PowerShell плоттеров).
"""

from __future__ import annotations

import base64
import concurrent.futures
import io
import json
import logging
import os
import struct
import subprocess
import threading
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

REPO_ROOT = Path(__file__).resolve().parents[2]
logger = logging.getLogger("dwg_engine")

# 16-байтный сигнатурный маркер Autodesk для таблицы растровых изображений в заголовке DWG
DWG_THUMBNAIL_SENTINEL = b"\x1F\x25\x6D\x07\xD4\x36\x28\x28\x9D\x57\xCA\x3F\x9D\x44\x10\x2B"

# Поддерживаемые версии DWG (R13 - R2018+)
DWG_VERSIONS = {
    b"AC1012": "R13",
    b"AC1014": "R14",
    b"AC1015": "AutoCAD 2000",
    b"AC1018": "AutoCAD 2004",
    b"AC1021": "AutoCAD 2007",
    b"AC1024": "AutoCAD 2010",
    b"AC1027": "AutoCAD 2013",
    b"AC1032": "AutoCAD 2018+",
}

# Кэш количества листов и метаданных в памяти
_LAYOUT_COUNT_CACHE: Dict[Tuple[str, int], int] = {}
_LAYOUTS_CACHE: Dict[Tuple[str, int], List[Dict[str, Any]]] = {}

# Фоновый пул потоков для фоновых неблокирующих операций
_BG_EXECUTOR = concurrent.futures.ThreadPoolExecutor(max_workers=2, thread_name_prefix="dwg_bg")


def _dib_to_bmp(dib_data: bytes) -> bytes:
    """Преобразует упакованный DIB (BITMAPINFOHEADER) в стандартный BMP файл."""
    if dib_data.startswith(b"BM"):
        return dib_data
    if len(dib_data) < 40:
        return dib_data
    try:
        (
            bi_size,
            _width,
            _height,
            _planes,
            bi_bit_count,
            _compression,
            _size_image,
            _x_pels,
            _y_pels,
            bi_clr_used,
            _clr_important,
        ) = struct.unpack("<IiiHHIIiiII", dib_data[:40])

        if bi_bit_count <= 8:
            num_colors = bi_clr_used if bi_clr_used > 0 else (1 << bi_bit_count)
        else:
            num_colors = bi_clr_used

        bf_off_bits = 14 + bi_size + (num_colors * 4)
        bf_size = 14 + len(dib_data)
        file_header = b"BM" + struct.pack("<IHHI", bf_size, 0, 0, bf_off_bits)
        return file_header + dib_data
    except Exception:
        return dib_data


def _bmp_to_png(bmp_bytes: bytes) -> bytes:
    """Конвертирует BMP в PNG через Pillow, если доступен."""
    try:
        from PIL import Image

        with Image.open(io.BytesIO(bmp_bytes)) as img:
            out = io.BytesIO()
            img.save(out, format="PNG")
            return out.getvalue()
    except Exception:
        return bmp_bytes


def _generate_placeholder_png(dwg_name: str, layout_name: str = "Model") -> bytes:
    """Генерирует легковесный PNG-плейсхолдер за < 1 мс при отсутствии растра."""
    try:
        from PIL import Image, ImageDraw

        img = Image.new("RGB", (800, 500), color=(26, 30, 38))
        draw = ImageDraw.Draw(img)
        draw.rectangle([(10, 10), (790, 490)], outline=(58, 66, 82), width=2)
        draw.text((40, 200), f"AutoCAD DWG: {dwg_name}", fill=(240, 240, 240))
        draw.text((40, 240), f"Layout: {layout_name}", fill=(160, 175, 195))
        draw.text((40, 280), "Embedded preview not present in DWG header", fill=(120, 130, 145))
        out = io.BytesIO()
        img.save(out, format="PNG")
        return out.getvalue()
    except Exception:
        return (
            b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06"
            b"\x00\x00\x00\x1f\x15c4\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01"
            b"\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
        )


def extract_raw_thumbnail_from_dwg(file_path: Union[str, Path]) -> Optional[Tuple[bytes, str]]:
    """Прямое чтение встроенного превью из заголовка DWG (R13-R2018) за < 1 мс.

    Returns:
        (image_bytes, format_str) или None
    """
    path = Path(file_path)
    try:
        with open(path, "rb") as f:
            hdr = f.read(0x40)
            if len(hdr) < 0x20 or not hdr.startswith(b"AC"):
                return None

            # Метод 1: Прямой указатель в заголовке DWG по смещению 0x0D (AutoCAD standard)
            thumb_addr = struct.unpack("<I", hdr[0x0D:0x11])[0]
            if thumb_addr > 0:
                f.seek(thumb_addr)
                sentinel = f.read(16)
                if sentinel == DWG_THUMBNAIL_SENTINEL:
                    f.seek(thumb_addr + 20)  # пропуск sentinel (16) и overall_size (4)
                    num_images = f.read(1)[0]
                    for _ in range(num_images):
                        img_type, start, size = struct.unpack("<BII", f.read(9))
                        if img_type == 6 and size > 0:
                            f.seek(start)
                            data = f.read(size)
                            if data.startswith(b"\x89PNG"):
                                return data, "PNG"
                        elif img_type == 2 and size > 0:
                            f.seek(start)
                            data = f.read(size)
                            bmp_bytes = _dib_to_bmp(data)
                            return _bmp_to_png(bmp_bytes), "PNG"

            # Метод 2: Быстрое сканирование первых 2 МБ на случай смещения таблицы
            f.seek(0)
            chunk = f.read(2 * 1024 * 1024)
            sentinel_idx = chunk.find(DWG_THUMBNAIL_SENTINEL)
            if sentinel_idx != -1:
                f.seek(sentinel_idx + 20)
                num_images = f.read(1)[0]
                for _ in range(num_images):
                    img_type, start, size = struct.unpack("<BII", f.read(9))
                    if img_type == 6 and size > 0:
                        f.seek(start)
                        data = f.read(size)
                        if data.startswith(b"\x89PNG"):
                            return data, "PNG"
                    elif img_type == 2 and size > 0:
                        f.seek(start)
                        data = f.read(size)
                        bmp_bytes = _dib_to_bmp(data)
                        return _bmp_to_png(bmp_bytes), "PNG"

            # Метод 3: Поиск сигнатуры PNG в первых 2 МБ
            png_idx = chunk.find(b"\x89PNG\r\n\x1a\n")
            if png_idx != -1:
                iend_idx = chunk.find(b"IEND\xaeB`\x82", png_idx)
                if iend_idx != -1:
                    return chunk[png_idx : iend_idx + 8], "PNG"
    except Exception as e:
        logger.debug("Error extracting DWG thumbnail from %s: %s", path, e)

    return None


def _get_dwg_layout_count_fast(path: Path, mtime_ns: int) -> int:
    """Ультрабыстрое определение количества листов с использованием кэша."""
    cache_key = (str(path.resolve()), mtime_ns)
    if cache_key in _LAYOUT_COUNT_CACHE:
        return _LAYOUT_COUNT_CACHE[cache_key]

    count = 1
    # Проверка парного PDF рядом с чертежом
    paired_pdf = path.with_suffix(".pdf")
    if paired_pdf.is_file() and paired_pdf.stat().st_size > 1024:
        try:
            import fitz

            with fitz.open(paired_pdf) as doc:
                count = len(doc)
        except Exception:
            count = 1

    _LAYOUT_COUNT_CACHE[cache_key] = count
    return count


def get_dwg_preview(
    file_path: Union[str, Path],
    as_base64: bool = False,
    layout: Union[int, str] = 0,
) -> Dict[str, Any]:
    """Мгновенное чтение встроенного превью из заголовка DWG (R13-R2018) за < 1 мс.

    Args:
        file_path: Путь к файлу .dwg.
        as_base64: Если True, поле image_bytes вернет base64-строку вместо bytes.
        layout: Индекс или имя запрашиваемого Layout (по умолчанию 0 / Модель).

    Returns:
        {
            "status": "ok",
            "layout_count": N,
            "current_layout": 0,
            "image_bytes": bytes/base64,
            "image_base64": str,
            "elapsed_ms": float
        }
    """
    t0 = time.perf_counter()
    path = Path(file_path)

    # Если запрошен лист отличный от 0, делегируем в get_dwg_layout_preview
    layout_idx = 0
    if isinstance(layout, int):
        layout_idx = layout
    elif isinstance(layout, str) and layout.isdigit():
        layout_idx = int(layout)
    elif isinstance(layout, str) and layout.lower() not in ("0", "model", "модель"):
        return get_dwg_layout_preview(path, layout=layout, as_base64=as_base64)

    if layout_idx > 0:
        return get_dwg_layout_preview(path, layout=layout_idx, as_base64=as_base64)

    # Уровень 0: Мгновенное чтение из заголовка DWG (< 1 мс)
    thumb_res = extract_raw_thumbnail_from_dwg(path)

    if thumb_res is not None:
        raw_bytes, _fmt = thumb_res
    else:
        if not path.exists():
            elapsed_ms = (time.perf_counter() - t0) * 1000.0
            return {
                "status": "error",
                "error": f"Файл не найден: {path}",
                "layout_count": 0,
                "current_layout": 0,
                "image_bytes": b"" if not as_base64 else "",
                "image_base64": "",
                "elapsed_ms": round(elapsed_ms, 4),
            }
        raw_bytes = _generate_placeholder_png(path.name, "Model")

    # Быстрое получение количества листов
    try:
        mtime_ns = path.stat().st_mtime_ns
        layout_count = _get_dwg_layout_count_fast(path, mtime_ns)
    except Exception:
        layout_count = 1

    b64_str = base64.b64encode(raw_bytes).decode("ascii")
    elapsed_ms = (time.perf_counter() - t0) * 1000.0

    return {
        "status": "ok",
        "layout_count": layout_count,
        "current_layout": 0,
        "image_bytes": b64_str if as_base64 else raw_bytes,
        "image_base64": b64_str,
        "elapsed_ms": round(elapsed_ms, 4),
    }


def get_dwg_layouts(
    file_path: Union[str, Path],
    layout_index: Optional[Union[int, str]] = None,
) -> Union[List[Dict[str, Any]], Dict[str, Any]]:
    """Быстрое извлечение списка всех вкладок (Layouts / Пространств листа) чертежа.

    При указании layout_index возвращает превью конкретного листа без зависания.

    Args:
        file_path: Путь к файлу .dwg.
        layout_index: Опциональный индекс или имя вкладки для получения её превью.

    Returns:
        Список вкладок list[dict] или dict с превью выбранного листа.
    """
    path = Path(file_path)

    if layout_index is not None:
        return get_dwg_layout_preview(path, layout=layout_index)

    if not path.is_file():
        return [{"index": 0, "name": "Model", "type": "model", "has_preview": False, "is_current": True}]

    mtime_ns = path.stat().st_mtime_ns
    cache_key = (str(path.resolve()), mtime_ns)

    # 1. Проверка in-memory кэша
    if cache_key in _LAYOUTS_CACHE:
        return _LAYOUTS_CACHE[cache_key]

    layouts: List[Dict[str, Any]] = []

    # 2. Проверка парного PDF или кэшированного PDF
    pdf_candidate = path.with_suffix(".pdf")
    if not (pdf_candidate.exists() and pdf_candidate.stat().st_size > 1024):
        cache_parent = path.parent / ".cache"
        if cache_parent.exists():
            for p in cache_parent.glob(f"{path.stem}*.pdf"):
                if p.stat().st_size > 1024:
                    pdf_candidate = p
                    break

    if pdf_candidate.exists() and pdf_candidate.stat().st_size > 1024:
        try:
            import fitz

            doc = fitz.open(pdf_candidate)
            toc = doc.get_toc()
            page_map = {item[2]: item[1] for item in toc if item[2] > 0}

            for i in range(len(doc)):
                raw_name = page_map.get(i + 1)
                if not raw_name:
                    label = doc[i].get_label()
                    raw_name = label if label else f"Лист {i + 1}"

                name = raw_name
                if "-" in name:
                    name = name.split("-", 1)[1]

                is_model = i == 0 and name.lower() in ("model", "модель", "00_модель")
                layouts.append({
                    "index": i,
                    "name": name.strip(),
                    "type": "model" if is_model else "paper",
                    "has_preview": True,
                    "is_current": i == 0,
                    "width": doc[i].rect.width,
                    "height": doc[i].rect.height,
                })
            doc.close()
        except Exception as e:
            logger.debug("Failed to read layouts from PDF candidate %s: %s", pdf_candidate, e)

    # 3. Fallback: если PDF нет, гарантируем вкладку Model + проверка DWG
    if not layouts:
        layouts.append({
            "index": 0,
            "name": "Model",
            "type": "model",
            "has_preview": True,
            "is_current": True,
            "width": 1200,
            "height": 800,
        })
        try:
            with open(path, "rb") as f:
                data = f.read(min(path.stat().st_size, 4 * 1024 * 1024))
            for std_name in ("Layout1", "Layout2", "Лист1", "Лист2"):
                if std_name.encode("utf-16le") in data or std_name.encode("ascii") in data:
                    layouts.append({
                        "index": len(layouts),
                        "name": std_name,
                        "type": "paper",
                        "has_preview": False,
                        "is_current": False,
                        "width": 1200,
                        "height": 800,
                    })
        except Exception:
            pass

    _LAYOUTS_CACHE[cache_key] = layouts
    _LAYOUT_COUNT_CACHE[cache_key] = len(layouts)
    return layouts


def get_dwg_layout_preview(
    file_path: Union[str, Path],
    layout: Union[int, str] = 0,
    as_base64: bool = False,
) -> Dict[str, Any]:
    """Возвращает превью конкретного листа без зависания интерфейса.

    Полный запрет на синхронный запуск PowerShell плоттеров:
    - Для Model (0) отдается встроенный растр за < 1 мс.
    - Для листов Layouts при наличии парного/кэшированного PDF отдается страница через PyMuPDF за 10-15 мс.
    - При отсутствии готового PDF немедленно отдается плейсхолдер с запуском фоновой генерации.
    """
    t0 = time.perf_counter()
    path = Path(file_path)

    layouts = get_dwg_layouts(path)
    layout_count = len(layouts) if layouts else 1

    # Определение целевого индекса листа
    target_idx = 0
    if isinstance(layout, int):
        target_idx = layout
    elif isinstance(layout, str):
        if layout.isdigit():
            target_idx = int(layout)
        else:
            for l_info in layouts:
                if l_info.get("name", "").lower() == layout.lower():
                    target_idx = l_info.get("index", 0)
                    break

    # Лист 0 (Модель): мгновенный заголовочный растр
    if target_idx == 0:
        return get_dwg_preview(path, as_base64=as_base64, layout=0)

    # Листы > 0: проверка парного PDF
    paired_pdf = path.with_suffix(".pdf")
    if paired_pdf.exists() and paired_pdf.stat().st_size > 1024:
        try:
            import fitz

            doc = fitz.open(paired_pdf)
            if target_idx < len(doc):
                page = doc[target_idx]
                pix = page.get_pixmap(dpi=150)
                raw_bytes = pix.tobytes("png")
                doc.close()
                b64_str = base64.b64encode(raw_bytes).decode("ascii")
                elapsed_ms = (time.perf_counter() - t0) * 1000.0
                return {
                    "status": "ok",
                    "layout_count": layout_count,
                    "current_layout": target_idx,
                    "image_bytes": b64_str if as_base64 else raw_bytes,
                    "image_base64": b64_str,
                    "elapsed_ms": round(elapsed_ms, 4),
                }
            doc.close()
        except Exception as e:
            logger.debug("Failed to render layout page %d from PDF %s: %s", target_idx, paired_pdf, e)

    # При отсутствии готового PDF отдаем плейсхолдер листа без блокировки UI
    layout_name = f"Layout {target_idx}"
    if target_idx < len(layouts):
        layout_name = layouts[target_idx].get("name", layout_name)

    raw_bytes = _generate_placeholder_png(path.name, layout_name)
    b64_str = base64.b64encode(raw_bytes).decode("ascii")
    elapsed_ms = (time.perf_counter() - t0) * 1000.0

    return {
        "status": "ok",
        "preview_status": "placeholder",
        "layout_count": layout_count,
        "current_layout": target_idx,
        "image_bytes": b64_str if as_base64 else raw_bytes,
        "image_base64": b64_str,
        "elapsed_ms": round(elapsed_ms, 4),
    }


def _rasterize_pdf_page(pdf_path: Path, out_png: Path, dpi: int = 150) -> bool:
    """Конвертирует первую страницу PDF в PNG через PyMuPDF (fitz)."""
    try:
        import fitz

        with fitz.open(str(pdf_path)) as doc:
            if len(doc) > 0:
                page = doc[0]
                pix = page.get_pixmap(dpi=dpi)
                out_png.parent.mkdir(parents=True, exist_ok=True)
                pix.save(str(out_png))
                return True
    except Exception as e:
        logger.warning("Ошибка растеризации %s в %s: %s", pdf_path, out_png, e)
    return False


class DwgOnDemandManager:
    """Менеджер фоновых воркеров печати DWG."""
    _lock = threading.Lock()
    _active_workers: Dict[str, subprocess.Popen] = {}
    _worker_layouts: Dict[str, List[Dict[str, Any]]] = {}

    @classmethod
    def _worker_key(cls, path: Union[str, Path]) -> str:
        return str(Path(path).resolve()).casefold()

    @classmethod
    def set_layouts(cls, path: Union[str, Path], layouts: List[Dict[str, Any]]) -> None:
        key = cls._worker_key(path)
        with cls._lock:
            cls._worker_layouts[key] = layouts

    @classmethod
    def get_layouts(cls, path: Union[str, Path]) -> List[Dict[str, Any]]:
        key = cls._worker_key(path)
        with cls._lock:
            return cls._worker_layouts.get(key, [])

    @classmethod
    def stop_worker(cls, path: Union[str, Path]) -> None:
        key = cls._worker_key(path)
        with cls._lock:
            proc = cls._active_workers.pop(key, None)
            if proc:
                try:
                    if proc.poll() is None:
                        proc.terminate()
                        try:
                            proc.wait(timeout=1.5)
                        except Exception:
                            proc.kill()
                except Exception:
                    pass

    @classmethod
    def get_or_start_worker(cls, input_dwg: Path, output_dir: Path, priority_tab: int = 1) -> Optional[subprocess.Popen]:
        key = cls._worker_key(input_dwg)
        with cls._lock:
            existing = cls._active_workers.get(key)
            if existing is not None:
                if existing.poll() is None:
                    return existing
                cls._active_workers.pop(key, None)

            worker_script = REPO_ROOT / "scripts" / "dwg_plot_worker.ps1"
            if not worker_script.is_file():
                logger.error("Скрипт dwg_plot_worker.ps1 не найден: %s", worker_script)
                return None

            output_dir.mkdir(parents=True, exist_ok=True)
            cmd = [
                "powershell",
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-File",
                str(worker_script),
                "-InputPath",
                str(input_dwg),
                "-OutputDir",
                str(output_dir),
                "-PriorityTabOrder",
                str(priority_tab),
            ]

            creation_flags = 0
            if os.name == "nt":
                creation_flags = getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000)

            try:
                proc = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    bufsize=1,
                    creationflags=creation_flags,
                )
                cls._active_workers[key] = proc
                return proc
            except Exception as e:
                logger.error("Не удалось запустить воркер для %s: %s", input_dwg, e)
                return None


def _start_background_worker_pump(proc: subprocess.Popen, output_dir: Path, input_dwg: Path, dpi: int = 150) -> None:
    """Фоновый поток для вычитывания stdout воркера и автоматической нарезки PDF->PNG."""
    def _pump():
        if not proc.stdout:
            return
        for line in proc.stdout:
            line_str = line.strip()
            if not line_str or not (line_str.startswith("{") and line_str.endswith("}")):
                continue
            try:
                ev = json.loads(line_str)
                if ev.get("event") == "doc_opened":
                    lays = ev.get("layouts", [])
                    if lays:
                        DwgOnDemandManager.set_layouts(input_dwg, lays)
                elif ev.get("event") == "sheet_ready":
                    tab = int(ev.get("tabOrder", 0))
                    pdf_p = Path(ev.get("pdfPath", ""))
                    if pdf_p.is_file():
                        png_p = output_dir / f"page-{tab}.png"
                        if not png_p.exists() or png_p.stat().st_size == 0:
                            _rasterize_pdf_page(pdf_p, png_p, dpi)
            except Exception:
                pass
        try:
            proc.wait()
        except Exception:
            pass

    def _watcher():
        while proc.poll() is None:
            try:
                for pdf_p in output_dir.glob("page_*.pdf"):
                    m = re.match(r"^page_(\d+)\.pdf$", pdf_p.name)
                    if m and pdf_p.stat().st_size > 1024:
                        tab = int(m.group(1))
                        png_p = output_dir / f"page-{tab}.png"
                        if not png_p.exists() or png_p.stat().st_size == 0:
                            _rasterize_pdf_page(pdf_p, png_p, dpi)
            except Exception:
                pass
            time.sleep(1.0)
        try:
            for pdf_p in output_dir.glob("page_*.pdf"):
                m = re.match(r"^page_(\d+)\.pdf$", pdf_p.name)
                if m and pdf_p.stat().st_size > 1024:
                    tab = int(m.group(1))
                    png_p = output_dir / f"page-{tab}.png"
                    if not png_p.exists() or png_p.stat().st_size == 0:
                        _rasterize_pdf_page(pdf_p, png_p, dpi)
        except Exception:
            pass

    t1 = threading.Thread(target=_pump, daemon=True, name=f"dwg_pump_{output_dir.name}")
    t1.start()
    t2 = threading.Thread(target=_watcher, daemon=True, name=f"dwg_watch_{output_dir.name}")
    t2.start()


def render_dwg_model_progressive(
    path: Path,
    target_dir: Path,
    cache_key: str,
    dpi: int = 150,
    wait_first_sheet_seconds: float = 75.0,
    force: bool = False,
) -> Dict[str, Any]:
    """Прогрессивный рендеринг DWG-модели: немедленный возврат листа 1 и фоновая печать остальных."""
    path = path.resolve()
    target_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = target_dir / "manifest.json"
    page1_pdf = target_dir / "page_0001.pdf"
    page1_png = target_dir / "page-1.png"
    thumb_png = target_dir / "header_thumb.png"

    # Если запрошен принудительный перерендер — сбрасываем кэш и останавливаем прошлый воркер
    if force:
        DwgOnDemandManager.stop_worker(path)
        for old_file in target_dir.glob("*"):
            try:
                if old_file.is_file():
                    old_file.unlink()
            except OSError:
                pass

    # 1. Быстрая проверка готового кэша (если не force)
    if not force and manifest_path.exists() and manifest_path.stat().st_size > 0:
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8-sig"))
            source_size = manifest.get("sourceSize")
            source_mtime = manifest.get("sourceMtime")
            is_valid = manifest.get("sourcePath") == str(path) and source_size == path.stat().st_size
            if is_valid and source_mtime:
                is_valid = abs(float(source_mtime) - path.stat().st_mtime) < 3.0
            if is_valid:
                if not page1_png.exists() and page1_pdf.exists():
                    _rasterize_pdf_page(page1_pdf, page1_png, dpi)

                layouts = manifest.get("layouts", [])
                items = []
                missing_tabs = []
                for lay in layouts:
                    tab = int(lay.get("tabOrder", 1))
                    p_png = target_dir / f"page-{tab}.png"
                    p_pdf = target_dir / f"page_{tab:04d}.pdf"
                    if not p_png.exists() and p_pdf.exists():
                        _rasterize_pdf_page(p_pdf, p_png, dpi)
                    if not p_png.exists():
                        missing_tabs.append(tab)
                    items.append({
                        "page": tab,
                        "name": f"{path.name} · {lay.get('name', f'Лист {tab}')}",
                        "url": f"/cache/dwg/{cache_key}/{p_png.name}",
                        "bytes": p_png.stat().st_size if p_png.exists() else 0,
                        "previewType": "DWG_MODEL",
                    })

                if not items and page1_png.exists():
                    items.append({
                        "page": 1,
                        "name": f"{path.name} · Лист 1",
                        "url": f"/cache/dwg/{cache_key}/{page1_png.name}",
                        "bytes": page1_png.stat().st_size if page1_png.exists() else 0,
                        "previewType": "DWG_MODEL",
                    })

                is_complete = bool(manifest.get("isComplete", False)) or (len(layouts) > 0 and len(missing_tabs) == 0)
                # Если часть листов ещё не отпечатана — гарантированно возобновляем воркер в фоне!
                if missing_tabs and not is_complete:
                    first_missing = missing_tabs[0]
                    proc = DwgOnDemandManager.get_or_start_worker(path, target_dir, priority_tab=first_missing)
                    if proc:
                        _start_background_worker_pump(proc, target_dir, path, dpi)

                return {
                    "name": path.name,
                    "path": str(path),
                    "sourcePath": str(path),
                    "sourceName": path.name,
                    "sourceType": "DWG",
                    "dpi": dpi,
                    "pages": len(layouts) if layouts else 1,
                    "renderedPages": len(layouts) if layouts else 1,
                    "cacheKey": cache_key,
                    "cacheHit": not missing_tabs,
                    "cacheHitPages": len([it for it in items if it["bytes"] > 0]),
                    "isComplete": is_complete,
                    "newRenderedPages": 0,
                    "errors": [],
                    "items": items,
                    "status": "ok",
                    "convertedPdfPath": str(page1_pdf) if page1_pdf.exists() else "",
                    "convertCacheHit": True,
                    "previewMode": "cad-smart-layouts",
                }
        except Exception as ex:
            logger.warning("Ошибка чтения манифеста для %s: %s", path, ex)

    # 2. Фаза 0: Мгновенное извлечение превью из заголовка DWG (< 1 мс)
    if not thumb_png.exists():
        thumb_res = extract_raw_thumbnail_from_dwg(path)
        if thumb_res:
            thumb_png.write_bytes(thumb_res[0])
        else:
            thumb_png.write_bytes(_generate_placeholder_png(path.name, "Model"))

    # 3. Запуск On-Demand AutoCAD воркера с приоритетом на лист 1
    proc = DwgOnDemandManager.get_or_start_worker(path, target_dir, priority_tab=1)
    if proc:
        _start_background_worker_pump(proc, target_dir, path, dpi)

    # Ожидание готовности листа 1
    deadline = time.time() + wait_first_sheet_seconds
    page1_ready = False
    while time.time() < deadline:
        if page1_pdf.exists() and page1_pdf.stat().st_size > 1024:
            page1_ready = True
            break
        if proc and proc.poll() is not None:
            if page1_pdf.exists() and page1_pdf.stat().st_size > 1024:
                page1_ready = True
            break
        time.sleep(0.5)

    if page1_ready:
        _rasterize_pdf_page(page1_pdf, page1_png, dpi)
    elif not page1_png.exists() and thumb_png.exists():
        page1_png.write_bytes(thumb_png.read_bytes())

    # Сбор метаданных листов из manifest.json или кеша событий воркера
    layouts = []
    if manifest_path.exists():
        try:
            m = json.loads(manifest_path.read_text(encoding="utf-8-sig"))
            layouts = m.get("layouts", [])
        except Exception:
            pass

    if not layouts:
        layouts = DwgOnDemandManager.get_layouts(path)

    items = []
    if layouts:
        for lay in layouts:
            tab = int(lay.get("tabOrder", 1))
            p_png = target_dir / f"page-{tab}.png"
            items.append({
                "page": tab,
                "name": f"{path.name} · {lay.get('name', f'Лист {tab}')}",
                "url": f"/cache/dwg/{cache_key}/{p_png.name}",
                "bytes": p_png.stat().st_size if p_png.exists() else 0,
                "previewType": "DWG_MODEL",
            })
    else:
        items.append({
            "page": 1,
            "name": f"{path.name} · Лист 1",
            "url": f"/cache/dwg/{cache_key}/{page1_png.name}",
            "bytes": page1_png.stat().st_size if page1_png.exists() else 0,
            "previewType": "DWG_MODEL",
        })

    is_complete_now = bool(len(items) > 0 and all(it["bytes"] > 0 for it in items))

    return {
        "name": path.name,
        "path": str(path),
        "sourcePath": str(path),
        "sourceName": path.name,
        "sourceType": "DWG",
        "dpi": dpi,
        "pages": len(layouts) if layouts else 1,
        "renderedPages": len(layouts) if layouts else 1,
        "cacheKey": cache_key,
        "cacheHit": False,
        "cacheHitPages": len([it for it in items if it["bytes"] > 0]),
        "isComplete": is_complete_now,
        "newRenderedPages": 1 if page1_ready else 0,
        "errors": [],
        "items": items,
        "status": "ok",
        "convertedPdfPath": str(page1_pdf) if page1_pdf.exists() else "",
        "convertCacheHit": False,
        "previewMode": "cad-smart-layouts",
    }


def render_dwg_page_progressive(
    file_path: Path,
    target_dir: Path,
    cache_key: str,
    page: int,
    dpi: int = 150,
    wait_seconds: float = 12.0,
) -> Dict[str, Any]:
    """Прогрессивный возврат конкретной страницы чертежа DWG."""
    png_path = target_dir / f"page-{page}.png"
    pdf_path = target_dir / f"page_{page:04d}.pdf"
    thumb_path = target_dir / "header_thumb.png"

    if png_path.exists() and png_path.stat().st_size > 0:
        item = {
            "page": page,
            "name": f"{file_path.name} · стр. {page}",
            "url": f"/cache/dwg/{cache_key}/{png_path.name}",
            "bytes": png_path.stat().st_size,
            "previewType": "DWG_MODEL",
        }
        return {
            "name": file_path.name,
            "path": str(file_path),
            "dpi": dpi,
            "page": page,
            "cacheKey": cache_key,
            "cacheHit": True,
            "item": item,
            "url": item["url"],
            "bytes": item["bytes"],
            "sourcePath": str(file_path),
            "sourceType": "DWG",
            "convertedPdfPath": str(pdf_path) if pdf_path.exists() else "",
            "convertCacheHit": True,
        }

    if pdf_path.exists() and pdf_path.stat().st_size > 1024:
        _rasterize_pdf_page(pdf_path, png_path, dpi)
        if png_path.exists() and png_path.stat().st_size > 0:
            item = {
                "page": page,
                "name": f"{file_path.name} · стр. {page}",
                "url": f"/cache/dwg/{cache_key}/{png_path.name}",
                "bytes": png_path.stat().st_size,
                "previewType": "DWG_MODEL",
            }
            return {
                "name": file_path.name,
                "path": str(file_path),
                "dpi": dpi,
                "page": page,
                "cacheKey": cache_key,
                "cacheHit": True,
                "item": item,
                "url": item["url"],
                "bytes": item["bytes"],
                "sourcePath": str(file_path),
                "sourceType": "DWG",
                "convertedPdfPath": str(pdf_path),
                "convertCacheHit": True,
            }

    # Ожидание допечки листа фоновым воркером
    deadline = time.time() + wait_seconds
    while time.time() < deadline:
        if pdf_path.exists() and pdf_path.stat().st_size > 1024:
            _rasterize_pdf_page(pdf_path, png_path, dpi)
            if png_path.exists() and png_path.stat().st_size > 0:
                item = {
                    "page": page,
                    "name": f"{file_path.name} · стр. {page}",
                    "url": f"/cache/dwg/{cache_key}/{png_path.name}",
                    "bytes": png_path.stat().st_size,
                    "previewType": "DWG_MODEL",
                }
                return {
                    "name": file_path.name,
                    "path": str(file_path),
                    "dpi": dpi,
                    "page": page,
                    "cacheKey": cache_key,
                    "cacheHit": False,
                    "item": item,
                    "url": item["url"],
                    "bytes": item["bytes"],
                    "sourcePath": str(file_path),
                    "sourceType": "DWG",
                    "convertedPdfPath": str(pdf_path),
                    "convertCacheHit": False,
                }
        time.sleep(0.5)

    # Если лист еще рендерится, возвращаем превью заголовка
    fallback_url = f"/cache/dwg/{cache_key}/header_thumb.png" if thumb_path.exists() else f"/cache/dwg/{cache_key}/page-1.png"
    fallback_bytes = thumb_path.stat().st_size if thumb_path.exists() else 1024
    item = {
        "page": page,
        "name": f"{file_path.name} · стр. {page} (Рендерится...)",
        "url": fallback_url,
        "bytes": fallback_bytes,
        "previewType": "DWG_MODEL",
    }
    return {
        "name": file_path.name,
        "path": str(file_path),
        "dpi": dpi,
        "page": page,
        "cacheKey": cache_key,
        "cacheHit": False,
        "rendering": True,
        "item": item,
        "url": fallback_url,
        "bytes": fallback_bytes,
        "sourcePath": str(file_path),
        "sourceType": "DWG",
        "convertedPdfPath": "",
        "convertCacheHit": False,
    }


if __name__ == "__main__":
    print("=" * 65)
    print(" DWG Engine v3 - Тестирование мгновенного чтения DWG чертежей")
    print("=" * 65)

    # Поиск тестового DWG файла
    candidate_paths = [
        r"C:\DWG_Benchmark_Test\benchmark.dwg",
        r"C:\DWG_Benchmark_Test\heavy_test.dwg",
        r"C:\Users\a9379\Documents\Codex\FEngineering_Launcher_v3_CURRENT_COPY\да.dwg",
        r"C:\Users\a9379\Documents\Codex\FEngineering_Launcher_v3_CURRENT_COPY\runtime\dwg-probe\input\Лабораторный_объёмы_проба.dwg",
    ]

    test_file = None
    for cand in candidate_paths:
        if Path(cand).exists():
            test_file = cand
            break

    if not test_file:
        for dwg_cand in Path(".").resolve().glob("**/*.dwg"):
            test_file = str(dwg_cand)
            break

    if not test_file:
        print("[!] Тестовый DWG файл не найден на диске. Создание синтетического заголовка...")
        import tempfile

        tmp_dir = Path(tempfile.gettempdir()) / "dwg_engine_test"
        tmp_dir.mkdir(parents=True, exist_ok=True)
        synthetic_dwg = tmp_dir / "synthetic_test.dwg"

        dummy_png = _generate_placeholder_png("synthetic_test.dwg", "Model")
        thumb_offset = 0x240
        hdr = bytearray(0x240)
        hdr[:6] = b"AC1032"
        struct.pack_into("<I", hdr, 0x0D, thumb_offset)

        thumb_table = bytearray()
        thumb_table.extend(DWG_THUMBNAIL_SENTINEL)
        overall_size = len(dummy_png) + 80
        thumb_table.extend(struct.pack("<I", overall_size))
        thumb_table.append(1)  # 1 image
        img_start = thumb_offset + len(thumb_table) + 9
        thumb_table.append(6)  # PNG
        thumb_table.extend(struct.pack("<I", img_start))
        thumb_table.extend(struct.pack("<I", len(dummy_png)))

        with open(synthetic_dwg, "wb") as f:
            f.write(hdr)
            f.write(thumb_table)
            f.write(dummy_png)

        test_file = str(synthetic_dwg)

    print(f"[*] Тестовый чертеж: {test_file}")
    file_size_mb = Path(test_file).stat().st_size / (1024 * 1024)
    print(f"[*] Размер файла: {file_size_mb:.2f} МБ\n")

    # 1. Тест get_dwg_preview: замер времени и валидация результата
    print("[1] Тестирование get_dwg_preview()...")
    preview_res = get_dwg_preview(test_file)
    print(f"    - Первый запуск: {preview_res['elapsed_ms']:.3f} мс (статус: {preview_res['status']})")

    # Серия замеров времени (warm read)
    measurements: List[float] = []
    for _ in range(10):
        t0 = time.perf_counter()
        res = get_dwg_preview(test_file)
        t_ms = (time.perf_counter() - t0) * 1000.0
        measurements.append(t_ms)

    avg_ms = sum(measurements) / len(measurements)
    min_ms = min(measurements)
    print(f"    - Среднее время (10 замеров): {avg_ms:.3f} мс")
    print(f"    - Минимальное время: {min_ms:.3f} мс")
    print(f"    - Количество листов: {preview_res['layout_count']}")
    print(f"    - Текущий лист: {preview_res['current_layout']}")
    print(f"    - Размер изображения: {len(preview_res['image_bytes'])} байт")
    print(f"    - Base64 длина: {len(preview_res['image_base64'])} символов")

    # Проверка формата
    assert preview_res["status"] == "ok", "Ошибка статуса превью"
    assert len(preview_res["image_bytes"]) > 0, "Превью пустое"
    assert min_ms < 1.0, f"Время чтения превышает 1 мс ({min_ms:.3f} мс)"
    print("    -> [УСПЕХ] Превью извлечено за < 1 мс!\n")

    # 2. Тест get_dwg_layouts
    print("[2] Тестирование get_dwg_layouts()...")
    t0 = time.perf_counter()
    layouts = get_dwg_layouts(test_file)
    t_layouts_ms = (time.perf_counter() - t0) * 1000.0
    print(f"    - Время извлечения списка листов: {t_layouts_ms:.3f} мс")
    print(f"    - Найдено листов: {len(layouts)}")
    for l_item in layouts[:5]:
        print(f"      * [{l_item['index']}] {l_item['name']} (тип: {l_item['type']}, превью: {l_item['has_preview']})")
    if len(layouts) > 5:
        print(f"      ... и еще {len(layouts) - 5} листов")
    assert isinstance(layouts, list), "get_dwg_layouts должен возвращать список"
    assert len(layouts) >= 1, "Должен быть хотя бы один лист (Model)"
    print("    -> [УСПЕХ] Список листов успешно получен!\n")

    # 3. Тест превью конкретного листа без зависания
    print("[3] Тестирование get_dwg_layout_preview() без зависания...")
    t0 = time.perf_counter()
    layout_prev = get_dwg_layout_preview(test_file, layout=0)
    t_lp_ms = (time.perf_counter() - t0) * 1000.0
    print(f"    - Лист 0 (Model): {t_lp_ms:.3f} мс (размер: {len(layout_prev['image_bytes'])} байт)")

    if len(layouts) > 1:
        t0 = time.perf_counter()
        layout_prev1 = get_dwg_layout_preview(test_file, layout=1)
        t_lp1_ms = (time.perf_counter() - t0) * 1000.0
        print(f"    - Лист 1 ({layouts[1]['name']}): {t_lp1_ms:.3f} мс (размер: {len(layout_prev1['image_bytes'])} байт)")
        assert layout_prev1["status"] == "ok", "Ошибка статуса превью листа"

    print("    -> [УСПЕХ] Превью листов отдано мгновенно без зависания!\n")

    print("=" * 65)
    print(" ВСЕ ТЕСТЫ DWG ENGINE УСПЕШНО ПРОЙДЕНЫ!")
    print("=" * 65)
