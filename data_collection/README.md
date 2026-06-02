# Dataset thu thập — Google Books API

Bộ dữ liệu sách **tự thu thập** bằng Google Books API, dùng để **thay thế dataset Kaggle** (`7k-books-with-metadata`) trong hệ gợi ý sách của nhóm. Mục tiêu: cả pipeline (5 mô hình IR + đánh giá) chạy trên dữ liệu nhóm tự crawl thay vì dataset có sẵn.

## Nội dung folder

```
data_collection/
├── books.csv               ← DATASET CHÍNH (12 cột, đúng schema pipeline) — drop-in thay Kaggle
├── build_team_dataset.py   ← raw/google_search.jsonl → books.csv (chạy lại được)
├── quality_report.py       ← báo cáo chất lượng (đo theo đúng field pipeline dùng)
├── requirements.txt
├── raw/
│   ├── google_search.jsonl ← dữ liệu thô crawl (provenance, 14 trường/record)
│   └── test_queries.json   ← 50 query đánh giá (bản sao để chạy quality_report)
└── crawler/                ← code crawl (tài liệu phương pháp / tái lập)
    ├── crawl_google_search.py
    └── src/{config.py, data/collect.py}
```

## Cách dùng (thay dataset trong repo nhóm)

1. Copy `books.csv` → `AI/data/raw/books.csv` trong repo nhóm.
2. Chạy `python run_pipeline.py` từ thư mục `AI/` — pipeline tự làm sạch (strip HTML, dedup, lọc outlier/độ dài) rồi build 5 model + sinh `reports/evaluation_final.json`.
3. Không cần sửa code pipeline: `books.csv` đã đúng 12 cột pipeline mong đợi.

## Phương pháp thu thập

- **Nguồn:** Google Books API — endpoint `volumes?q=...` (tìm kiếm, trả 40 sách/request kèm metadata đầy đủ).
- **Chiến lược:** phân trang theo **chủ đề / tác giả / từ khoá** (search-pagination) thay vì tra cứu từng sách → rẻ quota hơn ~15-30 lần. Các trục query: ~145 sub-genre + ~100 sub-genre/chủ đề mở rộng + ~130 tác giả (`inauthor:`) + ~50 chủ đề free-text + 50 phrase từ bộ test query.
- **Lọc khi crawl:** chỉ giữ sách tiếng Anh, `description ≥ 20 từ` (sàn chất lượng cho NLP).
- **Chống trùng / resume:** dedup theo ISBN-13 (hoặc title+author), checkpoint theo trang, xoay vòng nhiều API key (mỗi project Google = 1.000 request/ngày).
- **Taxonomy:** `categories` lấy nguyên taxonomy Google Books → **khớp trực tiếp** với `relevant_categories` của bộ test query (không cần mapper).

## Thống kê dataset (`books.csv`)

| Chỉ số | Giá trị |
|---|---|
| Số sách dùng được | **12.688** (≈2× Kaggle 6.385) |
| `description` không rỗng | 100%, median ~118 từ |
| `categories` không rỗng | ~91% (taxonomy Google, khớp eval) |
| Độ phủ relevant/test-query | min ~1.360, median ~5.830 sách/query |
| Ngôn ngữ | 100% tiếng Anh |
| Trùng ISBN-13 / title rỗng | 0 / 0 |

> Số liệu ứng với bản crawl 15.008 record (raw) → 12.688 sách dùng được sau khi lọc ISBN-13.
> Muốn mở rộng thêm: chạy lại crawler rồi `build_team_dataset.py` để cập nhật `books.csv`.

## Schema `books.csv` (12 cột — đúng pipeline)

`isbn13` (int, khoá chính + id ChromaDB), `isbn10`, `title`, `subtitle`, `authors` (phân tách `;`), `categories`, `thumbnail`, `description`, `published_year`, `average_rating`, `num_pages`, `ratings_count`.

Hai cột pipeline thực sự dùng cho chất lượng: **`description`** (input của cả 5 model: TF-IDF, BM25, BGE-small, Hybrid RRF, Cross-encoder rerank) và **`categories`** (ground-truth đánh giá). Các cột còn lại chỉ để hiển thị.

## Hạn chế đã biết (trung thực)

- **~15% sách thô bị loại** do thiếu ISBN-13 hợp lệ (pipeline dùng ISBN-13 làm khoá chính + id ChromaDB nên bắt buộc bỏ). Vẫn còn 12.688 sách, gần gấp đôi Kaggle.
- **~28% sách** thuộc chủ đề ngoài 50 query test (Computers, Medical, Cooking...) — bình thường với corpus tổng quát, không ảnh hưởng tính hợp lệ của eval.
- `average_rating` / `ratings_count` thưa (Google không phải lúc nào cũng có) — chỉ là field hiển thị, không ảnh hưởng điểm model.

## Tái lập crawl

Cần file `.env` ở thư mục gốc project với `GOOGLE_BOOKS_API_KEY` (có thể thêm `GOOGLE_BOOKS_API_KEY_2..N` để xoay vòng, mỗi key thuộc 1 Google Cloud project khác nhau = thêm 1.000 request/ngày). `crawler/` để nguyên cấu trúc `src/` như project gốc:

```
python crawler/crawl_google_search.py --test   # thử 1 query, 2 trang
python crawler/crawl_google_search.py          # crawl đầy đủ (resumable)
python build_team_dataset.py                   # raw → books.csv
python quality_report.py                       # in báo cáo chất lượng
```
