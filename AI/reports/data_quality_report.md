# Data Quality Report — books_clean.csv

- Số cuốn (corpus cuối): **11,606**
- Số cột: **15** (12 gốc + 3 engineered)
- isbn13 duy nhất: **True**
- categories non-empty: **90.3%**
- description (số từ) min/median/max: **20 / 119 / 1048**
- published_year: **1813–2026**

## Taxonomy alignment (eval contract)
- Taxonomy test_queries: 51 category, có mặt trong corpus: **46**.
- Query có ≥1 sách relevant: **50/50**.
- Cuốn relevant với ≥1 query: **7,317** (63%).

## Cảnh báo trung thực
- **Độ phân giải eval THẤP**: median 4023 cuốn (~35% corpus) bị tính 'relevant' mỗi query (category-proxy lỏng + nhãn 'Fiction' phủ rộng). P@5 trông cao nhưng ít phân biệt model → chỉ tin chênh lệch tương đối, không tin số tuyệt đối.
- `average_rating`: ~86% giá trị bị điền median (Google hiếm trả rating). **Không dùng làm đặc trưng mô hình**, chỉ để hiển thị.
- `num_pages`: 'không rõ' (Google mã hóa bằng 0) đã được điền median.

## Bước làm sạch thêm (sau khi tự phản biện)
- Bỏ ~170 mô tả boilerplate public-domain (không phải mô tả thật).
- Khử trùng edition theo title+author (giữ bản mô tả dài nhất) — isbn13 unique không chặn được.

## 2 deviation so với cleaning của team (có lý do)
1. `num_pages == 0` được coi là 'không rõ' (→ NaN) trước khi lọc outlier → giữ ~2.273 cuốn hợp lệ.
2. Cận trên năm xuất bản = 2026 (năm hiện tại) thay vì 2024 → giữ 628 cuốn 2025–2026.