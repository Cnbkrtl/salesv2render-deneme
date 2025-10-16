# 📋 Render.com Deployment Checklist

## ✅ Pre-Deployment

- [x] Test ve development dosyaları temizlendi
- [x] `render.yaml` yapılandırması oluşturuldu
- [x] `requirements.txt` PostgreSQL driver eklendi
- [x] Database connection PostgreSQL desteği eklendi
- [x] `.env.example` dosyaları oluşturuldu
- [x] `.gitignore` güncellendi
- [x] README.md oluşturuldu
- [x] DEPLOYMENT.md guide hazırlandı

## 🔧 GitHub Setup

- [ ] GitHub repository oluştur
- [ ] Local repo'yu initialize et
- [ ] Remote repository ekle
- [ ] İlk commit ve push

```bash
git init
git add .
git commit -m "Initial commit - Render deployment ready"
git remote add origin https://github.com/YOUR-USERNAME/sales-analytics-v2.git
git branch -M main
git push -u origin main
```

## 🌐 Render.com Setup

- [ ] Render.com hesabı oluştur/giriş yap
- [ ] "New Blueprint" seçeneğini kullan
- [ ] GitHub repository bağla
- [ ] `render.yml` doğrula

## 🔐 Environment Variables

### Backend:
- [ ] `DATABASE_URL` (Otomatik - PostgreSQL Internal URL)
- [ ] `SENTOS_API_URL`
- [ ] `SENTOS_API_KEY`
- [ ] `SENTOS_API_SECRET`
- [ ] `SENTOS_COOKIE`
- [ ] `API_KEY` (Güçlü bir key oluştur!)
- [ ] `ALLOWED_ORIGINS=*`

### Frontend:
- [ ] `VITE_API_URL` (Backend URL)
- [ ] `VITE_API_KEY` (Backend ile aynı)

## 🚀 Deploy

- [ ] "Create Blueprint Instance" butonuna tıkla
- [ ] 3 service oluşturulduğunu doğrula:
  - [ ] sales-analytics-backend
  - [ ] sales-analytics-frontend
  - [ ] sales-analytics-db
- [ ] Deploy loglarını izle
- [ ] Hataları kontrol et

## ✅ Post-Deployment Verification

### Backend:
- [ ] Health endpoint test: `https://sales-analytics-backend.onrender.com/health`
- [ ] API docs erişilebilir: `https://sales-analytics-backend.onrender.com/docs`
- [ ] Database connection çalışıyor

### Frontend:
- [ ] Frontend açılıyor
- [ ] API bağlantısı çalışıyor
- [ ] Dashboard yükleniyor

### Functionality:
- [ ] Settings → Ürün Senkronizasyonu çalışıyor
- [ ] Ürünler database'e kaydediliyor
- [ ] Satış verisi çekme çalışıyor
- [ ] Analytics sayfası çalışıyor
- [ ] Product Performance sayfası çalışıyor

## 🔄 Optional - Custom Domain

- [ ] Render dashboard → Service → Settings
- [ ] Custom Domain ekle
- [ ] DNS ayarlarını güncelle
- [ ] SSL sertifikası otomatik oluşturulacak

## 📊 Monitoring

- [ ] Render dashboard'dan metrikler kontrol et
- [ ] Backend logs izle
- [ ] Database kullanımı kontrol et
- [ ] Free tier limitlerini takip et

## 🎯 Production Checklist

- [ ] API_KEY production-grade güçlü key ile değiştirildi
- [ ] CORS ayarları production domain'e göre daraltıldı
- [ ] Error handling test edildi
- [ ] Rate limiting eklenecekse planla
- [ ] Database backup stratejisi belirle
- [ ] Monitoring/alerting ayarla (opsiyonel)

## 📝 Documentation

- [ ] Takım üyelerine deployment URL'leri paylaş
- [ ] API key'i güvenli şekilde sakla
- [ ] Sentos credentials güvenli yerde tut
- [ ] Production ortam erişim bilgilerini dokümante et

## 🎉 Deploy Tamamlandı!

URLs:
- Frontend: `https://sales-analytics-frontend.onrender.com`
- Backend: `https://sales-analytics-backend.onrender.com`
- API Docs: `https://sales-analytics-backend.onrender.com/docs`

---

**Not:** Free tier'da service 15 dakika inactivity sonrası uyuyacaktır. İlk request 30-60 saniye sürebilir (cold start).
