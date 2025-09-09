import React, { useState, useEffect, createContext, useContext } from "react";
import "./App.css";
import axios from "axios";
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
  ArcElement,
  BarElement,
} from 'chart.js';
import { Line, Pie, Bar } from 'react-chartjs-2';

ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
  ArcElement,
  BarElement
);

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

// Authentication Context
const AuthContext = createContext();

const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};

const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  // Check authentication on app start and handle URL fragments
  useEffect(() => {
    const checkAuth = async () => {
      try {
        // First, check for session_id in URL fragment (priority)
        const hash = window.location.hash;
        if (hash.includes('session_id=')) {
          const sessionId = hash.split('session_id=')[1].split('&')[0];
          
          // Authenticate with session ID
          const response = await axios.post(`${API}/auth/profile`, {
            session_id: sessionId
          }, { withCredentials: true });
          
          setUser(response.data.user);
          
          // Clear the fragment from URL
          window.location.hash = '';
          window.history.replaceState(null, null, '/profile');
          setLoading(false);
          return;
        }
        
        // If no fragment, check existing session
        const response = await axios.get(`${API}/auth/me`, { withCredentials: true });
        setUser(response.data);
      } catch (error) {
        console.log('Not authenticated');
        setUser(null);
      } finally {
        setLoading(false);
      }
    };

    checkAuth();
  }, []);

  const login = () => {
    const currentUrl = window.location.origin + '/profile';
    window.location.href = `https://auth.emergentagent.com/?redirect=${encodeURIComponent(currentUrl)}`;
  };

  const logout = async () => {
    try {
      await axios.post(`${API}/auth/logout`, {}, { withCredentials: true });
      setUser(null);
    } catch (error) {
      console.error('Logout error:', error);
      setUser(null);
    }
  };

  return (
    <AuthContext.Provider value={{ user, login, logout, loading }}>
      {children}
    </AuthContext.Provider>
  );
};

// Login Component
const LoginScreen = () => {
  const { login } = useAuth();

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 flex items-center justify-center p-4">
      <div className="bg-white rounded-2xl shadow-xl p-8 max-w-md w-full">
        <div className="text-center mb-8">
          <div className="w-16 h-16 bg-blue-600 rounded-full flex items-center justify-center mx-auto mb-4">
            <span className="text-white text-2xl font-bold">₿</span>
          </div>
          <h1 className="text-3xl font-bold text-gray-900 mb-2">Crypto PnL Tracker</h1>
          <p className="text-gray-600">Track your daily cryptocurrency portfolio performance</p>
        </div>
        
        <div className="space-y-4">
          <button
            onClick={login}
            className="w-full btn-primary flex items-center justify-center space-x-2 py-3"
          >
            <svg className="w-5 h-5" viewBox="0 0 24 24" fill="currentColor">
              <path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
              <path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
              <path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/>
              <path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/>
            </svg>
            <span>Continue with Google</span>
          </button>
          
          <div className="text-center text-sm text-gray-500">
            Secure authentication powered by Emergent
          </div>
        </div>
      </div>
    </div>
  );
};

// Mobile-Optimized PnL Tracker Component
const CryptoPnLTracker = () => {
  const { user, logout } = useAuth();
  const [entries, setEntries] = useState([]);
  const [stats, setStats] = useState({});
  const [chartData, setChartData] = useState({});
  const [monthlyPerformance, setMonthlyPerformance] = useState({});
  const [exchanges, setExchanges] = useState([]);
  const [kpis, setKPIs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showAddForm, setShowAddForm] = useState(false);
  const [showCharts, setShowCharts] = useState(false);
  const [showMonthlyView, setShowMonthlyView] = useState(false);
  const [showExchangeManager, setShowExchangeManager] = useState(false);
  const [showKPIManager, setShowKPIManager] = useState(false);
  const [showMobileMenu, setShowMobileMenu] = useState(false);
  const [editingEntry, setEditingEntry] = useState(null);
  const [formData, setFormData] = useState({
    date: new Date().toISOString().split('T')[0],
    balances: [],
    notes: ''
  });
  const [newExchange, setNewExchange] = useState({
    name: '',
    display_name: '',
    color: '#3B82F6'
  });
  const [newKPI, setNewKPI] = useState({
    name: '',
    target_amount: '',
    color: '#10B981'
  });
  const [editingKPI, setEditingKPI] = useState(null);

  // Configure axios defaults
  axios.defaults.withCredentials = true;

  // Initialize default exchanges and KPIs
  const initializeDefaults = async () => {
    try {
      await Promise.all([
        axios.post(`${API}/initialize-default-exchanges`),
        axios.post(`${API}/initialize-default-kpis`)
      ]);
    } catch (error) {
      console.error('Error initializing defaults:', error);
    }
  };

  // Fetch all data
  const fetchData = async () => {
    try {
      setLoading(true);
      
      // Initialize defaults first
      await initializeDefaults();
      
      const [entriesRes, statsRes, chartRes, monthlyRes, exchangesRes, kpisRes] = await Promise.all([
        axios.get(`${API}/entries`),
        axios.get(`${API}/stats`),
        axios.get(`${API}/chart-data`),
        axios.get(`${API}/monthly-performance`),
        axios.get(`${API}/exchanges`),
        axios.get(`${API}/kpis`)
      ]);
      
      setEntries(entriesRes.data);
      setStats(statsRes.data);
      setChartData(chartRes.data);
      setMonthlyPerformance(monthlyRes.data);
      setExchanges(exchangesRes.data);
      setKPIs(kpisRes.data);
      
      // Initialize form balances with exchanges
      const initialBalances = exchangesRes.data.map(exchange => ({
        exchange_id: exchange.id,
        amount: 0
      }));
      setFormData(prev => ({ ...prev, balances: initialBalances }));
      
    } catch (error) {
      console.error('Error fetching data:', error);
      if (error.response?.status === 401) {
        logout();
      }
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (user) {
      fetchData();
    }
  }, [user]);

  // Handle form input changes
  const handleInputChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: value
    }));
  };

  // Handle balance input changes
  const handleBalanceChange = (exchangeId, value) => {
    setFormData(prev => ({
      ...prev,
      balances: prev.balances.map(balance => 
        balance.exchange_id === exchangeId 
          ? { ...balance, amount: parseFloat(value) || 0 }
          : balance
      )
    }));
  };

  // Add new entry
  const handleAddEntry = async (e) => {
    e.preventDefault();
    try {
      const entryData = {
        date: formData.date,
        balances: formData.balances.filter(b => b.amount > 0),
        notes: formData.notes
      };

      await axios.post(`${API}/entries`, entryData);
      resetForm();
      setShowAddForm(false);
      fetchData();
    } catch (error) {
      console.error('Error adding entry:', error);
      alert('Error adding entry. Please try again.');
    }
  };

  // Edit entry
  const handleEditEntry = async (e) => {
    e.preventDefault();
    try {
      const updateData = {
        date: formData.date,
        balances: formData.balances.filter(b => b.amount > 0),
        notes: formData.notes
      };

      await axios.put(`${API}/entries/${editingEntry.id}`, updateData);
      setEditingEntry(null);
      resetForm();
      fetchData();
    } catch (error) {
      console.error('Error updating entry:', error);
      alert('Error updating entry. Please try again.');
    }
  };

  // Delete entry
  const handleDeleteEntry = async (entryId) => {
    if (window.confirm('Are you sure you want to delete this entry?')) {
      try {
        await axios.delete(`${API}/entries/${entryId}`);
        fetchData();
      } catch (error) {
        console.error('Error deleting entry:', error);
        alert('Error deleting entry. Please try again.');
      }
    }
  };

  // Start editing
  const startEditing = (entry) => {
    setEditingEntry(entry);
    
    const editBalances = exchanges.map(exchange => {
      const existingBalance = entry.balances.find(b => b.exchange_id === exchange.id);
      return {
        exchange_id: exchange.id,
        amount: existingBalance ? existingBalance.amount : 0
      };
    });
    
    setFormData({
      date: entry.date,
      balances: editBalances,
      notes: entry.notes || ''
    });
    setShowAddForm(true);
  };

  // Reset form
  const resetForm = () => {
    const initialBalances = exchanges.map(exchange => ({
      exchange_id: exchange.id,
      amount: 0
    }));
    setFormData({
      date: new Date().toISOString().split('T')[0],
      balances: initialBalances,
      notes: ''
    });
  };

  // Cancel editing
  const cancelEditing = () => {
    setEditingEntry(null);
    resetForm();
    setShowAddForm(false);
  };

  // Export to CSV
  const handleExportCSV = async () => {
    try {
      const response = await axios.get(`${API}/export/csv`, {
        responseType: 'blob'
      });
      
      const blob = new Blob([response.data], { type: 'text/csv' });
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = 'crypto_pnl_data.csv';
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);
    } catch (error) {
      console.error('Error exporting CSV:', error);
      alert('Error exporting data. Please try again.');
    }
  };

  // KPI management
  const handleAddKPI = async (e) => {
    e.preventDefault();
    try {
      await axios.post(`${API}/kpis`, {
        ...newKPI,
        target_amount: parseFloat(newKPI.target_amount)
      });
      setNewKPI({ name: '', target_amount: '', color: '#10B981' });
      fetchData();
    } catch (error) {
      console.error('Error adding KPI:', error);
      alert('Error adding KPI. Please try again.');
    }
  };

  const handleUpdateKPI = async (e) => {
    e.preventDefault();
    try {
      await axios.put(`${API}/kpis/${editingKPI.id}`, {
        ...newKPI,
        target_amount: parseFloat(newKPI.target_amount)
      });
      setEditingKPI(null);
      setNewKPI({ name: '', target_amount: '', color: '#10B981' });
      fetchData();
    } catch (error) {
      console.error('Error updating KPI:', error);
      alert('Error updating KPI. Please try again.');
    }
  };

  const startEditingKPI = (kpi) => {
    setEditingKPI(kpi);
    setNewKPI({
      name: kpi.name,
      target_amount: kpi.target_amount.toString(),
      color: kpi.color
    });
  };

  const cancelEditingKPI = () => {
    setEditingKPI(null);
    setNewKPI({ name: '', target_amount: '', color: '#10B981' });
  };

  const handleDeleteKPI = async (kpiId) => {
    if (window.confirm('Are you sure you want to delete this KPI?')) {
      try {
        await axios.delete(`${API}/kpis/${kpiId}`);
        fetchData();
      } catch (error) {
        console.error('Error deleting KPI:', error);
        alert('Error deleting KPI. Please try again.');
      }
    }
  };
  const handleAddExchange = async (e) => {
    e.preventDefault();
    try {
      await axios.post(`${API}/exchanges`, newExchange);
      setNewExchange({ name: '', display_name: '', color: '#3B82F6' });
      fetchData();
    } catch (error) {
      console.error('Error adding exchange:', error);
      alert('Error adding exchange. Please try again.');
    }
  };

  const handleDeleteExchange = async (exchangeId) => {
    if (window.confirm('Are you sure you want to remove this exchange?')) {
      try {
        await axios.delete(`${API}/exchanges/${exchangeId}`);
        fetchData();
      } catch (error) {
        console.error('Error deleting exchange:', error);
        alert('Error deleting exchange. Please try again.');
      }
    }
  };

  // Utility functions
  const getPnLColor = (value) => {
    if (value > 0) return 'text-green-600 bg-green-50';
    if (value < 0) return 'text-red-600 bg-red-50';
    return 'text-gray-600 bg-gray-50';
  };

  const formatCurrency = (amount) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'EUR',
      minimumFractionDigits: 0,
      maximumFractionDigits: 0
    }).format(amount);
  };

  const getExchangeBalance = (entry, exchangeId) => {
    const balance = entry.balances.find(b => b.exchange_id === exchangeId);
    return balance ? balance.amount : 0;
  };

  // Chart preparation functions
  const getPortfolioChartData = () => {
    if (!chartData.portfolio_timeline || chartData.portfolio_timeline.length === 0) return null;
    
    const datasets = [
      {
        label: 'Total Portfolio',
        data: chartData.portfolio_timeline.map(item => item.total),
        borderColor: 'rgb(59, 130, 246)',
        backgroundColor: 'rgba(59, 130, 246, 0.1)',
        tension: 0.1,
        fill: true
      }
    ];

    exchanges.forEach((exchange) => {
      datasets.push({
        label: exchange.display_name,
        data: chartData.portfolio_timeline.map(item => item[exchange.name] || 0),
        borderColor: exchange.color,
        backgroundColor: exchange.color + '20',
        tension: 0.1
      });
    });
    
    return {
      labels: chartData.portfolio_timeline.map(item => new Date(item.date).toLocaleDateString()),
      datasets: datasets
    };
  };

  const getPnLChartData = () => {
    if (!chartData.pnl_timeline || chartData.pnl_timeline.length === 0) return null;
    
    return {
      labels: chartData.pnl_timeline.map(item => new Date(item.date).toLocaleDateString()),
      datasets: [
        {
          label: 'Daily PnL %',
          data: chartData.pnl_timeline.map(item => item.pnl_percentage),
          backgroundColor: chartData.pnl_timeline.map(item => 
            item.pnl_percentage > 0 ? 'rgba(16, 185, 129, 0.6)' : 'rgba(239, 68, 68, 0.6)'
          ),
          borderWidth: 1
        }
      ]
    };
  };

  const getExchangeBreakdownData = () => {
    if (!chartData.exchange_breakdown) return null;
    
    const labels = [];
    const data = [];
    const colors = [];
    
    Object.entries(chartData.exchange_breakdown).forEach(([exchangeName, exchangeData]) => {
      if (exchangeData.amount > 0) {
        labels.push(exchangeData.display_name);
        data.push(exchangeData.amount);
        colors.push(exchangeData.color);
      }
    });
    
    if (data.length === 0) return null;
    
    return {
      labels: labels,
      datasets: [
        {
          data: data,
          backgroundColor: colors.map(color => color + 'CC'),
          borderColor: colors,
          borderWidth: 2
        }
      ]
    };
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Mobile-First Header */}
      <div className="bg-white shadow-sm border-b sticky top-0 z-40">
        <div className="px-4 py-4">
          <div className="flex justify-between items-center">
            <div className="flex items-center space-x-3">
              <div className="w-8 h-8 bg-blue-600 rounded-full flex items-center justify-center">
                <span className="text-white text-sm font-bold">₿</span>
              </div>
              <div>
                <h1 className="text-lg font-bold text-gray-900 md:text-xl">Crypto PnL</h1>
                <p className="text-xs text-gray-500 hidden sm:block">Portfolio Tracker</p>
              </div>
            </div>
            
            {/* Mobile Menu Button */}
            <button
              onClick={() => setShowMobileMenu(!showMobileMenu)}
              className="md:hidden p-2 rounded-lg hover:bg-gray-100"
            >
              <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
              </svg>
            </button>
            
            {/* Desktop Actions */}
            <div className="hidden md:flex items-center space-x-3">
              <button onClick={() => setShowMonthlyView(!showMonthlyView)} className="btn-secondary text-sm">
                {showMonthlyView ? 'Hide Monthly' : 'Monthly View'}
              </button>
              <button onClick={() => setShowCharts(!showCharts)} className="btn-secondary text-sm">
                {showCharts ? 'Hide Charts' : 'Charts'}
              </button>
              <button onClick={() => setShowKPIManager(true)} className="btn-secondary text-sm">
                KPIs
              </button>
              <button onClick={() => setShowExchangeManager(true)} className="btn-secondary text-sm">
                Exchanges
              </button>
              <button onClick={handleExportCSV} className="btn-secondary text-sm">
                Export
              </button>
              <button onClick={() => setShowAddForm(true)} className="btn-primary text-sm">
                Add Entry
              </button>
              <button onClick={logout} className="text-gray-500 hover:text-gray-700 text-sm">
                Logout
              </button>
            </div>
          </div>
          
          {/* Mobile Menu */}
          {showMobileMenu && (
            <div className="mt-4 pb-4 border-t pt-4 md:hidden">
              <div className="space-y-2">
                <button onClick={() => { setShowAddForm(true); setShowMobileMenu(false); }} className="w-full btn-primary text-sm py-3">
                  Add Entry
                </button>
                <div className="grid grid-cols-2 gap-2">
                  <button onClick={() => { setShowMonthlyView(!showMonthlyView); setShowMobileMenu(false); }} className="btn-secondary text-xs py-2">
                    Monthly
                  </button>
                  <button onClick={() => { setShowCharts(!showCharts); setShowMobileMenu(false); }} className="btn-secondary text-xs py-2">
                    Charts
                  </button>
                  <button onClick={() => { setShowKPIManager(true); setShowMobileMenu(false); }} className="btn-secondary text-xs py-2">
                    KPIs
                  </button>
                  <button onClick={() => { setShowExchangeManager(true); setShowMobileMenu(false); }} className="btn-secondary text-xs py-2">
                    Exchanges
                  </button>
                  <button onClick={handleExportCSV} className="btn-secondary text-xs py-2">
                    Export
                  </button>
                </div>
                <button onClick={logout} className="w-full text-red-600 text-sm py-2">
                  Logout
                </button>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Mobile-Optimized Stats Cards */}
      <div className="px-4 py-6">
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4 mb-6">
          <div className="bg-white rounded-xl shadow-sm p-4 col-span-2 md:col-span-1">
            <h3 className="text-xs font-medium text-gray-500 uppercase tracking-wide mb-1">Total Balance</h3>
            <p className="text-xl md:text-2xl font-bold text-gray-900">{formatCurrency(stats.total_balance || 0)}</p>
          </div>
          <div className="bg-white rounded-xl shadow-sm p-4">
            <h3 className="text-xs font-medium text-gray-500 uppercase tracking-wide mb-1">Daily PnL</h3>
            <p className={`text-lg md:text-xl font-bold ${stats.daily_pnl > 0 ? 'text-green-600' : stats.daily_pnl < 0 ? 'text-red-600' : 'text-gray-900'}`}>
              {formatCurrency(stats.daily_pnl || 0)}
            </p>
            <p className={`text-xs ${stats.daily_pnl_percentage > 0 ? 'text-green-600' : stats.daily_pnl_percentage < 0 ? 'text-red-600' : 'text-gray-500'}`}>
              {stats.daily_pnl_percentage > 0 ? '+' : ''}{(stats.daily_pnl_percentage || 0).toFixed(2)}%
            </p>
          </div>
          <div className="bg-white rounded-xl shadow-sm p-4">
            <h3 className="text-xs font-medium text-gray-500 uppercase tracking-wide mb-1">Avg Daily €</h3>
            <p className={`text-lg md:text-xl font-bold ${stats.avg_daily_pnl > 0 ? 'text-green-600' : stats.avg_daily_pnl < 0 ? 'text-red-600' : 'text-gray-900'}`}>
              {formatCurrency(stats.avg_daily_pnl || 0)}
            </p>
          </div>
          <div className="bg-white rounded-xl shadow-sm p-4">
            <h3 className="text-xs font-medium text-gray-500 uppercase tracking-wide mb-1">Avg Daily %</h3>
            <p className={`text-lg md:text-xl font-bold ${stats.avg_daily_pnl_percentage > 0 ? 'text-green-600' : stats.avg_daily_pnl_percentage < 0 ? 'text-red-600' : 'text-gray-900'}`}>
              {stats.avg_daily_pnl_percentage > 0 ? '+' : ''}{(stats.avg_daily_pnl_percentage || 0).toFixed(2)}%
            </p>
          </div>
          <div className="bg-white rounded-xl shadow-sm p-4">
            <h3 className="text-xs font-medium text-gray-500 uppercase tracking-wide mb-1">Avg Monthly %</h3>
            <p className={`text-lg md:text-xl font-bold ${stats.avg_monthly_pnl_percentage > 0 ? 'text-green-600' : stats.avg_monthly_pnl_percentage < 0 ? 'text-red-600' : 'text-gray-900'}`}>
              {stats.avg_monthly_pnl_percentage > 0 ? '+' : ''}{(stats.avg_monthly_pnl_percentage || 0).toFixed(2)}%
            </p>
          </div>
          <div className="bg-white rounded-xl shadow-sm p-4">
            <h3 className="text-xs font-medium text-gray-500 uppercase tracking-wide mb-1">Total Entries</h3>
            <p className="text-lg md:text-xl font-bold text-gray-900">{stats.total_entries || 0}</p>
          </div>
        </div>

        {/* Monthly Performance View */}
        {showMonthlyView && monthlyPerformance.monthly_performance && (
          <div className="mb-6">
            {/* Best/Worst Months - Mobile Stack */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
              {monthlyPerformance.best_month && (
                <div className="bg-green-50 border border-green-200 rounded-xl p-4">
                  <h3 className="text-sm font-semibold text-green-800 mb-2 flex items-center">
                    🏆 <span className="ml-1">Best Month</span>
                  </h3>
                  <p className="text-lg font-bold text-green-600">{monthlyPerformance.best_month.display_name}</p>
                  <p className="text-green-700 text-sm">
                    {monthlyPerformance.best_month.pnl_percentage > 0 ? '+' : ''}{monthlyPerformance.best_month.pnl_percentage}% 
                    ({formatCurrency(monthlyPerformance.best_month.pnl_amount)})
                  </p>
                </div>
              )}
              
              {monthlyPerformance.worst_month && (
                <div className="bg-red-50 border border-red-200 rounded-xl p-4">
                  <h3 className="text-sm font-semibold text-red-800 mb-2 flex items-center">
                    📉 <span className="ml-1">Worst Month</span>
                  </h3>
                  <p className="text-lg font-bold text-red-600">{monthlyPerformance.worst_month.display_name}</p>
                  <p className="text-red-700 text-sm">
                    {monthlyPerformance.worst_month.pnl_percentage}% 
                    ({formatCurrency(monthlyPerformance.worst_month.pnl_amount)})
                  </p>
                </div>
              )}
            </div>

            {/* Monthly Performance Table - Mobile Optimized */}
            <div className="bg-white rounded-xl shadow-sm overflow-hidden">
              <div className="px-4 py-3 border-b border-gray-200">
                <h3 className="text-lg font-semibold text-gray-900">Monthly Performance</h3>
              </div>
              <div className="overflow-x-auto">
                <div className="max-h-96 overflow-y-auto">
                  {monthlyPerformance.monthly_performance.slice(0, 6).map((month, index) => (
                    <div key={index} className="px-4 py-3 border-b border-gray-100 last:border-b-0">
                      <div className="flex justify-between items-center">
                        <div>
                          <p className="font-medium text-gray-900 text-sm">{month.display_name}</p>
                          <p className="text-xs text-gray-500">{month.trading_days} days</p>
                        </div>
                        <div className="text-right">
                          <p className={`font-semibold text-sm ${month.monthly_pnl_percentage >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                            {month.monthly_pnl_percentage > 0 ? '+' : ''}{month.monthly_pnl_percentage}%
                          </p>
                          <p className={`text-xs ${month.monthly_pnl_amount >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                            {formatCurrency(month.monthly_pnl_amount)}
                          </p>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Charts Section - Mobile Optimized */}
        {showCharts && (
          <div className="space-y-6 mb-6">
            {/* Portfolio Chart */}
            {getPortfolioChartData() && (
              <div className="bg-white rounded-xl shadow-sm p-4">
                <h3 className="text-lg font-semibold text-gray-900 mb-4">Portfolio Timeline</h3>
                <div className="h-64 md:h-80">
                  <Line 
                    data={getPortfolioChartData()} 
                    options={{
                      responsive: true,
                      maintainAspectRatio: false,
                      plugins: {
                        legend: {
                          position: 'top',
                          labels: { boxWidth: 12, font: { size: 11 } }
                        }
                      },
                      scales: {
                        y: {
                          beginAtZero: false,
                          ticks: {
                            font: { size: 10 },
                            callback: function(value) {
                              return '€' + value.toLocaleString();
                            }
                          }
                        },
                        x: {
                          ticks: { font: { size: 10 } }
                        }
                      }
                    }}
                  />
                </div>
              </div>
            )}

            {/* Mobile Chart Grid */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {/* Exchange Breakdown */}
              {getExchangeBreakdownData() && (
                <div className="bg-white rounded-xl shadow-sm p-4">
                  <h3 className="text-lg font-semibold text-gray-900 mb-4">Exchange Breakdown</h3>
                  <div className="h-48">
                    <Pie 
                      data={getExchangeBreakdownData()} 
                      options={{
                        responsive: true,
                        maintainAspectRatio: false,
                        plugins: {
                          legend: {
                            position: 'bottom',
                            labels: { font: { size: 10 } }
                          }
                        }
                      }}
                    />
                  </div>
                </div>
              )}

              {/* PnL Performance */}
              {getPnLChartData() && (
                <div className="bg-white rounded-xl shadow-sm p-4">
                  <h3 className="text-lg font-semibold text-gray-900 mb-4">Daily PnL Performance</h3>
                  <div className="h-48">
                    <Bar 
                      data={getPnLChartData()} 
                      options={{
                        responsive: true,
                        maintainAspectRatio: false,
                        plugins: {
                          legend: { display: false }
                        },
                        scales: {
                          y: {
                            beginAtZero: true,
                            ticks: {
                              font: { size: 10 },
                              callback: function(value) {
                                return value + '%';
                              }
                            }
                          },
                          x: {
                            ticks: { font: { size: 9 } }
                          }
                        }
                      }}
                    />
                  </div>
                </div>
              )}
            </div>
          </div>
        )}

        {/* KPI Progress - Mobile Optimized */}
        <div className="bg-white rounded-xl shadow-sm p-4 mb-6">
          <div className="flex justify-between items-center mb-4">
            <h3 className="text-lg font-semibold text-gray-900">KPI Progress</h3>
            <button
              onClick={() => setShowKPIManager(true)}
              className="text-blue-600 hover:text-blue-800 text-sm"
            >
              Manage
            </button>
          </div>
          <div className="space-y-4">
            {kpis.map((kpi) => {
              const kpiProgress = entries.length > 0 
                ? entries[0].kpi_progress.find(p => p.kpi_id === kpi.id)
                : null;
              const progress = kpiProgress ? kpiProgress.progress : 0;
              const current = kpi.target_amount + progress;
              const percentage = Math.max(0, Math.min(100, (current / kpi.target_amount) * 100));
              
              return (
                <div key={kpi.id}>
                  <div className="flex justify-between text-sm mb-2">
                    <span className="font-medium text-gray-700">{kpi.name}</span>
                    <span className={progress >= 0 ? 'text-green-600' : 'text-red-600'}>
                      {progress >= 0 ? '+' : ''}{formatCurrency(progress)}
                    </span>
                  </div>
                  <div className="w-full bg-gray-200 rounded-full h-2 mb-1">
                    <div
                      className="h-2 rounded-full transition-all duration-300"
                      style={{ 
                        width: `${percentage}%`,
                        backgroundColor: kpi.color
                      }}
                    ></div>
                  </div>
                  <div className="text-xs text-gray-500">
                    {formatCurrency(current)} / {formatCurrency(kpi.target_amount)} ({percentage.toFixed(1)}%)
                  </div>
                </div>
              );
            })}
            
            {kpis.length === 0 && (
              <div className="text-center py-4">
                <p className="text-gray-500 text-sm">No KPIs set yet.</p>
                <button
                  onClick={() => setShowKPIManager(true)}
                  className="text-blue-600 hover:text-blue-800 text-sm mt-2"
                >
                  Add your first KPI
                </button>
              </div>
            )}
          </div>
        </div>

      {/* Mobile-Optimized Entries List */}
      <div className="bg-white rounded-xl shadow-sm overflow-hidden">
        <div className="px-4 py-3 border-b border-gray-200">
          <h2 className="text-lg font-semibold text-gray-900">Recent Entries</h2>
        </div>
        
        {/* Mobile Entry Cards */}
        <div className="divide-y divide-gray-100">
          {entries.slice(0, 10).map((entry) => (
            <div key={entry.id} className="px-4 py-4">
              <div className="flex justify-between items-start mb-2">
                <div>
                  <p className="font-medium text-gray-900 text-sm">
                    {new Date(entry.date).toLocaleDateString()}
                  </p>
                  <p className="text-xl font-bold text-gray-900">
                    {formatCurrency(entry.total)}
                  </p>
                </div>
                <div className="text-right">
                  <span className={`px-2 py-1 rounded-full text-xs font-medium ${getPnLColor(entry.pnl_percentage)}`}>
                    {entry.pnl_percentage > 0 ? '+' : ''}{entry.pnl_percentage.toFixed(2)}%
                  </span>
                  <p className={`text-sm mt-1 ${entry.pnl_amount >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                    {entry.pnl_amount > 0 ? '+' : ''}{formatCurrency(entry.pnl_amount)}
                  </p>
                </div>
              </div>
              
              {/* Exchange Balances */}
              <div className="grid grid-cols-3 gap-2 text-xs text-gray-600 mb-2">
                {exchanges.map((exchange) => (
                  <div key={exchange.id}>
                    <span className="font-medium">{exchange.display_name}:</span>
                    <span className="ml-1">{formatCurrency(getExchangeBalance(entry, exchange.id))}</span>
                  </div>
                ))}
              </div>
              
              {entry.notes && (
                <p className="text-xs text-gray-500 mb-2">{entry.notes}</p>
              )}
              
              <div className="flex space-x-3 text-xs">
                <button
                  onClick={() => startEditing(entry)}
                  className="text-blue-600 hover:text-blue-800"
                >
                  Edit
                </button>
                <button
                  onClick={() => handleDeleteEntry(entry.id)}
                  className="text-red-600 hover:text-red-800"
                >
                  Delete
                </button>
              </div>
            </div>
          ))}
        </div>
        
        {entries.length === 0 && (
          <div className="text-center py-12">
            <p className="text-gray-500">No entries yet. Add your first entry to get started!</p>
          </div>
        )}
      </div>
    </div>

      {/* Floating Add Button - Mobile */}
      <button
        onClick={() => setShowAddForm(true)}
        className="md:hidden fixed bottom-6 right-6 w-14 h-14 bg-blue-600 hover:bg-blue-700 text-white rounded-full shadow-lg flex items-center justify-center z-30"
      >
        <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
        </svg>
      </button>

      {/* Add/Edit Form Modal - Mobile Optimized */}
      {showAddForm && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-end md:items-center justify-center z-50 p-4 md:p-4">
          <div className="bg-white rounded-t-3xl md:rounded-2xl shadow-xl w-full md:max-w-md md:w-full max-h-[90vh] overflow-y-auto">
            <div className="p-6">
              <div className="flex justify-between items-center mb-6">
                <h2 className="text-xl font-semibold text-gray-900">
                  {editingEntry ? 'Edit Entry' : 'Add New Entry'}
                </h2>
                <button
                  onClick={cancelEditing}
                  className="text-gray-400 hover:text-gray-600"
                >
                  ✕
                </button>
              </div>
              
              <form onSubmit={editingEntry ? handleEditEntry : handleAddEntry} className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">Date</label>
                  <input
                    type="date"
                    name="date"
                    value={formData.date}
                    onChange={handleInputChange}
                    className="w-full px-4 py-3 border border-gray-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-500"
                    required
                  />
                </div>
                
                {/* Dynamic Exchange Balances */}
                {exchanges.map((exchange) => (
                  <div key={exchange.id}>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      {exchange.display_name} Balance (€)
                    </label>
                    <input
                      type="number"
                      value={formData.balances.find(b => b.exchange_id === exchange.id)?.amount || ''}
                      onChange={(e) => handleBalanceChange(exchange.id, e.target.value)}
                      step="0.01"
                      className="w-full px-4 py-3 border border-gray-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-500"
                      placeholder="0.00"
                    />
                  </div>
                ))}
                
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">Notes</label>
                  <textarea
                    name="notes"
                    value={formData.notes}
                    onChange={handleInputChange}
                    rows="3"
                    className="w-full px-4 py-3 border border-gray-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-500"
                    placeholder="Optional notes about this entry..."
                  />
                </div>
                
                <div className="flex space-x-3 pt-4">
                  <button
                    type="submit"
                    className="flex-1 btn-primary py-3"
                  >
                    {editingEntry ? 'Update Entry' : 'Add Entry'}
                  </button>
                  <button
                    type="button"
                    onClick={cancelEditing}
                    className="flex-1 btn-secondary py-3"
                  >
                    Cancel
                  </button>
                </div>
              </form>
            </div>
          </div>
        </div>
      )}

      {/* Exchange management */}
      {showExchangeManager && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-end md:items-center justify-center z-50 p-4 md:p-4">
          <div className="bg-white rounded-t-3xl md:rounded-2xl shadow-xl w-full md:max-w-2xl md:w-full max-h-[90vh] overflow-y-auto">
            <div className="p-6">
              <div className="flex justify-between items-center mb-6">
                <h2 className="text-xl font-semibold text-gray-900">Manage Exchanges</h2>
                <button
                  onClick={() => setShowExchangeManager(false)}
                  className="text-gray-400 hover:text-gray-600"
                >
                  ✕
                </button>
              </div>

              {/* Add New Exchange Form */}
              <form onSubmit={handleAddExchange} className="mb-6 p-4 border border-gray-200 rounded-xl">
                <h3 className="text-lg font-medium text-gray-900 mb-4">Add New Exchange</h3>
                <div className="space-y-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">Exchange Name</label>
                    <input
                      type="text"
                      value={newExchange.name}
                      onChange={(e) => setNewExchange(prev => ({ ...prev, name: e.target.value }))}
                      className="w-full px-4 py-3 border border-gray-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-500"
                      placeholder="coinbase"
                      required
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">Display Name</label>
                    <input
                      type="text"
                      value={newExchange.display_name}
                      onChange={(e) => setNewExchange(prev => ({ ...prev, display_name: e.target.value }))}
                      className="w-full px-4 py-3 border border-gray-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-500"
                      placeholder="Coinbase"
                      required
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">Color</label>
                    <input
                      type="color"
                      value={newExchange.color}
                      onChange={(e) => setNewExchange(prev => ({ ...prev, color: e.target.value }))}
                      className="w-full h-12 border border-gray-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-500"
                    />
                  </div>
                </div>
                <button type="submit" className="mt-4 btn-primary w-full py-3">Add Exchange</button>
              </form>

              {/* Current Exchanges */}
              <div>
                <h3 className="text-lg font-medium text-gray-900 mb-4">Current Exchanges</h3>
                <div className="space-y-3">
                  {exchanges.map((exchange) => (
                    <div key={exchange.id} className="flex items-center justify-between p-3 border border-gray-200 rounded-xl">
                      <div className="flex items-center space-x-3">
                        <div 
                          className="w-4 h-4 rounded-full" 
                          style={{ backgroundColor: exchange.color }}
                        ></div>
                        <div>
                          <p className="font-medium text-gray-900">{exchange.display_name}</p>
                          <p className="text-sm text-gray-500">{exchange.name}</p>
                        </div>
                      </div>
                      <button
                        onClick={() => handleDeleteExchange(exchange.id)}
                        className="text-red-600 hover:text-red-800 text-sm px-3 py-1 rounded"
                      >
                        Remove
                      </button>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* KPI Manager Modal - Mobile Optimized */}
      {showKPIManager && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-end md:items-center justify-center z-50 p-4 md:p-4">
          <div className="bg-white rounded-t-3xl md:rounded-2xl shadow-xl w-full md:max-w-2xl md:w-full max-h-[90vh] overflow-y-auto">
            <div className="p-6">
              <div className="flex justify-between items-center mb-6">
                <h2 className="text-xl font-semibold text-gray-900">Manage KPIs</h2>
                <button
                  onClick={() => {
                    setShowKPIManager(false);
                    cancelEditingKPI();
                  }}
                  className="text-gray-400 hover:text-gray-600"
                >
                  ✕
                </button>
              </div>

              {/* Add/Edit KPI Form */}
              <form onSubmit={editingKPI ? handleUpdateKPI : handleAddKPI} className="mb-6 p-4 border border-gray-200 rounded-xl">
                <h3 className="text-lg font-medium text-gray-900 mb-4">
                  {editingKPI ? 'Edit KPI' : 'Add New KPI'}
                </h3>
                <div className="space-y-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">KPI Name</label>
                    <input
                      type="text"
                      value={newKPI.name}
                      onChange={(e) => setNewKPI(prev => ({ ...prev, name: e.target.value }))}
                      className="w-full px-4 py-3 border border-gray-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-500"
                      placeholder="e.g., My Goal, Dream Target"
                      required
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">Target Amount (€)</label>
                    <input
                      type="number"
                      value={newKPI.target_amount}
                      onChange={(e) => setNewKPI(prev => ({ ...prev, target_amount: e.target.value }))}
                      className="w-full px-4 py-3 border border-gray-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-500"
                      placeholder="25000"
                      step="0.01"
                      required
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">Progress Bar Color</label>
                    <input
                      type="color"
                      value={newKPI.color}
                      onChange={(e) => setNewKPI(prev => ({ ...prev, color: e.target.value }))}
                      className="w-full h-12 border border-gray-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-500"
                    />
                  </div>
                </div>
                <div className="mt-4 flex space-x-3">
                  <button type="submit" className="flex-1 btn-primary py-3">
                    {editingKPI ? 'Update KPI' : 'Add KPI'}
                  </button>
                  {editingKPI && (
                    <button type="button" onClick={cancelEditingKPI} className="flex-1 btn-secondary py-3">
                      Cancel
                    </button>
                  )}
                </div>
              </form>

              {/* Current KPIs */}
              <div>
                <h3 className="text-lg font-medium text-gray-900 mb-4">Current KPIs</h3>
                <div className="space-y-3">
                  {kpis.map((kpi) => {
                    const kpiProgress = entries.length > 0 
                      ? entries[0].kpi_progress.find(p => p.kpi_id === kpi.id)
                      : null;
                    const progress = kpiProgress ? kpiProgress.progress : 0;
                    const current = kpi.target_amount + progress;
                    const percentage = Math.max(0, Math.min(100, (current / kpi.target_amount) * 100));
                    
                    return (
                      <div key={kpi.id} className="p-4 border border-gray-200 rounded-xl">
                        <div className="flex items-center justify-between mb-3">
                          <div className="flex items-center space-x-3">
                            <div 
                              className="w-4 h-4 rounded-full" 
                              style={{ backgroundColor: kpi.color }}
                            ></div>
                            <div>
                              <p className="font-medium text-gray-900">{kpi.name}</p>
                              <p className="text-sm text-gray-500">{formatCurrency(kpi.target_amount)} target</p>
                            </div>
                          </div>
                          <div className="flex space-x-2">
                            <button
                              onClick={() => startEditingKPI(kpi)}
                              className="text-blue-600 hover:text-blue-800 text-sm px-3 py-1 rounded"
                            >
                              Edit
                            </button>
                            <button
                              onClick={() => handleDeleteKPI(kpi.id)}
                              className="text-red-600 hover:text-red-800 text-sm px-3 py-1 rounded"
                            >
                              Delete
                            </button>
                          </div>
                        </div>
                        
                        {/* Progress Preview */}
                        <div className="space-y-2">
                          <div className="flex justify-between text-sm">
                            <span className="text-gray-600">Progress</span>
                            <span className={progress >= 0 ? 'text-green-600' : 'text-red-600'}>
                              {progress >= 0 ? '+' : ''}{formatCurrency(progress)}
                            </span>
                          </div>
                          <div className="w-full bg-gray-200 rounded-full h-2">
                            <div
                              className="h-2 rounded-full transition-all duration-300"
                              style={{ 
                                width: `${percentage}%`,
                                backgroundColor: kpi.color
                              }}
                            ></div>
                          </div>
                          <div className="text-xs text-gray-500">
                            {formatCurrency(current)} / {formatCurrency(kpi.target_amount)} ({percentage.toFixed(1)}%)
                          </div>
                        </div>
                      </div>
                    );
                  })}
                  
                  {kpis.length === 0 && (
                    <div className="text-center py-8">
                      <p className="text-gray-500">No KPIs created yet.</p>
                      <p className="text-sm text-gray-400 mt-1">Add your first KPI above to start tracking your progress!</p>
                    </div>
                  )}
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

// Main App Component
function App() {
  const { user, loading } = useAuth();

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  return (
    <div className="App">
      {user ? <CryptoPnLTracker /> : <LoginScreen />}
    </div>
  );
}

// App wrapped with AuthProvider
export default function AppWithAuth() {
  return (
    <AuthProvider>
      <App />
    </AuthProvider>
  );
}