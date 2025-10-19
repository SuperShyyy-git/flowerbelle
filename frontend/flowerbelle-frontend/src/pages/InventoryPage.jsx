import React, { useState, useEffect, useCallback } from 'react';
import { inventoryService } from '../services/inventoryService';
import { Plus, Edit, Trash2, AlertTriangle, Package, Search, Filter } from 'lucide-react';
import toast from 'react-hot-toast';
import Loading from '../components/common/Loading';

const InventoryPage = () => {
  const [products, setProducts] = useState([]);
  const [categories, setCategories] = useState([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedCategory, setSelectedCategory] = useState('');

const fetchData = useCallback(async () => {
  try {
    setLoading(true);
    const [productsRes, categoriesRes] = await Promise.all([
      inventoryService.getProducts({
        search: searchTerm,
        category: selectedCategory
      }),
      inventoryService.getCategories()
    ]);

    console.log("Products response:", productsRes.data);
    console.log("Categories response:", categoriesRes.data);

    // 🧩 Handle different response shapes safely
    const catData = categoriesRes.data;
    const prodData = productsRes.data;

    const normalizedCategories = Array.isArray(catData)
      ? catData
      : Array.isArray(catData.results)
      ? catData.results
      : Array.isArray(catData.categories)
      ? catData.categories
      : [];

    const normalizedProducts = Array.isArray(prodData)
      ? prodData
      : Array.isArray(prodData.results)
      ? prodData.results
      : Array.isArray(prodData.products)
      ? prodData.products
      : [];

    setProducts(normalizedProducts);
    setCategories(normalizedCategories);

  } catch (error) {
    console.error('Error fetching data:', error);
    toast.error('Failed to load inventory');
    setProducts([]);
    setCategories([]);
  } finally {
    setLoading(false);
  }
}, [searchTerm, selectedCategory]);


  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const handleDelete = async (id) => {
    if (!window.confirm('Are you sure you want to delete this product?')) {
      return;
    }

    try {
      await inventoryService.deleteProduct(id);
      toast.success('Product deleted successfully');
      fetchData();
    } catch (error) {
      toast.error('Failed to delete product');
    }
  };

  if (loading) {
    return <Loading message="Loading inventory..." />;
  }

  return (
    <div>
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-2xl font-bold">Inventory Management</h2>
        <button
          onClick={() => toast('Add product functionality coming soon', {
            icon: 'ℹ️',
            style: {
              background: '#3b82f6',
              color: 'white',
            },
          })}
          className="btn-primary flex items-center space-x-2"
        >
          <Plus className="w-5 h-5" />
          <span>Add Product</span>
        </button>
      </div>

      {/* Filters */}
      <div className="card mb-6">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {/* Search */}
          <div className="relative">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400" />
            <input
              type="text"
              placeholder="Search products..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="input-field pl-10"
            />
          </div>

          {/* Category Filter */}
          <div className="relative">
            <Filter className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400" />
            <select
              value={selectedCategory}
              onChange={(e) => setSelectedCategory(e.target.value)}
              className="input-field pl-10"
            >
              <option value="">All Categories</option>
              {categories.map(cat => (
                <option key={cat.id} value={cat.id}>{cat.name}</option>
              ))}
            </select>
          </div>

          {/* Stock Status */}
          <div className="flex items-center space-x-2">
            <button className="btn-secondary flex-1">All Stock</button>
            <button className="btn-secondary flex-1">Low Stock</button>
          </div>
        </div>
      </div>

      {/* Products Table */}
      <div className="card overflow-hidden">
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Product
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  SKU
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Category
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Price
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Stock
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Status
                </th>
                <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Actions
                </th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {products.map((product) => (
                <tr key={product.id} className="hover:bg-gray-50">
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div className="flex items-center">
                      <div className="w-10 h-10 bg-gray-100 rounded flex items-center justify-center mr-3">
                        {product.image ? (
                          <img src={product.image} alt={product.name} className="w-10 h-10 object-cover rounded" />
                        ) : (
                          <Package className="w-5 h-5 text-gray-400" />
                        )}
                      </div>
                      <div>
                        <div className="text-sm font-medium text-gray-900">{product.name}</div>
                      </div>
                    </div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                    {product.sku}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                    {product.category_name}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                    ₱{parseFloat(product.unit_price).toLocaleString()}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div className="flex items-center">
                      <span className={`text-sm font-medium ${
                        product.is_low_stock ? 'text-red-600' : 'text-gray-900'
                      }`}>
                        {product.current_stock}
                      </span>
                      {product.is_low_stock && (
                        <AlertTriangle className="w-4 h-4 text-red-600 ml-2" />
                      )}
                    </div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <span className={`px-2 py-1 inline-flex text-xs leading-5 font-semibold rounded-full ${
                      product.is_active 
                        ? 'bg-green-100 text-green-800' 
                        : 'bg-red-100 text-red-800'
                    }`}>
                      {product.is_active ? 'Active' : 'Inactive'}
                    </span>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                    <button
                      onClick={() => toast('Edit functionality coming soon', {
                        icon: 'ℹ️',
                        style: {
                          background: '#3b82f6',
                          color: 'white',
                        },
                      })}
                      className="text-primary-600 hover:text-primary-900 mr-3"
                    >
                      <Edit className="w-4 h-4" />
                    </button>
                    <button
                      onClick={() => handleDelete(product.id)}
                      className="text-red-600 hover:text-red-900"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>

          {products.length === 0 && (
            <div className="text-center py-12">
              <Package className="w-12 h-12 text-gray-400 mx-auto mb-3" />
              <p className="text-gray-500">No products found</p>
            </div>
          )}
        </div>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mt-6">
        <div className="card">
          <p className="text-sm text-gray-500 mb-1">Total Products</p>
          <p className="text-2xl font-bold">{products.length}</p>
        </div>
        <div className="card">
          <p className="text-sm text-gray-500 mb-1">Low Stock Items</p>
          <p className="text-2xl font-bold text-red-600">
            {products.filter(p => p.is_low_stock).length}
          </p>
        </div>
        <div className="card">
          <p className="text-sm text-gray-500 mb-1">Out of Stock</p>
          <p className="text-2xl font-bold text-red-600">
            {products.filter(p => p.current_stock === 0).length}
          </p>
        </div>
        <div className="card">
          <p className="text-sm text-gray-500 mb-1">Categories</p>
          <p className="text-2xl font-bold">{categories.length}</p>
        </div>
      </div>
    </div>
  );
};

export default InventoryPage;