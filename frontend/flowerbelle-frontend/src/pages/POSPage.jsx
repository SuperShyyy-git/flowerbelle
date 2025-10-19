import React, { useState, useEffect, useCallback } from 'react';
import { inventoryService } from '../services/inventoryService';
import { posService } from '../services/posService';
import { Search, Plus, Minus, Trash2, ShoppingCart, X, Package } from 'lucide-react';
import toast from 'react-hot-toast';

const POSPage = () => {
  const [products, setProducts] = useState([]);
  const [cart, setCart] = useState([]);
  const [searchTerm, setSearchTerm] = useState('');
  const [loading, setLoading] = useState(false);
  const [showCheckout, setShowCheckout] = useState(false);
  const [paymentMethod, setPaymentMethod] = useState('CASH');
  const [amountPaid, setAmountPaid] = useState('');
  const [customerName, setCustomerName] = useState('');

const fetchProducts = useCallback(async () => {
  try {
    const response = await inventoryService.getProducts({ search: searchTerm });
    console.log('Fetched products response:', response.data);

    // Normalize data: handle array or paginated object
    const data = response.data;

    if (Array.isArray(data)) {
      setProducts(data);
    } else if (Array.isArray(data.results)) {
      setProducts(data.results);
    } else if (Array.isArray(data.products)) {
      setProducts(data.products);
    } else {
      console.error("Unexpected product data format:", data);
      setProducts([]); // fallback to empty array
    }

  } catch (error) {
    console.error('Error fetching products:', error);
    setProducts([]);
  }
}, [searchTerm]);


  const addToCart = (product) => {
    const existingItem = cart.find(item => item.id === product.id);
    
    if (existingItem) {
      if (existingItem.quantity >= product.current_stock) {
        toast.error('Insufficient stock');
        return;
      }
      setCart(cart.map(item =>
        item.id === product.id
          ? { ...item, quantity: item.quantity + 1 }
          : item
      ));
    } else {
      if (product.current_stock === 0) {
        toast.error('Product out of stock');
        return;
      }
      setCart([...cart, { ...product, quantity: 1 }]);
    }
    toast.success('Added to cart');
  };

  const updateQuantity = (productId, delta) => {
    const product = products.find(p => p.id === productId);
    const cartItem = cart.find(item => item.id === productId);
    
    if (delta > 0 && cartItem.quantity >= product.current_stock) {
      toast.error('Insufficient stock');
      return;
    }

    setCart(cart.map(item =>
      item.id === productId
        ? { ...item, quantity: Math.max(1, item.quantity + delta) }
        : item
    ));
  };

  const removeFromCart = (productId) => {
    setCart(cart.filter(item => item.id !== productId));
    toast.success('Removed from cart');
  };

  const clearCart = () => {
    setCart([]);
    toast.success('Cart cleared');
  };

  const calculateSubtotal = () => {
    return cart.reduce((sum, item) => sum + (item.unit_price * item.quantity), 0);
  };

  const calculateTotal = () => {
    return calculateSubtotal();
  };

  const calculateChange = () => {
    const paid = parseFloat(amountPaid) || 0;
    const total = calculateTotal();
    return Math.max(0, paid - total);
  };

  const handleCheckout = async () => {
    if (cart.length === 0) {
      toast.error('Cart is empty');
      return;
    }

    const paid = parseFloat(amountPaid);
    const total = calculateTotal();

    if (!paid || paid < total) {
      toast.error('Insufficient payment amount');
      return;
    }

    setLoading(true);
    try {
      const transactionData = {
        items: cart.map(item => ({
          product: item.id,
          quantity: item.quantity,
          unit_price: item.unit_price,
          discount: 0
        })),
        payment_method: paymentMethod,
        amount_paid: paid,
        tax: 0,
        discount: 0,
        customer_name: customerName,
      };

      await posService.createTransaction(transactionData);
      
      toast.success('Sale completed successfully!');
      setCart([]);
      setShowCheckout(false);
      setAmountPaid('');
      setCustomerName('');
      fetchProducts();
    } catch (error) {
      console.error('Checkout error:', error);
      toast.error(error.response?.data?.error || 'Checkout failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
      {/* Products Section */}
      <div className="lg:col-span-2">
        <div className="card">
          <div className="mb-4">
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
          </div>

          <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
            {products.map((product) => (
              <div
                key={product.id}
                onClick={() => addToCart(product)}
                className="border border-gray-200 rounded-lg p-4 hover:border-primary-500 hover:shadow-md cursor-pointer transition-all"
              >
                <div className="aspect-square bg-gray-100 rounded-lg mb-3 flex items-center justify-center">
                  {product.image ? (
                    <img src={product.image} alt={product.name} className="w-full h-full object-cover rounded-lg" />
                  ) : (
                    <Package className="w-12 h-12 text-gray-400" />
                  )}
                </div>
                <h3 className="font-medium text-gray-900 mb-1 truncate">{product.name}</h3>
                <p className="text-sm text-gray-500 mb-2">{product.sku}</p>
                <div className="flex items-center justify-between">
                  <span className="text-lg font-bold text-primary-600">
                    ₱{parseFloat(product.unit_price).toLocaleString()}
                  </span>
                  <span className={`text-xs ${product.current_stock <= product.reorder_level ? 'text-red-600' : 'text-gray-500'}`}>
                    Stock: {product.current_stock}
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Cart Section */}
      <div className="lg:col-span-1">
        <div className="card sticky top-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-xl font-bold flex items-center">
              <ShoppingCart className="w-6 h-6 mr-2" />
              Cart ({cart.length})
            </h2>
            {cart.length > 0 && (
              <button onClick={clearCart} className="text-red-600 text-sm hover:underline">
                Clear All
              </button>
            )}
          </div>

          <div className="space-y-3 mb-4 max-h-96 overflow-y-auto">
            {cart.length === 0 ? (
              <p className="text-gray-500 text-center py-8">Cart is empty</p>
            ) : (
              cart.map((item) => (
                <div key={item.id} className="border border-gray-200 rounded-lg p-3">
                  <div className="flex items-start justify-between mb-2">
                    <div className="flex-1">
                      <h4 className="font-medium text-gray-900">{item.name}</h4>
                      <p className="text-sm text-gray-500">₱{parseFloat(item.unit_price).toLocaleString()}</p>
                    </div>
                    <button
                      onClick={() => removeFromCart(item.id)}
                      className="text-red-600 hover:text-red-700"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>
                  <div className="flex items-center justify-between">
                    <div className="flex items-center space-x-2">
                      <button
                        onClick={() => updateQuantity(item.id, -1)}
                        className="w-8 h-8 flex items-center justify-center bg-gray-100 rounded hover:bg-gray-200"
                      >
                        <Minus className="w-4 h-4" />
                      </button>
                      <span className="w-12 text-center font-medium">{item.quantity}</span>
                      <button
                        onClick={() => updateQuantity(item.id, 1)}
                        className="w-8 h-8 flex items-center justify-center bg-gray-100 rounded hover:bg-gray-200"
                      >
                        <Plus className="w-4 h-4" />
                      </button>
                    </div>
                    <span className="font-bold">
                      ₱{(item.unit_price * item.quantity).toLocaleString()}
                    </span>
                  </div>
                </div>
              ))
            )}
          </div>

          {cart.length > 0 && (
            <div className="border-t border-gray-200 pt-4 space-y-2">
              <div className="flex justify-between text-lg">
                <span className="font-medium">Subtotal:</span>
                <span className="font-bold">₱{calculateSubtotal().toLocaleString()}</span>
              </div>
              <div className="flex justify-between text-xl">
                <span className="font-bold">Total:</span>
                <span className="font-bold text-primary-600">
                  ₱{calculateTotal().toLocaleString()}
                </span>
              </div>
              <button
                onClick={() => setShowCheckout(true)}
                className="w-full btn-primary py-3 mt-4"
              >
                Proceed to Checkout
              </button>
            </div>
          )}
        </div>
      </div>

      {/* Checkout Modal */}
      {showCheckout && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-6 max-w-md w-full mx-4">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-2xl font-bold">Checkout</h2>
              <button onClick={() => setShowCheckout(false)} className="text-gray-500 hover:text-gray-700">
                <X className="w-6 h-6" />
              </button>
            </div>

            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Customer Name (Optional)
                </label>
                <input
                  type="text"
                  value={customerName}
                  onChange={(e) => setCustomerName(e.target.value)}
                  className="input-field"
                  placeholder="Enter customer name"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Payment Method
                </label>
                <select
                  value={paymentMethod}
                  onChange={(e) => setPaymentMethod(e.target.value)}
                  className="input-field"
                >
                  <option value="CASH">Cash</option>
                  <option value="CARD">Card</option>
                  <option value="GCASH">GCash</option>
                  <option value="PAYMAYA">PayMaya</option>
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Amount Paid
                </label>
                <input
                  type="number"
                  value={amountPaid}
                  onChange={(e) => setAmountPaid(e.target.value)}
                  className="input-field"
                  placeholder="0.00"
                  step="0.01"
                  required
                />
              </div>

              <div className="bg-gray-50 rounded-lg p-4 space-y-2">
                <div className="flex justify-between">
                  <span>Total:</span>
                  <span className="font-bold">₱{calculateTotal().toLocaleString()}</span>
                </div>
                <div className="flex justify-between">
                  <span>Amount Paid:</span>
                  <span className="font-bold">₱{parseFloat(amountPaid || 0).toLocaleString()}</span>
                </div>
                <div className="flex justify-between text-lg border-t border-gray-200 pt-2">
                  <span className="font-bold">Change:</span>
                  <span className="font-bold text-green-600">
                    ₱{calculateChange().toLocaleString()}
                  </span>
                </div>
              </div>

              <div className="flex space-x-3">
                <button
                  onClick={() => setShowCheckout(false)}
                  className="flex-1 btn-secondary"
                  disabled={loading}
                >
                  Cancel
                </button>
                <button
                  onClick={handleCheckout}
                  className="flex-1 btn-primary"
                  disabled={loading}
                >
                  {loading ? 'Processing...' : 'Complete Payment'}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default POSPage;