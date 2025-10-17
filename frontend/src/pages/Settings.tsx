import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/Card';
import { Button } from '../components/ui/Button';
import { syncProducts, fetchSalesData, getSyncStatus, triggerFullSync, triggerLiveSync, syncTrendyolOrders, testTrendyolConnection, type SyncStatus, type TrendyolSyncResponse, type TrendyolTestConnectionResponse } from '../lib/api-service';
import { Database, Download, Settings as SettingsIcon, Clock, RefreshCw, ShoppingBag } from 'lucide-react';
import { format, subDays } from 'date-fns';
import { tr } from 'date-fns/locale';

const Settings: React.FC = () => {
  const [syncing, setSyncing] = useState(false);
  const [fetching, setFetching] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [startDate, setStartDate] = useState(format(subDays(new Date(), 7), 'yyyy-MM-dd'));
  const [endDate, setEndDate] = useState(format(new Date(), 'yyyy-MM-dd'));
  const [maxPages, setMaxPages] = useState<number>(50); // Varsayılan 50 sayfa (5000 ürün)
  
  // Sync status state
  const [syncStatus, setSyncStatus] = useState<SyncStatus | null>(null);
  const [syncLoading, setSyncLoading] = useState(false);

  // Trendyol state
  const [trendyolSyncing, setTrendyolSyncing] = useState(false);
  const [trendyolDays, setTrendyolDays] = useState<number>(14);
  const [trendyolConnectionStatus, setTrendyolConnectionStatus] = useState<TrendyolTestConnectionResponse | null>(null);
  const [trendyolLastSync, setTrendyolLastSync] = useState<string | null>(null);

  // Fetch sync status on mount and every 30 seconds
  useEffect(() => {
    const fetchSyncStatus = async () => {
      try {
        const status = await getSyncStatus();
        setSyncStatus(status);
      } catch (err) {
        console.error('Sync status fetch error:', err);
      }
    };

    fetchSyncStatus();
    const interval = setInterval(fetchSyncStatus, 30000); // 30 seconds
    return () => clearInterval(interval);
  }, []);

  const handleTriggerFullSync = async () => {
    setSyncLoading(true);
    setError(null);
    setSuccess(null);
    try {
      await triggerFullSync();
      setSuccess('✅ Tam senkronizasyon başlatıldı! Bir kaç dakika içinde tamamlanacak.');
      setTimeout(() => setSuccess(null), 5000);
      // Refresh status
      const status = await getSyncStatus();
      setSyncStatus(status);
    } catch (err) {
      setError('Tam senkronizasyon başlatılamadı');
    } finally {
      setSyncLoading(false);
    }
  };

  const handleTriggerLiveSync = async () => {
    setSyncLoading(true);
    setError(null);
    setSuccess(null);
    try {
      await triggerLiveSync();
      setSuccess('✅ Canlı senkronizasyon başlatıldı!');
      setTimeout(() => setSuccess(null), 5000);
      // Refresh status
      const status = await getSyncStatus();
      setSyncStatus(status);
    } catch (err) {
      setError('Canlı senkronizasyon başlatılamadı');
    } finally {
      setSyncLoading(false);
    }
  };

  const formatSyncTime = (dateStr: string | null) => {
    if (!dateStr) return 'Henüz yapılmadı';
    try {
      const date = new Date(dateStr);
      return format(date, 'dd MMM yyyy HH:mm', { locale: tr });
    } catch {
      return 'Geçersiz tarih';
    }
  };

  const handleSyncProducts = async () => {
    console.log('🔄 Ürün senkronizasyonu başlatılıyor...', { maxPages });
    setSyncing(true);
    setError(null);
    setSuccess(null);
    try {
      console.log('📡 syncProducts fonksiyonu çağrılıyor...');
      const result = await syncProducts(maxPages);
      console.log('✅ Senkronizasyon başarılı:', result);
      setSuccess(`✅ ${result.products_synced || 0} ürün senkronize edildi!`);
      setTimeout(() => setSuccess(null), 5000);
    } catch (err) {
      console.error('❌ Senkronizasyon hatası:', err);
      const errorMessage = (err as any).response?.data?.detail || 
                          (err as any).message || 
                          'Ürün senkronizasyonu başarısız';
      setError(errorMessage);
      console.error('Error details:', {
        response: (err as any).response,
        message: (err as any).message,
        stack: (err as any).stack
      });
    } finally {
      setSyncing(false);
      console.log('🏁 Senkronizasyon işlemi tamamlandı');
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
        max_pages: 10,
      });
      setSuccess(`✅ ${result.orders_fetched || 0} sipariş çekildi!`);
      setTimeout(() => setSuccess(null), 5000);
    } catch (err) {
      setError((err as any).response?.data?.detail || 'Veri çekme başarısız');
    } finally {
      setFetching(false);
    }
  };

  // Trendyol handlers
  const handleTestTrendyolConnection = async () => {
    try {
      const result = await testTrendyolConnection();
      setTrendyolConnectionStatus(result);
      if (result.status === 'success') {
        setSuccess('✅ Trendyol API bağlantısı başarılı!');
      } else {
        setError(`⚠️ ${result.message}`);
      }
      setTimeout(() => {
        setSuccess(null);
        setError(null);
      }, 5000);
    } catch (err) {
      setError('Trendyol bağlantı testi başarısız');
      setTimeout(() => setError(null), 5000);
    }
  };

  const handleSyncTrendyol = async () => {
    setTrendyolSyncing(true);
    setError(null);
    setSuccess(null);
    try {
      const result = await syncTrendyolOrders(trendyolDays);
      setSuccess(`✅ ${result.orders_fetched} Trendyol siparişi senkronize edildi! (${result.items_stored} item)`);
      setTrendyolLastSync(result.timestamp);
      setTimeout(() => setSuccess(null), 5000);
    } catch (err) {
      const errorMessage = (err as any).response?.data?.detail || 
                          (err as any).message || 
                          'Trendyol senkronizasyonu başarısız';
      setError(errorMessage);
      setTimeout(() => setError(null), 5000);
    } finally {
      setTrendyolSyncing(false);
    }
  };

  return (
    <div className="space-y-8">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold flex items-center gap-2">
          <SettingsIcon className="h-8 w-8" />
          Ayarlar
        </h1>
        <p className="text-muted-foreground mt-2">
          Sistem ayarları ve veri yönetimi
        </p>
      </div>

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

      {/* Data Management Section */}
      <div className="space-y-4">
        <h2 className="text-2xl font-semibold">Veri Yönetimi</h2>
        
        {/* Automated Sync Status Card */}
        <Card className="border-2 border-blue-200 dark:border-blue-800">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <RefreshCw className={`h-5 w-5 ${syncStatus?.is_running ? 'animate-spin text-blue-600' : ''}`} />
              Otomatik Senkronizasyon Durumu
            </CardTitle>
            <CardDescription>
              Arka planda otomatik olarak çalışan veri senkronizasyon sistemi
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {/* Status Overview */}
              <div className="grid gap-4 md:grid-cols-2">
                <div className="bg-gradient-to-br from-purple-50 to-purple-100 dark:from-purple-950 dark:to-purple-900 p-4 rounded-lg">
                  <div className="flex items-center gap-2 mb-2">
                    <Clock className="h-4 w-4 text-purple-600 dark:text-purple-400" />
                    <span className="text-sm font-medium text-purple-900 dark:text-purple-100">
                      Son Tam Senkronizasyon
                    </span>
                  </div>
                  <p className="text-lg font-bold text-purple-900 dark:text-purple-100">
                    {formatSyncTime(syncStatus?.last_full_sync || null)}
                  </p>
                  <p className="text-xs text-purple-700 dark:text-purple-300 mt-1">
                    Her gün saat {syncStatus?.full_sync_time || '02:00'}
                  </p>
                </div>

                <div className="bg-gradient-to-br from-green-50 to-green-100 dark:from-green-950 dark:to-green-900 p-4 rounded-lg">
                  <div className="flex items-center gap-2 mb-2">
                    <Clock className="h-4 w-4 text-green-600 dark:text-green-400" />
                    <span className="text-sm font-medium text-green-900 dark:text-green-100">
                      Son Canlı Senkronizasyon
                    </span>
                  </div>
                  <p className="text-lg font-bold text-green-900 dark:text-green-100">
                    {formatSyncTime(syncStatus?.last_live_sync || null)}
                  </p>
                  <p className="text-xs text-green-700 dark:text-green-300 mt-1">
                    Her {syncStatus?.live_sync_interval_minutes || 10} dakikada (08:00-23:00)
                  </p>
                </div>
              </div>

              {/* Info Box */}
              <div className="bg-blue-50 dark:bg-blue-950 p-4 rounded-md border border-blue-200 dark:border-blue-800">
                <h4 className="font-medium mb-2 text-blue-900 dark:text-blue-100">🤖 Otomatik Sistem</h4>
                <p className="text-sm text-blue-800 dark:text-blue-200 mb-2">
                  Bu sistem arka planda sürekli çalışır ve verilerinizi güncel tutar:
                </p>
                <ul className="text-sm text-blue-800 dark:text-blue-200 space-y-1 list-disc list-inside">
                  <li><strong>Tam Senkronizasyon:</strong> Her gece saat {syncStatus?.full_sync_time || '02:00'}'da tüm satış verilerini çeker</li>
                  <li><strong>Canlı Senkronizasyon:</strong> Gündüz saatlerinde (08:00-23:00) her {syncStatus?.live_sync_interval_minutes || 10} dakikada güncel verileri çeker</li>
                  <li><strong>Otomatik:</strong> Hiçbir işlem yapmanıza gerek yok, sistem kendi başına çalışır</li>
                </ul>
              </div>

              {/* Manual Trigger Buttons */}
              <div className="bg-muted/50 p-4 rounded-md">
                <h4 className="font-medium mb-3">Manuel Senkronizasyon</h4>
                <p className="text-sm text-muted-foreground mb-3">
                  İsterseniz manuel olarak da senkronizasyon başlatabilirsiniz:
                </p>
                <div className="grid gap-2 md:grid-cols-2">
                  <Button
                    onClick={handleTriggerFullSync}
                    disabled={syncLoading || syncStatus?.is_running || false}
                    variant="outline"
                    className="w-full"
                  >
                    <Database className={`mr-2 h-4 w-4 ${syncLoading ? 'animate-spin' : ''}`} />
                    Tam Senkronizasyon Başlat
                  </Button>
                  <Button
                    onClick={handleTriggerLiveSync}
                    disabled={syncLoading || syncStatus?.is_running || false}
                    variant="outline"
                    className="w-full"
                  >
                    <RefreshCw className={`mr-2 h-4 w-4 ${syncLoading ? 'animate-spin' : ''}`} />
                    Canlı Senkronizasyon Başlat
                  </Button>
                </div>
                {syncStatus?.is_running && (
                  <p className="text-xs text-orange-600 dark:text-orange-400 mt-2 text-center">
                    ⚠️ Senkronizasyon şu anda çalışıyor, lütfen bekleyin...
                  </p>
                )}
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Trendyol Sync Card */}
        <Card className="border-2 border-orange-200 dark:border-orange-800">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <ShoppingBag className="h-5 w-5 text-orange-600" />
              Trendyol Senkronizasyonu
            </CardTitle>
            <CardDescription>
              Trendyol siparişlerini direkt Trendyol API'sinden çekin
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {/* Info Box */}
              <div className="bg-orange-50 dark:bg-orange-950 p-4 rounded-md border border-orange-200 dark:border-orange-800">
                <h4 className="font-medium mb-2 text-orange-900 dark:text-orange-100">🎯 Direkt Entegrasyon</h4>
                <p className="text-sm text-orange-800 dark:text-orange-200 mb-2">
                  Trendyol siparişleri artık <strong>doğrudan Trendyol API'sinden</strong> çekiliyor. 
                  Sentos üzerinden gelen Trendyol verileri otomatik olarak filtreleniyor.
                </p>
                <ul className="text-sm text-orange-800 dark:text-orange-200 space-y-1 list-disc list-inside">
                  <li><strong>Daha güncel veriler:</strong> Trendyol'dan direkt veri akışı</li>
                  <li><strong>Otomatik sync:</strong> Arka planda günlük ve canlı olarak çalışır</li>
                  <li><strong>Manuel kontrol:</strong> İstediğiniz zaman manuel sync yapabilirsiniz</li>
                </ul>
              </div>

              {/* Connection Status */}
              {trendyolConnectionStatus && (
                <div className={`p-4 rounded-md border ${
                  trendyolConnectionStatus.status === 'success' 
                    ? 'bg-green-50 dark:bg-green-950 border-green-200 dark:border-green-800'
                    : 'bg-red-50 dark:bg-red-950 border-red-200 dark:border-red-800'
                }`}>
                  <h4 className={`font-medium mb-2 ${
                    trendyolConnectionStatus.status === 'success'
                      ? 'text-green-900 dark:text-green-100'
                      : 'text-red-900 dark:text-red-100'
                  }`}>
                    {trendyolConnectionStatus.status === 'success' ? '✅ Bağlantı Başarılı' : '❌ Bağlantı Hatası'}
                  </h4>
                  <p className={`text-sm ${
                    trendyolConnectionStatus.status === 'success'
                      ? 'text-green-800 dark:text-green-200'
                      : 'text-red-800 dark:text-red-200'
                  }`}>
                    {trendyolConnectionStatus.message}
                  </p>
                  {trendyolConnectionStatus.test_query && (
                    <p className="text-xs mt-2 text-green-700 dark:text-green-300">
                      Toplam {trendyolConnectionStatus.test_query.total_elements} sipariş bulundu
                    </p>
                  )}
                </div>
              )}

              {/* Days Selector */}
              <div>
                <label className="text-sm font-medium mb-2 block">Son Kaç Günün Verisi Çekilecek?</label>
                <select
                  value={trendyolDays}
                  onChange={(e) => setTrendyolDays(Number(e.target.value))}
                  className="w-full px-3 py-2 border rounded-md"
                  disabled={trendyolSyncing}
                >
                  <option value={1}>Son 1 gün</option>
                  <option value={3}>Son 3 gün</option>
                  <option value={7}>Son 7 gün</option>
                  <option value={14}>Son 14 gün (önerilen)</option>
                  <option value={30}>Son 30 gün</option>
                  <option value={60}>Son 60 gün (2 ay)</option>
                  <option value={90}>Son 90 gün (3 ay)</option>
                </select>
                <p className="text-xs text-muted-foreground mt-1">
                  Otomatik sync her gün son 7 günü çeker. Manuel sync için 1-90 gün arası seçebilirsiniz.
                </p>
              </div>

              {/* Last Sync Info */}
              {trendyolLastSync && (
                <div className="bg-muted/50 p-3 rounded-md">
                  <p className="text-sm text-muted-foreground">
                    <strong>Son Sync:</strong> {formatSyncTime(trendyolLastSync)}
                  </p>
                </div>
              )}

              {/* Action Buttons */}
              <div className="grid gap-2 md:grid-cols-2">
                <Button
                  onClick={handleTestTrendyolConnection}
                  disabled={trendyolSyncing}
                  variant="outline"
                  className="w-full"
                >
                  <RefreshCw className="mr-2 h-4 w-4" />
                  Bağlantıyı Test Et
                </Button>
                <Button
                  onClick={handleSyncTrendyol}
                  disabled={trendyolSyncing}
                  className="w-full bg-orange-600 hover:bg-orange-700"
                >
                  <ShoppingBag className={`mr-2 h-4 w-4 ${trendyolSyncing ? 'animate-spin' : ''}`} />
                  {trendyolSyncing ? 'Senkronize ediliyor...' : `Trendyol Siparişlerini Çek`}
                </Button>
              </div>

              {/* Warning */}
              <div className="bg-yellow-50 dark:bg-yellow-950 p-4 rounded-md border border-yellow-200 dark:border-yellow-800">
                <h4 className="font-medium mb-2 text-yellow-900 dark:text-yellow-100">⚠️ Önemli</h4>
                <ul className="text-sm text-yellow-800 dark:text-yellow-200 space-y-1 list-disc list-inside">
                  <li>Trendyol credentials (TRENDYOL_SUPPLIER_ID, TRENDYOL_API_SECRET) .env dosyasında tanımlanmalı</li>
                  <li>Credentials eksikse otomatik sync çalışmaz</li>
                  <li>Bağlantı testi ile credentials'ları kontrol edebilirsiniz</li>
                </ul>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Database className="h-5 w-5" />
              Ürün Senkronizasyonu
            </CardTitle>
            <CardDescription>
              Sentos API'den ürün bilgilerini ve görsellerini çekerek veritabanınızı güncelleyin
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              <div className="bg-muted/50 p-4 rounded-md">
                <h4 className="font-medium mb-2">Nedir?</h4>
                <p className="text-sm text-muted-foreground">
                  Ürün senkronizasyonu, Sentos sistemindeki tüm ürünlerin bilgilerini (SKU, maliyet, vs.) 
                  ve <strong>ürün görsellerini</strong> yerel veritabanınıza aktarır. Bu işlem, satış analizlerinde 
                  doğru maliyet hesaplamaları yapabilmek ve ürün performans sayfasında görsellerin görünmesi için gereklidir.
                </p>
              </div>
              <div className="bg-blue-50 dark:bg-blue-950 p-4 rounded-md border border-blue-200 dark:border-blue-800">
                <h4 className="font-medium mb-2 text-blue-900 dark:text-blue-100">💡 Ne Zaman Kullanılmalı?</h4>
                <ul className="text-sm text-blue-800 dark:text-blue-200 space-y-1 list-disc list-inside">
                  <li>İlk kurulumda mutlaka çalıştırın</li>
                  <li>Yeni ürün eklendiğinde</li>
                  <li>Ürün maliyetleri güncellendiğinde</li>
                  <li>Ürün görselleri eksik veya güncel değilse</li>
                  <li>Ayda bir düzenli olarak (görseller ve maliyetler için)</li>
                </ul>
              </div>
              
              {/* Image Sync Info */}
              <div className="bg-green-50 dark:bg-green-950 p-4 rounded-md border border-green-200 dark:border-green-800">
                <h4 className="font-medium mb-2 text-green-900 dark:text-green-100">🖼️ Ürün Görselleri</h4>
                <p className="text-sm text-green-800 dark:text-green-200">
                  Bu işlem sırasında ürünlerin <strong>ilk görselleri otomatik olarak</strong> Sentos'tan çekilip 
                  veritabanına kaydedilir. Ürün Performans sayfasında görseller bu şekilde görüntülenir.
                </p>
                <p className="text-sm text-green-800 dark:text-green-200 mt-2">
                  💡 <strong>Gelişmiş Arama:</strong> Görseller ürünün ana bilgilerinden bulunamazsa, 
                  varyantların (renk/beden) görselleri otomatik olarak çekilir.
                </p>
              </div>
              
              {/* Max Pages Selector */}
              <div>
                <label className="text-sm font-medium mb-2 block">Maksimum Sayfa Sayısı</label>
                <select
                  value={maxPages}
                  onChange={(e) => setMaxPages(Number(e.target.value))}
                  className="w-full px-3 py-2 border rounded-md"
                  disabled={syncing || fetching}
                >
                  <option value={10}>10 sayfa (~1,000 ürün)</option>
                  <option value={25}>25 sayfa (~2,500 ürün)</option>
                  <option value={50}>50 sayfa (~5,000 ürün)</option>
                  <option value={100}>100 sayfa (~10,000 ürün)</option>
                  <option value={200}>200 sayfa (~20,000 ürün)</option>
                  <option value={500}>500 sayfa (~50,000 ürün)</option>
                  <option value={1000}>1000 sayfa (TÜM ÜRÜNLER - ~100,000)</option>
                </select>
                <p className="text-xs text-muted-foreground mt-1">
                  Her sayfa 100 ürün içerir. Tüm ürünlerinizi çekmek için yeterli sayfa seçin.
                </p>
              </div>
              
              <Button 
                onClick={handleSyncProducts} 
                disabled={syncing || fetching}
                className="w-full"
                size="lg"
              >
                <Database className={`mr-2 h-4 w-4 ${syncing ? 'animate-spin' : ''}`} />
                {syncing ? 'Senkronize ediliyor...' : `Ürünleri Senkronize Et (${maxPages} sayfa)`}
              </Button>
            </div>
          </CardContent>
        </Card>

        {/* Sales Data Fetch Card */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Download className="h-5 w-5" />
              Satış Verilerini Çek
            </CardTitle>
            <CardDescription>
              Belirtilen tarih aralığındaki satış verilerini Sentos API'den çekin
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              <div className="bg-muted/50 p-4 rounded-md">
                <h4 className="font-medium mb-2">Nedir?</h4>
                <p className="text-sm text-muted-foreground">
                  Bu işlem, seçtiğiniz tarih aralığındaki tüm siparişleri ve sipariş detaylarını 
                  Sentos API'den çekerek veritabanınıza kaydeder. Analizler bu veriler üzerinden yapılır.
                </p>
              </div>
              
              <div className="grid gap-4 md:grid-cols-2">
                <div>
                  <label className="text-sm font-medium mb-2 block">Başlangıç Tarihi</label>
                  <input
                    type="date"
                    value={startDate}
                    onChange={(e) => setStartDate(e.target.value)}
                    className="w-full px-3 py-2 border rounded-md"
                  />
                </div>
                <div>
                  <label className="text-sm font-medium mb-2 block">Bitiş Tarihi</label>
                  <input
                    type="date"
                    value={endDate}
                    onChange={(e) => setEndDate(e.target.value)}
                    className="w-full px-3 py-2 border rounded-md"
                  />
                </div>
              </div>

              <div className="bg-orange-50 dark:bg-orange-950 p-4 rounded-md border border-orange-200 dark:border-orange-800">
                <h4 className="font-medium mb-2 text-orange-900 dark:text-orange-100">⚠️ Önemli Notlar</h4>
                <ul className="text-sm text-orange-800 dark:text-orange-200 space-y-1 list-disc list-inside">
                  <li>Önce ürün senkronizasyonu yapmalısınız</li>
                  <li>Geniş tarih aralıkları için işlem uzun sürebilir</li>
                  <li>Mevcut veriler güncellenir, silinmez</li>
                  <li>İlk kullanımda tüm geçmiş verilerinizi çekin</li>
                </ul>
              </div>

              <Button 
                onClick={handleFetchData} 
                disabled={fetching || syncing}
                className="w-full"
                size="lg"
              >
                <Download className={`mr-2 h-4 w-4 ${fetching ? 'animate-spin' : ''}`} />
                {fetching ? 'Çekiliyor...' : 'Satış Verilerini Çek'}
              </Button>
            </div>
          </CardContent>
        </Card>

        {/* Workflow Guide */}
        <Card className="bg-gradient-to-br from-purple-50 to-blue-50 dark:from-purple-950 dark:to-blue-950">
          <CardHeader>
            <CardTitle>📋 İş Akışı Rehberi</CardTitle>
            <CardDescription>Doğru sırada işlem yapın</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              <div className="flex items-start gap-3">
                <div className="flex-shrink-0 w-8 h-8 rounded-full bg-primary text-primary-foreground flex items-center justify-center font-bold">
                  1
                </div>
                <div>
                  <h4 className="font-medium">Ürünleri Senkronize Et</h4>
                  <p className="text-sm text-muted-foreground">
                    İlk olarak tüm ürün bilgilerini sisteme aktarın
                  </p>
                </div>
              </div>
              <div className="flex items-start gap-3">
                <div className="flex-shrink-0 w-8 h-8 rounded-full bg-primary text-primary-foreground flex items-center justify-center font-bold">
                  2
                </div>
                <div>
                  <h4 className="font-medium">Satış Verilerini Çek</h4>
                  <p className="text-sm text-muted-foreground">
                    İstediğiniz tarih aralığındaki satış verilerini çekin
                  </p>
                </div>
              </div>
              <div className="flex items-start gap-3">
                <div className="flex-shrink-0 w-8 h-8 rounded-full bg-primary text-primary-foreground flex items-center justify-center font-bold">
                  3
                </div>
                <div>
                  <h4 className="font-medium">Analiz Sayfasına Git</h4>
                  <p className="text-sm text-muted-foreground">
                    Veri Analiz sayfasından raporlarınızı görüntüleyin
                  </p>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
};

export default Settings;
