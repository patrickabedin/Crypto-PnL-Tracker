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

  // Initialize Google OAuth
  useEffect(() => {
    const initializeGoogleAuth = () => {
      if (window.google) {
        window.google.accounts.id.initialize({
          client_id: process.env.REACT_APP_GOOGLE_CLIENT_ID || "your-google-client-id.apps.googleusercontent.com",
          callback: handleGoogleCallback,
          auto_select: false,
          cancel_on_tap_outside: false
        });
      }
    };

    // Wait for Google script to load
    if (window.google) {
      initializeGoogleAuth();
    } else {
      const checkGoogle = setInterval(() => {
        if (window.google) {
          initializeGoogleAuth();
          clearInterval(checkGoogle);
        }
      }, 100);
    }
  }, []);

  // Check authentication on app start
  useEffect(() => {
    const checkAuth = async () => {
      try {
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

  // Handle Google OAuth callback
  const handleGoogleCallback = async (response) => {
    try {
      console.log('Google OAuth response:', response);
      
      if (!response.credential) {
        throw new Error('No credential received from Google');
      }

      setLoading(true);
      
      // Send Google token to our backend
      const backendResponse = await axios.post(`${API}/auth/google`, {
        token: response.credential
      }, { 
        withCredentials: true,
        headers: {
          'Content-Type': 'application/json'
        }
      });
      
      if (backendResponse.data.success) {
        console.log('Authentication successful');
        setUser(backendResponse.data.user);
      } else {
        throw new Error(backendResponse.data.message || 'Authentication failed');
      }
    } catch (error) {
      console.error('Google OAuth error:', error);
      // You might want to show this error to the user in a more user-friendly way
      alert(`Login failed: ${error.response?.data?.detail || error.message}`);
    } finally {
      setLoading(false);
    }
  };

  const login = () => {
    if (window.google) {
      window.google.accounts.id.prompt();
    } else {
      console.error('Google OAuth not loaded');
    }
  };

  const logout = async () => {
    try {
      await axios.post(`${API}/auth/logout`, {}, { withCredentials: true });
      setUser(null);
      // Sign out from Google
      if (window.google) {
        window.google.accounts.id.disableAutoSelect();
      }
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
  const [isGoogleLoaded, setIsGoogleLoaded] = useState(false);

  useEffect(() => {
    const checkGoogleLoaded = () => {
      if (window.google) {
        setIsGoogleLoaded(true);
        // Render Google button
        window.google.accounts.id.renderButton(
          document.getElementById("google-signin-button"),
          {
            theme: "outline",
            size: "large",
            type: "standard",
            text: "continue_with",
            shape: "pill",
            width: "280"
          }
        );
      }
    };

    if (window.google) {
      checkGoogleLoaded();
    } else {
      const interval = setInterval(() => {
        if (window.google) {
          checkGoogleLoaded();
          clearInterval(interval);
        }
      }, 100);
      
      return () => clearInterval(interval);
    }
  }, []);

  const handleManualLogin = () => {
    if (isGoogleLoaded) {
      login();
    } else {
      alert('Google authentication is loading. Please try again in a moment.');
    }
  };

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
          {/* Google Sign-In Button Container */}
          <div className="flex justify-center">
            <div id="google-signin-button"></div>
          </div>
          
          {/* Fallback Manual Button */}
          {!isGoogleLoaded && (
            <button
              onClick={handleManualLogin}
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
          )}
          
          <div className="text-center text-sm text-gray-500">
            Secure OAuth authentication
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
  const [editingKPI, setEditingKPI] = useState(null);
  
  // Starting Balance & Capital Deposits State
  const [showSettingsManager, setShowSettingsManager] = useState(false);
  const [startingBalances, setStartingBalances] = useState([]);
  const [capitalDeposits, setCapitalDeposits] = useState([]);
  const [settingsLoading, setSettingsLoading] = useState(false);
  const [editingStartingBalance, setEditingStartingBalance] = useState(null);
  const [editingCapitalDeposit, setEditingCapitalDeposit] = useState(null);
  const [newStartingBalance, setNewStartingBalance] = useState({ exchange_id: '', starting_balance: '', starting_date: '' });
  const [newCapitalDeposit, setNewCapitalDeposit] = useState({ amount: '', deposit_date: '', notes: '' });
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
  
  // Dark Mode State
  const [darkMode, setDarkMode] = useState(() => {
    // Check localStorage or default to false
    const saved = localStorage.getItem('darkMode');
    return saved ? JSON.parse(saved) : false;
  });

  // Performance Heatmap State
  const [showHeatmap, setShowHeatmap] = useState(false);
  const [heatmapData, setHeatmapData] = useState([]);

  // Smart Alerts State
  const [smartAlerts, setSmartAlerts] = useState([]);
  const [showAlerts, setShowAlerts] = useState(false);


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
      loadStartingBalances();
      loadCapitalDeposits();
    }
  }, [user]);

  // Starting Balance & Capital Deposits Functions
  const loadStartingBalances = async () => {
    try {
      setSettingsLoading(true);
      const response = await axios.get(`${API}/starting-balances`);
      setStartingBalances(response.data || []);
    } catch (error) {
      console.error('Error loading starting balances:', error);
      setStartingBalances([]);
    } finally {
      setSettingsLoading(false);
    }
  };

  const loadCapitalDeposits = async () => {
    try {
      const response = await axios.get(`${API}/capital-deposits`);
      setCapitalDeposits(response.data || []);
    } catch (error) {
      console.error('Error loading capital deposits:', error);
      setCapitalDeposits([]);
    }
  };

  const handleAddStartingBalance = async (e) => {
    e.preventDefault();
    if (!newStartingBalance.exchange_id || !newStartingBalance.starting_balance || !newStartingBalance.starting_date) {
      alert('Please fill in all fields');
      return;
    }

    try {
      if (editingStartingBalance) {
        // Update existing starting balance
        await axios.post(`${API}/starting-balances`, {
          ...newStartingBalance,
          starting_balance: parseFloat(newStartingBalance.starting_balance)
        });
        setEditingStartingBalance(null);
        alert('Starting balance updated successfully!');
      } else {
        // Create new starting balance
        await axios.post(`${API}/starting-balances`, {
          ...newStartingBalance,
          starting_balance: parseFloat(newStartingBalance.starting_balance)
        });
        alert('Starting balance set successfully!');
      }
      
      await loadStartingBalances();
      await fetchData(); // Refresh stats to update ROI cards
      setNewStartingBalance({ exchange_id: '', starting_balance: '', starting_date: '' });
    } catch (error) {
      console.error('Error with starting balance:', error);
      alert('Error with starting balance: ' + (error.response?.data?.detail || error.message));
    }
  };

  const startEditingStartingBalance = (balance) => {
    setEditingStartingBalance(balance);
    setNewStartingBalance({
      exchange_id: balance.exchange_id,
      starting_balance: balance.starting_balance.toString(),
      starting_date: balance.starting_date
    });
  };

  const cancelEditingStartingBalance = () => {
    setEditingStartingBalance(null);
    setNewStartingBalance({ exchange_id: '', starting_balance: '', starting_date: '' });
  };

  const handleDeleteStartingBalance = async (exchangeId) => {
    if (!confirm('Are you sure you want to delete this starting balance?')) return;

    try {
      await axios.delete(`${API}/starting-balances/${exchangeId}`);
      await loadStartingBalances();
      await fetchData(); // Refresh stats to update ROI cards
      alert('Starting balance deleted successfully!');
    } catch (error) {
      console.error('Error deleting starting balance:', error);
      alert('Error deleting starting balance: ' + (error.response?.data?.detail || error.message));
    }
  };

  const handleAddCapitalDeposit = async (e) => {
    e.preventDefault();
    if (!newCapitalDeposit.amount || !newCapitalDeposit.deposit_date) {
      alert('Please fill in amount and date');
      return;
    }

    try {
      if (editingCapitalDeposit) {
        // Update existing capital deposit - need to implement PUT endpoint
        const response = await axios.put(`${API}/capital-deposits/${editingCapitalDeposit.id}`, {
          ...newCapitalDeposit,
          amount: parseFloat(newCapitalDeposit.amount)
        });
        setEditingCapitalDeposit(null);
        alert('Capital deposit updated successfully!');
      } else {
        // Create new capital deposit
        await axios.post(`${API}/capital-deposits`, {
          ...newCapitalDeposit,
          amount: parseFloat(newCapitalDeposit.amount)
        });
        alert('Capital deposit added successfully!');
      }
      
      await loadCapitalDeposits();
      await fetchData(); // Refresh stats to update ROI cards
      setNewCapitalDeposit({ amount: '', deposit_date: '', notes: '' });
    } catch (error) {
      console.error('Error with capital deposit:', error);
      alert('Error with capital deposit: ' + (error.response?.data?.detail || error.message));
    }
  };

  const startEditingCapitalDeposit = (deposit) => {
    setEditingCapitalDeposit(deposit);
    setNewCapitalDeposit({
      amount: deposit.amount.toString(),
      deposit_date: deposit.deposit_date,
      notes: deposit.notes || ''
    });
  };

  const cancelEditingCapitalDeposit = () => {
    setEditingCapitalDeposit(null);
    setNewCapitalDeposit({ amount: '', deposit_date: '', notes: '' });
  };

  const handleDeleteCapitalDeposit = async (depositId) => {
    if (!confirm('Are you sure you want to delete this capital deposit?')) return;

    try {
      await axios.delete(`${API}/capital-deposits/${depositId}`);
      await loadCapitalDeposits();
      await fetchData(); // Refresh stats to update ROI cards
      alert('Capital deposit deleted successfully!');
    } catch (error) {
      console.error('Error deleting capital deposit:', error);
      alert('Error deleting capital deposit: ' + (error.response?.data?.detail || error.message));
    }
  };

  // Dark Mode Functions
  const toggleDarkMode = () => {
    const newDarkMode = !darkMode;
    setDarkMode(newDarkMode);
    localStorage.setItem('darkMode', JSON.stringify(newDarkMode));
    // Apply dark mode class to document
    if (newDarkMode) {
      document.documentElement.classList.add('dark');
    } else {
      document.documentElement.classList.remove('dark');
    }
  };

  // Apply dark mode on component mount
  useEffect(() => {
    if (darkMode) {
      document.documentElement.classList.add('dark');
    } else {
      document.documentElement.classList.remove('dark');
    }
  }, [darkMode]);

  // Performance Heatmap Functions
  const generateHeatmapData = () => {
    const today = new Date();
    const yearAgo = new Date(today.getFullYear() - 1, today.getMonth(), today.getDate());
    const heatmapDays = [];
    
    // Generate array of last 365 days
    for (let d = new Date(yearAgo); d <= today; d.setDate(d.getDate() + 1)) {
      const dateStr = d.toISOString().split('T')[0];
      const entry = entries.find(e => e.date === dateStr);
      
      let performanceLevel = 0;
      if (entry && entry.pnl_percentage !== 0) {
        const pnl = entry.pnl_percentage;
        // Classify performance into 5 levels (0-4)
        if (pnl > 5) performanceLevel = 4;      // Excellent day (>5%)
        else if (pnl > 2) performanceLevel = 3; // Good day (2-5%)
        else if (pnl > 0) performanceLevel = 2; // Positive day (0-2%)
        else if (pnl > -2) performanceLevel = 1; // Small loss (0 to -2%)
        else performanceLevel = 0;               // Bad day (<-2%)
      }
      
      heatmapDays.push({
        date: dateStr,
        level: performanceLevel,
        pnl: entry ? entry.pnl_percentage : 0,
        hasEntry: !!entry
      });
    }
    
    setHeatmapData(heatmapDays);
  };

  const getHeatmapColor = (level, darkMode) => {
    const lightColors = {
      0: '#ebedf0', // No data / Bad performance
      1: '#ffeb9c', // Small loss
      2: '#c6e48b', // Small gain  
      3: '#7bc96f', // Good gain
      4: '#239a3b'  // Excellent gain
    };
    
    const darkColors = {
      0: '#161b22', // No data / Bad performance
      1: '#0e4429', // Small loss
      2: '#006d32', // Small gain
      3: '#26a641', // Good gain
      4: '#39d353'  // Excellent gain
    };
    
    return darkMode ? darkColors[level] : lightColors[level];
  };

  // Load heatmap data when entries change
  useEffect(() => {
    if (entries.length > 0) {
      generateHeatmapData();
    }
  }, [entries]);

  // Smart Alerts Functions
  const generateSmartAlerts = () => {
    const alerts = [];
    const currentBalance = stats.total_balance || 0;
    
    // Goal Proximity Alerts
    const kpiTargets = [5000, 10000, 15000, 20000];
    kpiTargets.forEach(target => {
      const progress = currentBalance;
      const remaining = target - progress;
      const percentComplete = (progress / target) * 100;
      
      if (percentComplete >= 95 && percentComplete < 100) {
        alerts.push({
          id: `goal-close-${target}`,
          type: 'success',
          icon: '🎯',
          title: `So Close to ${formatCurrency(target)}!`,
          message: `You're only ${formatCurrency(remaining)} away from your ${formatCurrency(target)} goal. That's just ${(100 - percentComplete).toFixed(1)}% to go!`,
          priority: 'high'
        });
      } else if (percentComplete >= 100) {
        const excess = progress - target;
        alerts.push({
          id: `goal-achieved-${target}`,
          type: 'celebration',
          icon: '🎉',
          title: `${formatCurrency(target)} Goal Achieved!`,
          message: `Congratulations! You've exceeded your ${formatCurrency(target)} goal by ${formatCurrency(excess)}. Time to set a new target!`,
          priority: 'high'
        });
      }
    });

    // Performance Streak Alerts
    const recentEntries = entries.slice(-7); // Last 7 days
    const positiveStreak = recentEntries.reduce((streak, entry) => {
      return entry.pnl_percentage > 0 ? streak + 1 : 0;
    }, 0);
    
    if (positiveStreak >= 3) {
      alerts.push({
        id: 'positive-streak',
        type: 'success',
        icon: '🔥',
        title: `${positiveStreak} Day Win Streak!`,
        message: `You're on fire! ${positiveStreak} consecutive days of positive returns. Keep up the great work!`,
        priority: 'medium'
      });
    }

    // Recovery Alerts
    if (stats.daily_pnl > 0 && currentBalance < (stats.total_capital_deposited || stats.total_starting_balance || 0)) {
      const deficit = (stats.total_capital_deposited || stats.total_starting_balance || 0) - currentBalance;
      const recoveryPercent = ((stats.daily_pnl) / deficit * 100);
      if (recoveryPercent > 1) {
        alerts.push({
          id: 'recovery-progress',
          type: 'info',
          icon: '📈',
          title: 'Recovery in Progress',
          message: `Great day! Today's gain of ${formatCurrency(stats.daily_pnl)} gets you ${recoveryPercent.toFixed(1)}% closer to breaking even.`,
          priority: 'medium'
        });
      }
    }

    // Loss Warning Alerts
    if (stats.daily_pnl < -1000) {
      alerts.push({
        id: 'large-loss',
        type: 'warning',
        icon: '⚠️',
        title: 'Significant Daily Loss',
        message: `Today's loss of ${formatCurrency(Math.abs(stats.daily_pnl))} is substantial. Consider reviewing your risk management strategy.`,
        priority: 'high'
      });
    }

    // Milestone Alerts
    const milestones = [1000, 2500, 5000, 7500, 10000, 15000, 20000, 25000, 50000];
    milestones.forEach(milestone => {
      if (currentBalance >= milestone && currentBalance < milestone + 500) {
        alerts.push({
          id: `milestone-${milestone}`,
          type: 'celebration',
          icon: '🏆',
          title: `${formatCurrency(milestone)} Milestone Reached!`,
          message: `Awesome achievement! Your portfolio has reached ${formatCurrency(milestone)}. You're building real wealth!`,
          priority: 'high'
        });
      }
    });

    // ROI Achievement Alerts
    if (stats.roi_vs_capital > 0) {
      const roi = stats.roi_vs_capital;
      if (roi >= 10 && roi < 15) {
        alerts.push({
          id: 'roi-double-digit',
          type: 'success',
          icon: '💰',
          title: 'Double-Digit Returns!',
          message: `Excellent! You've achieved ${roi.toFixed(1)}% ROI on your invested capital. You're outperforming most traditional investments!`,
          priority: 'medium'
        });
      }
    }

    setSmartAlerts(alerts);
  };

  // Generate alerts when stats change
  useEffect(() => {
    if (stats.total_balance && stats.total_balance > 0) {
      generateSmartAlerts();
    }
  }, [stats, entries]);

  // Load starting balances and capital deposits when Settings modal opens
  useEffect(() => {
    if (showSettingsManager) {
      loadStartingBalances();
      loadCapitalDeposits();
    }
  }, [showSettingsManager]);
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

  // Enhanced Manual Entry Functions
  const handleAddEntry = async (e) => {
    e.preventDefault();
    
    try {
      // Validate required fields
      if (!formData.date) {
        alert('Date is required');
        return;
      }

      // Calculate total from exchange balances
      const total = formData.balances.reduce((sum, balance) => {
        const amount = parseFloat(balance.amount || 0);
        return sum + amount;
      }, 0);

      if (total <= 0) {
        alert('Please enter at least one exchange balance');
        return;
      }

      // Create entry with proper structure
      const entryData = {
        date: formData.date,
        balances: formData.balances.filter(b => b.amount > 0),
        notes: formData.notes,
        // Let backend calculate PnL and KPI progress
      };

      console.log('Submitting entry:', entryData);
      
      await axios.post(`${API}/entries`, entryData);
      
      // Refresh data
      fetchData();
      
      // Reset form
      resetForm();
      setShowAddForm(false);
      
      alert('Entry added successfully!');
      
    } catch (error) {
      console.error('Error adding entry:', error);
      const errorMsg = error.response?.data?.detail || error.message || 'Failed to add entry';
      alert(`Error adding entry: ${errorMsg}`);
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
      <div className="min-h-screen bg-gray-50 dark:bg-gray-900 flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 dark:border-blue-400"></div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900 transition-colors duration-200">
      {/* Mobile-First Header */}
      <div className="bg-white dark:bg-gray-800 shadow-sm border-b dark:border-gray-700 sticky top-0 z-40 transition-colors duration-200">
        <div className="px-4 py-4">
          <div className="flex justify-between items-center">
            <div className="flex items-center space-x-3">
              <div className="w-8 h-8 bg-blue-600 rounded-full flex items-center justify-center">
                <span className="text-white text-sm font-bold">₿</span>
              </div>
              <div>
                <h1 className="text-lg font-bold text-gray-900 dark:text-white md:text-xl transition-colors duration-200">Crypto PnL</h1>
                <p className="text-xs text-gray-500 dark:text-gray-400 hidden sm:block transition-colors duration-200">Portfolio Tracker</p>
              </div>
            </div>
            
            {/* Mobile Menu Button */}
            <button
              onClick={() => setShowMobileMenu(!showMobileMenu)}
              className="md:hidden p-2 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700 text-gray-700 dark:text-gray-300 transition-colors duration-200"
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
              <button onClick={() => setShowHeatmap(!showHeatmap)} className="btn-secondary text-sm">
                {showHeatmap ? 'Hide Heatmap' : 'Performance Map'}
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
              <button onClick={() => {
                setShowSettingsManager(true);
                loadStartingBalances();
                loadCapitalDeposits();
              }} className="btn-secondary text-sm">
                Settings
              </button>
              <button onClick={handleExportCSV} className="btn-secondary text-sm">
                Export
              </button>
              <button onClick={() => setShowAddForm(true)} className="btn-primary text-sm">
                Manual Entry
              </button>
              <button 
                onClick={toggleDarkMode} 
                className="text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200 text-sm px-3 py-2 rounded-lg border border-gray-300 dark:border-gray-600 hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors"
                title={darkMode ? 'Switch to Light Mode' : 'Switch to Dark Mode'}
              >
                {darkMode ? '☀️' : '🌙'}
              </button>
              <button onClick={logout} className="text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200 text-sm">
                Logout
              </button>
            </div>
          </div>
          
          {/* Mobile Menu */}
          {showMobileMenu && (
            <div className="mt-4 pb-4 border-t pt-4 md:hidden">
              <div className="space-y-2">
                <button onClick={() => { setShowAddForm(true); setShowMobileMenu(false); }} className="w-full btn-primary text-sm py-3">
                  Manual Entry
                </button>
                <div className="grid grid-cols-2 gap-2">
                  <button onClick={() => { setShowMonthlyView(!showMonthlyView); setShowMobileMenu(false); }} className="btn-secondary text-xs py-2">
                    Monthly
                  </button>
                  <button onClick={() => { setShowHeatmap(!showHeatmap); setShowMobileMenu(false); }} className="btn-secondary text-xs py-2">
                    Heat Map
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
                  <button onClick={() => { 
                    setShowSettingsManager(true); 
                    setShowMobileMenu(false);
                    loadStartingBalances();
                    loadCapitalDeposits();
                  }} className="btn-secondary text-xs py-2">
                    Settings
                  </button>
                  <button onClick={handleExportCSV} className="btn-secondary text-xs py-2">
                    Export
                  </button>
                </div>
                <div className="mt-4 space-y-2">
                  <button 
                    onClick={() => { toggleDarkMode(); setShowMobileMenu(false); }} 
                    className="w-full btn-secondary text-sm py-3"
                  >
                    {darkMode ? '☀️ Light Mode' : '🌙 Dark Mode'}
                  </button>
                  <button onClick={logout} className="w-full text-red-600 text-sm py-2">
                    Logout
                  </button>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Mobile-Optimized Stats Cards */}
      <div className="px-4 py-6">

        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4 mb-6">
          <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm p-4 col-span-2 md:col-span-1 transition-colors duration-200">
            <h3 className="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wide mb-1">Total Balance</h3>
            <p className="text-xl md:text-2xl font-bold text-gray-900 dark:text-white">{formatCurrency(stats.total_balance || 0)}</p>
          </div>
          <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm p-4 transition-colors duration-200">
            <h3 className="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wide mb-1">Daily PnL</h3>
            <p className={`text-lg md:text-xl font-bold ${stats.daily_pnl > 0 ? 'text-green-600 dark:text-green-400' : stats.daily_pnl < 0 ? 'text-red-600 dark:text-red-400' : 'text-gray-900 dark:text-white'}`}>
              {formatCurrency(stats.daily_pnl || 0)}
            </p>
            <p className={`text-xs ${stats.daily_pnl_percentage > 0 ? 'text-green-600 dark:text-green-400' : stats.daily_pnl_percentage < 0 ? 'text-red-600 dark:text-red-400' : 'text-gray-500 dark:text-gray-400'}`}>
              {stats.daily_pnl_percentage > 0 ? '+' : ''}{(stats.daily_pnl_percentage || 0).toFixed(2)}%
            </p>
          </div>
          <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm p-4 transition-colors duration-200">
            <h3 className="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wide mb-1">Avg Daily €</h3>
            <p className={`text-lg md:text-xl font-bold ${stats.avg_daily_pnl > 0 ? 'text-green-600 dark:text-green-400' : stats.avg_daily_pnl < 0 ? 'text-red-600 dark:text-red-400' : 'text-gray-900 dark:text-white'}`}>
              {formatCurrency(stats.avg_daily_pnl || 0)}
            </p>
          </div>
          <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm p-4 transition-colors duration-200">
            <h3 className="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wide mb-1">Avg Daily %</h3>
            <p className={`text-lg md:text-xl font-bold ${stats.avg_daily_pnl_percentage > 0 ? 'text-green-600 dark:text-green-400' : stats.avg_daily_pnl_percentage < 0 ? 'text-red-600 dark:text-red-400' : 'text-gray-900 dark:text-white'}`}>
              {stats.avg_daily_pnl_percentage > 0 ? '+' : ''}{(stats.avg_daily_pnl_percentage || 0).toFixed(2)}%
            </p>
          </div>
          <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm p-4 transition-colors duration-200">
            <h3 className="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wide mb-1">Avg Monthly %</h3>
            <p className={`text-lg md:text-xl font-bold ${stats.avg_monthly_pnl_percentage > 0 ? 'text-green-600 dark:text-green-400' : stats.avg_monthly_pnl_percentage < 0 ? 'text-red-600 dark:text-red-400' : 'text-gray-900 dark:text-white'}`}>
              {stats.avg_monthly_pnl_percentage > 0 ? '+' : ''}{(stats.avg_monthly_pnl_percentage || 0).toFixed(2)}%
            </p>
          </div>
          <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm p-4 transition-colors duration-200">
            <h3 className="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wide mb-1">Total Entries</h3>
            <p className="text-lg md:text-xl font-bold text-gray-900 dark:text-white">{stats.total_entries || 0}</p>
          </div>
        </div>

        {/* Smart Alerts Panel */}
        {smartAlerts.length > 0 && (
          <div className="mb-6">
            <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm transition-colors duration-200">
              <div className="p-4 border-b border-gray-200 dark:border-gray-700">
                <div className="flex items-center justify-between">
                  <h3 className="text-lg font-semibold text-gray-900 dark:text-white flex items-center">
                    🧠 <span className="ml-2">Smart Insights</span>
                  </h3>
                  <button 
                    onClick={() => setShowAlerts(!showAlerts)}
                    className="text-sm text-blue-600 dark:text-blue-400 hover:text-blue-800 dark:hover:text-blue-300"
                  >
                    {showAlerts ? 'Hide' : `Show ${smartAlerts.length}`}
                  </button>
                </div>
              </div>
              
              {showAlerts && (
                <div className="p-4 space-y-3">
                  {smartAlerts
                    .sort((a, b) => {
                      const priorityOrder = { high: 3, medium: 2, low: 1 };
                      return priorityOrder[b.priority] - priorityOrder[a.priority];
                    })
                    .slice(0, 5) // Show top 5 alerts
                    .map((alert) => (
                      <div 
                        key={alert.id}
                        className={`p-4 rounded-xl border ${
                          alert.type === 'celebration' ? 'bg-green-50 dark:bg-green-900/20 border-green-200 dark:border-green-800' :
                          alert.type === 'success' ? 'bg-blue-50 dark:bg-blue-900/20 border-blue-200 dark:border-blue-800' :
                          alert.type === 'warning' ? 'bg-yellow-50 dark:bg-yellow-900/20 border-yellow-200 dark:border-yellow-800' :
                          'bg-gray-50 dark:bg-gray-700 border-gray-200 dark:border-gray-600'
                        } transition-colors duration-200`}
                      >
                        <div className="flex items-start space-x-3">
                          <span className="text-xl flex-shrink-0">{alert.icon}</span>
                          <div className="flex-1 min-w-0">
                            <h4 className={`font-semibold text-sm ${
                              alert.type === 'celebration' ? 'text-green-800 dark:text-green-200' :
                              alert.type === 'success' ? 'text-blue-800 dark:text-blue-200' :
                              alert.type === 'warning' ? 'text-yellow-800 dark:text-yellow-200' :
                              'text-gray-800 dark:text-gray-200'
                            }`}>
                              {alert.title}
                            </h4>
                            <p className={`text-sm mt-1 ${
                              alert.type === 'celebration' ? 'text-green-700 dark:text-green-300' :
                              alert.type === 'success' ? 'text-blue-700 dark:text-blue-300' :
                              alert.type === 'warning' ? 'text-yellow-700 dark:text-yellow-300' :
                              'text-gray-600 dark:text-gray-300'
                            }`}>
                              {alert.message}
                            </p>
                          </div>
                          {alert.priority === 'high' && (
                            <div className="flex-shrink-0">
                              <div className="w-2 h-2 bg-red-500 rounded-full animate-pulse"></div>
                            </div>
                          )}
                        </div>
                      </div>
                    ))}
                    
                  {smartAlerts.length > 5 && (
                    <div className="text-center pt-2">
                      <p className="text-sm text-gray-500 dark:text-gray-400">
                        +{smartAlerts.length - 5} more insights available
                      </p>
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>
        )}

        {/* ROI Performance Cards */}
        {(stats.total_capital_deposited > 0 || stats.total_starting_balance > 0) && (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
            {stats.total_capital_deposited > 0 && (
              <div className="bg-gradient-to-r from-blue-50 to-indigo-50 border border-blue-200 rounded-xl p-4">
                <h3 className="text-xs font-medium text-blue-700 uppercase tracking-wide mb-1">Capital Deposited</h3>
                <p className="text-lg md:text-xl font-bold text-blue-900">{formatCurrency(stats.total_capital_deposited)}</p>
              </div>
            )}
            
            {stats.total_starting_balance > 0 && (
              <div className="bg-gradient-to-r from-purple-50 to-pink-50 border border-purple-200 rounded-xl p-4">
                <h3 className="text-xs font-medium text-purple-700 uppercase tracking-wide mb-1">Starting Balance</h3>
                <p className="text-lg md:text-xl font-bold text-purple-900">{formatCurrency(stats.total_starting_balance)}</p>
              </div>
            )}
            
            {stats.total_capital_deposited > 0 && (
              <div className="bg-gradient-to-r from-emerald-50 to-teal-50 border border-emerald-200 rounded-xl p-4">
                <h3 className="text-xs font-medium text-emerald-700 uppercase tracking-wide mb-1">ROI vs Capital</h3>
                <p className={`text-lg md:text-xl font-bold ${stats.roi_vs_capital > 0 ? 'text-emerald-600' : stats.roi_vs_capital < 0 ? 'text-red-600' : 'text-gray-900'}`}>
                  {stats.roi_vs_capital > 0 ? '+' : ''}{(stats.roi_vs_capital || 0).toFixed(2)}%
                </p>
                <p className={`text-xs ${stats.roi_vs_capital > 0 ? 'text-emerald-600' : 'text-red-600'}`}>
                  {formatCurrency(Math.abs((stats.total_balance || 0) - (stats.total_capital_deposited || 0)))} {stats.roi_vs_capital >= 0 ? 'profit' : 'loss'}
                </p>
              </div>
            )}
            
            {stats.total_starting_balance > 0 && (
              <div className="bg-gradient-to-r from-amber-50 to-orange-50 border border-amber-200 rounded-xl p-4">
                <h3 className="text-xs font-medium text-amber-700 uppercase tracking-wide mb-1">ROI vs Start</h3>
                <p className={`text-lg md:text-xl font-bold ${stats.roi_vs_starting_balance > 0 ? 'text-amber-600' : stats.roi_vs_starting_balance < 0 ? 'text-red-600' : 'text-gray-900'}`}>
                  {stats.roi_vs_starting_balance > 0 ? '+' : ''}{(stats.roi_vs_starting_balance || 0).toFixed(2)}%
                </p>
                <p className={`text-xs ${stats.roi_vs_starting_balance > 0 ? 'text-amber-600' : 'text-red-600'}`}>
                  {formatCurrency(Math.abs((stats.total_balance || 0) - (stats.total_starting_balance || 0)))} {stats.roi_vs_starting_balance >= 0 ? 'gain' : 'loss'}
                </p>
              </div>
            )}
          </div>
        )}

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

        {/* Performance Heatmap - GitHub Style */}
        {showHeatmap && heatmapData.length > 0 && (
          <div className="mb-6">
            <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm p-6 transition-colors duration-200">
              <div className="flex justify-between items-center mb-6">
                <h3 className="text-lg font-semibold text-gray-900 dark:text-white">Performance Heatmap</h3>
                <div className="flex items-center space-x-2 text-xs text-gray-500 dark:text-gray-400">
                  <span>Less</span>
                  <div className="flex space-x-1">
                    {[0, 1, 2, 3, 4].map(level => (
                      <div 
                        key={level}
                        className="w-3 h-3 rounded-sm"
                        style={{ backgroundColor: getHeatmapColor(level, darkMode) }}
                      ></div>
                    ))}
                  </div>
                  <span>More</span>
                </div>
              </div>
              
              <div className="overflow-x-auto">
                <div className="min-w-max">
                  {/* Month Labels */}
                  <div className="flex mb-2">
                    <div className="w-6"></div>
                    {Array.from({length: 12}, (_, i) => {
                      const month = new Date(2024, i, 1).toLocaleDateString('en', { month: 'short' });
                      return (
                        <div key={i} className="flex-1 text-center text-xs text-gray-500 dark:text-gray-400 min-w-20">
                          {month}
                        </div>
                      );
                    })}
                  </div>
                  
                  {/* Days Grid */}
                  <div className="flex">
                    {/* Day Labels */}
                    <div className="flex flex-col space-y-1 mr-3">
                      {['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'].map((day, i) => (
                        <div key={day} className="h-3 flex items-center text-xs text-gray-500 dark:text-gray-400 w-6">
                          {i % 2 === 1 ? day : ''}
                        </div>
                      ))}
                    </div>
                    
                    {/* Heatmap Grid */}
                    <div className="grid grid-cols-53 gap-1">
                      {heatmapData.map((day, index) => {
                        const dayOfWeek = new Date(day.date).getDay();
                        return (
                          <div
                            key={index}
                            className={`w-3 h-3 rounded-sm cursor-pointer hover:ring-2 hover:ring-blue-400 dark:hover:ring-blue-300 transition-all duration-200`}
                            style={{ 
                              backgroundColor: getHeatmapColor(day.level, darkMode),
                              gridRow: dayOfWeek + 1
                            }}
                            title={`${day.date}: ${day.hasEntry ? `${day.pnl > 0 ? '+' : ''}${day.pnl.toFixed(2)}%` : 'No entry'}`}
                            onClick={() => {
                              if (day.hasEntry) {
                                alert(`${day.date}\nDaily PnL: ${day.pnl > 0 ? '+' : ''}${day.pnl.toFixed(2)}%`);
                              }
                            }}
                          ></div>
                        );
                      })}
                    </div>
                  </div>
                  
                  {/* Legend */}
                  <div className="mt-4 text-xs text-gray-500 dark:text-gray-400">
                    <div className="flex flex-wrap items-center space-x-4">
                      <span>📈 Green: Profitable days</span>
                      <span>🟨 Yellow: Small losses</span>
                      <span>⚫ Gray: No data / Large losses</span>
                      <span>💡 Hover for details</span>
                    </div>
                  </div>
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
          {entries.slice(0, 10).map((entry, index) => (
            <div key={entry.id} className={`px-4 py-4 ${index % 2 === 1 ? 'bg-gray-50' : 'bg-white'}`}>
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

      {/* Settings Manager Modal - Mobile Optimized */}
      {showSettingsManager && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-end md:items-center justify-center z-50 p-4 md:p-4">
          <div className="bg-white rounded-t-3xl md:rounded-2xl shadow-xl w-full md:max-w-4xl md:w-full max-h-[90vh] overflow-y-auto">
            <div className="p-6">
              <div className="flex justify-between items-center mb-6">
                <h2 className="text-xl font-semibold text-gray-900">Portfolio Settings</h2>
                <button
                  onClick={() => setShowSettingsManager(false)}
                  className="text-gray-400 hover:text-gray-600"
                >
                  ✕
                </button>
              </div>

              {/* Starting Balances Section */}
              <div className="mb-8">
                <h3 className="text-lg font-medium text-gray-900 mb-4">Starting Balances</h3>
                <div className="bg-blue-50 border border-blue-200 rounded-xl p-4 mb-4">
                  <p className="text-blue-700 text-sm">
                    Set starting balances for each exchange to track performance from your initial investment.
                  </p>
                </div>

                {/* Current Starting Balances - Show First */}
                <div className="mb-6">
                  <h4 className="text-md font-medium text-gray-800 mb-3">Current Starting Balances</h4>
                  
                  {settingsLoading ? (
                    <div className="text-center py-6 bg-gray-50 rounded-xl">
                      <p className="text-gray-500">Loading...</p>
                    </div>
                  ) : (
                    <div className="space-y-3">
                      {startingBalances.map((balance) => {
                        const exchange = exchanges.find(ex => ex.id === balance.exchange_id);
                        return (
                          <div key={balance.id} className="p-4 border border-gray-200 rounded-xl flex items-center justify-between bg-gray-50">
                            <div>
                              <p className="font-medium text-gray-900">{exchange?.display_name || 'Unknown Exchange'}</p>
                              <p className="text-sm text-gray-500">
                                Starting: {formatCurrency(balance.starting_balance)} on {new Date(balance.starting_date).toLocaleDateString()}
                              </p>
                            </div>
                            <div className="flex items-center space-x-2">
                              <button
                                onClick={() => startEditingStartingBalance(balance)}
                                className="text-blue-600 hover:text-blue-800 text-sm px-3 py-1 rounded border border-blue-200 hover:bg-blue-50"
                              >
                                Edit
                              </button>
                              <button
                                onClick={() => handleDeleteStartingBalance(balance.exchange_id)}
                                className="text-red-600 hover:text-red-800 text-sm px-3 py-1 rounded border border-red-200 hover:bg-red-50"
                              >
                                Delete
                              </button>
                            </div>
                          </div>
                        );
                      })}
                      
                      {startingBalances.length === 0 && !settingsLoading && (
                        <div className="text-center py-6 bg-gray-50 rounded-xl">
                          <p className="text-gray-500">No starting balances set yet.</p>
                          <p className="text-sm text-gray-400 mt-1">Add starting balances below to enable ROI tracking!</p>
                        </div>
                      )}
                    </div>
                  )}
                </div>
                
                {/* Add Starting Balance Form */}
                <div className="border-t pt-6">
                  <h4 className="text-md font-medium text-gray-800 mb-3">
                    {editingStartingBalance ? 'Edit Starting Balance' : 'Add New Starting Balance'}
                  </h4>
                  <form onSubmit={handleAddStartingBalance} className="p-4 border border-gray-200 rounded-xl">
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-2">Exchange</label>
                        <select
                          value={newStartingBalance.exchange_id}
                          onChange={(e) => setNewStartingBalance(prev => ({ ...prev, exchange_id: e.target.value }))}
                          className="w-full px-4 py-3 border border-gray-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-500"
                          required
                        >
                          <option value="">Select Exchange</option>
                          {exchanges.map((exchange) => (
                            <option key={exchange.id} value={exchange.id}>
                              {exchange.display_name}
                            </option>
                          ))}
                        </select>
                      </div>
                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-2">Starting Balance (€)</label>
                        <input
                          type="number"
                          step="0.01"
                          value={newStartingBalance.starting_balance}
                          onChange={(e) => setNewStartingBalance(prev => ({ ...prev, starting_balance: e.target.value }))}
                          className="w-full px-4 py-3 border border-gray-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-500"
                          placeholder="0.00"
                          required
                        />
                      </div>
                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-2">Starting Date</label>
                        <input
                          type="date"
                          value={newStartingBalance.starting_date}
                          onChange={(e) => setNewStartingBalance(prev => ({ ...prev, starting_date: e.target.value }))}
                          className="w-full px-4 py-3 border border-gray-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-500"
                          required
                        />
                      </div>
                    </div>
                    <div className="mt-4 flex space-x-3">
                      <button type="submit" className="btn-primary">
                        {editingStartingBalance ? 'Update Starting Balance' : 'Set Starting Balance'}
                      </button>
                      {editingStartingBalance && (
                        <button type="button" onClick={cancelEditingStartingBalance} className="btn-secondary">
                          Cancel
                        </button>
                      )}
                    </div>
                  </form>
                </div>
              </div>

              {/* Capital Deposits Section */}
              <div>
                <h3 className="text-lg font-medium text-gray-900 mb-4">Capital Deposits</h3>
                <div className="bg-green-50 border border-green-200 rounded-xl p-4 mb-4">
                  <p className="text-green-700 text-sm">
                    Track all capital deposits to calculate true ROI against your invested capital.
                  </p>
                </div>

                {/* Current Capital Deposits - Show First */}
                <div className="mb-6">
                  <h4 className="text-md font-medium text-gray-800 mb-3">Current Capital Deposits</h4>
                  <div className="space-y-3">
                    {capitalDeposits.map((deposit) => (
                      <div key={deposit.id} className="p-4 border border-gray-200 rounded-xl flex items-center justify-between bg-gray-50">
                        <div>
                          <p className="font-medium text-gray-900">{formatCurrency(deposit.amount)}</p>
                          <p className="text-sm text-gray-500">
                            {new Date(deposit.deposit_date).toLocaleDateString()}
                            {deposit.notes && ` • ${deposit.notes}`}
                          </p>
                        </div>
                        <div className="flex items-center space-x-2">
                          <button
                            onClick={() => startEditingCapitalDeposit(deposit)}
                            className="text-blue-600 hover:text-blue-800 text-sm px-3 py-1 rounded border border-blue-200 hover:bg-blue-50"
                          >
                            Edit
                          </button>
                          <button
                            onClick={() => handleDeleteCapitalDeposit(deposit.id)}
                            className="text-red-600 hover:text-red-800 text-sm px-3 py-1 rounded border border-red-200 hover:bg-red-50"
                          >
                            Delete
                          </button>
                        </div>
                      </div>
                    ))}
                    
                    {capitalDeposits.length === 0 && (
                      <div className="text-center py-6 bg-gray-50 rounded-xl">
                        <p className="text-gray-500">No capital deposits recorded yet.</p>
                        <p className="text-sm text-gray-400 mt-1">Add deposits below to track ROI vs invested capital!</p>
                      </div>
                    )}
                  </div>
                </div>
                
                {/* Add Capital Deposit Form */}
                <div className="border-t pt-6">
                  <h4 className="text-md font-medium text-gray-800 mb-3">
                    {editingCapitalDeposit ? 'Edit Capital Deposit' : 'Add New Capital Deposit'}
                  </h4>
                  <form onSubmit={handleAddCapitalDeposit} className="p-4 border border-gray-200 rounded-xl">
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-2">Amount (€)</label>
                        <input
                          type="number"
                          step="0.01"
                          value={newCapitalDeposit.amount}
                          onChange={(e) => setNewCapitalDeposit(prev => ({ ...prev, amount: e.target.value }))}
                          className="w-full px-4 py-3 border border-gray-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-500"
                          placeholder="0.00"
                          required
                        />
                      </div>
                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-2">Deposit Date</label>
                        <input
                          type="date"
                          value={newCapitalDeposit.deposit_date}
                          onChange={(e) => setNewCapitalDeposit(prev => ({ ...prev, deposit_date: e.target.value }))}
                          className="w-full px-4 py-3 border border-gray-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-500"
                          required
                        />
                      </div>
                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-2">Notes (Optional)</label>
                        <input
                          type="text"
                          value={newCapitalDeposit.notes}
                          onChange={(e) => setNewCapitalDeposit(prev => ({ ...prev, notes: e.target.value }))}
                          className="w-full px-4 py-3 border border-gray-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-500"
                          placeholder="Bank transfer, etc."
                        />
                      </div>
                    </div>
                    <div className="mt-4 flex space-x-3">
                      <button type="submit" className="btn-primary">
                        {editingCapitalDeposit ? 'Update Capital Deposit' : 'Add Capital Deposit'}
                      </button>
                      {editingCapitalDeposit && (
                        <button type="button" onClick={cancelEditingCapitalDeposit} className="btn-secondary">
                          Cancel
                        </button>
                      )}
                    </div>
                  </form>
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