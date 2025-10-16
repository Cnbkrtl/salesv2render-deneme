# Sales Analytics v2 - Production Deployment

Modern satış analiz platformu. Sentos API entegrasyonu ile e-ticaret satış verilerini analiz eder.

## 🚀 Render.com Deployment

Bu proje Render.com üzerinde deploy edilmek üzere yapılandırılmıştır.

### Deployment Adımları:

1. **GitHub Repository'ye Push Edin**
   ```bash
   git init
   git add .
   git commit -m "Initial commit for Render deployment"
   git remote add origin <your-repo-url>
   git push -u origin main
   ```

2. **Render Dashboard'da Blueprint Deploy Edin**
   - Render.com'a giriş yapın
   - "New" > "Blueprint" seçin
   - GitHub repository'nizi bağlayın
   - `render.yml` otomatik algılanacak

3. **Environment Variables Ekleyin**
   
   Backend için:
   ```
   DATABASE_URL=<render-postgresql-url>
   SENTOS_API_URL=https://stildiva.sentos.com.tr/api
   SENTOS_API_KEY=<your-key>
   SENTOS_API_SECRET=<your-secret>
   SENTOS_COOKIE=<your-cookie>
   API_KEY=<your-secure-api-key>
   ```

   Frontend için:
   ```
   VITE_API_URL=https://sales-analytics-backend.onrender.com
   VITE_API_KEY=<same-as-backend-api-key>
   ```

4. **Deploy**
   - "Apply" butonuna tıklayın
   - Backend ve Frontend otomatik deploy edilecek

## 📁 Proje Yapısı

```
sales-analytics-v2/
├── app/                    # Backend API
│   ├── api/               # API endpoints
│   ├── core/              # Core config & enums
│   └── models.py          # Pydantic models
├── database/              # Database models & connection
├── services/              # Business logic
├── connectors/            # External API clients
├── frontend/              # React frontend
│   ├── src/
│   │   ├── components/   # UI components
│   │   ├── pages/        # Page components
│   │   └── lib/          # API client & utils
│   └── dist/             # Build output
└── render.yml            # Render deployment config
```

## 🔧 Teknolojiler

**Backend:**
- FastAPI
- SQLAlchemy
- PostgreSQL (Production) / SQLite (Development)
- Python 3.11+

**Frontend:**
- React 18
- TypeScript
- Vite
- TailwindCSS
- Recharts

## 🌐 Endpoints

- Backend API: `https://sales-analytics-backend.onrender.com`
- Frontend: `https://sales-analytics-frontend.onrender.com`
- API Docs: `https://sales-analytics-backend.onrender.com/docs`

## 🔐 Güvenlik

- API Key authentication
- CORS yapılandırması
- Environment variables ile hassas bilgilerin korunması

## 📊 Özellikler

- ✅ Satış verilerini Sentos API'den çekme
- ✅ Ürün senkronizasyonu
- ✅ Detaylı satış analizleri
- ✅ Marketplace bazlı raporlama
- ✅ Ürün performans analizi
- ✅ Kâr/zarar hesaplamaları
- ✅ Responsive dashboard

## 🛠️ Lokal Development

```bash
# Backend
python -m venv .venv
.venv\Scripts\activate  # Windows
source .venv/bin/activate  # Linux/Mac
pip install -r requirements.txt
uvicorn app.main:app --reload

# Frontend
cd frontend
npm install
npm run dev
```

## 📝 License

Private - All rights reserved
