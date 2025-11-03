"""
ML Analytics API for Laravel Integration
Simple Flask application with machine learning models
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
from datetime import datetime, timedelta
import numpy as np
from collections import Counter
import logging
import os

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)  # Enable CORS for Laravel integration

# === Route utama untuk Railway ===
@app.route('/')
def home():
    """Root route for Railway deployment"""
    return jsonify({
        "message": "✅ Flask Analitik API is running successfully on Railway!",
        "service": "ML Analytics API",
        "version": "1.0.0",
        "available_endpoints": [
            "/health",
            "/api/analyze",
            "/api/predict",
            "/api/query"
        ]
    })

class SimpleMLModel:
    """Simple machine learning models for sales analytics"""
    
    @staticmethod
    def calculate_moving_average(data, window=7):
        if len(data) < window:
            return np.mean(data) if data else 0
        return np.mean(data[-window:])
    
    @staticmethod
    def predict_sales(historical_orders, days_ahead=1):
        if not historical_orders:
            return 0
        
        daily_counts = Counter()
        for order in historical_orders:
            date = datetime.fromisoformat(order['created_at']).date()
            daily_counts[date] += 1
        
        last_date = max(daily_counts.keys())
        recent_data = [daily_counts.get(last_date - timedelta(days=i), 0) for i in range(13, -1, -1)]
        
        ma_7 = SimpleMLModel.calculate_moving_average(recent_data, 7)
        ma_14 = SimpleMLModel.calculate_moving_average(recent_data, 14)
        
        trend = (recent_data[-1] - recent_data[0]) / len(recent_data) if len(recent_data) >= 2 else 0
        prediction = ma_7 + (trend * days_ahead)
        
        confidence = 85 if days_ahead == 1 else 75 if days_ahead == 7 else 65
        
        return {'value': max(0, int(prediction)), 'confidence': confidence}
    
    @staticmethod
    def analyze_stock_levels(products):
        alerts = []
        for product in products:
            issues = []
            stock = product.get('stock', {})
            
            if stock.get('dus', 0) <= 10 and stock.get('dus', 0) > 0:
                issues.append(f"Dus ({stock['dus']})")
            if stock.get('pack', 0) <= 20 and stock.get('pack', 0) > 0:
                issues.append(f"Pack ({stock['pack']})")
            if stock.get('satuan', 0) <= 50 and stock.get('satuan', 0) > 0:
                issues.append(f"Satuan ({stock['satuan']})")
            if stock.get('bal', 0) <= 5 and stock.get('bal', 0) > 0:
                issues.append(f"Bal ({stock['bal']})")
            if stock.get('kg', 0) <= 50 and stock.get('kg', 0) > 0:
                issues.append(f"Kg ({stock['kg']})")
            
            if issues:
                alerts.append({
                    'title': 'Stock Alert',
                    'message': f"{product['name']} memiliki stok rendah: {', '.join(issues)}",
                    'icon': 'exclamation-triangle',
                    'confidence': 95,
                    'action': 'restock',
                    'priority': 'high'
                })
        return alerts
    
    @staticmethod
    def analyze_sales_trend(orders):
        insights = []
        if not orders:
            return insights
        
        now = datetime.now()
        last_7_days = now - timedelta(days=7)
        last_14_days = now - timedelta(days=14)
        
        recent_revenue = sum(o['total'] for o in orders if datetime.fromisoformat(o['created_at'].replace('Z', '+00:00')) >= last_7_days)
        previous_revenue = sum(o['total'] for o in orders if last_14_days <= datetime.fromisoformat(o['created_at'].replace('Z', '+00:00')) < last_7_days)
        
        if previous_revenue > 0:
            growth = ((recent_revenue - previous_revenue) / previous_revenue) * 100
            if abs(growth) > 5:
                insights.append({
                    'title': 'Sales Growth' if growth > 0 else 'Sales Decline',
                    'message': f"Penjualan {'meningkat' if growth > 0 else 'turun'} {abs(growth):.1f}% dari minggu lalu",
                    'icon': 'arrow-up' if growth > 0 else 'arrow-down',
                    'confidence': 88 if growth > 0 else 85,
                    'action': 'maintain' if growth > 0 else 'analyze',
                    'priority': 'medium' if growth > 0 else 'high'
                })
        return insights
    
    @staticmethod
    def get_top_products(orders, products, limit=5):
        product_sales = Counter()
        for order in orders:
            for item in order.get('items', []):
                product_sales[item['product_id']] += item['quantity']
        
        top_products = product_sales.most_common(limit)
        insights = []
        for pid, qty in top_products:
            product = next((p for p in products if p['id'] == pid), None)
            if product:
                insights.append({
                    'title': 'Best Seller',
                    'message': f"{product['name']} adalah produk terlaris ({qty} terjual)",
                    'icon': 'fire',
                    'confidence': 90,
                    'action': 'promote',
                    'priority': 'medium'
                })
        return insights
    
    @staticmethod
    def analyze_customer_patterns(orders, customers):
        insights = []
        if customers:
            avg_orders = np.mean([c['orders_count'] for c in customers])
            if avg_orders < 2:
                insights.append({
                    'title': 'Customer Retention',
                    'message': 'Retention pelanggan rendah. Pertimbangkan program loyalitas.',
                    'icon': 'user-friends',
                    'confidence': 80,
                    'action': 'loyalty_program',
                    'priority': 'medium'
                })
        hour_counts = Counter()
        for o in orders:
            try:
                hour = datetime.fromisoformat(o['created_at'].replace('Z', '+00:00')).hour
                hour_counts[hour] += 1
            except:
                continue
        if hour_counts:
            peak = hour_counts.most_common(1)[0]
            if peak[1] > 10:
                insights.append({
                    'title': 'Peak Hours',
                    'message': f"Jam sibuk: {peak[0]}:00 dengan {peak[1]} pesanan",
                    'icon': 'clock',
                    'confidence': 92,
                    'action': 'staff_planning',
                    'priority': 'medium'
                })
        return insights

@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({'status': 'healthy', 'service': 'ML Analytics API', 'version': '1.0.0'})

@app.route('/api/analyze', methods=['POST'])
def analyze():
    try:
        data = request.json
        orders = data.get('orders', [])
        products = data.get('products', [])
        customers = data.get('customers', [])
        
        insights = []
        insights.extend(SimpleMLModel.analyze_stock_levels(products))
        insights.extend(SimpleMLModel.analyze_sales_trend(orders))
        insights.extend(SimpleMLModel.get_top_products(orders, products, 3)[:2])
        insights.extend(SimpleMLModel.analyze_customer_patterns(orders, customers)[:2])
        
        predictions = {
            'next_day': SimpleMLModel.predict_sales(orders, 1)['value'],
            'next_week': SimpleMLModel.predict_sales(orders, 7)['value'],
            'next_month': SimpleMLModel.predict_sales(orders, 30)['value']
        }
        
        return jsonify({
            'status': 'success',
            'insights': insights[:10],
            'predictions': predictions
        })
    except Exception as e:
        logger.error(f"Error in analyze: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/predict', methods=['GET'])
def predict():
    return jsonify({
        'status': 'success',
        'predictions': {'next_day': 45, 'next_week': 320, 'next_month': 1400},
        'confidence': {'day': 85, 'week': 75, 'month': 65}
    })

@app.route('/api/query', methods=['POST'])
def query():
    try:
        data = request.json
        query = data.get('query', '').lower()
        context = data.get('context', {})
        answer = "Maaf, saya tidak bisa menjawab pertanyaan tersebut."
        confidence = 0

        if any(w in query for w in ['produk', 'product', 'barang', 'terlaris']):
            if context.get('products'):
                best = max(context['products'], key=lambda x: sum(1 for o in context.get('orders', []) for i in o.get('items', []) if i['product_id'] == x['id']))
                answer = f"Produk terlaris adalah {best['name']}"
                confidence = 85
        elif any(w in query for w in ['penjualan', 'sales', 'revenue', 'pendapatan']):
            orders = context.get('orders', [])
            answer = f"Total pendapatan: Rp {sum(o['total'] for o in orders):,.0f} dari {len(orders)} pesanan"
            confidence = 90
        elif any(w in query for w in ['stok', 'stock', 'tersedia']):
            products = context.get('products', [])
            low = sum(1 for p in products if p.get('stock', {}).get('dus', 0) < 10)
            answer = f"Ada {low} produk dengan stok rendah"
            confidence = 88

        return jsonify({'status': 'success', 'answer': answer, 'confidence': confidence})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
