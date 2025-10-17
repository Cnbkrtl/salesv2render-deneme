# 📊 Sales Analytics V2

> Sentos e-ticaret platformu için gelişmiş satış analiz ve raporlama sistemi

[![Deployment Status](https://img.shields.io/badge/Status-Live-success)](https://sales-analytics-frontend.onrender.com)
[![Backend](https://img.shields.io/badge/Backend-Python%203.11-blue)](https://sales-analytics-backend-ctxn.onrender.com)
[![Frontend](https://img.shields.io/badge/Frontend-React%2018-61dafb)](https://reactjs.org/)
[![License](https://img.shields.io/badge/License-Private-red)]()

## 🚀 Canlı Sistem

- **Frontend:** https://sales-analytics-frontend.onrender.com
- **Backend API:** https://sales-analytics-backend-ctxn.onrender.com
- **Health Check:** https://sales-analytics-backend-ctxn.onrender.com/health

## ✨ Özellikler

### 📈 Gerçek Zamanlı Analizler
- **Satış Dashboard:** Günlük, haftalık, aylık satış trendleri
- **Ürün Performansı:** En çok satan ürünler, kar marjları
- **Müşteri Analizleri:** Müşteri segmentasyonu ve davranış analizi
- **Canlı Dashboard:** Anlık güncel veriler

### 🤖 Otomatik Veri Senkronizasyonu
- **Günlük Tam Senkronizasyon:** Her gece saat 02:00'da tüm veriler güncellenir
- **Canlı Güncellemeler:** Gün içinde her 10 dakikada bir anlık veriler çekilir
- **Arka Plan İşleme:** Senkronizasyon işlemleri kullanıcı deneyimini etkilemez
- **Manuel Kontrol:** İstediğiniz zaman manuel senkronizasyon başlatabilirsiniz

### 🎨 Modern Arayüz
- **Responsive Tasarım:** Mobil, tablet ve masaüstü uyumlu
- **Dark Mode:** Koyu tema desteği
- **Hızlı Navigasyon:** Kullanıcı dostu menü yapısı
- **Görsel Raporlar:** Grafik ve tablolarla zengin veri görselleştirme

### 🔗 Sentos API Entegrasyonu
- Ürün bilgileri ve görseller
- Sipariş ve satış verileri
- Müşteri bilgileri
- Stok durumu

## 🛠️ Teknolojiler

### Backend
- **Python 3.11** - Ana programlama dili
- **FastAPI** - Modern, hızlı web framework
- **SQLAlchemy** - ORM ve veritabanı yönetimi
- **PostgreSQL** - İlişkisel veritabanı
- **Uvicorn** - ASGI server

### Frontend
- **React 18** - UI framework
- **TypeScript** - Type-safe JavaScript
- **Vite** - Hızlı build tool
- **TailwindCSS** - Utility-first CSS framework
- **Axios** - HTTP client
- **date-fns** - Tarih işlemleri

### Deployment
- **Render.com** - Cloud hosting
- **GitHub Actions** - CI/CD (optional)

## 📦 Kurulum

### Gereksinimler
- Python 3.11+
- Node.js 18+
- PostgreSQL 14+

### Backend Kurulum

```bash
# Repository'yi clone edin
git clone https://github.com/Cnbkrtl/salesv2render-deneme.git
cd salesv2render-deneme

# Virtual environment oluşturun
python -m venv .venv
.venv\Scripts\activate  # Windows
source .venv/bin/activate  # macOS/Linux

# Bağımlılıkları yükleyin
pip install -r requirements.txt

# .env dosyası oluşturun
cp .env.example .env
# .env dosyasını düzenleyip API bilgilerinizi girin

# Veritabanını başlatın
python -c "from database.init_db import init_database; init_database()"

# Backend'i çalıştırın
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Backend http://localhost:8000 adresinde çalışacaktır.

### Frontend Kurulum

```bash
# Frontend dizinine gidin
cd frontend

# Bağımlılıkları yükleyin
npm install

# Development server'ı başlatın
npm run dev

# Production build için
npm run build
```

Frontend http://localhost:5173 adresinde çalışacaktır.

## ⚙️ Yapılandırma

### Backend Environment Variables (.env)

```bash
# Database
DATABASE_URL=postgresql://user:password@localhost:5432/sales_analytics

# Sentos API
SENTOS_API_URL=https://stildiva.sentos.com.tr/api
SENTOS_API_KEY=your_api_key_here
SENTOS_ACCOUNT=your_account_name

# Trendyol API (NEW - Direct Integration)
TRENDYOL_SUPPLIER_ID=your_supplier_id_here     # Required - Your Trendyol Supplier ID
TRENDYOL_API_SECRET=your_api_secret_here       # Required - Your Trendyol API Secret
TRENDYOL_API_KEY=your_api_key_here             # Optional - For future use
TRENDYOL_API_URL=https://apigw.trendyol.com    # Optional - Default value

# Application
ENVIRONMENT=development
FRONTEND_URL=http://localhost:5173

# Sync Schedule (optional)
FULL_SYNC_TIME=02:00  # Günlük tam senkronizasyon saati
LIVE_SYNC_INTERVAL=10  # Canlı senkronizasyon aralığı (dakika)
LIVE_SYNC_START_HOUR=8  # Canlı senkronizasyon başlangıç saati
LIVE_SYNC_END_HOUR=23  # Canlı senkronizasyon bitiş saati
```

**Trendyol Credentials Nasıl Alınır?**
1. Trendyol Seller Portal'a giriş yapın
2. Entegrasyonlar → API Yönetimi bölümüne gidin
3. Supplier ID ve API Secret bilgilerinizi kopyalayın
4. Bu bilgileri `.env` dosyasına ekleyin
5. Uygulamayı yeniden başlatın
6. Settings sayfasından "Bağlantıyı Test Et" butonuyla kontrol edin

### Frontend Environment Variables

Frontend için `.env` dosyası gerekmez, API URL'si `src/lib/api.ts` içinde yapılandırılır.

## 📖 Kullanım

### İlk Kurulum

1. **Ürünleri Senkronize Edin**
   - Settings sayfasına gidin
   - "Ürün Senkronizasyonu" kartında maksimum sayfa sayısını seçin
   - "Ürünleri Senkronize Et" butonuna tıklayın
   - İşlem birkaç dakika sürebilir

2. **Satış Verilerini Çekin**
   - Settings sayfasında "Satış Verilerini Çek" kartına gidin
   - Tarih aralığını seçin
   - "Satış Verilerini Çek" butonuna tıklayın

3. **Analizleri Görüntüleyin**
   - Dashboard sayfasından genel görünümü inceleyin
   - Analytics sayfasından detaylı raporlara erişin
   - Product Performance'dan ürün bazlı analizleri görün

### Otomatik Senkronizasyon

Sistem otomatik olarak aşağıdaki senkronizasyonları yapar:

- **Her Gece 02:00:** Tüm satış verilerini çeker (son 7 gün)
- **Gün İçinde:** 08:00-23:00 arası her 10 dakikada anlık verileri günceller

Manuel senkronizasyon için Settings sayfasındaki "Otomatik Senkronizasyon Durumu" kartını kullanabilirsiniz.

## 🎯 API Endpoints

### Health Check
```
GET /health
Response: {"status": "ok", "environment": "production"}
```

### Sync Control
```
GET  /api/sync/status          # Senkronizasyon durumunu görüntüle
POST /api/sync/trigger/full    # Tam senkronizasyon başlat
POST /api/sync/trigger/live    # Canlı senkronizasyon başlat
```

### Data Management
```
POST /api/data/sync-products?max_pages=50  # Ürünleri senkronize et
POST /api/data/fetch-sales                 # Satış verilerini çek
```

### Analytics
```
GET /api/analytics/summary?days=30         # Özet istatistikler
GET /api/analytics/sales-trend?days=30     # Satış trendi
GET /api/analytics/top-products?limit=10   # En çok satan ürünler
```

Tüm API dokümantasyonu: https://sales-analytics-backend-ctxn.onrender.com/docs

## 🚀 Deployment

### Render.com'a Deploy

Bu proje Render.com üzerinde çalışacak şekilde yapılandırılmıştır.

1. **GitHub Repository'yi Bağlayın**
   - Render.com'da yeni bir Blueprint oluşturun
   - GitHub repository'sini seçin
   - `render.yaml` otomatik olarak algılanacaktır

2. **Environment Variables Ekleyin**
   - Backend servisine gerekli environment variables'ları ekleyin
   - Özellikle `SENTOS_API_KEY` ve `DATABASE_URL` gereklidir

3. **Deploy Edin**
   - "Create" butonuna tıklayın
   - Render otomatik olarak 3 servisi oluşturacaktır:
     - Backend (Python)
     - Frontend (Static Site)
     - Database (PostgreSQL)

4. **Doğrulayın**
   - Backend health check: `https://your-backend.onrender.com/health`
   - Frontend: `https://your-frontend.onrender.com`

## 📊 Proje Yapısı

```
sales-analytics-v2/
├── app/                          # Backend application
│   ├── main.py                  # FastAPI app
│   ├── models.py                # Pydantic models
│   ├── api/                     # API endpoints
│   │   ├── sync.py             # Sync control
│   │   ├── data.py             # Data management
│   │   ├── analytics.py        # Analytics
│   │   └── ...
│   └── core/                    # Core settings
│       ├── config.py
│       └── enums.py
├── services/                     # Business logic
│   ├── scheduled_sync.py        # Background scheduler
│   ├── data_fetcher.py          # Sentos API client
│   └── ...
├── database/                     # Database layer
│   ├── models.py                # SQLAlchemy models
│   ├── connection.py
│   └── init_db.py
├── connectors/                   # External API connectors
│   └── sentos_client.py
├── frontend/                     # React frontend
│   ├── src/
│   │   ├── pages/               # Page components
│   │   ├── components/          # Reusable components
│   │   ├── lib/                 # Utilities
│   │   └── ...
│   ├── package.json
│   └── vite.config.ts
├── .python-version              # Python version (3.11)
├── requirements.txt             # Python dependencies
├── render.yaml                  # Render.com config
├── AI_CONTEXT.md               # AI agent context (for developers)
└── README.md                    # This file
```

## 🐛 Sorun Giderme

### Backend Çalışmıyor
```bash
# Log'ları kontrol edin
tail -f logs/app.log

# Health check yapın
curl http://localhost:8000/health

# Database bağlantısını test edin
python -c "from database.connection import get_db; next(get_db())"
```

### Frontend Build Hatası
```bash
# Node modules'ları temizleyin
cd frontend
rm -rf node_modules package-lock.json
npm install

# Cache'i temizleyin
npm run build -- --force
```

### Senkronizasyon Çalışmıyor
- Settings sayfasından sync status'u kontrol edin
- Backend log'larında "Scheduled sync service started" mesajını arayın
- Manuel senkronizasyon butonlarını deneyin
- Sentos API key'inin doğru olduğundan emin olun

### Rate Limit Hatası (HTTP 429)
- Sentos API günlük/saatlik limiti aşıldı
- Bekleyin ve daha sonra tekrar deneyin
- `max_pages` parametresini düşürün

## 🔒 Güvenlik

- **API Keys:** Asla git'e commit etmeyin, `.env` dosyasında saklayın
- **Database URL:** Production'da internal URL kullanın
- **CORS:** Sadece frontend domain'ine izin verin
- **Authentication:** Şu an yok (gelecek versiyon için planlanıyor)

## 📝 Changelog

### [2.0.0] - 2025-10-16

#### Added ✨
- Otomatik background senkronizasyon sistemi
- Günlük tam senkronizasyon (02:00 UTC)
- Canlı senkronizasyon (10 dakikalık aralıklar)
- Sync status UI (Settings sayfası)
- Manuel sync trigger butonları
- Background task desteği (timeout sorununu çözer)

#### Fixed 🐛
- Backend 60s timeout sorunu (background tasks ile çözüldü)
- Rate limiting problemi (health check optimize edildi)
- CORS configuration
- SPA routing issues

#### Changed 🔄
- Product sync artık background task olarak çalışıyor
- Health check artık Sentos API'yi çağırmıyor

### [1.0.0] - Initial Release
- Temel dashboard ve analiz özellikleri
- Sentos API entegrasyonu
- Manuel veri senkronizasyonu

## 🤝 Katkıda Bulunma

Bu proje şu an private repository'dir. Sorularınız için issue açabilir veya pull request gönderebilirsiniz.

## 📄 Lisans

Private - Tüm hakları saklıdır.

## 👥 İletişim

- **Repository:** https://github.com/Cnbkrtl/salesv2render-deneme
- **Issues:** https://github.com/Cnbkrtl/salesv2render-deneme/issues

---

**Not:** AI agent için detaylı teknik dokümantasyon `AI_CONTEXT.md` dosyasında bulunmaktadır.
