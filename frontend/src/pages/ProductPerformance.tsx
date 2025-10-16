import React, { useState, useEffect } from 'react';
import { Card } from '../components/ui/Card';
import { Button } from '../components/ui/Button';
import apiClient from '../lib/api';

interface ProductPerformanceItem {
  product_sku: string;
  product_name: string;
  product_image: string | null;
  brand: string | null;
  total_revenue: number;
  total_quantity: number;
  total_orders: number;
  total_cost: number;
  total_profit: number;
  profit_margin: number;
  avg_profit_per_unit: number;
  return_quantity: number;
  return_rate: number;
  return_revenue_loss: number;
  current_stock: number;
  days_of_stock: number | null;
  daily_sales_avg: number;
  performance_score: number;
  rank: number;
}

interface ProductPerformanceResponse {
  top_performers: ProductPerformanceItem[];
  worst_performers: ProductPerformanceItem[];
  total_products: number;
  date_range: {
    start: string;
    end: string;
    days: number;
  };
  marketplace: string;
  total_revenue: number;
  total_profit: number;
  avg_profit_margin: number;
}

export default function ProductPerformance() {
  const [data, setData] = useState<ProductPerformanceResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  
  // Filters
  const [startDate, setStartDate] = useState(() => {
    const date = new Date();
    date.setDate(date.getDate() - 30);
    return date.toISOString().split('T')[0];
  });
  const [endDate, setEndDate] = useState(() => new Date().toISOString().split('T')[0]);
  const [marketplace, setMarketplace] = useState<string>('');
  const [topN, setTopN] = useState(20);
  const [sortBy, setSortBy] = useState<'revenue' | 'profit' | 'quantity' | 'profit_margin'>('revenue');
  const [viewMode, setViewMode] = useState<'both' | 'top' | 'worst'>('both');

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    setLoading(true);
    setError(null);

    try {
      const params = new URLSearchParams({
        start_date: startDate,
        end_date: endDate,
        top_n: topN.toString(),
        sort_by: sortBy,
      });

      if (marketplace) {
        params.append('marketplace', marketplace);
      }

      const response = await apiClient.get(`/api/product-performance/analyze?${params}`);
      setData(response.data);
    } catch (err: any) {
      setError(err.message || 'Veri yüklenirken hata oluştu');
      console.error('Error:', err);
    } finally {
      setLoading(false);
    }
  };

  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat('tr-TR', {
      style: 'currency',
      currency: 'TRY',
      minimumFractionDigits: 2,
    }).format(amount);
  };

  const formatNumber = (num: number) => {
    return new Intl.NumberFormat('tr-TR').format(num);
  };

  const renderProductCard = (product: ProductPerformanceItem, isWorst: boolean = false) => {
    const stockAlert = product.days_of_stock !== null && product.days_of_stock < 7;
    const highReturnAlert = product.return_rate > 15;

    return (
      <div
        key={product.product_sku}
        className="bg-white rounded-lg shadow-md hover:shadow-lg transition-shadow p-4 border border-gray-200"
      >
        {/* Header with rank */}
        <div className="flex items-start gap-4 mb-3">
          <div className={`flex-shrink-0 w-12 h-12 rounded-full flex items-center justify-center text-white font-bold text-lg ${
            isWorst ? 'bg-red-500' : product.rank <= 3 ? 'bg-gradient-to-r from-yellow-400 to-yellow-600' : 'bg-blue-500'
          }`}>
            #{product.rank}
          </div>
          
          <div className="flex-1 min-w-0">
            <h3 className="font-semibold text-gray-900 truncate text-sm">
              {product.product_name}
            </h3>
            <p className="text-xs text-gray-500 mt-1">
              SKU: {product.product_sku}
              {product.brand && <span className="ml-2 px-2 py-0.5 bg-gray-100 rounded">Marka: {product.brand}</span>}
            </p>
          </div>

          {/* Product Image */}
          <div className="flex-shrink-0">
            <img
              src={product.product_image || 'https://via.placeholder.com/80'}
              alt={product.product_name}
              className="w-20 h-20 object-cover rounded border"
            />
          </div>
        </div>

        {/* Stats Grid */}
        <div className="grid grid-cols-2 gap-3 mb-3">
          {/* Revenue */}
          <div className="bg-green-50 p-2 rounded">
            <p className="text-xs text-gray-600">Ciro</p>
            <p className="text-lg font-bold text-green-700">{formatCurrency(product.total_revenue)}</p>
          </div>

          {/* Profit */}
          <div className="bg-blue-50 p-2 rounded">
            <p className="text-xs text-gray-600">Kar</p>
            <p className="text-lg font-bold text-blue-700">{formatCurrency(product.total_profit)}</p>
          </div>

          {/* Quantity */}
          <div className="bg-purple-50 p-2 rounded">
            <p className="text-xs text-gray-600">Satılan</p>
            <p className="text-lg font-bold text-purple-700">{formatNumber(product.total_quantity)} adet</p>
          </div>

          {/* Profit Margin */}
          <div className={`p-2 rounded ${product.profit_margin > 30 ? 'bg-green-50' : product.profit_margin > 15 ? 'bg-yellow-50' : 'bg-red-50'}`}>
            <p className="text-xs text-gray-600">Kar Marjı</p>
            <p className={`text-lg font-bold ${product.profit_margin > 30 ? 'text-green-700' : product.profit_margin > 15 ? 'text-yellow-700' : 'text-red-700'}`}>
              %{product.profit_margin.toFixed(1)}
            </p>
          </div>
        </div>

        {/* Returns Alert */}
        {highReturnAlert && (
          <div className="bg-red-50 border border-red-200 rounded p-2 mb-3">
            <p className="text-xs text-red-700 font-medium">
              ⚠️ Yüksek İade Oranı: %{product.return_rate.toFixed(1)} ({product.return_quantity} adet)
            </p>
            <p className="text-xs text-red-600 mt-1">
              İade Zararı: {formatCurrency(product.return_revenue_loss)}
            </p>
          </div>
        )}

        {/* Stock Info */}
        <div className={`border rounded p-2 ${stockAlert ? 'bg-orange-50 border-orange-300' : 'bg-gray-50 border-gray-200'}`}>
          <div className="flex justify-between items-center text-xs">
            <span className="text-gray-600">Stok Durumu:</span>
            <span className="font-semibold">{formatNumber(product.current_stock)} adet</span>
          </div>
          {product.days_of_stock !== null && (
            <div className="flex justify-between items-center text-xs mt-1">
              <span className="text-gray-600">Stok Süresi:</span>
              <span className={`font-semibold ${stockAlert ? 'text-orange-700' : 'text-gray-700'}`}>
                ~{product.days_of_stock.toFixed(0)} gün
                {stockAlert && ' ⚠️'}
              </span>
            </div>
          )}
          <div className="flex justify-between items-center text-xs mt-1">
            <span className="text-gray-600">Günlük Satış:</span>
            <span className="font-semibold">{product.daily_sales_avg.toFixed(1)} adet/gün</span>
          </div>
        </div>

        {/* Performance Score */}
        <div className="mt-3 pt-3 border-t">
          <div className="flex items-center justify-between">
            <span className="text-xs text-gray-600">Performans Skoru:</span>
            <div className="flex items-center gap-2">
              <div className="w-24 h-2 bg-gray-200 rounded-full overflow-hidden">
                <div
                  className={`h-full ${product.performance_score > 70 ? 'bg-green-500' : product.performance_score > 40 ? 'bg-yellow-500' : 'bg-red-500'}`}
                  style={{ width: `${product.performance_score}%` }}
                />
              </div>
              <span className="text-sm font-bold">{product.performance_score.toFixed(0)}/100</span>
            </div>
          </div>
        </div>

        {/* Additional Stats */}
        <div className="mt-2 pt-2 border-t grid grid-cols-3 gap-2 text-xs text-gray-600">
          <div>
            <p className="text-gray-500">Sipariş</p>
            <p className="font-semibold text-gray-700">{product.total_orders}</p>
          </div>
          <div>
            <p className="text-gray-500">Birim Kar</p>
            <p className="font-semibold text-gray-700">{formatCurrency(product.avg_profit_per_unit)}</p>
          </div>
          <div>
            <p className="text-gray-500">İade</p>
            <p className="font-semibold text-gray-700">%{product.return_rate.toFixed(1)}</p>
          </div>
        </div>
      </div>
    );
  };

  return (
    <div className="min-h-screen bg-gray-50 p-6">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="mb-6">
          <h1 className="text-3xl font-bold text-gray-900">📊 Ürün Performans Analizi</h1>
          <p className="text-gray-600 mt-2">En iyi ve en kötü performans gösteren ürünlerin detaylı analizi</p>
        </div>

        {/* Filters */}
        <Card className="mb-6 p-6">
          <h2 className="text-lg font-semibold mb-4">Filtreler</h2>
          
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Başlangıç</label>
              <input
                type="date"
                value={startDate}
                onChange={(e) => setStartDate(e.target.value)}
                className="w-full px-3 py-2 border rounded-lg"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Bitiş</label>
              <input
                type="date"
                value={endDate}
                onChange={(e) => setEndDate(e.target.value)}
                className="w-full px-3 py-2 border rounded-lg"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Platform</label>
              <select
                value={marketplace}
                onChange={(e) => setMarketplace(e.target.value)}
                className="w-full px-3 py-2 border rounded-lg"
              >
                <option value="">Tümü</option>
                <option value="Trendyol">Trendyol</option>
                <option value="Hepsiburada">Hepsiburada</option>
                <option value="N11">N11</option>
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Gösterim</label>
              <select
                value={topN}
                onChange={(e) => setTopN(Number(e.target.value))}
                className="w-full px-3 py-2 border rounded-lg"
              >
                <option value="10">Top 10</option>
                <option value="20">Top 20</option>
                <option value="50">Top 50</option>
                <option value="100">Top 100</option>
              </select>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Sıralama</label>
              <select
                value={sortBy}
                onChange={(e) => setSortBy(e.target.value as any)}
                className="w-full px-3 py-2 border rounded-lg"
              >
                <option value="revenue">Ciro</option>
                <option value="profit">Kar</option>
                <option value="quantity">Satılan Adet</option>
                <option value="profit_margin">Kar Marjı</option>
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Görünüm</label>
              <select
                value={viewMode}
                onChange={(e) => setViewMode(e.target.value as any)}
                className="w-full px-3 py-2 border rounded-lg"
              >
                <option value="both">Her İkisi</option>
                <option value="top">Sadece En İyiler</option>
                <option value="worst">Sadece En Kötüler</option>
              </select>
            </div>
          </div>

          <Button onClick={fetchData} disabled={loading} className="w-full">
            {loading ? 'Yükleniyor...' : 'Analiz Et'}
          </Button>
        </Card>

        {/* Summary */}
        {data && (
          <Card className="mb-6 p-6 bg-gradient-to-r from-blue-50 to-purple-50">
            <h2 className="text-lg font-semibold mb-4">Özet</h2>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div>
                <p className="text-sm text-gray-600">Toplam Ürün</p>
                <p className="text-2xl font-bold text-gray-900">{formatNumber(data.total_products)}</p>
              </div>
              <div>
                <p className="text-sm text-gray-600">Toplam Ciro</p>
                <p className="text-2xl font-bold text-green-700">{formatCurrency(data.total_revenue)}</p>
              </div>
              <div>
                <p className="text-sm text-gray-600">Toplam Kar</p>
                <p className="text-2xl font-bold text-blue-700">{formatCurrency(data.total_profit)}</p>
              </div>
              <div>
                <p className="text-sm text-gray-600">Ort. Kar Marjı</p>
                <p className="text-2xl font-bold text-purple-700">%{data.avg_profit_margin.toFixed(1)}</p>
              </div>
            </div>
            <p className="text-xs text-gray-500 mt-4">
              📅 {data.date_range.start} - {data.date_range.end} ({data.date_range.days} gün) | 
              🏪 {data.marketplace}
            </p>
          </Card>
        )}

        {/* Error */}
        {error && (
          <div className="bg-red-50 border border-red-200 rounded-lg p-4 mb-6">
            <p className="text-red-700">❌ {error}</p>
          </div>
        )}

        {/* Loading */}
        {loading && (
          <div className="text-center py-12">
            <div className="inline-block animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
            <p className="mt-4 text-gray-600">Veriler yükleniyor...</p>
          </div>
        )}

        {/* Results */}
        {!loading && data && (
          <>
            {/* Top Performers */}
            {(viewMode === 'both' || viewMode === 'top') && (
              <div className="mb-8">
                <h2 className="text-2xl font-bold text-gray-900 mb-4 flex items-center gap-2">
                  🏆 En İyi Performans Gösterenler (Top {data.top_performers.length})
                </h2>
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                  {data.top_performers.map((product) => renderProductCard(product, false))}
                </div>
              </div>
            )}

            {/* Worst Performers */}
            {(viewMode === 'both' || viewMode === 'worst') && (
              <div>
                <h2 className="text-2xl font-bold text-gray-900 mb-4 flex items-center gap-2">
                  📉 En Kötü Performans Gösterenler (Bottom {data.worst_performers.length})
                </h2>
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                  {data.worst_performers.map((product) => renderProductCard(product, true))}
                </div>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}
