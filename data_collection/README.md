# Book Dataset — Google Books API

Bộ dữ liệu sách tiếng Anh **tự thu thập** bằng Google Books API, dùng làm dữ liệu đầu vào cho hệ gợi ý sách ngữ nghĩa (semantic book recommender). Toàn bộ pipeline (5 mô hình IR + đánh giá) chạy trên dữ liệu tự thu thập này.

## Cấu trúc

```
data_collection/
├── books.csv               # Dataset chính: 12 cột, schema chuẩn cho pipeline
├── build_team_dataset.py   # raw/google_search.jsonl → books.csv
├── quality_report.py       # Báo cáo chất lượng theo đúng field pipeline dùng
├── requirements.txt
├── raw/
│   ├── google_search.jsonl # Dữ liệu thô crawl (14 trường/record)
│   └── test_queries.json   # 50 query đánh giá (để chạy quality_report)
└── crawler/                # Code thu thập (tài liệu phương pháp / tái lập)
    ├── crawl_google_search.py
    └── src/{config.py, data/collect.py}
```

## Dataset `books.csv`

12.688 sách, 12 cột. Hai cột quyết định chất lượng truy hồi: **`description`** (input của cả 5 mô hình — TF-IDF, BM25, BGE-small, Hybrid RRF, Cross-encoder rerank) và **`categories`** (ground-truth cho đánh giá). Các cột còn lại phục vụ hiển thị.

| Cột | Mô tả |
|---|---|
| `isbn13` | Khoá chính (int, đồng thời là id trong ChromaDB) |
| `isbn10`, `title`, `subtitle`, `authors` (phân tách `;`), `thumbnail` | Metadata hiển thị |
| `categories` | Phân loại theo taxonomy Google Books |
| `description` | Mô tả sách — văn bản chính cho NLP |
| `published_year`, `average_rating`, `num_pages`, `ratings_count` | Số liệu bổ sung |

### Thống kê

| Chỉ số | Giá trị |
|---|---|
| Số sách | **12.688** (raw 15.008 → lọc theo ISBN-13 hợp lệ) |
| `description` không rỗng | 100%, median ~118 từ |
| `categories` không rỗng | ~91% (taxonomy Google) |
| Độ phủ relevant / test-query | min ~1.360, median ~5.830 sách/query |
| Ngôn ngữ | 100% tiếng Anh |
| Trùng ISBN-13 / title rỗng | 0 / 0 |

## Phương pháp thu thập

- **Nguồn:** Google Books API — endpoint `volumes?q=...` (trả 40 sách/request kèm metadata đầy đủ).
- **Chiến lược:** phân trang theo **chủ đề / tác giả / từ khoá** (search-pagination) thay vì tra cứu từng sách → tiết kiệm quota ~15-30 lần. Các trục query: ~245 sub-genre/chủ đề + ~130 tác giả (`inauthor:`) + ~50 chủ đề free-text + 50 phrase từ bộ test query.
- **Lọc khi crawl:** chỉ giữ sách tiếng Anh, `description ≥ 20 từ` (sàn chất lượng cho NLP).
- **Chống trùng / resume:** dedup theo ISBN-13 (hoặc title+author), checkpoint theo trang, xoay vòng nhiều API key (mỗi Google Cloud project = 1.000 request/ngày).
- **Taxonomy:** `categories` giữ nguyên taxonomy Google Books → khớp trực tiếp với `relevant_categories` của bộ test query, không cần mapper.

## Hạn chế đã biết

- **~15% sách thô bị loại** do thiếu ISBN-13 hợp lệ (ISBN-13 là khoá chính + id ChromaDB nên bắt buộc). Còn 12.688 sách.
- **~28% sách** thuộc chủ đề ngoài 50 query test (Computers, Medical, Cooking...) — bình thường với corpus tổng quát, không ảnh hưởng tính hợp lệ của đánh giá.
- `average_rating` / `ratings_count` thưa (Google không phải lúc nào cũng có) — chỉ là field hiển thị, không ảnh hưởng điểm mô hình.

## Sử dụng trong pipeline

`books.csv` có sẵn 12 cột đúng định dạng pipeline yêu cầu. Pipeline tự làm sạch (strip HTML, dedup, lọc outlier + độ dài mô tả) trước khi build 5 mô hình + sinh báo cáo đánh giá — không cần xử lý thủ công trước.

## Tái lập

Cần file `.env` (ở thư mục gốc project) chứa `GOOGLE_BOOKS_API_KEY`; có thể thêm `GOOGLE_BOOKS_API_KEY_2..N` để xoay vòng (mỗi key thuộc một Google Cloud project khác nhau = thêm 1.000 request/ngày).

```bash
pip install -r requirements.txt
python crawler/crawl_google_search.py --test   # thử 1 query, 2 trang
python crawler/crawl_google_search.py          # crawl đầy đủ (resumable)
python build_team_dataset.py                   # raw → books.csv
python quality_report.py                        # in báo cáo chất lượng
```
