import React, { useState } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/Card';
import { Button } from '../components/ui/Button';
import { syncProducts, fetchSalesData } from '../lib/api-service';
import { Database, Download, Settings as SettingsIcon } from 'lucide-react';
import { format, subDays } from 'date-fns';

const Settings: React.FC = () => {
  const [syncing, setSyncing] = useState(false);
  const [fetching, setFetching] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [startDate, setStartDate] = useState(format(subDays(new Date(), 7), 'yyyy-MM-dd'));
  const [endDate, setEndDate] = useState(format(new Date(), 'yyyy-MM-dd'));
  const [maxPages, setMaxPages] = useState<number>(50); // Varsayılan 50 sayfa (5000 ürün)

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
        
        {/* Product Sync Card */}
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
