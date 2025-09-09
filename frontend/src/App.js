import React, { useState, useEffect } from "react";
import "./App.css";
import axios from "axios";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const CryptoPnLTracker = () => {
  const [entries, setEntries] = useState([]);
  const [stats, setStats] = useState({});
  const [loading, setLoading] = useState(true);
  const [showAddForm, setShowAddForm] = useState(false);
  const [editingEntry, setEditingEntry] = useState(null);
  const [formData, setFormData] = useState({
    date: new Date().toISOString().split('T')[0],
    kraken: '',
    bitget: '',
    binance: '',
    notes: ''
  });

  // Fetch entries and stats
  const fetchData = async () => {
    try {
      setLoading(true);
      const [entriesRes, statsRes] = await Promise.all([
        axios.get(`${API}/entries`),
        axios.get(`${API}/stats`)
      ]);
      setEntries(entriesRes.data);
      setStats(statsRes.data);
    } catch (error) {
      console.error('Error fetching data:', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  // Handle form input changes
  const handleInputChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: value
    }));
  };

  // Add new entry
  const handleAddEntry = async (e) => {
    e.preventDefault();
    try {
      const entryData = {
        date: formData.date,
        balances: {
          kraken: parseFloat(formData.kraken) || 0,
          bitget: parseFloat(formData.bitget) || 0,
          binance: parseFloat(formData.binance) || 0
        },
        notes: formData.notes
      };

      await axios.post(`${API}/entries`, entryData);
      setFormData({
        date: new Date().toISOString().split('T')[0],
        kraken: '',
        bitget: '',
        binance: '',
        notes: ''
      });
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
        balances: {
          kraken: parseFloat(formData.kraken) || 0,
          bitget: parseFloat(formData.bitget) || 0,
          binance: parseFloat(formData.binance) || 0
        },
        notes: formData.notes
      };

      await axios.put(`${API}/entries/${editingEntry.id}`, updateData);
      setEditingEntry(null);
      setFormData({
        date: new Date().toISOString().split('T')[0],
        kraken: '',
        bitget: '',
        binance: '',
        notes: ''
      });
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
    setFormData({
      date: entry.date,
      kraken: entry.balances.kraken.toString(),
      bitget: entry.balances.bitget.toString(),
      binance: entry.balances.binance.toString(),
      notes: entry.notes || ''
    });
    setShowAddForm(true);
  };

  // Cancel editing
  const cancelEditing = () => {
    setEditingEntry(null);
    setFormData({
      date: new Date().toISOString().split('T')[0],
      kraken: '',
      bitget: '',
      binance: '',
      notes: ''
    });
    setShowAddForm(false);
  };

  // Format currency
  const formatCurrency = (amount) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'EUR',
      minimumFractionDigits: 0,
      maximumFractionDigits: 0
    }).format(amount);
  };

  // Get PnL color class
  const getPnLColor = (value) => {
    if (value > 0) return 'text-green-600 bg-green-50';
    if (value < 0) return 'text-red-600 bg-red-50';
    return 'text-gray-600 bg-gray-50';
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
      {/* Header */}
      <div className="bg-white shadow-sm border-b">
        <div className="max-w-7xl mx-auto px-4 py-6">
          <div className="flex justify-between items-center">
            <div>
              <h1 className="text-3xl font-bold text-gray-900">Crypto PnL Tracker</h1>
              <p className="text-gray-600 mt-1">Track your daily cryptocurrency portfolio performance</p>
            </div>
            <button
              onClick={() => setShowAddForm(true)}
              className="btn-primary"
            >
              Add Entry
            </button>
          </div>
        </div>
      </div>

      {/* Stats Cards */}
      <div className="max-w-7xl mx-auto px-4 py-6">
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
          <div className="bg-white rounded-lg shadow-sm p-6">
            <h3 className="text-sm font-medium text-gray-500 uppercase tracking-wide">Total Balance</h3>
            <p className="mt-2 text-3xl font-bold text-gray-900">{formatCurrency(stats.total_balance || 0)}</p>
          </div>
          <div className="bg-white rounded-lg shadow-sm p-6">
            <h3 className="text-sm font-medium text-gray-500 uppercase tracking-wide">Daily PnL</h3>
            <p className={`mt-2 text-3xl font-bold ${stats.daily_pnl > 0 ? 'text-green-600' : stats.daily_pnl < 0 ? 'text-red-600' : 'text-gray-900'}`}>
              {formatCurrency(stats.daily_pnl || 0)}
            </p>
            <p className={`text-sm ${stats.daily_pnl_percentage > 0 ? 'text-green-600' : stats.daily_pnl_percentage < 0 ? 'text-red-600' : 'text-gray-500'}`}>
              {stats.daily_pnl_percentage > 0 ? '+' : ''}{(stats.daily_pnl_percentage || 0).toFixed(2)}%
            </p>
          </div>
          <div className="bg-white rounded-lg shadow-sm p-6">
            <h3 className="text-sm font-medium text-gray-500 uppercase tracking-wide">Avg Daily PnL</h3>
            <p className={`mt-2 text-3xl font-bold ${stats.avg_daily_pnl > 0 ? 'text-green-600' : stats.avg_daily_pnl < 0 ? 'text-red-600' : 'text-gray-900'}`}>
              {formatCurrency(stats.avg_daily_pnl || 0)}
            </p>
          </div>
          <div className="bg-white rounded-lg shadow-sm p-6">
            <h3 className="text-sm font-medium text-gray-500 uppercase tracking-wide">Total Entries</h3>
            <p className="mt-2 text-3xl font-bold text-gray-900">{stats.total_entries || 0}</p>
          </div>
        </div>

        {/* KPI Progress */}
        <div className="bg-white rounded-lg shadow-sm p-6 mb-8">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">KPI Progress</h3>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {['5k', '10k', '15k'].map((kpi) => {
              const progress = stats.kpi_progress?.[kpi] || 0;
              const target = parseInt(kpi.replace('k', '000'));
              const current = target + progress;
              const percentage = Math.max(0, Math.min(100, (current / target) * 100));
              
              return (
                <div key={kpi} className="space-y-2">
                  <div className="flex justify-between text-sm">
                    <span className="font-medium text-gray-700">KPI {kpi.toUpperCase()}</span>
                    <span className={progress >= 0 ? 'text-green-600' : 'text-red-600'}>
                      {progress >= 0 ? '+' : ''}{formatCurrency(progress)}
                    </span>
                  </div>
                  <div className="w-full bg-gray-200 rounded-full h-2">
                    <div
                      className={`h-2 rounded-full transition-all duration-300 ${
                        percentage >= 100 ? 'bg-green-500' : percentage >= 75 ? 'bg-yellow-500' : 'bg-blue-500'
                      }`}
                      style={{ width: `${percentage}%` }}
                    ></div>
                  </div>
                  <div className="text-xs text-gray-500">
                    {formatCurrency(current)} / {formatCurrency(target)} ({percentage.toFixed(1)}%)
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Add/Edit Form Modal */}
        {showAddForm && (
          <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
            <div className="bg-white rounded-lg shadow-xl max-w-md w-full">
              <div className="p-6">
                <h2 className="text-xl font-semibold text-gray-900 mb-4">
                  {editingEntry ? 'Edit Entry' : 'Add New Entry'}
                </h2>
                <form onSubmit={editingEntry ? handleEditEntry : handleAddEntry} className="space-y-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Date</label>
                    <input
                      type="date"
                      name="date"
                      value={formData.date}
                      onChange={handleInputChange}
                      className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                      required
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Kraken Balance (€)</label>
                    <input
                      type="number"
                      name="kraken"
                      value={formData.kraken}
                      onChange={handleInputChange}
                      step="0.01"
                      className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                      placeholder="0.00"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Bitget Balance (€)</label>
                    <input
                      type="number"
                      name="bitget"
                      value={formData.bitget}
                      onChange={handleInputChange}
                      step="0.01"
                      className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                      placeholder="0.00"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Binance Balance (€)</label>
                    <input
                      type="number"
                      name="binance"
                      value={formData.binance}
                      onChange={handleInputChange}
                      step="0.01"
                      className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                      placeholder="0.00"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Notes</label>
                    <textarea
                      name="notes"
                      value={formData.notes}
                      onChange={handleInputChange}
                      rows="3"
                      className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                      placeholder="Optional notes about this entry..."
                    />
                  </div>
                  <div className="flex space-x-3 pt-4">
                    <button
                      type="submit"
                      className="flex-1 btn-primary"
                    >
                      {editingEntry ? 'Update Entry' : 'Add Entry'}
                    </button>
                    <button
                      type="button"
                      onClick={cancelEditing}
                      className="flex-1 btn-secondary"
                    >
                      Cancel
                    </button>
                  </div>
                </form>
              </div>
            </div>
          </div>
        )}

        {/* Entries Table */}
        <div className="bg-white rounded-lg shadow-sm overflow-hidden">
          <div className="px-6 py-4 border-b border-gray-200">
            <h2 className="text-lg font-semibold text-gray-900">Daily Entries</h2>
          </div>
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Date</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Kraken</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Bitget</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Binance</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Total</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">PnL %</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">PnL €</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">KPI 5K</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">KPI 10K</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">KPI 15K</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Notes</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Actions</th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {entries.map((entry) => (
                  <tr key={entry.id} className="hover:bg-gray-50">
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                      {new Date(entry.date).toLocaleDateString()}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                      {formatCurrency(entry.balances.kraken)}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                      {formatCurrency(entry.balances.bitget)}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                      {formatCurrency(entry.balances.binance)}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                      {formatCurrency(entry.total)}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm">
                      <span className={`px-2 py-1 rounded-full text-xs font-medium ${getPnLColor(entry.pnl_percentage)}`}>
                        {entry.pnl_percentage > 0 ? '+' : ''}{entry.pnl_percentage.toFixed(2)}%
                      </span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm">
                      <span className={`px-2 py-1 rounded-full text-xs font-medium ${getPnLColor(entry.pnl_amount)}`}>
                        {entry.pnl_amount > 0 ? '+' : ''}{formatCurrency(entry.pnl_amount)}
                      </span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm">
                      <span className={`text-xs font-medium ${entry.kpi_5k >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                        {entry.kpi_5k > 0 ? '+' : ''}{formatCurrency(entry.kpi_5k)}
                      </span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm">
                      <span className={`text-xs font-medium ${entry.kpi_10k >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                        {entry.kpi_10k > 0 ? '+' : ''}{formatCurrency(entry.kpi_10k)}
                      </span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm">
                      <span className={`text-xs font-medium ${entry.kpi_15k >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                        {entry.kpi_15k > 0 ? '+' : ''}{formatCurrency(entry.kpi_15k)}
                      </span>
                    </td>
                    <td className="px-6 py-4 text-sm text-gray-500 max-w-xs truncate">
                      {entry.notes}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      <div className="flex space-x-2">
                        <button
                          onClick={() => startEditing(entry)}
                          className="text-blue-600 hover:text-blue-900 text-xs"
                        >
                          Edit
                        </button>
                        <button
                          onClick={() => handleDeleteEntry(entry.id)}
                          className="text-red-600 hover:text-red-900 text-xs"
                        >
                          Delete
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {entries.length === 0 && (
            <div className="text-center py-12">
              <p className="text-gray-500">No entries yet. Add your first entry to get started!</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

function App() {
  return (
    <div className="App">
      <CryptoPnLTracker />
    </div>
  );
}

export default App;