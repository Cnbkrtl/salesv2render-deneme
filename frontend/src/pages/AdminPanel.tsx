import React, { useState } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/Card';
import { Button } from '../components/ui/Button';
import { AlertTriangle, Database, RefreshCw, Trash2 } from 'lucide-react';
import apiClient from '../lib/api';

const AdminPanel: React.FC = () => {
  const [loading, setLoading] = useState(false);
  const [stats, setStats] = useState<any>(null);
  const [result, setResult] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const loadStats = async () => {
    try {
      const response = await apiClient.get('/api/admin/database-stats');
      setStats(response.data);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'İstatistikler yüklenemedi');
    }
  };

  React.useEffect(() => {
    loadStats();
  }, []);

  const handleFullResync = async () => {
    if (!window.confirm('⚠️ DİKKAT! Bu işlem database\'i temizleyip yeniden sync yapacak. Devam etmek istiyor musunuz?')) {
      return;
    }

    const startDate = window.prompt('Başlangıç tarihi (YYYY-MM-DD):', '2025-10-01');
    const endDate = window.prompt('Bitiş tarihi (YYYY-MM-DD):', '2025-10-17');

    if (!startDate || !endDate) {
      setError('Tarih girilmedi');
      return;
    }

    setLoading(true);
    setError(null);
    setResult(null);

    try {
      const response = await apiClient.post('/api/admin/full-resync', null, {
        params: {
          start_date: startDate,
          end_date: endDate,
          clear_first: true
        }
      });

      // 🆕 Background task başladı - status takip et
      if (response.data.status === 'started') {
        setResult('✅ Resync başlatıldı! Arkaplanda devam ediyor...\n\n📊 İlerlemeyi takip etmek için sayfayı yenileyin.');
        
        // Auto-refresh status her 5 saniyede bir
        const interval = setInterval(async () => {
          try {
            const statusRes = await apiClient.get('/api/admin/resync-status');
            
            if (!statusRes.data.running) {
              clearInterval(interval);
              
              if (statusRes.data.error) {
                setError(`❌ Resync hatası: ${statusRes.data.error}`);
              } else if (statusRes.data.result) {
                setResult(
                  `✅ Resync tamamlandı!\n` +
                  `- Ürünler: ${statusRes.data.result.products_synced}\n` +
                  `- Siparişler: ${statusRes.data.result.orders_synced}\n` +
                  `- Items: ${statusRes.data.result.items_synced}\n` +
                  `- Süre: ${statusRes.data.result.duration_seconds?.toFixed(1)}s`
                );
                await loadStats();
              }
            } else {
              setResult(`🔄 ${statusRes.data.progress}\n\nBaşlangıç: ${new Date(statusRes.data.start_time).toLocaleTimeString()}`);
            }
          } catch (e) {
            console.error('Status check error:', e);
          }
        }, 5000);
        
        // 10 dakika sonra interval'i durdur
        setTimeout(() => clearInterval(interval), 600000);
      } else {
        // Legacy response format (eski API)
        setResult(
          `✅ Başarılı!\n` +
          `- Ürünler: ${response.data.products_synced}\n` +
          `- Siparişler: ${response.data.orders_synced}\n` +
          `- Items: ${response.data.items_synced}\n` +
          `- Süre: ${response.data.duration_seconds.toFixed(1)}s`
        );
        await loadStats();
      }
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Resync başarısız!');
    } finally {
      setLoading(false);
    }
  };

  const handleResetDatabase = async () => {
    const confirm = window.prompt('⚠️⚠️⚠️ ÇOOOK TEHLİKELİ!\n\nTÜM sipariş verileri silinecek!\n\nDevam etmek için "CONFIRM" yazın:');
    
    if (confirm !== 'CONFIRM') {
      setError('İptal edildi');
      return;
    }

    setLoading(true);
    setError(null);
    setResult(null);

    try {
      const response = await apiClient.post('/api/admin/reset-database', null, {
        params: { confirm: 'CONFIRM' }
      });

      setResult(`✅ Database temizlendi!\n- Siparişler: ${response.data.orders_deleted}\n- Items: ${response.data.items_deleted}`);
      await loadStats();
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Reset başarısız!');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-8">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold">⚙️ Admin Panel</h1>
        <p className="text-muted-foreground mt-2">
          Database yönetimi ve bakım işlemleri
        </p>
      </div>

      {/* Stats */}
      {stats && (
        <Card>
          <CardHeader>
            <CardTitle>📊 Database İstatistikleri</CardTitle>
            <CardDescription>Mevcut veri durumu</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div>
                <p className="text-sm text-muted-foreground">Ürünler</p>
                <p className="text-2xl font-bold">{stats.products}</p>
              </div>
              <div>
                <p className="text-sm text-muted-foreground">Siparişler</p>
                <p className="text-2xl font-bold">{stats.orders}</p>
              </div>
              <div>
                <p className="text-sm text-muted-foreground">Items</p>
                <p className="text-2xl font-bold">{stats.items}</p>
              </div>
              <div>
                <p className="text-sm text-muted-foreground">Tarih Aralığı</p>
                <p className="text-sm font-medium">
                  {stats.date_range.min} / {stats.date_range.max}
                </p>
              </div>
            </div>

            {stats.status_distribution && (
              <div className="mt-4 pt-4 border-t">
                <p className="text-sm font-medium mb-2">Status Dağılımı:</p>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-2 text-xs">
                  {Object.entries(stats.status_distribution).map(([status, count]) => (
                    <div key={status} className="flex justify-between">
                      <span className="text-muted-foreground">Status {status}:</span>
                      <span className="font-medium">{count as number}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {/* Actions */}
      <div className="grid md:grid-cols-2 gap-4">
        {/* Full Resync */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <RefreshCw className="h-5 w-5" />
              Full Resync
            </CardTitle>
            <CardDescription>
              Database'i temizleyip yeniden sync yapar
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              <div className="text-sm space-y-2">
                <p>Bu işlem:</p>
                <ul className="list-disc list-inside space-y-1 text-muted-foreground">
                  <li>Seçilen tarihleri database'den siler</li>
                  <li>Ürünleri Sentos'tan çeker (batch)</li>
                  <li>Siparişleri yeniden sync eder</li>
                  <li>~1-3 dakika sürer</li>
                </ul>
              </div>

              <Button
                onClick={handleFullResync}
                disabled={loading}
                className="w-full"
              >
                <RefreshCw className={`mr-2 h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
                Full Resync Başlat
              </Button>
            </div>
          </CardContent>
        </Card>

        {/* Reset Database */}
        <Card className="border-destructive">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-destructive">
              <AlertTriangle className="h-5 w-5" />
              Database Reset
            </CardTitle>
            <CardDescription>
              ⚠️ TEHLİKELİ! TÜM sipariş verileri silinir
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              <div className="text-sm space-y-2">
                <p className="font-medium text-destructive">DİKKAT:</p>
                <ul className="list-disc list-inside space-y-1 text-muted-foreground">
                  <li>TÜM siparişler silinir</li>
                  <li>TÜM items silinir</li>
                  <li>Ürünler korunur</li>
                  <li>GERİ ALINAMAZ!</li>
                </ul>
              </div>

              <Button
                onClick={handleResetDatabase}
                disabled={loading}
                variant="destructive"
                className="w-full"
              >
                <Trash2 className="mr-2 h-4 w-4" />
                Database'i Sıfırla
              </Button>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Result/Error */}
      {result && (
        <Card className="border-green-500 bg-green-50">
          <CardContent className="pt-6">
            <pre className="whitespace-pre-wrap text-sm">{result}</pre>
          </CardContent>
        </Card>
      )}

      {error && (
        <Card className="border-destructive bg-destructive/10">
          <CardContent className="pt-6">
            <p className="text-destructive">{error}</p>
          </CardContent>
        </Card>
      )}
    </div>
  );
};

export default AdminPanel;
