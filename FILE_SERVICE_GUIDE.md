# Bazar Market - File Service Guide

**Production URL:** `https://files.bazarmarket.org`
**Local URL:** `http://localhost:6767`

A standalone FastAPI microservice for uploading and serving files (product images, banners, etc.). Files are content-addressed using SHA-256, so uploading the same file twice returns the same URL without wasting disk space.

---

## Authentication

Every request (except `/health`) requires the `X-API-TOKEN` header.

```
X-API-TOKEN: your-secret-token-here
```

The token is set via the `API_TOKEN` env var (or `FILE_API_TOKEN` in docker-compose).

Missing or wrong token returns:
```json
{ "success": false, "message": "Invalid or missing API Token" }
```
**Status:** `401`

---

## Endpoints

### Health Check

```
GET /health
```

No auth required. Returns:
```json
{ "success": true, "health": "ok", "version": "0.0.1" }
```

---

### Upload File

```
POST /files
Content-Type: multipart/form-data
X-API-TOKEN: your-token
```

**Form field:** `file` (the binary file)

#### cURL Example

```bash
curl -X POST https://files.bazarmarket.org/files \
  -H "X-API-TOKEN: your-token" \
  -F "file=@/path/to/image.jpg"
```

#### JavaScript / Fetch

```javascript
const form = new FormData();
form.append("file", fileInput.files[0]);

const res = await fetch("https://files.bazarmarket.org/files", {
  method: "POST",
  headers: { "X-API-TOKEN": "your-token" },
  body: form,
});
const data = await res.json();
// data.url → use this in product/banner/category image fields
```

#### Python / requests

```python
import requests

resp = requests.post(
    "https://files.bazarmarket.org/files",
    headers={"X-API-TOKEN": "your-token"},
    files={"file": open("image.jpg", "rb")},
)
data = resp.json()
print(data["url"])  # https://files.bazarmarket.org/files/abc123...
```

#### Response

```json
{
  "id": "fb5c286235ed6c721e380e92f8a05ea635bcc183a1efdff2297fe26d0c1fc45c",
  "url": "https://files.bazarmarket.org/files/fb5c286235ed6c721e380e92f8a05ea635bcc183a1efdff2297fe26d0c1fc45c",
  "filename": "cat.jpeg",
  "content_type": "image/jpeg",
  "size": 10244,
  "duplicate": false
}
```

| Field          | Description                                                |
| -------------- | ---------------------------------------------------------- |
| `id`           | SHA-256 hash of the file contents (64 hex chars)           |
| `url`          | Full URL to download this file — store this in your DB     |
| `filename`     | Original filename from the upload                          |
| `content_type` | MIME type (image/jpeg, image/png, application/pdf, etc.)   |
| `size`         | File size in bytes                                         |
| `duplicate`    | `true` if this exact file was already uploaded before       |

---

### Download / View File

```
GET /files/{file_id}
X-API-TOKEN: your-token
```

Returns the raw file with the correct `Content-Type` and `Content-Disposition` headers. Browsers will render images inline.

#### Example

```
GET https://files.bazarmarket.org/files/fb5c286235ed6c721e380e92f8a05ea635bcc183a1efdff2297fe26d0c1fc45c
```

Use the `url` from the upload response directly — it's the same thing.

---

## Usage with Django Admin API

When creating or updating products, banners, categories, etc., upload the image first, then pass the returned `url` as the image field.

#### Example: Create a product with an image

**Step 1 — Upload the image:**
```bash
curl -X POST https://files.bazarmarket.org/files \
  -H "X-API-TOKEN: your-token" \
  -F "file=@product-photo.jpg"
```
Response: `"url": "https://files.bazarmarket.org/files/abc123..."`

**Step 2 — Create the product using that URL:**
```bash
curl -X POST https://api.bazarmarket.org/admin-api/product/create \
  -H "Authorization: Bearer your-session-key" \
  -H "Content-Type: application/json" \
  -d '{
    "category_id": 1,
    "name_uz": "Olma",
    "unit": "kg",
    "price": "15000",
    "images": [
      { "image": "https://files.bazarmarket.org/files/abc123..." }
    ]
  }'
```

Same flow for banners (`image` field), categories (`image` field), etc.

---

## How It Works Internally

1. **Upload** — file is streamed to a temp file in 1 MiB chunks (never fully loaded into memory)
2. **Hash** — SHA-256 is computed during the stream
3. **Dedup** — if a file with that hash already exists, the temp file is discarded and `duplicate: true` is returned
4. **Store** — otherwise, the temp file is atomically renamed to `/data/files/{sha256_hash}`
5. **Metadata** — a sidecar `.json` file stores the original filename and content type
6. **Download** — uses the kernel's `sendfile()` syscall for zero-copy serving

---

## Running Locally

The file service runs as a separate container on port `6767`:

```bash
# With docker-compose (already configured)
docker compose up file-downloader

# Standalone
cd file_downloader
cp .env-example .env
# Set API_TOKEN in .env
uv run uvicorn main:app --host 0.0.0.0 --port 6767
```

### Environment Variables

| Variable      | Default                    | Description                        |
| ------------- | -------------------------- | ---------------------------------- |
| `API_TOKEN`   | *(none — all requests 401)* | Required. Secret token for auth    |
| `STORAGE_DIR` | `./data/files`             | Where uploaded blobs are stored    |

---

## Postman Setup

Add these to your Postman environment:

| Variable          | Value                              |
| ----------------- | ---------------------------------- |
| `file_service_url`| `https://files.bazarmarket.org`    |
| `file_api_token`  | your token                         |

**Upload request:**
- Method: `POST`
- URL: `{{file_service_url}}/files`
- Headers: `X-API-TOKEN: {{file_api_token}}`
- Body: `form-data` → Key: `file` (type: File) → select your file

**Download request:**
- Method: `GET`
- URL: `{{file_service_url}}/files/{{file_id}}`
- Headers: `X-API-TOKEN: {{file_api_token}}`
