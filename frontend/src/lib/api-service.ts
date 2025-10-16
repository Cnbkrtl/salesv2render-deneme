import apiClient from './api';

// Types
export interface SalesMetrics {
  total_orders: number;
  gross_revenue: number;
  cancelled_revenue: number;
  net_revenue: number;
  total_cost: number;
  shipping_expense: number;
  marketplace_commission?: number;  // 🆕 YENİ
  profit: number;
  profit_margin: number;
  avg_order_value: number;
  marketplace_breakdown: Record<string, {
    orders: number;
    revenue: number;
  }>;
}

export interface AnalyzeResponse {
  summary: {
    brut: {
      brut_ciro: number;
      brut_siparis_sayisi: number;
      brut_satilan_adet: number;
      kargo_ucreti_toplam: number;
    };
    iptal_iade: {
      iptal_iade_ciro: number;
      iptal_iade_siparis_sayisi: number;
      iptal_iade_adet: number;
    };
    net: {
      net_ciro: number;
      net_siparis_sayisi: number;
      net_satilan_adet: number;
    };
    karlilik: {
      urun_maliyeti_kdvli: number;
      kargo_gideri: number;
      marketplace_komisyon?: number;  // 🆕 YENİ
      kar: number;
      kar_marji: number;
    };
  };
  by_marketplace: Array<{
    marketplace: string;
    brut: any;
    iptal_iade: any;
    net: {
      net_ciro: number;
      net_siparis_sayisi: number;
    };
    karlilik: any;
  }>;
  by_product: any[];
  by_date: any[];
}

export interface FetchDataRequest {
  start_date: string;
  end_date: string;
  marketplace?: string;
  status?: number;
  max_pages?: number;
}

export interface AnalyzeRequest {
  start_date: string;
  end_date: string;
  marketplace?: string;
  cache_ttl?: number;
}

// API Functions
export const healthCheck = async () => {
  const response = await apiClient.get('/health');
  return response.data;
};

export const syncProducts = async (maxPages: number = 50) => {
  console.log('📡 API: syncProducts çağrılıyor', { maxPages });
  console.log('📡 URL:', '/api/data/sync-products');
  console.log('📡 Params:', { max_pages: maxPages });
  
  try {
    const response = await apiClient.post('/api/data/sync-products', null, {
      params: { max_pages: maxPages }
    });
    console.log('✅ API Response:', response.data);
    return response.data;
  } catch (error) {
    console.error('❌ API Error:', error);
    throw error;
  }
};

export const fetchSalesData = async (params: FetchDataRequest) => {
  const response = await apiClient.post('/api/data/fetch', params);
  return response.data;
};

export const analyzeSales = async (params: AnalyzeRequest) => {
  const response = await apiClient.post<AnalyzeResponse>('/api/analytics/analyze', params);
  return response.data;
};

// Analyze sonucunu metrics formatına çevir
export const getMetrics = async (
  startDate: string,
  endDate: string,
  marketplace?: string
): Promise<SalesMetrics> => {
  const analyzeResult = await analyzeSales({
    start_date: startDate,
    end_date: endDate,
    marketplace,
  });
  
  // Backend response'ı frontend formatına dönüştür
  const { summary, by_marketplace } = analyzeResult;
  
  return {
    total_orders: summary.net.net_siparis_sayisi,
    gross_revenue: summary.brut.brut_ciro,
    cancelled_revenue: summary.iptal_iade.iptal_iade_ciro,
    net_revenue: summary.net.net_ciro,
    total_cost: summary.karlilik.urun_maliyeti_kdvli,
    shipping_expense: summary.karlilik.kargo_gideri,
    marketplace_commission: summary.karlilik.marketplace_komisyon,  // 🆕 YENİ
    profit: summary.karlilik.kar,
    profit_margin: summary.karlilik.kar_marji,
    avg_order_value: summary.net.net_ciro / summary.net.net_siparis_sayisi || 0,
    marketplace_breakdown: by_marketplace.reduce((acc, mp) => {
      acc[mp.marketplace] = {
        orders: mp.net.net_siparis_sayisi,
        revenue: mp.net.net_ciro,
      };
      return acc;
    }, {} as Record<string, { orders: number; revenue: number }>),
  };
};

// Sync Status Types
export interface SyncStatus {
  is_running: boolean;
  last_full_sync: string | null;
  last_live_sync: string | null;
  full_sync_time: string;
  live_sync_interval_minutes: number;
  timestamp: string;
}

// Get sync status
export const getSyncStatus = async (): Promise<SyncStatus> => {
  const response = await apiClient.get('/api/sync/status');
  return response.data;
};

// Trigger full sync
export const triggerFullSync = async (): Promise<{status: string; message: string}> => {
  const response = await apiClient.post('/api/sync/trigger/full');
  return response.data;
};

// Trigger live sync
export const triggerLiveSync = async (): Promise<{status: string; message: string}> => {
  const response = await apiClient.post('/api/sync/trigger/live');
  return response.data;
};
