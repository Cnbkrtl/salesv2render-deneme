import React from 'react';
import { Link, useLocation } from 'react-router-dom';
import { Home, BarChart3, TrendingUp, Settings, Shield } from 'lucide-react';

interface LayoutProps {
  children: React.ReactNode;
}

const Layout: React.FC<LayoutProps> = ({ children }) => {
  const location = useLocation();

  const navItems = [
    { path: '/', label: 'Canlı Görünüm', icon: Home },
    { path: '/analytics', label: 'Veri Analiz', icon: BarChart3 },
    { path: '/product-performance', label: 'Ürün Performans', icon: TrendingUp },
    { path: '/settings', label: 'Ayarlar', icon: Settings },
    { path: '/admin', label: 'Admin Panel', icon: Shield },
  ];

  const isActive = (path: string) => {
    return location.pathname === path;
  };

  return (
    <div className="min-h-screen bg-background">
      {/* Top Navigation */}
      <nav className="bg-card border-b border-border sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-8">
          <div className="flex items-center justify-between h-16">
            <div className="flex items-center gap-2">
              <BarChart3 className="h-6 w-6 text-primary" />
              <h1 className="text-xl font-bold">Satış Analiz Paneli</h1>
            </div>
            
            <div className="flex gap-1">
              {navItems.map((item) => {
                const Icon = item.icon;
                return (
                  <Link
                    key={item.path}
                    to={item.path}
                    className={`flex items-center gap-2 px-4 py-2 rounded-md transition-colors ${
                      isActive(item.path)
                        ? 'bg-primary text-primary-foreground'
                        : 'text-muted-foreground hover:bg-muted hover:text-foreground'
                    }`}
                  >
                    <Icon className="h-4 w-4" />
                    <span className="font-medium">{item.label}</span>
                  </Link>
                );
              })}
            </div>
          </div>
        </div>
      </nav>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto p-8">
        {children}
      </main>
    </div>
  );
};

export default Layout;
