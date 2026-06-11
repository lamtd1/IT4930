# 📖 Hướng Dẫn Cài Đặt & Chạy Backend (Dành cho người dùng mới)

Tài liệu này hướng dẫn chi tiết cách thiết lập môi trường và chạy ứng dụng **FastAPI Backend** cho dự án **Semantic Book Recommender** từ đầu.

---

## 🛠️ 1. Yêu Cầu Môi Trường (Prerequisites)

Trước khi bắt đầu, hãy đảm bảo máy tính của bạn đã cài đặt các công cụ sau:

1. **Python (Khuyến nghị: phiên bản `3.10` đến `3.12`)**
   * *Lưu ý:* Tránh dùng Python quá mới (như 3.13+) vì một số thư viện AI như `chromadb` hoặc `torch` chưa hỗ trợ đầy đủ.
   * Bạn có thể tải Python tại [python.org](https://www.python.org/downloads/). Nhớ tích chọn **"Add Python to PATH"** trong quá trình cài đặt.
2. **Git** (để clone dự án).
3. **Kết nối Internet ổn định**: Lần chạy đầu tiên sẽ cần tải các mô hình ngôn ngữ từ HuggingFace (khoảng ~500MB).

---

## 🚀 2. Các Bước Cài Đặt (Setup Steps)

Mở Terminal (Command Prompt hoặc PowerShell trên Windows) và di chuyển vào thư mục dự án:

### Bước 2.1: Di chuyển vào thư mục backend
```bash
cd backend
```

### Bước 2.2: Tạo môi trường ảo (Virtual Environment)
Môi trường ảo giúp các thư viện của dự án này không bị xung đột với các ứng dụng Python khác trên máy của bạn.
```bash
python -m venv .venv
```

### Bước 2.3: Kích hoạt môi trường ảo
* **Trên Windows (PowerShell):**
  ```powershell
  .venv\Scripts\Activate.ps1
  ```
* **Trên Windows (CMD):**
  ```cmd
  .venv\Scripts\activate.bat
  ```
* **Trên macOS / Linux:**
  ```bash
  source .venv/bin/activate
  ```

*Sau khi kích hoạt, bạn sẽ thấy chữ `(.venv)` xuất hiện ở đầu dòng lệnh.*

### Bước 2.4: Cài đặt các thư viện cần thiết (Dependencies)
Cài đặt toàn bộ thư viện web, khoa học dữ liệu và học máy:
```bash
pip install -r requirements.txt
```

### Bước 2.5: Tạo file cấu hình môi trường (.env)
Tạo bản sao của file cấu hình mẫu:
* **Trên Windows:**
  ```cmd
  copy .env.example .env
  ```
* **Trên macOS / Linux / Git Bash:**
  ```bash
  cp .env.example .env
  ```

---

## 💾 3. Khởi Tạo Chỉ Mục Học Máy (Build Indexes)

Người dùng mới sau khi clone dự án về sẽ **chưa có các file chỉ mục tìm kiếm** (TF-IDF, BM25, và cơ sở dữ liệu Vector ChromaDB). 

Bạn cần build các chỉ mục này một lần duy nhất trước khi chạy dự án.

### Lệnh chạy khởi tạo:
```bash
python scripts/init_models.py
```

* **Quá trình này làm gì?**
  1. Đọc dữ liệu từ file sách `AI/data/processed/books_with_emotions.csv`.
  2. Tạo chỉ mục TF-IDF và BM25 (lưu vào `AI/models/`).
  3. Sử dụng mô hình `BAAI/bge-small-en-v1.5` để chuyển đổi mô tả của 11,606 cuốn sách thành Vector và lưu vào cơ sở dữ liệu Vector `AI/data/chroma_db/`.
* **Thời gian hoàn thành:** Khoảng **5 - 15 phút** tùy thuộc vào tốc độ CPU/GPU và kết nối mạng của bạn (để tải mô hình).

---

## 🏃‍♂️ 4. Chạy Backend (Run Backend)

Sau khi khởi tạo dữ liệu xong, bạn chạy server bằng lệnh sau:

```bash
uvicorn main:app --reload --port 8000
```

* **`--reload`**: Tự động tải lại server khi bạn thay đổi code (rất tiện khi phát triển).
* **`--port 8000`**: Server sẽ chạy tại cổng `8000`.

### Địa chỉ truy cập:
* **Trang chủ / Kiểm tra hệ thống:** [http://127.0.0.1:8000/health](http://127.0.0.1:8000/health)
* **Tài liệu API tương tác (Swagger UI):** [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs) (Tại đây bạn có thể trực tiếp test thử các API `/search`, `/stats`, `/books/{isbn13}`).
* **Tài liệu dạng ReDoc:** [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)

---

## 📡 5. Tóm Tắt Các API Cung Cấp

Khi tích hợp với Frontend, bạn sẽ gọi các API sau:

| Phương thức | API Path | Mô tả | Request Body mẫu |
| :--- | :--- | :--- | :--- |
| **POST** | `/search` | Tìm kiếm sách bằng 1 trong 5 thuật toán. | `{"query": "a history book", "method": "hybrid", "top_k": 10}` |
| **POST** | `/search/compare` | Chạy nhiều thuật toán cùng lúc để so sánh. | `{"query": "love story", "methods": ["tfidf", "semantic"]}` |
| **GET** | `/books/{isbn13}` | Lấy chi tiết sách + điểm số của 7 loại cảm xúc. | *(Đường dẫn chứa ISBN13)* |
| **GET** | `/stats` | Lấy thống kê tổng quan (tổng số sách, phân bổ cảm xúc).| — |
| **GET** | `/evaluation` | Lấy kết quả đánh giá độ chính xác thực tế của AI. | — |
