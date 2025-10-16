import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/Card';
import { Button } from '../components/ui/Button';
import { getMetrics, syncProducts, fetchSalesData } from '../lib/api-service';
import type { SalesMetrics } from '../lib/api-service';
import { TrendingUp, DollarSign, ShoppingCart, Package, RefreshCw, Download, Database } from 'lucide-react';
import { format, subDays } from 'date-fns';

const Dashboard: React.FC = () => {
  const [metrics, setMetrics] = useState<SalesMetrics | null>(null);
  const [loading, setLoading] = useState(false);
  const [syncing, setSyncing] = useState(false);
  const [fetching, setFetching] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [startDate, setStartDate] = useState(format(subDays(new Date(), 30), 'yyyy-MM-dd'));
  const [endDate, setEndDate] = useState(format(new Date(), 'yyyy-MM-dd'));

  const loadMetrics = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await getMetrics(startDate, endDate);
      setMetrics(data);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Veriler yüklenirken hata oluştu');
    } finally {
      setLoading(false);
    }
  };

  const handleSyncProducts = async () => {
    setSyncing(true);
    setError(null);
    setSuccess(null);
    try {
      const result = await syncProducts();
      setSuccess(`✅ ${result.products_synced || 0} ürün senkronize edildi!`);
      setTimeout(() => setSuccess(null), 5000);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Ürün senkronizasyonu başarısız');
    } finally {
      setSyncing(false);
    }
  };

  const handleFetchData = async () => {
    setFetching(true);
    setError(null);
    setSuccess(null);
    try {
      const result = await fetchSalesData({
        start_date: startDate,
        end_date: endDate,
        max_pages: 10, // İlk 10 sayfa
      });
      setSuccess(`✅ ${result.orders_fetched || 0} sipariş çekildi!`);
      setTimeout(() => setSuccess(null), 5000);
      // Verileri çektikten sonra metrikleri yenile
      await loadMetrics();
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Veri çekme başarısız');
    } finally {
      setFetching(false);
    }
  };

  useEffect(() => {
    loadMetrics();
  }, []);

  const formatCurrency = (value: number) => {
    return new Intl.NumberFormat('tr-TR', {
      style: 'currency',
      currency: 'TRY',
    }).format(value);
  };

  const formatNumber = (value: number) => {
    return new Intl.NumberFormat('tr-TR').format(value);
  };

  // Marketplace komisyon oranları
  const COMMISSION_RATES: { [key: string]: number } = {
    'Trendyol': 21.5,
    'Hepsiburada': 15.0,
    'N11': 12.0,
    'Shopify': 0.0,
    'LCWaikiki': 0.0,
  };

  // Komisyon hesaplama
  const calculateTotalCommission = () => {
    if (!metrics?.marketplace_breakdown) return 0;
    
    let totalCommission = 0;
    Object.entries(metrics.marketplace_breakdown).forEach(([marketplace, data]) => {
      const rate = COMMISSION_RATES[marketplace] || 0;
      const commission = (data.revenue * rate) / 100;
      totalCommission += commission;
    });
    
    return totalCommission;
  };

  const totalCommission = metrics ? calculateTotalCommission() : 0;

  return (
    <div className="min-h-screen bg-background p-8">
      <div className="max-w-7xl mx-auto space-y-8">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-4xl font-bold">Satış Analiz Paneli</h1>
            <p className="text-muted-foreground mt-2">
              E-ticaret satış performansınızı takip edin
            </p>
          </div>
          <Button onClick={loadMetrics} disabled={loading}>
            <RefreshCw className={`mr-2 h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
            Yenile
          </Button>
        </div>

        {/* Date Filter */}
        <Card>
          <CardContent className="pt-6">
            <div className="flex gap-4 items-end">
              <div className="flex-1">
                <label className="text-sm font-medium mb-2 block">Başlangıç Tarihi</label>
                <input
                  type="date"
                  value={startDate}
                  onChange={(e) => setStartDate(e.target.value)}
                  className="w-full px-3 py-2 border rounded-md"
                />
              </div>
              <div className="flex-1">
                <label className="text-sm font-medium mb-2 block">Bitiş Tarihi</label>
                <input
                  type="date"
                  value={endDate}
                  onChange={(e) => setEndDate(e.target.value)}
                  className="w-full px-3 py-2 border rounded-md"
                />
              </div>
              <Button onClick={loadMetrics} disabled={loading}>
                Filtrele
              </Button>
            </div>
          </CardContent>
        </Card>

        {/* Error Message */}
        {error && (
          <div className="bg-destructive/10 text-destructive px-4 py-3 rounded-md">
            {error}
          </div>
        )}

        {/* Success Message */}
        {success && (
          <div className="bg-green-50 text-green-700 px-4 py-3 rounded-md border border-green-200">
            {success}
          </div>
        )}

        {/* Data Management Card */}
        <Card>
          <CardHeader>
            <CardTitle>Veri Yönetimi</CardTitle>
            <CardDescription>Veritabanını güncelleyin</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="flex gap-4">
              <Button 
                onClick={handleSyncProducts} 
                disabled={syncing || loading}
                variant="outline"
                className="flex-1"
              >
                <Database className={`mr-2 h-4 w-4 ${syncing ? 'animate-spin' : ''}`} />
                {syncing ? 'Senkronize ediliyor...' : 'Ürünleri Senkronize Et'}
              </Button>
              <Button 
                onClick={handleFetchData} 
                disabled={fetching || loading}
                className="flex-1"
              >
                <Download className={`mr-2 h-4 w-4 ${fetching ? 'animate-spin' : ''}`} />
                {fetching ? 'Çekiliyor...' : 'Satış Verilerini Çek'}
              </Button>
            </div>
            <p className="text-xs text-muted-foreground mt-3">
              💡 İpucu: Önce ürünleri senkronize edin, ardından satış verilerini çekin.
            </p>
          </CardContent>
        </Card>

        {/* Metrics Cards */}
        {metrics && (
          <>
            <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
              <Card>
                <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                  <CardTitle className="text-sm font-medium">Toplam Sipariş</CardTitle>
                  <ShoppingCart className="h-4 w-4 text-muted-foreground" />
                </CardHeader>
                <CardContent>
                  <div className="text-2xl font-bold">{formatNumber(metrics.total_orders)}</div>
                  <p className="text-xs text-muted-foreground">
                    Ort: {formatCurrency(metrics.avg_order_value)}
                  </p>
                </CardContent>
              </Card>

              <Card>
                <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                  <CardTitle className="text-sm font-medium">Brüt Ciro</CardTitle>
                  <DollarSign className="h-4 w-4 text-muted-foreground" />
                </CardHeader>
                <CardContent>
                  <div className="text-2xl font-bold">{formatCurrency(metrics.gross_revenue)}</div>
                  <p className="text-xs text-muted-foreground">
                    Kargo dahil
                  </p>
                </CardContent>
              </Card>

              <Card>
                <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                  <CardTitle className="text-sm font-medium">Net Ciro</CardTitle>
                  <TrendingUp className="h-4 w-4 text-muted-foreground" />
                </CardHeader>
                <CardContent>
                  <div className="text-2xl font-bold">{formatCurrency(metrics.net_revenue)}</div>
                  <p className="text-xs text-muted-foreground">
                    İptal/İade düşülmüş
                  </p>
                </CardContent>
              </Card>

              <Card>
                <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                  <CardTitle className="text-sm font-medium">Kâr</CardTitle>
                  <Package className="h-4 w-4 text-muted-foreground" />
                </CardHeader>
                <CardContent>
                  <div className="text-2xl font-bold">{formatCurrency(metrics.profit)}</div>
                  <p className="text-xs text-muted-foreground">
                    Marj: %{metrics.profit_margin.toFixed(1)}
                  </p>
                </CardContent>
              </Card>
            </div>

            {/* Additional Metrics */}
            <div className="grid gap-4 md:grid-cols-2">
              <Card>
                <CardHeader>
                  <CardTitle>Maliyet Dağılımı</CardTitle>
                  <CardDescription>Gider kalemleri</CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="space-y-2">
                    <div className="flex justify-between">
                      <span className="text-sm text-muted-foreground">Ürün Maliyeti</span>
                      <span className="font-medium">{formatCurrency(metrics.total_cost)}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-sm text-muted-foreground">Kargo Gideri</span>
                      <span className="font-medium">{formatCurrency(metrics.shipping_expense)}</span>
                    </div>
                    {totalCommission > 0 && (
                      <div className="flex justify-between">
                        <span className="text-sm text-muted-foreground">Marketplace Komisyon</span>
                        <span className="font-medium text-orange-600">{formatCurrency(totalCommission)}</span>
                      </div>
                    )}
                    <div className="flex justify-between pt-2 border-t">
                      <span className="text-sm font-semibold">Toplam Maliyet</span>
                      <span className="font-semibold">
                        {formatCurrency(
                          metrics.total_cost + 
                          metrics.shipping_expense + 
                          totalCommission
                        )}
                      </span>
                    </div>
                    <div className="flex justify-between pt-1 text-muted-foreground border-t">
                      <span className="text-sm">İptal/İade (Kayıp)</span>
                      <span className="font-medium text-destructive">
                        {formatCurrency(metrics.cancelled_revenue)}
                      </span>
                    </div>
                  </div>
                </CardContent>
              </Card>

              <Card>
                <CardHeader>
                  <CardTitle>Marketplace Dağılımı</CardTitle>
                  <CardDescription>Platforma göre satışlar</CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="space-y-2">
                    {Object.entries(metrics.marketplace_breakdown).map(([marketplace, data]) => (
                      <div key={marketplace} className="flex justify-between">
                        <span className="text-sm font-medium">{marketplace}</span>
                        <div className="text-right">
                          <div className="text-sm font-medium">{formatCurrency(data.revenue)}</div>
                          <div className="text-xs text-muted-foreground">
                            {data.orders} sipariş
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                </CardContent>
              </Card>
            </div>
          </>
        )}

        {/* Loading State */}
        {loading && !metrics && (
          <div className="flex items-center justify-center py-12">
            <RefreshCw className="h-8 w-8 animate-spin text-primary" />
          </div>
        )}
      </div>
    </div>
  );
};

export default Dashboard;
