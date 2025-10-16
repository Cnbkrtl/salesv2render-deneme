# 🚀 Render.com Deployment Guide

Sales Analytics v2 uygulamasını Render.com'da deploy etmek için detaylı adım adım kılavuz.

## 📋 Ön Gereksinimler

- GitHub hesabı
- Render.com hesabı (ücretsiz)
- Git kurulu
- Sentos API credentials

## 🔧 Adım 1: GitHub Repository Oluşturma

```bash
# Projeyi git ile başlat
cd sales-analytics-v2
git init

# Tüm dosyaları ekle
git add .

# İlk commit
git commit -m "Initial commit - Ready for Render deployment"

# GitHub'da yeni repo oluştur ve remote ekle
git remote add origin https://github.com/YOUR-USERNAME/sales-analytics-v2.git

# Push et
git branch -M main
git push -u origin main
```

## 🌐 Adım 2: Render.com'da Blueprint Deploy

1. **Render Dashboard'a Git**
   - https://dashboard.render.com

2. **New Blueprint Instance Oluştur**
   - "New" → "Blueprint" seçin
   - GitHub repository'nizi seçin
   - `render.yml` otomatik algılanacak

3. **Service Group Adı Ver**
   - Örnek: `sales-analytics-production`

## 🔐 Adım 3: Environment Variables Ayarlama

### Backend Service için:

Render dashboard'da backend service'i seçin ve Environment bölümünde şu değişkenleri ekleyin:

```bash
# Database (Otomatik oluşturulacak)
DATABASE_URL=<render-postgresql-internal-url>

# Sentos API
SENTOS_API_URL=https://stildiva.sentos.com.tr/api
SENTOS_API_KEY=7106b967-89b9-4dd0-9a56-49e3d16011d9
SENTOS_API_SECRET=O8eTRm0Isf20MwEikVLqqCOjrfbvSLGqy4QN2N1L
SENTOS_COOKIE=PHPSESSID=10mkos0o7bc363basth1951tu4; kullanici=ac589757aba860f71929633a43d2aec9

# Security (GÜÇ LÜ BİR KEY OLUŞTURUN!)
API_KEY=your-super-secret-api-key-change-this

# CORS
ALLOWED_ORIGINS=*
```

### Frontend Service için:

```bash
# Backend URL (backend deploy edildikten sonra URL'i buraya yazın)
VITE_API_URL=https://sales-analytics-backend.onrender.com

# API Key (backend ile AYNI olmalı)
VITE_API_KEY=your-super-secret-api-key-change-this
```

## 🗄️ Adım 4: PostgreSQL Database Bağlantısı

1. **Database Service Oluşturuldu**
   - Render otomatik olarak PostgreSQL instance oluşturacak

2. **Internal Database URL**
   - Backend service için Internal Database URL kullanın
   - Format: `postgresql://user:pass@hostname/dbname`

3. **DATABASE_URL Environment Variable**
   - Backend service'de DATABASE_URL otomatik set edilecek
   - Manuel ayar gerekmez

## 🚀 Adım 5: Deploy Başlat

1. **"Create Blueprint Instance" Tıklayın**
   - Render 3 service oluşturacak:
     - `sales-analytics-backend` (Web Service)
     - `sales-analytics-frontend` (Static Site)
     - `sales-analytics-db` (PostgreSQL)

2. **Deploy Sürecini İzleyin**
   - Her service'in log'larını görebilirsiniz
   - Backend: ~3-5 dakika
   - Frontend: ~2-3 dakika
   - Database: ~1-2 dakika

## ✅ Adım 6: Deploy Sonrası Kontroller

### Backend Kontrolü:

```bash
# Health check
curl https://sales-analytics-backend.onrender.com/health

# API docs
https://sales-analytics-backend.onrender.com/docs
```

### Frontend Kontrolü:

- Frontend URL'i açın
- Dashboard görünmeli
- Settings → Ürün Senkronizasyonu test edin

### Database Migration:

Render'da backend deploy edildikten sonra database tabloları otomatik oluşturulacak (SQLAlchemy `Base.metadata.create_all()` ile).

## 🔄 Güncellemeler

```bash
# Kod değişikliği yaptınız
git add .
git commit -m "Update: description"
git push

# Render otomatik re-deploy edecek (auto-deploy enabled)
```

## ⚠️ Önemli Notlar

1. **Free Tier Limitasyonları:**
   - Backend: 750 saat/ay (her ay sıfırlanır)
   - Database: 1 GB storage, shared CPU
   - Static site: Unlimited

2. **Cold Start:**
   - Free tier'da service 15 dk inactive kalırsa uyur
   - İlk request 30-60 saniye sürebilir

3. **Database Backup:**
   - Production için paid plan kullanın (automatic backups)
   - Free tier'da manual backup yapın

4. **SSL/HTTPS:**
   - Tüm Render URLs otomatik HTTPS'dir
   - Özel domain eklemek isterseniz: Dashboard → Custom Domain

## 🛠️ Troubleshooting

### Backend Deploy Hatası:

```bash
# Logs kontrol et
Render Dashboard → Backend Service → Logs

# Common issues:
# - requirements.txt eksik paket
# - Environment variables yanlış
# - Database bağlantı sorunu
```

### Frontend Build Hatası:

```bash
# package.json kontrol et
# Environment variables kontrol et
# Build command doğru mu: npm run build
```

### Database Bağlantı Hatası:

```bash
# DATABASE_URL doğru mu?
# PostgreSQL driver kurulu mu? (psycopg2-binary)
# Database service çalışıyor mu?
```

## 📞 Destek

- Render Docs: https://render.com/docs
- Render Community: https://community.render.com

## 🎉 Başarılı Deploy!

Uygulamanız şu URL'lerde canlı olacak:

- **Frontend:** `https://sales-analytics-frontend.onrender.com`
- **Backend API:** `https://sales-analytics-backend.onrender.com`
- **API Docs:** `https://sales-analytics-backend.onrender.com/docs`

Artık Sentos verilerinizi cloud'da analiz edebilirsiniz! 🚀
