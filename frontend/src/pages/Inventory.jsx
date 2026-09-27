import React, { useState, useEffect } from 'react';
import { departmentsAPI, inventoryAPI } from '../services/api';
import { Package, AlertTriangle, CheckCircle2, ShoppingCart, RefreshCw, ArrowUpRight } from 'lucide-react';
import { getStatusColor, formatDateTime } from '../utils/helpers';
import { getDepartmentNameForCategory, matchesDepartment } from '../utils/departments';

export const Inventory = () => {
  const [items, setItems] = useState([]);
  const [pos, setPos] = useState([]);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState('inventory');
  const [departments, setDepartments] = useState([]);
  const [selectedDepartment, setSelectedDepartment] = useState('all');

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    try {
      const [itemsRes, posRes, departmentsRes] = await Promise.all([
        inventoryAPI.getItems(),
        inventoryAPI.getPurchaseOrders(),
        departmentsAPI.getAll()
      ]);
      setItems(itemsRes.data);
      setPos(posRes.data);
      setDepartments(departmentsRes.data);
    } catch (err) {
      console.error('Failed to fetch inventory data:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleReceivePO = async (poId) => {
    try {
      await inventoryAPI.receivePurchaseOrder(poId);
      await fetchData();
      alert('Purchase order marked as received! Inventory restocked.');
    } catch (err) {
      alert('Failed to receive order: ' + (err.response?.data?.detail || err.message));
    }
  };

  const handleApproveReorder = async (item) => {
    const qty = Math.max(item.reorder_threshold, (item.max_stock || item.reorder_threshold * 2) - item.current_stock);
    try {
      await inventoryAPI.createPurchaseOrder({
        inventory_item_id: item.id,
        quantity: qty,
        supplier: 'Primary Vendor'
      });
      await fetchData();
      alert(`✅ Purchase Order approved and issued for ${qty} ${item.unit} of ${item.name}!`);
    } catch (err) {
      alert('Failed to approve purchase order: ' + (err.response?.data?.detail || err.message));
    }
  };

  const handleApproveAllCritical = async () => {
    if (!window.confirm(`Approve purchase orders for all ${criticalItems.length} critical inventory items?`)) return;
    try {
      await Promise.all(criticalItems.map((item) => {
        const qty = Math.max(item.reorder_threshold, (item.max_stock || item.reorder_threshold * 2) - item.current_stock);
        return inventoryAPI.createPurchaseOrder({
          inventory_item_id: item.id,
          quantity: qty,
          supplier: 'Primary Vendor'
        });
      }));
      await fetchData();
      alert(`🎉 Successfully approved purchase orders for all ${criticalItems.length} critical items!`);
    } catch (err) {
      alert('Failed to approve critical purchase orders: ' + (err.response?.data?.detail || err.message));
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <RefreshCw className="w-8 h-8 text-forest-700 animate-spin" />
      </div>
    );
  }

  const filteredItems = items.filter((item) => matchesDepartment(
    getDepartmentNameForCategory(item.category),
    selectedDepartment
  ));
  const filteredPos = pos.filter((po) => matchesDepartment(
    getDepartmentNameForCategory(po.category),
    selectedDepartment
  ));
  const criticalItems = filteredItems.filter(i => i.stockout_risk === 'CRITICAL' || i.stockout_risk === 'HIGH');

  return (
    <div className="max-w-7xl mx-auto px-4 py-8 space-y-6">
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl md:text-3xl font-bold text-charcoal-900 flex items-center gap-3">
            <Package className="w-7 h-7 text-brass-600" />
            Inventory & Purchase Orders
          </h1>
          <p className="text-sm text-charcoal-600 mt-1">
            Predictive stockout alerts based on 7-day occupancy forecast demand
          </p>
        </div>

        <div className="flex items-center gap-2">
          <label htmlFor="inventory-department" className="text-xs font-bold text-charcoal-700 uppercase tracking-wider">Department:</label>
          <select
            id="inventory-department"
            value={selectedDepartment}
            onChange={(e) => setSelectedDepartment(e.target.value)}
            className="px-3 py-1.5 text-xs font-semibold rounded-lg bg-white border border-ivory-300 text-charcoal-900 shadow-sm focus:outline-none focus:ring-2 focus:ring-forest-500"
          >
            <option value="all">All Departments</option>
            {departments.map((department) => (
              <option key={department.id} value={department.name}>{department.name}</option>
            ))}
          </select>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex gap-2">
        <button
          onClick={() => setActiveTab('inventory')}
          className={`px-4 py-2 rounded-lg text-sm font-semibold transition ${
            activeTab === 'inventory'
              ? 'bg-forest-800 text-white shadow-sm'
              : 'bg-white border border-ivory-300 text-charcoal-700 hover:bg-ivory-50'
          }`}
        >
          Inventory Items ({items.length})
        </button>
        <button
          onClick={() => setActiveTab('pos')}
          className={`px-4 py-2 rounded-lg text-sm font-semibold transition ${
            activeTab === 'pos'
              ? 'bg-forest-800 text-white shadow-sm'
              : 'bg-white border border-ivory-300 text-charcoal-700 hover:bg-ivory-50'
          }`}
        >
          Purchase Orders ({pos.length})
        </button>
      </div>

      {activeTab === 'inventory' && (
        <div className="space-y-6">
          {/* Critical Risk Banner */}
          {criticalItems.length > 0 && (
            <div className="bg-red-50 border border-red-200 rounded-xl p-4 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 shadow-sm">
              <div className="flex items-center gap-3">
                <AlertTriangle className="w-5 h-5 text-red-600 flex-shrink-0" />
                <div>
                  <p className="text-sm font-bold text-red-900">
                    {criticalItems.length} items at critical risk of stockout within lead time!
                  </p>
                  <p className="text-xs text-red-700">
                    High occupancy demand requires immediate replenishment.
                  </p>
                </div>
              </div>
              <button
                onClick={handleApproveAllCritical}
                className="flex items-center gap-1.5 px-4 py-2 bg-red-700 hover:bg-red-800 text-white text-xs font-bold rounded-lg shadow-sm transition whitespace-nowrap"
              >
                <CheckCircle2 className="w-4 h-4" />
                Approve All {criticalItems.length} POs
              </button>
            </div>
          )}

          {/* Inventory Grid */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {filteredItems.map((item) => {
              const suggestedQty = Math.max(item.reorder_threshold, (item.max_stock || item.reorder_threshold * 2) - item.current_stock);
              const estCost = suggestedQty * (item.unit_cost || 5);
              return (
              <div
                key={item.id}
                className="surface p-5 rounded-xl border border-ivory-300 shadow-sm relative overflow-hidden flex flex-col justify-between"
              >
                <div>
                  <div className="flex items-start justify-between mb-3">
                    <div>
                      <span className="text-[10px] font-mono font-bold text-charcoal-500 uppercase tracking-wider">
                        {item.category}
                      </span>
                      <h3 className="font-bold text-charcoal-900 text-base">{item.name}</h3>
                    </div>
                    <span
                      className={`px-2 py-0.5 text-[10px] font-bold rounded border ${
                        item.stockout_risk === 'CRITICAL'
                          ? 'bg-red-100 text-red-800 border-red-200'
                          : item.stockout_risk === 'HIGH'
                          ? 'bg-amber-100 text-amber-900 border-amber-200'
                          : 'bg-emerald-100 text-emerald-800 border-emerald-200'
                      }`}
                    >
                      {item.stockout_risk} RISK
                    </span>
                  </div>

                  <div className="space-y-2 text-xs text-charcoal-700 mb-2 bg-ivory-50 p-3 rounded-lg border border-ivory-200">
                    <div className="flex justify-between">
                      <span className="text-charcoal-500">Current Stock:</span>
                      <span className="font-bold text-charcoal-900 font-mono">{item.current_stock} {item.unit}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-charcoal-500">Reorder Threshold:</span>
                      <span className="font-mono text-charcoal-800">{item.reorder_threshold} {item.unit}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-charcoal-500">Projected Runout:</span>
                      <span className="font-bold text-amber-800 font-mono">
                        {item.projected_days_left > 30 ? '> 30 days' : `${item.projected_days_left.toFixed(1)} days`}
                      </span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-charcoal-500">Supplier Lead Time:</span>
                      <span className="font-mono text-charcoal-800">{item.lead_time_days} days</span>
                    </div>
                  </div>
                </div>

                <div className="mt-3 pt-3 border-t border-ivory-200 flex items-center justify-between gap-2">
                  <span className="text-[11px] text-charcoal-500 font-medium">
                    Est. PO: <strong className="text-charcoal-900 font-mono">${estCost.toFixed(2)}</strong> ({suggestedQty} {item.unit})
                  </span>
                  <button
                    onClick={() => handleApproveReorder(item)}
                    className={`flex items-center gap-1.5 px-3 py-1.5 text-xs font-bold rounded-lg transition shadow-sm ${
                      item.stockout_risk === 'CRITICAL'
                        ? 'bg-red-700 hover:bg-red-800 text-white'
                        : item.stockout_risk === 'HIGH'
                        ? 'bg-amber-600 hover:bg-amber-700 text-white'
                        : 'bg-forest-800 hover:bg-forest-900 text-white'
                    }`}
                  >
                    <CheckCircle2 className="w-3.5 h-3.5" />
                    Approve PO
                  </button>
                </div>
              </div>
            );})}
          </div>
        </div>
      )}

      {activeTab === 'pos' && (
        <div className="surface p-6 rounded-xl border border-ivory-300 shadow-sm overflow-x-auto">
          <h2 className="text-lg font-bold text-charcoal-900 mb-4 flex items-center gap-2">
            <ShoppingCart className="w-5 h-5 text-forest-700" />
            Purchase Order Execution Trail
          </h2>

          {filteredPos.length === 0 ? (
            <p className="text-sm text-charcoal-500 text-center py-8">No purchase orders created yet.</p>
          ) : (
            <table className="w-full text-left text-xs text-charcoal-800">
              <thead className="bg-ivory-100 text-charcoal-700 uppercase tracking-wider text-[11px] border-b border-ivory-200">
                <tr>
                  <th className="p-3">PO #</th>
                  <th className="p-3">Item Name</th>
                  <th className="p-3">Quantity</th>
                  <th className="p-3">Est. Cost</th>
                  <th className="p-3">Supplier</th>
                  <th className="p-3">Status</th>
                  <th className="p-3">Approved By</th>
                  <th className="p-3">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-ivory-200">
                {filteredPos.map((po) => (
                  <tr key={po.id} className="hover:bg-ivory-50/60">
                    <td className="p-3 font-mono text-forest-800 font-bold">PO-{po.id}</td>
                    <td className="p-3 font-bold text-charcoal-900">{po.item_name}</td>
                    <td className="p-3 font-mono font-bold text-emerald-800">{po.quantity} {po.unit}</td>
                    <td className="p-3 font-mono text-charcoal-800">${po.estimated_cost?.toFixed(2)}</td>
                    <td className="p-3 text-charcoal-600">{po.supplier}</td>
                    <td className="p-3">
                      <span className={`px-2 py-0.5 text-[10px] font-semibold rounded border ${getStatusColor(po.status)}`}>
                        {po.status}
                      </span>
                    </td>
                    <td className="p-3 text-charcoal-700">{po.approved_by || 'System'}</td>
                    <td className="p-3">
                      {po.status === 'ORDERED' ? (
                        <button
                          onClick={() => handleReceivePO(po.id)}
                          className="px-2.5 py-1 bg-emerald-700 hover:bg-emerald-800 text-white rounded text-xs font-semibold shadow-sm"
                        >
                          Receive & Restock
                        </button>
                      ) : (
                        <span className="text-emerald-700 text-xs font-semibold">Fulfilled ✓</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      )}
    </div>
  );
};

