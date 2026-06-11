### 1. semantic (BGE-small + ChromaDB)
- Được triển khai trong file dense_retriever.py.

- Mô hình sử dụng: Bi-Encoder BAAI/bge-small-en-v1.5 từ thư viện sentence_transformers.
- Cơ chế:
  - Khi bạn chạy lệnh khởi tạo python scripts/init_models.py, backend sử dụng mô hình BGE-small chạy local để chuyển đổi toàn bộ mô tả của 11,606 cuốn sách thành các vector embeddings.
  - Các vector này được lưu trữ cục bộ vào cơ sở dữ liệu Vector ChromaDB dạng file trên đĩa cứng (chromadb.PersistentClient).
  - Khi nhận yêu cầu tìm kiếm, backend sẽ chuyển đổi (encode) câu truy vấn của người dùng thành vector, sau đó thực hiện truy vấn trong cơ sở dữ liệu ChromaDB cục bộ bằng thuật toán đo khoảng cách Cosine (cosine similarity) để tìm ra những cuốn sách gần nhất.

### 2. hybrid (Hybrid RRF - Reciprocal Rank Fusion)
- Được triển khai trong file hybrid_rrf_retriever.py.
- Mô hình sử dụng: Kết hợp cả BM25 (lexical - từ khóa) và BGE-small (semantic - ngữ nghĩa).
- Cơ chế:
  - Phương pháp này thực tế không chạy thêm mô hình AI nào mới mà hoạt động như một bộ kết hợp (Fusion).
  - Khi nhận câu truy vấn, nó sẽ gọi song song hai phương pháp: tìm kiếm từ khóa (BM25Retriever) và tìm kiếm ngữ nghĩa (DenseRetriever) để lấy ra hai danh sách ứng viên (mặc định lấy 50 cuốn mỗi bên).
  - Sau đó, nó áp dụng thuật toán toán học Reciprocal Rank Fusion (RRF) để tính toán lại điểm số tổng hợp dựa trên thứ hạng (rank) của cuốn sách trong cả hai danh sách: $$\text{RRF Score} = \sum_{m \in M} \frac{1}{k + r_m(d)}$$ (Trong đó $r_m(d)$ là thứ hạng của sách $d$ trong thuật toán $m$, $k$ là hằng số làm mượt, mặc định bằng 60).
  - Sách có điểm RRF cao nhất sẽ được sắp xếp và trả về.

### 3. reranking (BGE + Reranking)
- Được triển khai trong file rerank_retriever.py.
- Mô hình sử dụng: Tải thêm mô hình Cross-Encoder BAAI/bge-reranker-base chạy local qua sentence_transformers.
- Cơ chế (Mô hình tìm kiếm 2 giai đoạn - Two-stage Retrieval):
  - Giai đoạn 1 (Dense Recall): Dùng DenseRetriever để lấy nhanh ra một tập hợp ứng viên tiềm năng (mặc định là 20 cuốn sách tốt nhất) từ cơ sở dữ liệu vector ChromaDB. Bước này giúp loại bỏ bớt các sách không liên quan để tiết kiệm tài nguyên.
  - Giai đoạn 2 (Reranking): Với 20 cuốn sách lấy được, backend sử dụng mô hình Cross-Encoder để phân tích sâu đồng thời cả cặp (Query, Book Description). Do mô hình Cross-Encoder phân tích mối quan hệ ngữ nghĩa sâu sắc giữa câu hỏi và tài liệu tốt hơn Bi-Encoder, nó sẽ tính toán lại điểm số tương đồng thực tế chính xác hơn, sau đó sắp xếp lại (rerank) thứ tự của 20 cuốn sách này trước khi trả kết quả cuối cùng cho người dùng.