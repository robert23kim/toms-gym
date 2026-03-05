import React, { useState } from 'react';
import { motion } from 'framer-motion';
import Layout from '../components/Layout';
import { storeItems } from '../lib/data';
import { StoreItem } from '../lib/types';
import { ShoppingCart, Filter, Tag } from 'lucide-react';

const Store = () => {
  const [selectedCategory, setSelectedCategory] = useState<string>('all');
  const [cart, setCart] = useState<{ item: StoreItem; quantity: number }[]>([]);

  const categories = [
    { id: 'all', name: 'All Items' },
    { id: 'gear', name: 'Gear' },
    { id: 'supplements', name: 'Supplements' },
    { id: 'apparel', name: 'Apparel' },
    { id: 'accessories', name: 'Accessories' },
  ];

  const filteredItems = selectedCategory === 'all'
    ? storeItems
    : storeItems.filter(item => item.category === selectedCategory);

  const addToCart = (item: StoreItem) => {
    setCart(prevCart => {
      const existingItem = prevCart.find(cartItem => cartItem.item.id === item.id);
      if (existingItem) {
        return prevCart.map(cartItem =>
          cartItem.item.id === item.id
            ? { ...cartItem, quantity: cartItem.quantity + 1 }
            : cartItem
        );
      }
      return [...prevCart, { item, quantity: 1 }];
    });
  };

  const removeFromCart = (itemId: string) => {
    setCart(prevCart => prevCart.filter(cartItem => cartItem.item.id !== itemId));
  };

  const totalCost = cart.reduce((sum, { item, quantity }) => sum + item.price * quantity, 0);

  return (
    <Layout>
      <div className="mb-8">
        <motion.h1
          className="text-3xl font-bold mb-2"
          initial={{ opacity: 0, y: -20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5 }}
        >
          Store
        </motion.h1>
        <p className="text-muted-foreground">
          Spend your LiftingDollars on premium gear and accessories
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-4 gap-8">
        {/* Left Sidebar - Categories */}
        <motion.div
          className="lg:col-span-1"
          initial={{ opacity: 0, x: -20 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ duration: 0.5 }}
        >
          <div className="glass p-6 rounded-xl sticky top-20">
            <div className="flex items-center gap-2 mb-4">
              <Filter className="w-5 h-5" />
              <h2 className="text-lg font-semibold">Categories</h2>
            </div>
            <div className="space-y-2">
              {categories.map(category => (
                <button
                  key={category.id}
                  onClick={() => setSelectedCategory(category.id)}
                  className={`w-full text-left px-4 py-2 rounded-lg transition-colors ${
                    selectedCategory === category.id
                      ? 'bg-accent/10 border border-accent/30'
                      : 'hover:bg-secondary/70'
                  }`}
                >
                  {category.name}
                </button>
              ))}
            </div>
          </div>
        </motion.div>

        {/* Main Content - Store Items */}
        <motion.div
          className="lg:col-span-2"
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5 }}
        >
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {filteredItems.map((item, index) => (
              <motion.div
                key={item.id}
                className="glass overflow-hidden rounded-xl"
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.5, delay: index * 0.1 }}
              >
                <div className="aspect-square relative">
                  <img
                    src={item.image}
                    alt={item.name}
                    className="absolute inset-0 w-full h-full object-cover"
                  />
                </div>
                <div className="p-6">
                  <div className="flex items-start justify-between mb-2">
                    <h3 className="font-semibold">{item.name}</h3>
                    <div className="flex items-center gap-1 text-accent font-medium">
                      <Tag className="w-4 h-4" />
                      <span>{item.price} LD</span>
                    </div>
                  </div>
                  <p className="text-sm text-muted-foreground mb-4">
                    {item.description}
                  </p>
                  <button
                    onClick={() => addToCart(item)}
                    disabled={!item.inStock}
                    className={`w-full px-4 py-2 rounded-lg transition-colors ${
                      item.inStock
                        ? 'bg-accent text-white hover:bg-accent/90'
                        : 'bg-secondary/50 text-muted-foreground cursor-not-allowed'
                    }`}
                  >
                    {item.inStock ? 'Add to Cart' : 'Out of Stock'}
                  </button>
                </div>
              </motion.div>
            ))}
          </div>
        </motion.div>

        {/* Right Sidebar - Cart */}
        <motion.div
          className="lg:col-span-1"
          initial={{ opacity: 0, x: 20 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ duration: 0.5 }}
        >
          <div className="glass p-6 rounded-xl sticky top-20">
            <div className="flex items-center gap-2 mb-4">
              <ShoppingCart className="w-5 h-5" />
              <h2 className="text-lg font-semibold">Your Cart</h2>
            </div>
            
            {cart.length === 0 ? (
              <p className="text-muted-foreground text-sm">
                Your cart is empty
              </p>
            ) : (
              <div className="space-y-4">
                {cart.map(({ item, quantity }) => (
                  <div key={item.id} className="flex items-center justify-between">
                    <div>
                      <h4 className="font-medium">{item.name}</h4>
                      <p className="text-sm text-muted-foreground">
                        {quantity} × {item.price} LD
                      </p>
                    </div>
                    <button
                      onClick={() => removeFromCart(item.id)}
                      className="text-sm text-red-500 hover:text-red-600"
                    >
                      Remove
                    </button>
                  </div>
                ))}
                
                <div className="border-t border-border/50 pt-4 mt-4">
                  <div className="flex justify-between mb-4">
                    <span className="font-medium">Total</span>
                    <span className="font-semibold">{totalCost} LD</span>
                  </div>
                  <button
                    className="w-full px-4 py-2 bg-accent text-white rounded-lg hover:bg-accent/90 transition-colors"
                  >
                    Checkout
                  </button>
                </div>
              </div>
            )}
          </div>
        </motion.div>
      </div>
    </Layout>
  );
};

export default Store; 