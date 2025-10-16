# 🤖 AI Agent Context & Project State

> **Last Updated:** October 16, 2025  
> **Project Status:** ✅ Deployed and Running  
> **Current Phase:** Feature Enhancement (Automated Sync System)

---

## 📋 Quick Summary

This is a **Sales Analytics Dashboard** for Sentos e-commerce platform. The system automatically syncs product and sales data from Sentos API and provides real-time analytics.

**Tech Stack:**
- **Backend:** Python 3.11, FastAPI, SQLAlchemy, PostgreSQL
- **Frontend:** React 18, TypeScript, Vite, TailwindCSS
- **Deployment:** Render.com (separate backend + frontend services)
- **Repository:** https://github.com/Cnbkrtl/salesv2render-deneme

---

## 🎯 Current State (Where We Are)

### ✅ Completed Features

1. **Full Deployment on Render.com**
   - Backend: https://sales-analytics-backend-ctxn.onrender.com
   - Frontend: https://sales-analytics-frontend.onrender.com
   - Database: PostgreSQL (Render managed)
   - Status: All services running successfully

2. **Automated Background Sync System** ⭐ NEW
   - **Daily Full Sync:** Every day at 02:00 UTC (fetches all sales data)
   - **Live Sync:** Every 10 minutes between 08:00-23:00 UTC (fetches recent updates)
   - **Background Tasks:** Long-running sync operations converted to background tasks (fixes 60s timeout issue)
   - **Scheduler Service:** `services/scheduled_sync.py` handles automated syncs

3. **Sync Status UI** ⭐ JUST COMPLETED
   - Settings page now shows real-time sync status
   - Displays last full sync and last live sync times
   - Manual trigger buttons for full/live sync
   - Auto-refreshes every 30 seconds
   - Files modified:
     - `frontend/src/lib/api-service.ts` - Added sync API functions
     - `frontend/src/pages/Settings.tsx` - Added sync status card

4. **API Endpoints**
   - ✅ `/health` - Health check (no Sentos API calls to avoid rate limits)
   - ✅ `/api/data/sync-products` - Manual product sync (background task)
   - ✅ `/api/data/fetch-sales` - Manual sales data fetch
   - ✅ `/api/sync/status` - Get sync system status (NEW)
   - ✅ `/api/sync/trigger/full` - Trigger full sync manually (NEW)
   - ✅ `/api/sync/trigger/live` - Trigger live sync manually (NEW)
   - ✅ `/api/analytics/*` - Various analytics endpoints
   - ✅ `/api/product-performance/*` - Product performance endpoints

5. **Fixed Issues**
   - ✅ Python 3.13 compatibility (forced 3.11 via `.python-version`)
   - ✅ Missing frontend dependencies (axios, date-fns)
   - ✅ TypeScript configuration
   - ✅ CORS issues (configured specific origins)
   - ✅ Rate limiting (removed Sentos API test from health check)
   - ✅ SPA routing (`_redirects` file + render.yaml routes)
   - ✅ Backend timeout during sync (converted to background tasks)
   - ✅ Logs directory missing (added mkdir with error handling)

---

## 🚧 Known Issues & TODO

### ⚠️ Pending Verification

1. **Scheduler Startup**
   - **Issue:** No log message "✅ Scheduled sync service started" seen yet
   - **Location:** `app/main.py` startup event
   - **Action Needed:** Check backend logs on Render to verify scheduler is running
   - **Possible Fix:** If not running, check import errors or add explicit logging

2. **Original Product Sync Button**
   - **Issue:** User originally reported "butona basınca hiç bir şey olmuyor" (button does nothing)
   - **Current State:** Now returns immediately with background task
   - **Action Needed:** Verify UI feedback works properly
   - **Possible Fix:** Add loading states, progress indicators, or status polling

### 🔮 Future Enhancements

- [ ] Add progress indicators for background sync operations
- [ ] Email notifications when sync fails
- [ ] Sync history log (last 10 syncs with status)
- [ ] Better error handling and retry logic
- [ ] Dashboard widget showing sync status
- [ ] Webhook support for real-time updates

---

## 📁 Important Files & Their Purpose

### Backend Core
```
app/
├── main.py                 # FastAPI app, CORS, startup/shutdown events
├── models.py              # Pydantic models
├── api/
│   ├── sync.py           # 🆕 Sync control endpoints (status, triggers)
│   ├── data.py           # Data sync endpoints (background tasks)
│   ├── analytics.py      # Analytics endpoints
│   ├── health.py         # Health check (config only, no API calls)
│   └── product_performance.py
└── core/
    ├── config.py         # Environment variables, settings
    └── enums.py          # Enums for time ranges, etc.

services/
├── scheduled_sync.py     # 🆕 Background scheduler (daily + live sync)
├── data_fetcher.py       # Sentos API data fetching logic
├── analytics.py          # Analytics calculations
├── product_performance.py
└── smart_fallback.py     # Fallback logic for missing data

database/
├── connection.py         # Database connection management
├── models.py            # SQLAlchemy ORM models
└── init_db.py           # Database initialization

connectors/
└── sentos_client.py     # Sentos API client wrapper
```

### Frontend Core
```
frontend/src/
├── main.tsx             # React entry point
├── App.tsx              # Main app component with routing
├── pages/
│   ├── Settings.tsx     # 🆕 Settings page with sync status card
│   ├── Dashboard.tsx    # Main dashboard
│   ├── Analytics.tsx    # Analytics page
│   ├── LiveDashboard.tsx
│   └── ProductPerformance.tsx
├── lib/
│   ├── api-service.ts   # 🆕 API client with typed functions (sync APIs added)
│   └── api.ts           # Axios instance
└── components/
    ├── Layout.tsx       # App layout with navigation
    └── ui/              # Reusable UI components (Card, Button, etc.)
```

### Configuration
```
render.yaml              # Render.com deployment config (backend + frontend + db)
.python-version          # Forces Python 3.11
requirements.txt         # Python dependencies
frontend/package.json    # Node.js dependencies
frontend/public/_redirects  # SPA routing for Render
```

---

## 🔧 Development Setup

### Prerequisites
- Python 3.11 (NOT 3.13 - has pydantic issues)
- Node.js 18+
- PostgreSQL (or use Render's database)

### Backend Setup
```bash
cd sales-analytics-v2
python -m venv .venv
.venv\Scripts\activate  # Windows
pip install -r requirements.txt

# Set environment variables in .env
DATABASE_URL=postgresql://user:pass@host:5432/dbname
SENTOS_API_URL=https://stildiva.sentos.com.tr/api
SENTOS_API_KEY=your_key_here

# Run backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Frontend Setup
```bash
cd frontend
npm install
npm run dev  # Development server on http://localhost:5173
npm run build  # Production build
```

### Database Migration
```bash
python -c "from database.init_db import init_database; init_database()"
```

---

## 🚀 Deployment Info

### Render.com Services

**Backend Service:**
- Name: `sales-analytics-backend`
- URL: https://sales-analytics-backend-ctxn.onrender.com
- Build Command: `pip install -r requirements.txt`
- Start Command: `uvicorn app.main:app --host 0.0.0.0 --port 8000`
- Environment: Python 3.11 (via `.python-version`)
- Auto-Deploy: On `main` branch push

**Frontend Service:**
- Name: `sales-analytics-frontend`
- URL: https://sales-analytics-frontend.onrender.com
- Build Command: `cd frontend && npm install && npm run build`
- Publish Directory: `frontend/dist`
- Auto-Deploy: On `main` branch push

**Database:**
- Type: PostgreSQL 16
- Region: Frankfurt
- Internal URL: Set in `INTERNAL_DATABASE_URL` env var

### Environment Variables (Backend)
```bash
DATABASE_URL=${INTERNAL_DATABASE_URL}  # Auto from Render
SENTOS_API_URL=https://stildiva.sentos.com.tr/api
SENTOS_API_KEY=<your_key>
SENTOS_ACCOUNT=<your_account>
FRONTEND_URL=https://sales-analytics-frontend.onrender.com
ENVIRONMENT=production
```

---

## 🔄 Recent Changes (Last Session)

### Oct 16, 2025 - Automated Sync System Implementation

**Problem:** Backend restarted during product sync (Render 60s timeout)

**Solution:** Implemented background tasks + automated scheduler

**Files Modified:**
1. `app/api/data.py` - Converted sync to BackgroundTasks
2. `services/scheduled_sync.py` - NEW: Automated scheduler service
3. `app/api/sync.py` - NEW: Sync control API endpoints
4. `app/main.py` - Added scheduler startup/shutdown events
5. `frontend/src/lib/api-service.ts` - Added sync API functions
6. `frontend/src/pages/Settings.tsx` - Added sync status UI

**Commits:**
- `1af3068` - "feat: Implement automated background sync system"
- `f308a9f` - "feat: Add automated sync status display to Settings page"

---

## 🐛 Debugging Tips

### Backend Issues
```bash
# Check logs on Render
# Look for these messages:
# - "✅ Scheduled sync service started"
# - "⏰ Starting daily full sync..."
# - "🔄 Starting live sync..."

# Test sync endpoints locally
curl http://localhost:8000/api/sync/status
curl -X POST http://localhost:8000/api/sync/trigger/live
```

### Frontend Issues
```bash
# Check browser console for errors
# Verify API calls in Network tab
# Check CORS headers

# Test API connection
curl https://sales-analytics-backend-ctxn.onrender.com/health
```

### Database Issues
```bash
# Check connection
python -c "from database.connection import get_db; next(get_db())"

# Verify tables exist
# Should have: products, orders, order_items, customers, komisyon_data
```

### Sentos API Rate Limiting
- **Error:** HTTP 429 Too Many Requests
- **Cause:** Too many API calls in short time
- **Solution:** Health check no longer calls Sentos API
- **Note:** Sync operations include delays to avoid rate limits

---

## 💡 For Next AI Agent

### Context for Resuming Work

**What was the last task?**
- Implemented sync status UI in Settings page
- Added manual trigger buttons for full/live sync
- Auto-refresh every 30 seconds

**What needs verification?**
1. Check if scheduler actually starts (look for log message in Render)
2. Test manual sync triggers on production
3. Verify original product sync button works with new background task

**What's next?**
- Monitor scheduler logs to ensure daily/live syncs run successfully
- Add progress indicators for background operations
- Consider adding sync history feature
- Test under load to verify no rate limiting issues

**Important Notes:**
- Don't remove CORS middleware - frontend needs it
- Don't add Sentos API calls to health check - causes rate limits
- Always use background tasks for long operations (>30s)
- Scheduler runs in separate asyncio task, doesn't block requests

---

## 📞 API Examples

### Sync Control
```bash
# Get sync status
GET /api/sync/status
Response: {
  "is_running": false,
  "last_full_sync": "2025-10-16T02:00:15",
  "last_live_sync": "2025-10-16T14:30:08",
  "full_sync_time": "02:00",
  "live_sync_interval_minutes": 10
}

# Trigger manual full sync
POST /api/sync/trigger/full
Response: {"message": "Full sync triggered", "status": "running"}

# Trigger manual live sync
POST /api/sync/trigger/live
Response: {"message": "Live sync triggered", "status": "running"}
```

### Product Sync
```bash
# Sync products (background task)
POST /api/data/sync-products?max_pages=50
Response: {
  "status": "running",
  "message": "Product sync started in background"
}
```

### Sales Data
```bash
# Fetch sales data
POST /api/data/fetch-sales
Body: {
  "start_date": "2025-10-01",
  "end_date": "2025-10-16",
  "max_pages": 10
}
Response: {
  "orders_fetched": 1250,
  "time_taken": "45.3s"
}
```

---

## 🎓 Learning for Next Session

### What Worked Well
- Background tasks pattern solved timeout issues
- Separate sync API endpoints provide good control
- Auto-refresh UI keeps status current
- TypeScript interfaces improve type safety

### What Could Be Better
- Scheduler startup verification needs improvement
- Progress indicators for long operations missing
- Error messages could be more descriptive
- Sync history would help with debugging

### Architecture Decisions
- **Why separate full/live sync?** Full sync is expensive (all data), live sync is quick (recent updates)
- **Why background tasks?** Render has 60s timeout, syncs can take 5+ minutes
- **Why scheduler service?** Automates data freshness without manual intervention
- **Why 30s refresh?** Balance between real-time updates and API load

---

## 📚 External Resources

- **Render.com Docs:** https://docs.render.com/
- **FastAPI Docs:** https://fastapi.tiangolo.com/
- **React Router:** https://reactrouter.com/
- **TailwindCSS:** https://tailwindcss.com/
- **date-fns:** https://date-fns.org/

---

## 🔐 Security Notes

- API keys stored in Render environment variables (never in code)
- CORS restricted to specific frontend origin
- Database URL uses internal Render network (not exposed)
- No authentication implemented yet (future enhancement)

---

**END OF AI CONTEXT DOCUMENT**
