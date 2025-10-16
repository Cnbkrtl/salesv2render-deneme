# 📊 Sales Analytics V2 - Sentos E-Commerce Analytics Platform

![Version](https://img.shields.io/badge/version-2.0.0-blue.svg)
![Python](https://img.shields.io/badge/python-3.11-blue.svg)
![FastAPI](https://img.shields.io/badge/FastAPI-0.104-green.svg)
![React](https://img.shields.io/badge/React-18.2-blue.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)

> **Comprehensive sales analytics and business intelligence platform for Sentos e-commerce integration**

---

## 🎯 Project Overview

Sales Analytics V2 is a full-stack business intelligence platform designed specifically for Sentos e-commerce sellers. It provides real-time analytics, automated data synchronization, cost tracking, and actionable insights to maximize profitability.

### **Key Capabilities:**
- 📈 **Real-time Sales Analytics** - Track revenue, profit margins, and KPIs
- 🔄 **Automated Data Sync** - Background synchronization with Sentos API
- 💰 **Cost Management** - Automatic cost matching and profit calculation
- 📦 **Product Performance** - Identify top/worst performers
- 🏪 **Multi-Platform Support** - Track sales across Trendyol, Hepsiburada, N11, etc.
- 📊 **Advanced Reporting** - Export capabilities and custom reports
- 🔔 **Smart Notifications** - Automated alerts and daily reports

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    FRONTEND (React)                          │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐   │
│  │Dashboard │  │Analytics │  │ Products │  │ Settings │   │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘   │
└────────────────────────┬────────────────────────────────────┘
                         │ REST API
┌────────────────────────┴────────────────────────────────────┐
│                   BACKEND (FastAPI)                          │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐            │
│  │   API      │  │  Services  │  │ Background │            │
│  │ Endpoints  │  │            │  │   Tasks    │            │
│  └────────────┘  └────────────┘  └────────────┘            │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐            │
│  │ Scheduler  │  │    Cache   │  │ Connectors │            │
│  │  (Daily/   │  │  Manager   │  │  (Sentos)  │            │
│  │   Live)    │  └────────────┘  └────────────┘            │
│  └────────────┘                                              │
└────────────────────────┬────────────────────────────────────┘
                         │
┌────────────────────────┴────────────────────────────────────┐
│              DATABASE (PostgreSQL)                           │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐      │
│  │ Products │ │  Orders  │ │  Items   │ │  Cache   │      │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘      │
└──────────────────────────────────────────────────────────────┘
```

---

## 🚀 Features

### ✅ **Currently Available**

#### 1. **Automated Data Synchronization**
- **Daily Full Sync:** Every day at 02:00 UTC (fetches all historical data)
- **Live Sync:** Every 10 minutes (08:00-23:00 UTC) for recent updates
- **Background Processing:** Long-running tasks don't block the API
- **Smart Cache:** 24-hour TTL disk cache for product costs

#### 2. **Sales Analytics Dashboard**
- Real-time KPIs (Revenue, Profit, Orders, Items)
- Time range filtering (Last 7/30/90 days, Custom range)
- Marketplace breakdown
- Profit margin analysis
- Return/cancellation tracking

#### 3. **Product Performance Analysis**
- Top 20 best-performing products
- Bottom 20 worst-performing products
- Metrics per product:
  - Total revenue & quantity sold
  - Profit & profit margin
  - Return rate
  - Stock velocity (days of stock)
  - Performance score (0-100)

#### 4. **Smart Cost Matching**
- Automatic SKU-based cost lookup
- Barcode fallback mechanism
- BYK prefix handling for bulk products
- Smart normalization (leading zeros, S prefix)
- Disk-based cost cache (persistent across restarts)

#### 5. **Live Dashboard**
- Real-time sales feed
- Today's performance metrics
- Quick statistics

#### 6. **Settings & Control Panel**
- Manual sync triggers (Full/Live)
- Sync status monitoring
- Last sync timestamps
- Auto-refresh sync status (every 30s)

---

### 🚧 **Coming Soon (Roadmap)**

#### **Phase 1: Quick Wins** (1-2 weeks)
1. **Platform-Based Sales Analysis** ⭐⭐⭐⭐⭐
   - Revenue breakdown by marketplace (Trendyol, HB, N11)
   - Commission comparison across platforms
   - Average order value per platform
   - Platform profitability ranking

2. **Export & Reporting System** ⭐⭐⭐⭐⭐
   - Excel export (XLSX)
   - CSV export
   - PDF reports
   - Custom date range selection
   - Report types:
     - Sales Report
     - Product Performance Report
     - Profit & Loss Statement
     - Platform Comparison
     - Customer List (for invoicing)

3. **Stock Tracking & Alerts** ⭐⭐⭐⭐⭐
   - Real-time stock levels
   - Low stock warnings (<10 units)
   - Stock velocity calculation
   - Days of stock remaining
   - Slow-moving product detection
   - Dead stock identification

#### **Phase 2: Medium-Term** (2-3 weeks)
4. **Notification System** ⭐⭐⭐⭐
   - Email notifications
   - Daily performance reports
   - Low stock alerts
   - Profit margin warnings
   - Sync failure alerts
   - Custom threshold settings

5. **Profit Forecasting** ⭐⭐⭐⭐
   - Next 30-day profit prediction
   - Trend analysis (↑↓)
   - Seasonality detection
   - Linear regression model
   - Historical comparison

6. **Shipping Cost Analysis** ⭐⭐⭐⭐
   - Cost breakdown by carrier
   - Average shipping time
   - Carrier performance comparison
   - Shipping problem tracking
   - Cost optimization recommendations

#### **Phase 3: Advanced** (1 month)
7. **Category Performance Analysis** ⭐⭐⭐⭐
   - Sales by category
   - Top-selling categories
   - Category trend analysis
   - Category profitability

8. **Customer Segmentation (RFM)** ⭐⭐⭐
   - Recency, Frequency, Monetary analysis
   - VIP customer identification
   - Customer churn detection
   - Loyalty scoring
   - Customer lifetime value

9. **Basket Analysis & Cross-Sell** ⭐⭐⭐
   - Frequently bought together
   - Product affinity analysis
   - Bundle recommendations
   - Market basket analysis (Apriori algorithm)

#### **Phase 4: Future Enhancements**
10. **Advanced Dashboard** ⭐⭐⭐
    - Customizable widgets
    - Drag & drop layout
    - Personal dashboards
    - Dark mode

11. **User Management & RBAC** ⭐⭐
    - Multi-user support
    - Role-based access control
    - Audit logging
    - API key management

12. **AI Chatbot Assistant** ⭐⭐
    - Natural language queries
    - "What's my revenue this week?"
    - SQL generation from NL
    - Context-aware responses

---

## 🛠️ Tech Stack

### **Backend**
- **Framework:** FastAPI 0.104
- **Language:** Python 3.11
- **Database:** PostgreSQL 16 (Render managed)
- **ORM:** SQLAlchemy 2.0
- **API Client:** Requests + HTTPBasicAuth
- **Scheduler:** AsyncIO background tasks
- **Cache:** JSON file-based cache (24h TTL)

### **Frontend**
- **Framework:** React 18.2
- **Language:** TypeScript 5.x
- **Build Tool:** Vite 5.x
- **Styling:** TailwindCSS 3.x
- **HTTP Client:** Axios
- **Date Handling:** date-fns
- **Routing:** React Router v6

### **DevOps & Hosting**
- **Platform:** Render.com
- **Backend Deployment:** Web Service (Frankfurt)
- **Frontend Deployment:** Static Site
- **Database:** Managed PostgreSQL (Frankfurt)
- **CI/CD:** Auto-deploy on `main` branch push
- **Version Control:** GitHub

---

## 📦 Installation & Setup

### **Prerequisites**
```bash
- Python 3.11
- Node.js 18+
- PostgreSQL (or use Render's managed DB)
- Git
```

### **1. Clone Repository**
```bash
git clone https://github.com/Cnbkrtl/salesv2render-deneme.git
cd salesv2render-deneme
```

### **2. Backend Setup**
```bash
# Create virtual environment
python -m venv .venv

# Activate (Windows)
.venv\Scripts\activate

# Activate (Linux/Mac)
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Create .env file
cp .env.example .env

# Edit .env with your credentials
nano .env
```

**.env Configuration:**
```env
# Database
DATABASE_URL=postgresql://user:password@localhost:5432/sales_analytics

# Sentos API
SENTOS_API_URL=https://yourdomain.sentos.com.tr/api
SENTOS_API_KEY=your_api_key_here
SENTOS_API_SECRET=your_api_secret_here
SENTOS_COOKIE=your_cookie_here

# Security
API_KEY=your_secure_api_key

# CORS
ALLOWED_ORIGINS=http://localhost:5173,https://yourdomain.com

# Environment
ENVIRONMENT=development
```

**Initialize Database:**
```bash
python -c "from database.init_db import init_database; init_database()"
```

**Run Backend:**
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Backend will be available at: `http://localhost:8000`

### **3. Frontend Setup**
```bash
cd frontend

# Install dependencies
npm install

# Run development server
npm run dev
```

Frontend will be available at: `http://localhost:5173`

### **4. Production Build**
```bash
# Backend (already running via uvicorn)
# No build step needed

# Frontend
cd frontend
npm run build

# Output will be in frontend/dist/
```

---

## 🌍 Deployment (Render.com)

### **Automatic Deployment**
1. Push to `main` branch
2. Render automatically builds and deploys
3. Backend: ~2-3 minutes
4. Frontend: ~1-2 minutes

### **Manual Deployment**
1. Go to [Render Dashboard](https://dashboard.render.com)
2. Select service (backend/frontend)
3. Click "Manual Deploy" → "Deploy latest commit"

### **Environment Variables (Render)**
Backend service environment variables:
```
DATABASE_URL=${INTERNAL_DATABASE_URL}
SENTOS_API_URL=https://stildiva.sentos.com.tr/api
SENTOS_API_KEY=***
SENTOS_API_SECRET=***
SENTOS_COOKIE=***
FRONTEND_URL=https://sales-analytics-frontend.onrender.com
ENVIRONMENT=production
API_KEY=***
```

---

## 📊 Database Schema

### **Core Tables**

#### **products**
```sql
- id (PK)
- sentos_product_id (UNIQUE)
- sku (UNIQUE, INDEXED)
- name, brand, barcode
- image (URL)
- purchase_price, vat_rate, purchase_price_with_vat
- sale_price
- created_at, updated_at
```

#### **sales_orders**
```sql
- id (PK)
- sentos_order_id (UNIQUE)
- order_code, order_date (INDEXED)
- marketplace (INDEXED), shop
- order_status (INDEXED)
- order_total, shipping_total, carrying_charge, service_fee
- cargo_provider, cargo_number
- invoice info
- created_at, updated_at, fetched_at
```

#### **sales_order_items**
```sql
- id (PK)
- order_id (FK to sales_orders)
- sentos_order_id, sentos_item_id
- unique_key (UNIQUE: order_id_item_id)
- product_name, product_sku (INDEXED), barcode
- color, model_name, model_value
- item_status (INDEXED), quantity
- unit_price, item_amount
- unit_cost_with_vat, total_cost_with_vat
- commission_rate, commission_amount
- is_return, is_cancelled
- created_at, updated_at
```

#### **sales_metrics_cache**
```sql
- id (PK)
- period_start, period_end (INDEXED)
- marketplace (INDEXED)
- brut_ciro, brut_siparis_sayisi, brut_satilan_adet
- iptal_iade_ciro, iptal_iade_siparis_sayisi, iptal_iade_adet
- net_ciro, net_siparis_sayisi, net_satilan_adet
- urun_maliyeti_kdvli, kargo_gideri
- kar, kar_marji
- is_valid, calculated_at
```

---

## 🔄 API Endpoints

### **Health & Status**
```
GET  /health                    - Health check (no Sentos API calls)
GET  /api/sync/status          - Sync status (last sync times)
POST /api/sync/trigger/full    - Trigger full sync manually
POST /api/sync/trigger/live    - Trigger live sync manually
```

### **Data Sync**
```
POST /api/data/sync-products?max_pages=50  - Sync products (background)
POST /api/data/fetch-sales                 - Fetch sales data
     Body: {start_date, end_date, max_pages}
```

### **Analytics**
```
GET /api/analytics/summary?start_date=...&end_date=...&marketplace=...
    - Get sales summary with all KPIs
    
GET /api/analytics/daily?start_date=...&end_date=...
    - Daily breakdown time series
    
GET /api/analytics/marketplace-breakdown?start_date=...&end_date=...
    - Sales by marketplace
```

### **Product Performance**
```
GET /api/product-performance?start_date=...&end_date=...&marketplace=...
    - Top/worst performing products with detailed metrics
```

---

## 🧪 Testing

### **Backend Tests**
```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app --cov=services

# Run specific test file
pytest tests/test_analytics.py
```

### **Frontend Tests**
```bash
cd frontend

# Run unit tests
npm test

# Run with coverage
npm test -- --coverage
```

### **Manual Testing**
```bash
# Test image fetch
python test_image_fetch.py

# Test API connection
curl http://localhost:8000/health

# Test sync status
curl http://localhost:8000/api/sync/status
```

---

## 🐛 Troubleshooting

### **Backend Issues**

**Problem:** Database connection failed
```bash
# Check DATABASE_URL in .env
# Ensure PostgreSQL is running
# Test connection:
python -c "from database.connection import get_db; next(get_db())"
```

**Problem:** Sentos API rate limiting (429)
```bash
# Reduce sync frequency
# Check SENTOS_COOKIE is set
# Verify API credentials
```

**Problem:** Scheduler not starting
```bash
# Check logs for "✅ Scheduled sync service started"
# Verify no import errors
# Check app/main.py startup event
```

### **Frontend Issues**

**Problem:** CORS errors
```bash
# Check ALLOWED_ORIGINS in backend .env
# Ensure frontend URL is whitelisted
# Verify CORS middleware in app/main.py
```

**Problem:** API calls failing
```bash
# Check API_BASE_URL in frontend
# Verify backend is running
# Check browser console for errors
```

### **Deployment Issues**

**Problem:** Render deployment failed
```bash
# Check build logs in Render dashboard
# Verify requirements.txt is up to date
# Ensure Python version is 3.11 (.python-version file)
```

---

## 📈 Performance Optimization

### **Backend**
- ✅ Indexed database columns (SKU, order_date, marketplace)
- ✅ Background tasks for long-running operations
- ✅ Disk-based product cost cache (24h TTL)
- ✅ Batch database operations (bulk insert/update)
- ✅ Rate limiting delays (1s between API calls)

### **Frontend**
- ✅ Code splitting (React.lazy)
- ✅ Production build optimization (Vite)
- ✅ TailwindCSS purging (unused styles removed)
- ⏳ Future: Image lazy loading
- ⏳ Future: Virtual scrolling for large lists

### **Database**
- ✅ Composite indexes on common queries
- ✅ Normalized schema (no data duplication)
- ✅ Unique constraints prevent duplicates
- ⏳ Future: Materialized views for complex aggregations
- ⏳ Future: Partitioning for large tables

---

## 🔐 Security

### **Backend Security**
- ✅ API key authentication (API_KEY header)
- ✅ CORS whitelist (specific origins only)
- ✅ Environment variables (no hardcoded secrets)
- ✅ SQL injection prevention (SQLAlchemy ORM)
- ⏳ Future: JWT authentication
- ⏳ Future: Rate limiting per IP

### **Frontend Security**
- ✅ No API keys in client code
- ✅ HTTPS only in production
- ✅ XSS prevention (React escaping)
- ⏳ Future: CSP headers
- ⏳ Future: CSRF tokens

---

## 📝 Development Guidelines

### **Code Style**
```python
# Backend: PEP 8
# Use type hints
def calculate_profit(revenue: float, cost: float) -> float:
    return revenue - cost

# Use docstrings
def sync_products(db: Session, max_pages: int = 50) -> int:
    """
    Sync products from Sentos API.
    
    Args:
        db: Database session
        max_pages: Maximum number of pages to fetch
        
    Returns:
        Number of products synced
    """
    pass
```

```typescript
// Frontend: Prettier + ESLint
// Use TypeScript interfaces
interface Product {
  sku: string;
  name: string;
  price: number;
}

// Use functional components
const Dashboard: React.FC = () => {
  return <div>Dashboard</div>;
};
```

### **Commit Messages**
```bash
# Format: <type>: <description>

# Types:
feat: Add new feature
fix: Bug fix
docs: Documentation update
style: Code style changes
refactor: Code refactoring
test: Add tests
chore: Maintenance tasks

# Examples:
git commit -m "feat: Add platform-based sales analysis"
git commit -m "fix: Correct product image selection logic"
git commit -m "docs: Update README with deployment steps"
```

### **Branch Strategy**
```bash
main        # Production-ready code
develop     # Development branch (future)
feature/*   # New features
bugfix/*    # Bug fixes
hotfix/*    # Urgent production fixes
```

---

## 📞 Support & Contact

- **Repository:** https://github.com/Cnbkrtl/salesv2render-deneme
- **Issues:** https://github.com/Cnbkrtl/salesv2render-deneme/issues
- **Backend URL:** https://sales-analytics-backend-ctxn.onrender.com
- **Frontend URL:** https://sales-analytics-frontend.onrender.com

---

## 📄 License

MIT License - feel free to use and modify for your needs.

---

## 🙏 Acknowledgments

- **Sentos API** - E-commerce platform integration
- **Render.com** - Hosting platform
- **FastAPI** - Modern Python web framework
- **React** - Frontend framework
- **TailwindCSS** - Utility-first CSS framework

---

## 🗺️ Project Roadmap

### **Q4 2024**
- ✅ Core analytics dashboard
- ✅ Automated sync system
- ✅ Product performance tracking
- ✅ Cost matching system
- ✅ Smart image handling

### **Q1 2025**
- 🚧 Platform-based analysis
- 🚧 Export & reporting system
- 🚧 Stock tracking
- 📅 Notification system
- 📅 Profit forecasting

### **Q2 2025**
- 📅 Shipping cost analysis
- 📅 Category performance
- 📅 Customer segmentation
- 📅 Basket analysis

### **Q3 2025**
- 📅 Advanced dashboard customization
- 📅 User management & RBAC
- 📅 Mobile app (React Native)

---

## 📚 Additional Documentation

- [API Documentation](./docs/API.md) *(Coming soon)*
- [Database Schema](./docs/DATABASE.md) *(Coming soon)*
- [Deployment Guide](./DEPLOYMENT.md)
- [Development Checklist](./DEPLOYMENT_CHECKLIST.md)
- [AI Context](./AI_CONTEXT.md)

---

**Last Updated:** October 16, 2025  
**Version:** 2.0.0  
**Status:** ✅ Production Ready

---

Made with ❤️ for Sentos sellers
