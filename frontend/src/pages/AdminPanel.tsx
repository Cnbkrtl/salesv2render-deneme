import React, { useState } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/Card';
import { Button } from '../components/ui/Button';
import { ProgressBar } from '../components/ui/ProgressBar';
import { AlertTriangle, Database, RefreshCw, Trash2, Moon, Sun, CheckCircle2, Clock, TrendingUp } from 'lucide-react';
import apiClient from '../lib/api';

interface ResyncStatus {
  running: boolean;
  progress: string;
  start_time?: string;
  result?: {
    products_synced: number;
    orders_synced: number;
    items_synced: number;
    duration_seconds: number;
  };
  error?: string;
}

const AdminPanel: React.FC = () => {
  const [loading, setLoading] = useState(false);
  const [stats, setStats] = useState<any>(null);
  const [result, setResult] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [darkMode, setDarkMode] = useState(false);
  
  // Resync progress tracking
  const [resyncStatus, setResyncStatus] = useState<ResyncStatus | null>(null);
  const [resyncProgress, setResyncProgress] = useState(0);
  const [estimatedTimeLeft, setEstimatedTimeLeft] = useState<string>('');

  React.useEffect(() => {
    if (darkMode) {
      document.documentElement.classList.add('dark');
    } else {
      document.documentElement.classList.remove('dark');
    }
  }, [darkMode]);

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
    setResyncStatus(null);
    setResyncProgress(0);

    try {
      const response = await apiClient.post('/api/admin/full-resync', null, {
        params: {
          start_date: startDate,
          end_date: endDate,
          clear_first: true
        }
      });

      // Background task başladı - status takip et
      if (response.data.status === 'started') {
        const startTime = Date.now();
        
        // Auto-refresh status her 3 saniyede bir
        const interval = setInterval(async () => {
          try {
            const statusRes = await apiClient.get('/api/admin/resync-status');
            const status: ResyncStatus = statusRes.data;
            setResyncStatus(status);
            
            // Progress hesapla (phases: clean=10%, products=30%, orders=60%)
            let calculatedProgress = 0;
            if (status.progress.includes('temizleniyor')) calculatedProgress = 10;
            else if (status.progress.includes('Products')) calculatedProgress = 30;
            else if (status.progress.includes('Orders')) calculatedProgress = 60;
            else if (status.progress.includes('Tamamlandı')) calculatedProgress = 100;
            
            setResyncProgress(calculatedProgress);
            
            // Tahmini süre (basit heuristic)
            const elapsed = (Date.now() - startTime) / 1000;
            if (calculatedProgress > 0 && calculatedProgress < 100) {
              const totalEstimated = (elapsed / calculatedProgress) * 100;
              const remaining = totalEstimated - elapsed;
              const mins = Math.floor(remaining / 60);
              const secs = Math.floor(remaining % 60);
              setEstimatedTimeLeft(`~${mins}dk ${secs}sn`);
            }
            
            if (!status.running) {
              clearInterval(interval);
              setLoading(false);
              
              if (status.error) {
                setError(`❌ Resync hatası: ${status.error}`);
                setResyncProgress(0);
              } else if (status.result) {
                setResult(
                  `✅ Resync tamamlandı!\n` +
                  `- Ürünler: ${status.result.products_synced}\n` +
                  `- Siparişler: ${status.result.orders_synced}\n` +
                  `- Items: ${status.result.items_synced}\n` +
                  `- Süre: ${status.result.duration_seconds?.toFixed(1)}s`
                );
                setResyncProgress(100);
                await loadStats();
              }
            }
          } catch (e) {
            console.error('Status check error:', e);
          }
        }, 3000);
        
        // 15 dakika sonra interval'i durdur
        setTimeout(() => {
          clearInterval(interval);
          setLoading(false);
        }, 900000);
      } else {
        // Legacy response format
        setResult(
          `✅ Başarılı!\n` +
          `- Ürünler: ${response.data.products_synced}\n` +
          `- Siparişler: ${response.data.orders_synced}\n` +
          `- Items: ${response.data.items_synced}\n` +
          `- Süre: ${response.data.duration_seconds.toFixed(1)}s`
        );
        setResyncProgress(100);
        await loadStats();
        setLoading(false);
      }
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Resync başarısız!');
      setLoading(false);
      setResyncProgress(0);
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
    <div className="min-h-screen bg-gradient-to-br from-gray-50 via-gray-100 to-gray-200 dark:from-gray-900 dark:via-gray-800 dark:to-gray-900 transition-all duration-500">
      <div className="max-w-7xl mx-auto p-6 space-y-8">
        {/* Header with Dark Mode Toggle */}
        <div className="flex justify-between items-center">
          <div>
            <h1 className="text-5xl font-extrabold bg-gradient-to-r from-blue-600 via-purple-600 to-pink-600 dark:from-blue-400 dark:via-purple-400 dark:to-pink-400 bg-clip-text text-transparent">
              ⚙️ Admin Panel
            </h1>
            <p className="text-gray-600 dark:text-gray-400 mt-2 text-lg">
              Database yönetimi ve bakım işlemleri
            </p>
          </div>
          <Button
            onClick={() => setDarkMode(!darkMode)}
            variant="outline"
            className="flex items-center gap-2 px-6 py-3 rounded-xl shadow-lg hover:shadow-xl transition-all duration-300 border-2 dark:border-gray-600 hover:scale-105"
          >
            {darkMode ? <Sun className="w-5 h-5 text-yellow-500" /> : <Moon className="w-5 h-5 text-indigo-600" />}
            <span className="font-semibold">{darkMode ? 'Light Mode' : 'Dark Mode'}</span>
          </Button>
        </div>

        {/* Stats Card - Modern Gradient Design */}
        {stats && (
          <Card className="bg-gradient-to-br from-white via-blue-50 to-purple-50 dark:from-gray-800 dark:via-gray-800 dark:to-gray-900 border-2 border-blue-200 dark:border-gray-700 shadow-2xl">
            <CardHeader className="border-b-2 border-blue-100 dark:border-gray-700">
              <CardTitle className="text-3xl flex items-center gap-3">
                <Database className="w-8 h-8 text-blue-600 dark:text-blue-400" />
                <span className="bg-gradient-to-r from-blue-600 to-purple-600 dark:from-blue-400 dark:to-purple-400 bg-clip-text text-transparent">
                  Database İstatistikleri
                </span>
              </CardTitle>
              <CardDescription className="dark:text-gray-400 text-base">Mevcut veri durumu - Gerçek zamanlı</CardDescription>
            </CardHeader>
            <CardContent className="pt-6">
              <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
                <div className="p-6 bg-gradient-to-br from-blue-500 to-blue-600 dark:from-blue-600 dark:to-blue-700 rounded-2xl shadow-lg transform hover:scale-105 transition-all duration-300">
                  <div className="flex items-center justify-between mb-3">
                    <p className="text-sm font-medium text-blue-100">Ürünler</p>
                    <CheckCircle2 className="w-5 h-5 text-blue-200" />
                  </div>
                  <p className="text-4xl font-black text-white">{stats.products?.toLocaleString('tr-TR')}</p>
                </div>
                
                <div className="p-6 bg-gradient-to-br from-green-500 to-green-600 dark:from-green-600 dark:to-green-700 rounded-2xl shadow-lg transform hover:scale-105 transition-all duration-300">
                  <div className="flex items-center justify-between mb-3">
                    <p className="text-sm font-medium text-green-100">Siparişler</p>
                    <TrendingUp className="w-5 h-5 text-green-200" />
                  </div>
                  <p className="text-4xl font-black text-white">{stats.orders?.toLocaleString('tr-TR')}</p>
                </div>
                
                <div className="p-6 bg-gradient-to-br from-purple-500 to-purple-600 dark:from-purple-600 dark:to-purple-700 rounded-2xl shadow-lg transform hover:scale-105 transition-all duration-300">
                  <div className="flex items-center justify-between mb-3">
                    <p className="text-sm font-medium text-purple-100">Items</p>
                    <CheckCircle2 className="w-5 h-5 text-purple-200" />
                  </div>
                  <p className="text-4xl font-black text-white">{stats.items?.toLocaleString('tr-TR')}</p>
                </div>
                
                <div className="p-6 bg-gradient-to-br from-orange-500 to-orange-600 dark:from-orange-600 dark:to-orange-700 rounded-2xl shadow-lg transform hover:scale-105 transition-all duration-300">
                  <div className="flex items-center justify-between mb-3">
                    <p className="text-sm font-medium text-orange-100">Tarih Aralığı</p>
                    <Clock className="w-5 h-5 text-orange-200" />
                  </div>
                  <p className="text-sm font-bold text-white">
                    {stats.date_range?.min || 'N/A'}
                  </p>
                  <p className="text-xs text-orange-100 my-1">→</p>
                  <p className="text-sm font-bold text-white">
                    {stats.date_range?.max || 'N/A'}
                  </p>
                </div>
              </div>

              {stats.status_distribution && (
                <div className="mt-8 pt-6 border-t-2 border-blue-100 dark:border-gray-700">
                  <p className="text-lg font-bold mb-4 text-gray-900 dark:text-white flex items-center gap-2">
                    <CheckCircle2 className="w-5 h-5 text-blue-600 dark:text-blue-400" />
                    Status Dağılımı
                  </p>
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                    {Object.entries(stats.status_distribution).map(([status, count]) => (
                      <div key={status} className="text-center p-4 bg-white dark:bg-gray-800 rounded-xl shadow-md border-2 border-gray-100 dark:border-gray-700 hover:border-blue-300 dark:hover:border-blue-600 transition-all duration-300">
                        <p className="text-xs font-medium text-gray-600 dark:text-gray-400 mb-1">Status {status}</p>
                        <p className="text-2xl font-bold text-gray-900 dark:text-white">{count as number}</p>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </CardContent>
          </Card>
        )}

        {/* Progress Bar - Modern Design with Animations */}
        {resyncStatus && (
          <Card className="border-2 border-blue-400 dark:border-blue-600 bg-gradient-to-br from-blue-50 to-indigo-50 dark:from-blue-950 dark:to-indigo-950 shadow-2xl">
            <CardHeader className="border-b-2 border-blue-200 dark:border-blue-800">
              <CardTitle className="flex items-center gap-3 text-2xl text-blue-900 dark:text-blue-100">
                <RefreshCw className={`w-6 h-6 ${resyncStatus.running ? 'animate-spin text-blue-600' : 'text-green-600'}`} />
                {resyncStatus.running ? 'Resync Devam Ediyor...' : 'Resync Tamamlandı!'}
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-6 pt-6">
              <ProgressBar
                progress={resyncProgress}
                label={resyncStatus.progress}
                subLabel={estimatedTimeLeft ? `⏱️ Tahmini kalan süre: ${estimatedTimeLeft}` : undefined}
                variant={resyncProgress === 100 ? 'success' : 'default'}
                animated={resyncStatus.running}
              />
              
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mt-6">
                <div className="flex items-center gap-3 p-4 bg-white dark:bg-gray-800 rounded-xl shadow-md border dark:border-gray-700">
                  <Clock className="w-6 h-6 text-blue-600 dark:text-blue-400" />
                  <div>
                    <p className="text-xs text-gray-600 dark:text-gray-400">Başlangıç</p>
                    <p className="text-sm font-bold text-gray-900 dark:text-white">
                      {resyncStatus.start_time ? new Date(resyncStatus.start_time).toLocaleTimeString('tr-TR') : 'N/A'}
                    </p>
                  </div>
                </div>
                
                <div className="flex items-center gap-3 p-4 bg-white dark:bg-gray-800 rounded-xl shadow-md border dark:border-gray-700">
                  <TrendingUp className="w-6 h-6 text-purple-600 dark:text-purple-400" />
                  <div>
                    <p className="text-xs text-gray-600 dark:text-gray-400">İlerleme</p>
                    <p className="text-lg font-black text-purple-600 dark:text-purple-400">
                      {resyncProgress.toFixed(0)}%
                    </p>
                  </div>
                </div>
                
                {resyncStatus.result && (
                  <div className="flex items-center gap-3 p-4 bg-gradient-to-r from-green-500 to-green-600 rounded-xl shadow-md">
                    <CheckCircle2 className="w-6 h-6 text-white" />
                    <div>
                      <p className="text-xs text-green-100">Siparişler</p>
                      <p className="text-lg font-black text-white">
                        {resyncStatus.result.orders_synced}
                      </p>
                    </div>
                  </div>
                )}
              </div>

              {resyncStatus.result && (
                <div className="mt-6 p-6 bg-gradient-to-r from-green-50 to-emerald-50 dark:from-green-900/20 dark:to-emerald-900/20 rounded-xl border-2 border-green-300 dark:border-green-700">
                  <p className="font-bold mb-4 text-green-900 dark:text-green-100 flex items-center gap-2 text-lg">
                    <CheckCircle2 className="w-5 h-5" />
                    Başarı İstatistikleri
                  </p>
                  <div className="grid md:grid-cols-3 gap-4">
                    <div className="text-center p-3 bg-white dark:bg-gray-800 rounded-lg">
                      <p className="text-xs text-gray-600 dark:text-gray-400 mb-1">Ürünler</p>
                      <p className="text-2xl font-bold text-blue-600 dark:text-blue-400">{resyncStatus.result.products_synced}</p>
                    </div>
                    <div className="text-center p-3 bg-white dark:bg-gray-800 rounded-lg">
                      <p className="text-xs text-gray-600 dark:text-gray-400 mb-1">Siparişler</p>
                      <p className="text-2xl font-bold text-green-600 dark:text-green-400">{resyncStatus.result.orders_synced}</p>
                    </div>
                    <div className="text-center p-3 bg-white dark:bg-gray-800 rounded-lg">
                      <p className="text-xs text-gray-600 dark:text-gray-400 mb-1">Süre</p>
                      <p className="text-2xl font-bold text-purple-600 dark:text-purple-400">{resyncStatus.result.duration_seconds?.toFixed(1)}s</p>
                    </div>
                  </div>
                </div>
              )}
            </CardContent>
          </Card>
        )}

        {/* Actions - Modern Card Design */}
        <div className="grid md:grid-cols-2 gap-6">
          {/* Full Resync */}
          <Card className="border-2 border-blue-300 dark:border-blue-700 hover:shadow-2xl transition-all duration-300 bg-white dark:bg-gray-800">
            <CardHeader className="border-b-2 border-blue-100 dark:border-blue-900">
              <CardTitle className="flex items-center gap-3 text-2xl">
                <RefreshCw className="h-6 w-6 text-blue-600 dark:text-blue-400" />
                <span className="text-blue-900 dark:text-blue-100">Full Resync</span>
              </CardTitle>
              <CardDescription className="text-base dark:text-gray-400">
                Database'i temizleyip yeniden sync yapar
              </CardDescription>
            </CardHeader>
            <CardContent className="pt-6">
              <div className="space-y-4">
                <div className="text-sm space-y-3 p-4 bg-blue-50 dark:bg-blue-900/20 rounded-lg border dark:border-blue-800">
                  <p className="font-semibold text-blue-900 dark:text-blue-100">Bu işlem:</p>
                  <ul className="list-disc list-inside space-y-2 text-gray-700 dark:text-gray-300">
                    <li>Seçilen tarihleri database'den siler</li>
                    <li>Ürünleri Sentos'tan çeker (batch)</li>
                    <li>Siparişleri yeniden sync eder</li>
                    <li>~1-3 dakika sürer</li>
                  </ul>
                </div>

                <Button
                  onClick={handleFullResync}
                  disabled={loading}
                  className="w-full h-12 text-base font-semibold bg-gradient-to-r from-blue-600 to-blue-700 hover:from-blue-700 hover:to-blue-800 dark:from-blue-500 dark:to-blue-600 shadow-lg hover:shadow-xl transition-all duration-300"
                >
                  <RefreshCw className={`mr-2 h-5 w-5 ${loading ? 'animate-spin' : ''}`} />
                  Full Resync Başlat
                </Button>
              </div>
            </CardContent>
          </Card>

          {/* Reset Database */}
          <Card className="border-2 border-red-400 dark:border-red-700 hover:shadow-2xl transition-all duration-300 bg-white dark:bg-gray-800">
            <CardHeader className="border-b-2 border-red-200 dark:border-red-900">
              <CardTitle className="flex items-center gap-3 text-2xl text-red-600 dark:text-red-400">
                <AlertTriangle className="h-6 w-6" />
                Database Reset
              </CardTitle>
              <CardDescription className="text-base dark:text-gray-400">
                ⚠️ TEHLİKELİ! TÜM sipariş verileri silinir
              </CardDescription>
            </CardHeader>
            <CardContent className="pt-6">
              <div className="space-y-4">
                <div className="text-sm space-y-3 p-4 bg-red-50 dark:bg-red-900/20 rounded-lg border-2 border-red-300 dark:border-red-800">
                  <p className="font-bold text-red-700 dark:text-red-300">⚠️ DİKKAT:</p>
                  <ul className="list-disc list-inside space-y-2 text-gray-700 dark:text-gray-300">
                    <li>TÜM siparişler silinir</li>
                    <li>TÜM items silinir</li>
                    <li>Ürünler korunur</li>
                    <li className="font-bold text-red-600 dark:text-red-400">GERİ ALINAMAZ!</li>
                  </ul>
                </div>

                <Button
                  onClick={handleResetDatabase}
                  disabled={loading}
                  variant="destructive"
                  className="w-full h-12 text-base font-semibold bg-gradient-to-r from-red-600 to-red-700 hover:from-red-700 hover:to-red-800 shadow-lg hover:shadow-xl transition-all duration-300"
                >
                  <Trash2 className="mr-2 h-5 w-5" />
                  Database'i Sıfırla
                </Button>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Result/Error Messages */}
        {result && (
          <Card className="border-2 border-green-400 bg-gradient-to-r from-green-50 to-emerald-50 dark:from-green-900/20 dark:to-emerald-900/20 shadow-xl">
            <CardContent className="pt-6">
              <div className="flex items-start gap-3">
                <CheckCircle2 className="w-6 h-6 text-green-600 dark:text-green-400 mt-1" />
                <pre className="whitespace-pre-wrap text-sm font-medium text-green-900 dark:text-green-100">{result}</pre>
              </div>
            </CardContent>
          </Card>
        )}

        {error && (
          <Card className="border-2 border-red-400 bg-gradient-to-r from-red-50 to-pink-50 dark:from-red-900/20 dark:to-pink-900/20 shadow-xl">
            <CardContent className="pt-6">
              <div className="flex items-start gap-3">
                <AlertTriangle className="w-6 h-6 text-red-600 dark:text-red-400 mt-1" />
                <p className="text-red-700 dark:text-red-300 font-medium">{error}</p>
              </div>
            </CardContent>
          </Card>
        )}
      </div>
    </div>
  );
};

export default AdminPanel;
