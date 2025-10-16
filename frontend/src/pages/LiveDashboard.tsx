import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/Card';
import { Button } from '../components/ui/Button';
import { getMetrics } from '../lib/api-service';
import type { SalesMetrics } from '../lib/api-service';
import { TrendingUp, TrendingDown, DollarSign, ShoppingCart, Package, RefreshCw, Minus } from 'lucide-react';
import { format, subDays } from 'date-fns';

const LiveDashboard: React.FC = () => {
  const [todayMetrics, setTodayMetrics] = useState<SalesMetrics | null>(null);
  const [yesterdayMetrics, setYesterdayMetrics] = useState<SalesMetrics | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [lastUpdate, setLastUpdate] = useState<Date>(new Date());

  const loadLiveData = async () => {
    setLoading(true);
    setError(null);
    try {
      const today = format(new Date(), 'yyyy-MM-dd');
      const yesterday = format(subDays(new Date(), 1), 'yyyy-MM-dd');

      // Bugünün verileri (00:00 - şu anki saat)
      const todayData = await getMetrics(today, today);
      setTodayMetrics(todayData);

      // Dünün verileri (tam gün)
      const yesterdayData = await getMetrics(yesterday, yesterday);
      setYesterdayMetrics(yesterdayData);

      setLastUpdate(new Date());
    } catch (err) {
      setError((err as any).response?.data?.detail || 'Veriler yüklenirken hata oluştu');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadLiveData();
    // Her 5 dakikada bir otomatik yenile
    const interval = setInterval(loadLiveData, 5 * 60 * 1000);
    return () => clearInterval(interval);
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

  const calculateChange = (today: number, yesterday: number): { percent: number; isPositive: boolean; isNeutral: boolean } => {
    if (yesterday === 0) return { percent: 0, isPositive: today > 0, isNeutral: today === 0 };
    const change = ((today - yesterday) / yesterday) * 100;
    return { 
      percent: Math.abs(change), 
      isPositive: change > 0,
      isNeutral: Math.abs(change) < 0.01
    };
  };

  const renderChangeIndicator = (today: number, yesterday: number, isCurrency: boolean = false) => {
    const change = calculateChange(today, yesterday);
    const Icon = change.isNeutral ? Minus : (change.isPositive ? TrendingUp : TrendingDown);
    const colorClass = change.isNeutral ? 'text-muted-foreground' : (change.isPositive ? 'text-green-600' : 'text-red-600');
    
    return (
      <div className="flex items-center gap-2 text-xs mt-1">
        <span className="text-muted-foreground">
          Dün: {isCurrency ? formatCurrency(yesterday) : formatNumber(yesterday)}
        </span>
        <span className={`flex items-center gap-1 ${colorClass}`}>
          <Icon className="h-3 w-3" />
          {change.isNeutral ? '0' : change.percent.toFixed(1)}%
        </span>
      </div>
    );
  };

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">📊 Canlı Görünüm</h1>
          <p className="text-muted-foreground mt-2">
            Bugünün gerçek zamanlı satış verileri (00:00 - {format(new Date(), 'HH:mm')})
          </p>
          <p className="text-xs text-muted-foreground mt-1">
            Son güncelleme: {format(lastUpdate, 'HH:mm:ss')}
          </p>
        </div>
        <Button onClick={loadLiveData} disabled={loading}>
          <RefreshCw className={`mr-2 h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
          Yenile
        </Button>
      </div>

      {/* Error Message */}
      {error && (
        <div className="bg-destructive/10 text-destructive px-4 py-3 rounded-md">
          {error}
        </div>
      )}

      {/* Live Metrics */}
      {todayMetrics && yesterdayMetrics && (
        <>
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
            {/* Toplam Sipariş */}
            <Card className="bg-gradient-to-br from-blue-50 to-white dark:from-blue-950 dark:to-background">
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">Toplam Sipariş</CardTitle>
                <ShoppingCart className="h-4 w-4 text-blue-600" />
              </CardHeader>
              <CardContent>
                <div className="text-3xl font-bold">{formatNumber(todayMetrics.total_orders)}</div>
                {renderChangeIndicator(todayMetrics.total_orders, yesterdayMetrics.total_orders)}
                <p className="text-xs text-muted-foreground mt-2">
                  Ort: {formatCurrency(todayMetrics.avg_order_value)}
                </p>
              </CardContent>
            </Card>

            {/* Brüt Ciro */}
            <Card className="bg-gradient-to-br from-green-50 to-white dark:from-green-950 dark:to-background">
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">Brüt Ciro</CardTitle>
                <DollarSign className="h-4 w-4 text-green-600" />
              </CardHeader>
              <CardContent>
                <div className="text-3xl font-bold">{formatCurrency(todayMetrics.gross_revenue)}</div>
                {renderChangeIndicator(todayMetrics.gross_revenue, yesterdayMetrics.gross_revenue, true)}
                <p className="text-xs text-muted-foreground mt-2">
                  Kargo dahil
                </p>
              </CardContent>
            </Card>

            {/* Net Ciro */}
            <Card className="bg-gradient-to-br from-purple-50 to-white dark:from-purple-950 dark:to-background">
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">Net Ciro</CardTitle>
                <TrendingUp className="h-4 w-4 text-purple-600" />
              </CardHeader>
              <CardContent>
                <div className="text-3xl font-bold">{formatCurrency(todayMetrics.net_revenue)}</div>
                {renderChangeIndicator(todayMetrics.net_revenue, yesterdayMetrics.net_revenue, true)}
                <p className="text-xs text-muted-foreground mt-2">
                  İptal/İade düşülmüş
                </p>
              </CardContent>
            </Card>

            {/* Kâr */}
            <Card className="bg-gradient-to-br from-orange-50 to-white dark:from-orange-950 dark:to-background">
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">Kâr</CardTitle>
                <Package className="h-4 w-4 text-orange-600" />
              </CardHeader>
              <CardContent>
                <div className="text-3xl font-bold">{formatCurrency(todayMetrics.profit)}</div>
                {renderChangeIndicator(todayMetrics.profit, yesterdayMetrics.profit, true)}
                <p className="text-xs text-muted-foreground mt-2">
                  Marj: %{todayMetrics.profit_margin.toFixed(1)}
                </p>
              </CardContent>
            </Card>
          </div>

          {/* Marketplace Performance */}
          <Card>
            <CardHeader>
              <CardTitle>Marketplace Bazlı Performans</CardTitle>
              <CardDescription>Bugünün satış dağılımı</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                {Object.entries(todayMetrics.marketplace_breakdown).map(([marketplace, data]) => {
                  const yesterdayData = yesterdayMetrics.marketplace_breakdown[marketplace];
                  const yesterdayRevenue = yesterdayData?.revenue || 0;
                  const change = calculateChange(data.revenue, yesterdayRevenue);
                  
                  return (
                    <div key={marketplace} className="flex items-center justify-between p-3 bg-muted/50 rounded-lg">
                      <div className="flex-1">
                        <div className="flex items-center gap-2">
                          <span className="font-medium">{marketplace}</span>
                          {change.isPositive && <TrendingUp className="h-3 w-3 text-green-600" />}
                          {!change.isPositive && !change.isNeutral && <TrendingDown className="h-3 w-3 text-red-600" />}
                        </div>
                        <div className="text-xs text-muted-foreground mt-1">
                          {data.orders} sipariş
                        </div>
                      </div>
                      <div className="text-right">
                        <div className="font-medium">{formatCurrency(data.revenue)}</div>
                        <div className="text-xs text-muted-foreground">
                          {change.isNeutral ? '±' : (change.isPositive ? '+' : '-')}{change.percent.toFixed(1)}%
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            </CardContent>
          </Card>

          {/* Hourly Progress Indicator */}
          <Card>
            <CardHeader>
              <CardTitle>Günlük İlerleme</CardTitle>
              <CardDescription>Bugünün hedefine göre performans</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-2">
                <div className="flex justify-between text-sm">
                  <span>Güncel Ciro</span>
                  <span className="font-medium">{formatCurrency(todayMetrics.net_revenue)}</span>
                </div>
                <div className="flex justify-between text-sm text-muted-foreground">
                  <span>Dünkü Toplam</span>
                  <span>{formatCurrency(yesterdayMetrics.net_revenue)}</span>
                </div>
                <div className="relative pt-4">
                  <div className="h-4 bg-muted rounded-full overflow-hidden">
                    <div 
                      className="h-full bg-primary transition-all duration-500"
                      style={{ 
                        width: `${Math.min((todayMetrics.net_revenue / yesterdayMetrics.net_revenue) * 100, 100)}%` 
                      }}
                    />
                  </div>
                  <p className="text-xs text-muted-foreground mt-2 text-center">
                    {yesterdayMetrics.net_revenue > 0 
                      ? `Dünün %${((todayMetrics.net_revenue / yesterdayMetrics.net_revenue) * 100).toFixed(1)}'i`
                      : 'Henüz veri yok'}
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>
        </>
      )}

      {/* Loading State */}
      {loading && !todayMetrics && (
        <div className="flex items-center justify-center py-12">
          <RefreshCw className="h-8 w-8 animate-spin text-primary" />
        </div>
      )}
    </div>
  );
};

export default LiveDashboard;
