# Result 003 - Part 2 (Разделы C, D: Модули rendering, Фронтенд app.js)
status: ok
branch/commit: ed362f3 (bridge) / 4f44ce1 (main)

## Что выполнено
- C. Show-Range 'app\rendering\dispatcher.py' 1 159: ok
- C. Show-Range 'app\rendering\engine_dwg_pdf.py' 1 109: ok
- D. Select-String паттернов DPI и API в app\frontend\app.js: ok
- D. Show-Range 'app\frontend\app.js' 2660-2715: ok
- D. Show-Range 'app\frontend\app.js' 4100-4220: ok
- D. Show-Range 'app\frontend\app.js' 4640-4730: ok
- D. Show-Range 'app\frontend\app.js' 4880-4935: ok

## Вывод команд

### C. Show-Range 'app\rendering\dispatcher.py' 1 159
```text
1: """Единый шлюз превью: расширение → чистый движок или карточка нативного открытия.
2: 
3: Фронт дергает один маршрут POST /api/preview {path} и по полю type решает:
4: встроить превью (pdf/sheet/word_html/photo/text) либо показать заглушку
5: с кнопкой «Открыть в программе» (native_app → POST /api/open-file).
6: 
7: Движки намеренно не импортируют server.py (нет циклов): пути к кэшу
8: передаются явно, по умолчанию — runtime/cache/rendering.
9: """
10: 
11: from __future__ import annotations
12: 
13: import hashlib
14: import threading
15: import time
16: from pathlib import Path
17: 
18: from . import GOLDEN_EXTENSIONS, NATIVE_APP_EXTENSIONS
19: from . import engine_dwg_pdf, engine_excel, engine_media, engine_word
20: 
21: RENDER_CACHE_NS = "rendering"
22: 
23: _RENDERING_TASKS: dict[str, float] = {}
24: _RENDERING_LOCK = threading.Lock()
25: 
26: 
27: def repo_runtime_dir() -> Path:
28:     """Найти runtime/ от корня репозитория (зеркалит логику server.py)."""
29:     p = Path(__file__).resolve()
30:     if "_internal" in p.parts:
31:         idx = p.parts.index("_internal")
32:         return Path(*p.parts[:idx]) / "runtime"
33:     # app/rendering/dispatcher.py -> parents[2] == корень репозитория
34:     return p.parents[2] / "runtime"
35: 
36: 
37: def cache_root(runtime_dir: Path | None = None) -> Path:
38:     base = Path(runtime_dir) if runtime_dir else repo_runtime_dir()
39:     root = base / "cache" / RENDER_CACHE_NS
40:     root.mkdir(parents=True, exist_ok=True)
41:     return root
42: 
43: 
44: def file_key(path: Path, tag: str) -> str:
45:     stat = path.stat()
46:     raw = f"{path.resolve()}|{stat.st_mtime_ns}|{stat.st_size}|{tag}"
47:     return hashlib.sha1(raw.encode("utf-8")).hexdigest()[:16]
48: 
49: 
50: def native_app_card(path: Path) -> dict:
51:     """Заглушка для специфических форматов: метаданные + команда открытия."""
52:     stat = path.stat()
53:     return {
54:         "type": "native_app",
55:         "name": path.name,
56:         "path": str(path),
57:         "extension": path.suffix.casefold().lstrip("."),
58:         "bytes": stat.st_size,
59:         "openAction": "/api/open-file",
60:         "openPayload": {"path": str(path), "action": "default"},
61:         "hint": "Формат открывается в нативной программе (кнопка «Открыть»)",
62:     }
63: 
64: 
65: def get_file_preview(path: str | Path, runtime_dir: Path | None = None,
66:                      **params) -> dict:
67:     """Главная точка входа. Всегда возвращает JSON-сериализуемый dict."""
68:     src = Path(str(path)).expanduser()
69:     if not src.exists():
70:         return {"type": "error", "error": f"Файл не найден: {src}"}
71:     if not src.is_file() or src.name.startswith("~$") or src.name.startswith(".~"):
72:         return {"type": "error", "error": f"Не превью-файл: {src.name}"}
73: 
74:     task_key = str(src.resolve()).casefold()
75:     with _RENDERING_LOCK:
76:         now = time.time()
77:         for k, started in list(_RENDERING_TASKS.items()):
78:             if now - started > 120.0:
79:                 _RENDERING_TASKS.pop(k, None)
80:         if task_key in _RENDERING_TASKS:
81:             return {
82:                 "type": "rendering",
83:                 "status": "rendering",
84:                 "name": src.name,
85:                 "path": str(src),
86:                 "message": "Документ уже рендерится, ожидайте готовности…",
87:             }
88:         _RENDERING_TASKS[task_key] = now
89: 
90:     try:
91:         ext = src.suffix.casefold()
92:         root = cache_root(runtime_dir)
93: 
94:         if ext in NATIVE_APP_EXTENSIONS:
95:             return native_app_card(src)
96:         if ext not in GOLDEN_EXTENSIONS:
97:             return {"type": "unsupported", "name": src.name, "extension": ext,
98:                     "fallback": native_app_card(src)}
99: 
100:         if ext == ".pdf":
101:             key = file_key(src, f"pdf-{engine_dwg_pdf.PREVIEW_DPI}")
102:             info = engine_dwg_pdf.render_first_page(src, root / "pdf")
103:             return {"type": "pdf", "name": src.name, "path": str(src),
104:                     "pages": info.get("pages", engine_dwg_pdf.page_count(src)),
105:                     "firstPage": info, "cacheKey": info.get("cacheKey", key)}
106: 
107:         if ext == ".dwg":
108:             # DWG→PDF готовит нативный DWG-конвейер; здесь — стандарт растра.
109:             pdf_hint = params.get("pdf_path")
110:             if pdf_hint and Path(pdf_hint).is_file():
111:                 info = engine_dwg_pdf.render_first_page(Path(pdf_hint), root / "dwg")
112:                 return {"type": "dwg", "name": src.name, "path": str(src),
113:                         "via": "dwg-pdf", "firstPage": info}
114:             return {"type": "dwg", "name": src.name, "path": str(src),
115:                     "via": "dwg-pdf-pipeline",
116:                     "hint": "DWG→PDF готовит нативный DWG конвейер, растр — engine_dwg_pdf (150 DPI PNG)"}
117: 
118:         if ext in (".xlsx", ".xlsm"):
119:             key = file_key(src, "excel-html")
120:             cache_dir = root / "excel" / "html" / key
121:             metas = engine_excel.ensure_workbook_rendered(src, cache_dir)
122:             sheets = [{"index": i, "name": m["name"], **m} for i, m in enumerate(metas)]
123:             return {"type": "workbook", "name": src.name, "path": str(src),
124:                     "sheets": sheets, "cacheKey": key}
125: 
126:         if ext == ".xls":
127:             key = file_key(src, "xls-html")
128:             cache_dir = root / "xls" / "html" / key
129:             metas = engine_excel.ensure_xls_rendered(src, cache_dir)
130:             sheets = [{"index": i, "name": m["name"], **m} for i, m in enumerate(metas)]
131:             return {"type": "workbook", "name": src.name, "path": str(src),
132:                     "engine": "xlrd", "sheets": sheets, "cacheKey": key}
133: 
134:         if ext == ".docx":
135:             key = file_key(src, "word-html")
136:             cache_dir = root / "word" / "html" / key
137:             meta = engine_word.ensure_docx_preview(src, cache_dir)
138:             return {"type": "word_html", "name": src.name, "path": str(src),
139:                     "cacheKey": key, **meta}
140: 
141:         if ext in (".jpg", ".jpeg", ".png", ".gif"):
142:             key = file_key(src, "photo")
143:             dst = root / "photo" / key / f"preview{ext if ext != '.jpeg' else '.jpg'}"
144:             info = engine_media.photo_preview(src, dst)
145:             return {"type": "photo", "name": src.name, "path": str(src),
146:                     "cacheKey": key, **info}
147: 
148:         if ext in (".txt", ".log"):
149:             key = file_key(src, "text")
150:             dst = root / "text" / key / "preview.html"
151:             info = engine_media.text_preview(src, dst)
152:             return {"type": "text", "name": src.name, "path": str(src),
153:                     "cacheKey": key, **info}
154: 
155:         return {"type": "unsupported", "name": src.name, "extension": ext,
156:                 "fallback": native_app_card(src)}
157:     finally:
158:         with _RENDERING_LOCK:
159:             _RENDERING_TASKS.pop(task_key, None)
```

### C. Show-Range 'app\rendering\engine_dwg_pdf.py' 1 109
```text
1: """Растр PDF/чертежей: единый стандарт 150 DPI PNG через PyMuPDF.
2: 
3: Первая страница рендерится сразу, остальные — лениво по запросу.
4: DWG→PDF конвертация остается в существующем DWG-конвейере (AutoCAD/демон);
5: этот движок стандартизирует финальную растровую стадию для PDF-файлов
6: и уже готовых DWG-производных PDF.
7: """
8: 
9: from __future__ import annotations
10: 
11: import hashlib
12: import os
13: import threading
14: import time
15: from pathlib import Path
16: 
17: PREVIEW_DPI = 150
18: 
19: _FITZ_LOCK = threading.Lock()
20: 
21: 
22: def cache_key(source: Path, dpi: int, page: int) -> str:
23:     stat = source.stat()
24:     raw = f"{source.resolve()}|{stat.st_mtime_ns}|{stat.st_size}|dpi{dpi}|p{page}"
25:     return hashlib.sha1(raw.encode("utf-8")).hexdigest()[:16]
26: 
27: 
28: def page_count(pdf_path: Path) -> int:
29:     """Число страниц PDF без полного рендера."""
30:     with _FITZ_LOCK:
31:         import fitz
32:         doc = fitz.open(str(pdf_path))
33:         try:
34:             return len(doc)
35:         finally:
36:             doc.close()
37: 
38: 
39: def render_page(pdf_path: Path, page_index: int, out_png: Path,
40:                 dpi: int = PREVIEW_DPI) -> dict:
41:     """Отрендерить одну страницу в PNG с атомарной записью под _FITZ_LOCK. Возвращает метаданные."""
42:     with _FITZ_LOCK:
43:         import fitz
44:         t0 = time.perf_counter()
45:         doc = fitz.open(str(pdf_path))
46:         try:
47:             pix = doc[page_index].get_pixmap(
48:                 matrix=fitz.Matrix(dpi / 72.0, dpi / 72.0), alpha=False)
49:             width, height = pix.width, pix.height
50:             out_png.parent.mkdir(parents=True, exist_ok=True)
51:             tmp_png = out_png.with_suffix(f".tmp.{os.getpid()}_{int(time.time()*1000)}.png")
52:             pix.save(str(tmp_png))
53:             if tmp_png.exists() and tmp_png.stat().st_size > 0:
54:                 os.replace(str(tmp_png), str(out_png))
55:         finally:
56:             doc.close()
57:         ms = (time.perf_counter() - t0) * 1000
58:     return {
59:         "path": str(out_png),
60:         "page": page_index,
61:         "dpi": dpi,
62:         "width": width,
63:         "height": height,
64:         "bytes": out_png.stat().st_size if out_png.exists() else 0,
65:         "renderMs": round(ms, 1),
66:     }
67: 
68: 
69: def render_first_page(pdf_path: Path, cache_dir: Path,
70:                       dpi: int = PREVIEW_DPI) -> dict:
71:     """Первая страница сразу (карточка/превью). Результат кэшируется."""
72:     key = cache_key(pdf_path, dpi, 0)
73:     out = cache_dir / key / "p1.png"
74:     if out.exists() and out.stat().st_size > 0:
75:         try:
76:             from PIL import Image
77:             with Image.open(out) as im:
78:                 width, height = im.size
79:         except Exception:
80:             width = height = 0
81:         return {
82:             "path": str(out), "page": 0, "dpi": dpi,
83:             "width": width, "height": height,
84:             "bytes": out.stat().st_size, "renderMs": 0.0,
85:             "cacheHit": True, "cacheKey": key,
86:         }
87:     info = render_page(pdf_path, 0, out, dpi)
88:     info["cacheHit"] = False
89:     info["cacheKey"] = key
90:     info["pages"] = page_count(pdf_path)
91:     return info
92: 
93: 
94: def render_page_lazy(pdf_path: Path, page_index: int, cache_dir: Path,
95:                      dpi: int = PREVIEW_DPI) -> dict:
96:     """Ленивый рендер страниц 2..N по запросу фронта."""
97:     key = cache_key(pdf_path, dpi, page_index)
98:     out = cache_dir / key / f"p{page_index + 1}.png"
99:     if out.exists() and out.stat().st_size > 0:
100:         info = {
101:             "path": str(out), "page": page_index, "dpi": dpi,
102:             "bytes": out.stat().st_size, "renderMs": 0.0,
103:             "cacheHit": True, "cacheKey": key,
104:         }
105:         return info
106:     info = render_page(pdf_path, page_index, out, dpi)
107:     info["cacheHit"] = False
108:     info["cacheKey"] = key
109:     return info
```

### D. Select-String по паттернам в app\frontend\app.js
```text
53: viewerDpi: Number(localStorage.getItem("launcher_viewer_dpi")) || 150,
122: viewToggleDpi: document.getElementById("viewToggleDpi"),
2659: // Карточка нативного формата: метаданные из ядра (/api/preview),
2671: const response = await fetch("/api/preview", {
2692: console.warn("[Launcher] /api/preview unavailable, generic native card:", error);
3416: function updatePagePosition(page, currentDpiInfo = null) {
3417: // Счётчик «Стр. N из M» слева вверху сцены: всегда видно лист, DPI и точные пиксели
3430: let dpiLabel = "";
3431: if (currentDpiInfo) {
3432: dpiLabel = ` · ${currentDpiInfo}`;
3434: const dpi = page?.dpi || state.viewerDpi || 150;
3436: dpiLabel = ` · ${dpi} DPI (${natW}×${natH} px)`;
3438: dpiLabel = ` · ${dpi} DPI`;
3445: els.pagePosition.textContent = `${pageText}${dpiLabel}${emptyTag}`.trim();
3490: function updateViewerDpiButton(loading = false) {
3491: if (!els.viewToggleDpi) return;
3492: const dpi = state.viewerDpi || 150;
3493: els.viewToggleDpi.textContent = loading ? `${dpi} DPI…` : `${dpi} DPI`;
3494: els.viewToggleDpi.classList.toggle("dpi-300", dpi === 300);
3495: els.viewToggleDpi.classList.toggle("dpi-150", dpi === 150);
3496: els.viewToggleDpi.classList.toggle("dpi-72", dpi === 72);
3497: els.viewToggleDpi.classList.toggle("loading", loading);
3498: const nextDpi = dpi === 72 ? 150 : (dpi === 150 ? 300 : 72);
3499: els.viewToggleDpi.title = `Разрешение окна: ${dpi} DPI. Нажмите для переключения на ${nextDpi} DPI (режимы 72 → 150 → 300)`;
3504: async function requestHighQualityPage(page, targetDpi = (state.viewerDpi || 150)) {
3510: const cacheKey = `${baseKey}@${targetDpi}`;
3516: updateViewerDpiButton(false);
3527: updateViewerDpiButton(true);
3531: const endpoint = isDwg ? "/api/dwg/model-page" : "/api/pdf/page";
3535: body: JSON.stringify({ file: sourceDocPath, page: pageNum, dpi: targetDpi }),
3544: dpi: payload.dpi || targetDpi,
3573: updateViewerDpiButton(false);
3896: const currentDpi = state.viewerDpi || 150;
3897: const highPage = state.highQualityPages.get(`${key}@${currentDpi}`);
3921: updateViewerDpiButton();
3924: requestHighQualityPage(page, currentDpi);
4204: const PDF_PREVIEW_DPI = 72;
4205: const PDF_QUALITY_DPI = 300;
4610: payload = { documents: wordDocs, totalPages: wordDocs.length, renderedPages: wordDocs.length, dpi: PDF_PREVIEW_DPI, errors: [] };
4642: payload = { documents: excelDocs, totalPages: excelDocs.length, renderedPages: excelDocs.length, dpi: PDF_PREVIEW_DPI, errors: [] };
4644: const endpoint = isDwg ? "/api/dwg/model-render" : "/api/pdf/render";
4647: dpi: PDF_PREVIEW_DPI,
4648: firstPageOnly: false,
4703: dpi: payload.dpi,
4892: ? "/api/dwg/model-render"
4893: : "/api/pdf/render";
4899: body: JSON.stringify({ files: itemsToFetch.map((file) => file.path), dpi: PDF_PREVIEW_DPI, firstPageOnly: false }),
4915: dpi: payload.dpi,
5072: if (els.viewToggleDpi) {
5073: els.viewToggleDpi.addEventListener("click", (e) => {
5075: const cur = state.viewerDpi || 150;
5076: state.viewerDpi = cur === 72 ? 150 : (cur === 150 ? 300 : 72);
5078: localStorage.setItem("launcher_viewer_dpi", String(state.viewerDpi));
5080: updateViewerDpiButton();
5083: requestHighQualityPage(currPage, state.viewerDpi);
5306: body: JSON.stringify({ file: state.activeTocPath, page: num, dpi: PDF_PREVIEW_DPI })
5326: body: JSON.stringify({ file: state.activeTocPath, page: num, dpi: PDF_PREVIEW_DPI })
5337: dpi: payload.dpi,
```

### D. Show-Range 'app\frontend\app.js' 2660 2715
```text
2660:   // открытие — через /api/open-file. При недоступности ядра — generic-карточка.
2661:   resetPdfPreview();
2662:   let card = {
2663:     type: "native-file",
2664:     name: node.name,
2665:     sourcePath: node.path,
2666:     documentPath: node.path,
2667:     sourceType: (node.extension || "").toUpperCase(),
2668:     message: "Файл открывается через ассоциации Windows или настроенную нативную программу.",
2669:   };
2670:   try {
2671:     const response = await fetch("/api/preview", {
2672:       method: "POST",
2673:       headers: { "Content-Type": "application/json" },
2674:       body: JSON.stringify({ file: node.path }),
2675:     });
2676:     const info = await response.json();
2677:     const native = response.ok && info
2678:       ? (info.type === "native_app" ? info : info.fallback || null)
2679:       : null;
2680:     if (native) {
2681:       const label = nativeTypeLabel(native.extension);
2682:       card = {
2683:         type: "native-file",
2684:         name: native.name || node.name,
2685:         sourcePath: node.path,
2686:         documentPath: node.path,
2687:         sourceType: String(native.extension || node.extension || "").toUpperCase(),
2688:         message: `${label} · ${formatFileSize(native.bytes)}. ${native.hint || "Нажмите кнопку, чтобы открыть."}`,
2689:       };
2690:     }
2691:   } catch (error) {
2692:     console.warn("[Launcher] /api/preview unavailable, generic native card:", error);
2693:   }
2694:   showPdfPage(card);
2695:   if (options.fullView) setViewerMode("full");
2696: }
2697: 
2698: function resetPdfPreview() {
2699:   stopDwgStatusPolling();
2700:   state._userNavigatedDwgPage = false;
2701:   state.view.userZoomed = false;
2702:   state.activePageKey = "";
2703:   state.activePageUrl = "";
2704:   state.renderedPages = [];
2705:   state.activeTxtPath = "";
2706:   state.wordDoc = null;
2707:   state.wordDocs = [];
2708:   state.wordDocIndex = 0;
2709:   if (els.txtViewer) els.txtViewer.hidden = true;
2710:   if (els.wordViewer) els.wordViewer.hidden = true;
2711:   if (els.mediaVideoViewer) {
2712:     try { els.mediaVideoViewer.pause(); } catch (_) {}
2713:     els.mediaVideoViewer.hidden = true;
2714:     els.mediaVideoViewer.removeAttribute("src");
2715:   }
```

### D. Show-Range 'app\frontend\app.js' 4100 4220
```text
4100:     requestAnimationFrame(() => requestAnimationFrame(fitPdfPage));
4101:   }
4102: }
4103: 
4104: function setViewerMode(mode) {
4105:   const wasFull = state.viewMode === "full";
4106:   state.viewMode = mode;
4107:   state.view.userZoomed = false;
4108:   els.shell.classList.toggle("full-view", mode === "full");
4109:   if (mode === "full") {
4110:     setStageActive(true);
4111:     if (els.viewerControls) els.viewerControls.hidden = false;
4112:   } else {
4113:     setStageActive(false);
4114:     if (els.pdfTocDrawer) els.pdfTocDrawer.hidden = true;
4115:     if (els.viewerControls) els.viewerControls.hidden = true;
4116:   }
4117:   updateObjectButtons();
4118:   const showControls = mode === "full" || els.pdfViewer?.classList.contains("stage-active");
4119:   if (els.viewerControls) els.viewerControls.hidden = !showControls;
4120:   const hasMultiplePages = (state.renderedPages?.length || 0) > 1 || (Number(state.renderedPages?.[0]?.totalPages) || 0) > 1;
4121:   if (els.viewPrevPage) els.viewPrevPage.hidden = !hasMultiplePages;
4122:   if (els.viewNextPage) els.viewNextPage.hidden = !hasMultiplePages;
4123: 
4124:   // Возврат из полноэкранного (Окно 3 -> Окно 2 -> Окно 1):
4125:   // 1. В Окне 1 (дереве) гарантированно подсвечивается и выбирается этот файл!
4126:   // 2. В Окне 2 (ленте) гарантированно центрируется и подсвечивается миниатюра текущего листа!
4127:   if (wasFull && mode !== "full") {
4128:     state.activeNavZone = "thumbs";
4129:     const activePage = state.renderedPages?.find((p) => pageKey(p) === state.activePageKey) || state.renderedPages?.[0];
4130:     const docPath = (activePage && (thumbPathForPage(activePage) || activePage.documentPath || activePage.sourcePath)) || state.revealedPath || "";
4131:     if (docPath) {
4132:       revealPathInTree(docPath, { updateSelection: true, skipScroll: false });
4133:     }
4134:     if (state.activePageKey) {
4135:       updateActivePdfThumb();
4136:       requestAnimationFrame(() => {
4137:         requestAnimationFrame(() => {
4138:           try {
4139:             const thumbEl = els.pdfThumbs?.querySelector(`.pdf-thumb[data-page-key="${CSS.escape(state.activePageKey)}"]`);
4140:             if (thumbEl) {
4141:               thumbEl.focus();
4142:               thumbEl.scrollIntoView({ behavior: "smooth", block: "center" });
4143:             }
4144:           } catch (e) {}
4145:         });
4146:       });
4147:     }
4148:   } else if (state.revealedPath) {
4149:     revealPathInTree(state.revealedPath);
4150:   }
4151:   requestAnimationFrame(() => requestAnimationFrame(() => {
4152:     fitPdfPage();
4153:   }));
4154: }
4155: 
4156: function chunkPreviewItems(items) {
4157:   const chunks = [];
4158:   let currentChunk = [];
4159:   let currentType = null;
4160:   const maxForType = (type) => (type === "DWG_MODEL" ? 1 : type === "WORD" ? 1 : type === "EXCEL" ? 1 : 10);
4161: 
4162:   for (const item of items) {
4163:     const type = item.previewType || "PDF";
4164:     if (currentChunk.length > 0 && (currentType !== type || currentChunk.length >= maxForType(type))) {
4165:       chunks.push(currentChunk);
4166:       currentChunk = [];
4167:     }
4168:     currentType = type;
4169:     currentChunk.push(item);
4170:   }
4171:   if (currentChunk.length > 0) {
4172:     chunks.push(currentChunk);
4173:   }
4174:   return chunks;
4175: }
4176: 
4177: const PDF_RENDER_CONCURRENCY = 3;
4178: // DWG рендерится через общий AutoCAD COM: параллельные запуски дерутся
4179: // за CAD-процесс, поэтому пачки DWG_MODEL идут строго по одной, а PDF —
4180: // по-прежнему до трёх параллельно. Семафор общий на все показы: эпохи
4181: // и отмена проверяются внутри renderBatch, зависший слот отдаётся в finally.
4182: const DWG_RENDER_CONCURRENCY = 1;
4183: let dwgActiveCount = 0;
4184: const dwgWaiters = [];
4185: function acquireDwgSlot() {
4186:   if (dwgActiveCount < DWG_RENDER_CONCURRENCY) {
4187:     dwgActiveCount += 1;
4188:     return Promise.resolve();
4189:   }
4190:   return new Promise((resolve) => dwgWaiters.push(resolve));
4191: }
4192: function releaseDwgSlot() {
4193:   dwgActiveCount = Math.max(0, dwgActiveCount - 1);
4194:   const next = dwgWaiters.shift();
4195:   if (next) {
4196:     dwgActiveCount += 1;
4197:     next();
4198:   }
4199: }
4200: const PDF_FETCH_TIMEOUT_MS = 300000;
4201: // 15 секунд молотили /api/objects/diff каждые 15 с (живое облако H:, полный
4202: // скан на каждое изменение) и могли перезагружать дерево под руками. 10 минут.
4203: const DIFF_POLL_INTERVAL_MS = 600000;
4204: const PDF_PREVIEW_DPI = 72;
4205: const PDF_QUALITY_DPI = 300;
4206: 
4207: function formatBytes(bytes) {
4208:   if (!bytes || bytes <= 0) return "";
4209:   if (bytes < 1024) return `${bytes} Б`;
4210:   if (bytes < 1024 * 1024) return `${Math.round(bytes / 1024)} КБ`;
4211:   return `${(bytes / (1024 * 1024)).toFixed(1)} МБ`;
4212: }
4213: 
4214: function formatEta(ms) {
4215:   if (!ms || ms < 0) return "";
4216:   const sec = Math.ceil(ms / 1000);
4217:   if (sec < 60) return `~${sec} сек.`;
4218:   const min = Math.ceil(sec / 60);
4219:   return `~${min} мин.`;
4220: }
```

### D. Show-Range 'app\frontend\app.js' 4640 4730
```text
4640:           clearTimeout(timeoutId);
4641:           if (state.progressCancelled) return;
4642:           payload = { documents: excelDocs, totalPages: excelDocs.length, renderedPages: excelDocs.length, dpi: PDF_PREVIEW_DPI, errors: [] };
4643:         } else {
4644:           const endpoint = isDwg ? "/api/dwg/model-render" : "/api/pdf/render";
4645:           const requestBody = {
4646:             files: itemsToFetch.map((file) => file.path),
4647:             dpi: PDF_PREVIEW_DPI,
4648:             firstPageOnly: false,
4649:             force: Boolean(options?.force),
4650:           };
4651: 
4652:           const response = await fetch(endpoint, {
4653:             method: "POST",
4654:             headers: { "Content-Type": "application/json" },
4655:             body: JSON.stringify(requestBody),
4656:             signal: controller.signal,
4657:           });
4658:           clearTimeout(timeoutId);
4659: 
4660:           if (state.progressCancelled) return;
4661:           payload = await response.json();
4662:           const _hits = (payload.documents || []).filter((d) => d.cacheHit).length;
4663:           beaconPerf("display-batch", performance.now() - _batchT0, `files=${itemsToFetch.length} hits=${_hits}/${itemsToFetch.length}`);
4664:           if (!response.ok) {
4665:             if (state.progressCancelled) return;
4666:             allErrors.push({
4667:               document: itemsToFetch.map((f) => f.name).join(", "),
4668:               error: payload.error || `HTTP ${response.status}`,
4669:             });
4670:             const errCards = itemsToFetch.map((item) => ({
4671:               type: "missing-preview",
4672:               name: item?.name || "Документ",
4673:               documentPath: item?.path || "",
4674:               sourcePath: item?.path || "",
4675:               sourceType: item?.extension || "PDF",
4676:               message: payload.error || "Ошибка превью. Откройте файл через кнопку «Открыть».",
4677:             }));
4678:             pageGroups[batchIndex] = errCards;
4679:             await flushReadyBatches();
4680:             batchDone = true;
4681:             return;
4682:           }
4683:         }
4684: 
4685:         if (state.progressCancelled || state.renderEpoch !== myEpoch) return;
4686:         totalPages += payload.totalPages || 0;
4687:         renderedPages += payload.renderedPages || 0;
4688:         allErrors.push(...(payload.errors || []));
4689: 
4690:         const batchPages = (payload.documents || []).flatMap((document) => {
4691:           const matchedItem = itemsToFetch.find((f) => f.path === (document.sourcePath || document.path))
4692:             || itemsToFetch.find((f) => f.name === (document.sourceName || document.name))
4693:             || itemsToFetch[0];
4694:           const realSourcePath = document.sourcePath || matchedItem?.previewFor?.path || matchedItem?.path || document.path;
4695:           const realName = matchedItem?.previewFor ? matchedItem.previewFor.name : (document.sourceName || document.name);
4696:           return (document.items || []).map((page) => ({
4697:             ...page,
4698:             name: `${realName} · стр. ${page.page}`,
4699:             documentPath: document.path,
4700:             sourcePath: realSourcePath,
4701:             sourceName: realName,
4702:             sourceType: document.sourceType || matchedItem?.extension || "",
4703:             dpi: payload.dpi,
4704:             cacheHit: document.cacheHit,
4705:             previewFor: matchedItem?.previewFor || (realSourcePath ? { path: realSourcePath, name: realName } : null),
4706:             previewType: matchedItem?.previewType || document.sourceType || "",
4707:             totalPages: document.pages || 1,
4708:             rawDoc: document,
4709:           }));
4710:         });
4711:         pageGroups[batchIndex] = batchPages;
4712:         await flushReadyBatches();
4713:         batchDone = true;
4714:         payload.documents?.forEach((doc) => {
4715:           if (doc.sourceType === "DWG" || (doc.items && doc.items.some((it) => it.url && it.url.includes("/dwg/")))) {
4716:             const hasPending = (doc.cacheHitPages || 0) < (doc.pages || 0);
4717:             if (hasPending || !doc.isComplete) {
4718:               startDwgStatusPolling(doc.path || doc.sourcePath, doc.pages, myEpoch);
4719:             }
4720:           }
4721:         });
4722:       } catch (error) {
4723:         if (state.progressCancelled || state.renderEpoch !== myEpoch) return;
4724:         const isTimeout = error?.name === "AbortError";
4725:         if (isTimeout && attempt < 2) continue;
4726:         allErrors.push({
4727:           document: itemsToFetch.map((f) => f.name).join(", "),
4728:           error: isTimeout ? "timeout" : String(error?.message || error),
4729:         });
4730:         const errCards = itemsToFetch.map((item) => {
```

### D. Show-Range 'app\frontend\app.js' 4880 4935
```text
4880:     let batchDone = false;
4881:     while (!batchDone && attempt < 2) {
4882:       attempt += 1;
4883:       if (attempt === 1 && isDwg && totalDwgFiles > 0 && !state.progressCancelled) {
4884:         els.progressDetail.textContent = `Модель ${completedDwgFiles + 1} из ${totalDwgFiles}: ${itemsToFetch[0]?.name || "чертёж"} — рендерится…`;
4885:       }
4886:     try {
4887:       controller = new AbortController();
4888:       state.operationControllers.push(controller);
4889:       const timeoutId = setTimeout(() => controller.abort(), batchTimeout);
4890: 
4891:       const endpoint = isDwg
4892:         ? "/api/dwg/model-render"
4893:         : "/api/pdf/render";
4894: 
4895:       const _batchT0 = performance.now();
4896:       const response = await fetch(endpoint, {
4897:         method: "POST",
4898:         headers: { "Content-Type": "application/json" },
4899:         body: JSON.stringify({ files: itemsToFetch.map((file) => file.path), dpi: PDF_PREVIEW_DPI, firstPageOnly: false }),
4900:         signal: controller.signal,
4901:       });
4902:       clearTimeout(timeoutId);
4903: 
4904:       if (state.progressCancelled) return;
4905:       const payload = await response.json();
4906:       const _hits = (payload.documents || []).filter((d) => d.cacheHit).length;
4907:       beaconPerf("display-batch", performance.now() - _batchT0, `files=${itemsToFetch.length} hits=${_hits}/${itemsToFetch.length}`);
4908:       if (response.ok) {
4909:         const batchPages = payload.documents.flatMap((document) => {
4910:           const matchedItem = itemsToFetch.find((f) => f.path === document.path) || itemsToFetch[0];
4911:           return document.items.map((page) => ({
4912:             ...page,
4913:             name: `${matchedItem?.previewFor ? matchedItem.previewFor.name : document.name} · стр. ${page.page}`,
4914:             documentPath: document.path,
4915:             dpi: payload.dpi,
4916:             cacheHit: document.cacheHit,
4917:             previewFor: matchedItem?.previewFor || null,
4918:             previewType: matchedItem?.previewType || "",
4919:           }));
4920:         });
4921:         if (state.renderEpoch !== myEpoch) return;
4922:         await appendPagesToViewer(batchPages, null, myEpoch);
4923:         batchDone = true;
4924:         payload.documents?.forEach((doc) => {
4925:           if (doc.sourceType === "DWG" || (doc.items && doc.items.some((it) => it.url && it.url.includes("/dwg/")))) {
4926:             const hasPending = (doc.cacheHitPages || 0) < (doc.pages || 0);
4927:             if (hasPending || !doc.isComplete) {
4928:               startDwgStatusPolling(doc.path || doc.sourcePath, doc.pages, myEpoch);
4929:             }
4930:           }
4931:         });
4932:       } else {
4933:         const errCards = itemsToFetch.map((item) => ({
4934:           type: "missing-preview",
4935:           name: item?.name || "Документ",
```