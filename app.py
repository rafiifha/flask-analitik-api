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

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)  # Enable CORS for Laravel integration

class SimpleMLModel:
    """Simple machine learning models for sales analytics"""
    
    @staticmethod
    def calculate_moving_average(data, window=7):
        """Calculate moving average for time series"""
        if len(data) < window:
            return np.mean(data) if data else 0
        return np.mean(data[-window:])
    
    @staticmethod
    def predict_sales(historical_orders, days_ahead=1):
        """Predict future sales using simple moving average and trend"""
        if not historical_orders:
            return 0
        
        # Extract order counts per day
        daily_counts = Counter()
        for order in historical_orders:
            date = datetime.fromisoformat(order['created_at']).date()
            daily_counts[date] += 1
        
        # Get last 14 days data
        last_date = max(daily_counts.keys())
        recent_data = []
        for i in range(14):
            check_date = last_date - timedelta(days=i)
            recent_data.append(daily_counts.get(check_date, 0))
        
        recent_data.reverse()
        
        # Calculate moving average
        ma_7 = SimpleMLModel.calculate_moving_average(recent_data, 7)
        ma_14 = SimpleMLModel.calculate_moving_average(recent_data, 14)
        
        # Calculate trend
        if len(recent_data) >= 2:
            trend = (recent_data[-1] - recent_data[0]) / len(recent_data)
        else:
            trend = 0
        
        # Predict
        prediction = ma_7 + (trend * days_ahead)
        
        # Apply confidence factor
        if days_ahead == 1:
            confidence = 85
        elif days_ahead == 7:
            confidence = 75
        else:  # 30 days
            confidence = 65
        
        return {
            'value': max(0, int(prediction)),
            'confidence': confidence
        }
    
    @staticmethod
    def analyze_stock_levels(products):
        """Analyze products and identify low stock items"""
        alerts = []
        
        for product in products:
            issues = []
            
            # Check stock levels
            stock_dus = product.get('stock', {}).get('dus', 0)
            stock_pack = product.get('stock', {}).get('pack', 0)
            stock_satuan = product.get('stock', {}).get('satuan', 0)
            stock_bal = product.get('stock', {}).get('bal', 0)
            stock_kg = product.get('stock', {}).get('kg', 0)
            
            if stock_dus > 0 and stock_dus <= 10:
                issues.append(f"Dus ({stock_dus})")
            if stock_pack > 0 and stock_pack <= 20:
                issues.append(f"Pack ({stock_pack})")
            if stock_satuan > 0 and stock_satuan <= 50:
                issues.append(f"Satuan ({stock_satuan})")
            if stock_bal > 0 and stock_bal <= 5:
                issues.append(f"Bal ({stock_bal})")
            if stock_kg > 0 and stock_kg <= 50:
                issues.append(f"Kg ({stock_kg})")
            
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
        """Analyze sales trends and identify patterns"""
        insights = []
        
        if not orders:
            return insights
        
        # Calculate revenue for last 7 and 14 days
        now = datetime.now()
        last_7_days = now - timedelta(days=7)
        last_14_days = now - timedelta(days=14)
        
        recent_revenue = sum(
            order['total'] for order in orders
            if datetime.fromisoformat(order['created_at'].replace('Z', '+00:00')) >= last_7_days
        )
        
        previous_revenue = sum(
            order['total'] for order in orders
            if (last_14_days <= datetime.fromisoformat(order['created_at'].replace('Z', '+00:00')) < last_7_days)
        )
        
        # Calculate growth
        if previous_revenue > 0:
            growth = ((recent_revenue - previous_revenue) / previous_revenue) * 100
            
            if abs(growth) > 5:  # Significant change
                if growth > 0:
                    insights.append({
                        'title': 'Sales Growth',
                        'message': f"Penjualan meningkat {abs(growth):.1f}% dari minggu lalu",
                        'icon': 'arrow-up',
                        'confidence': 88,
                        'action': 'maintain',
                        'priority': 'medium'
                    })
                else:
                    insights.append({
                        'title': 'Sales Decline',
                        'message': f"Penjualan turun {abs(growth):.1f}% dari minggu lalu - perlu perhatian",
                        'icon': 'arrow-down',
                        'confidence': 85,
                        'action': 'analyze',
                        'priority': 'high'
                    })
        
        return insights
    
    @staticmethod
    def get_top_products(orders, products, limit=5):
        """Identify top-selling products"""
        product_sales = Counter()
        
        for order in orders:
            for item in order.get('items', []):
                product_sales[item['product_id']] += item['quantity']
        
        top_products = product_sales.most_common(limit)
        
        insights = []
        for product_id, quantity in top_products:
            product = next((p for p in products if p['id'] == product_id), None)
            if product:
                insights.append({
                    'title': 'Best Seller',
                    'message': f"{product['name']} adalah produk terlaris ({quantity} terjual)",
                    'icon': 'fire',
                    'confidence': 90,
                    'action': 'promote',
                    'priority': 'medium'
                })
        
        return insights
    
    @staticmethod
    def analyze_customer_patterns(orders, customers):
        """Analyze customer behavior and segments"""
        insights = []
        
        # Calculate average orders per customer
        if customers:
            avg_orders = np.mean([c['orders_count'] for c in customers])
            
            if avg_orders < 2:
                insights.append({
                    'title': 'Customer Retention',
                    'message': 'Tingkat retention pelanggan rendah. Pertimbangkan program loyalitas.',
                    'icon': 'user-friends',
                    'confidence': 80,
                    'action': 'loyalty_program',
                    'priority': 'medium'
                })
        
        # Identify peak hours
        hour_counts = Counter()
        for order in orders:
            try:
                order_time = datetime.fromisoformat(order['created_at'].replace('Z', '+00:00'))
                hour_counts[order_time.hour] += 1
            except:
                continue
        
        if hour_counts:
            peak_hour = hour_counts.most_common(1)[0]
            if peak_hour[1] > 10:
                insights.append({
                    'title': 'Peak Hours',
                    'message': f"Jam sibuk: {peak_hour[0]}:00 dengan {peak_hour[1]} pesanan",
                    'icon': 'clock',
                    'confidence': 92,
                    'action': 'staff_planning',
                    'priority': 'medium'
                })
        
        return insights

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'service': 'ML Analytics API',
        'version': '1.0.0'
    })

@app.route('/api/analyze', methods=['POST'])
def analyze():
    """Main analysis endpoint"""
    try:
        data = request.json
        logger.info("Received analyze request")
        
        orders = data.get('orders', [])
        products = data.get('products', [])
        customers = data.get('customers', [])
        
        # Generate insights
        insights = []
        
        # Stock analysis
        stock_alerts = SimpleMLModel.analyze_stock_levels(products)
        insights.extend(stock_alerts)
        
        # Sales trend analysis
        sales_insights = SimpleMLModel.analyze_sales_trend(orders)
        insights.extend(sales_insights)
        
        # Top products
        top_products = SimpleMLModel.get_top_products(orders, products, 3)
        insights.extend(top_products[:2])  # Limit to 2
        
        # Customer analysis
        customer_insights = SimpleMLModel.analyze_customer_patterns(orders, customers)
        insights.extend(customer_insights[:2])  # Limit to 2
        
        # Generate predictions
        predictions = {
            'next_day': SimpleMLModel.predict_sales(orders, 1)['value'],
            'next_week': SimpleMLModel.predict_sales(orders, 7)['value'],
            'next_month': SimpleMLModel.predict_sales(orders, 30)['value']
        }
        
        # Generate recommendations
        recommendations = []
        
        # Stock recommendations
        if stock_alerts:
            recommendations.append({
                'type': 'restock',
                'action': f"Restock {len(stock_alerts)} produk dengan stok rendah",
                'priority': 'high'
            })
        
        # Promotion recommendations
        if sales_insights and any('Decline' in s['title'] for s in sales_insights):
            recommendations.append({
                'type': 'promotion',
                'action': 'Lakukan promosi untuk meningkatkan penjualan',
                'priority': 'high'
            })
        
        response = {
            'status': 'success',
            'insights': insights[:10],  # Limit to 10 insights
            'predictions': predictions,
            'recommendations': recommendations
        }
        
        logger.info(f"Generated {len(insights)} insights")
        return jsonify(response)
        
    except Exception as e:
        logger.error(f"Error in analyze: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@app.route('/api/predict', methods=['GET'])
def predict():
    """Prediction endpoint"""
    try:
        pred_type = request.args.get('type', 'general')
        logger.info(f"Predict request: type={pred_type}")
        
        # This endpoint would ideally receive data from Laravel
        # For now, return a simple response structure
        predictions = {
            'next_day': 45,
            'next_week': 320,
            'next_month': 1400
        }
        
        confidence = {
            'day': 85,
            'week': 75,
            'month': 65
        }
        
        return jsonify({
            'status': 'success',
            'predictions': predictions,
            'confidence': confidence
        })
        
    except Exception as e:
        logger.error(f"Error in predict: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@app.route('/api/query', methods=['POST'])
def query():
    """Query endpoint for natural language queries"""
    try:
        data = request.json
        query = data.get('query', '').lower()
        context = data.get('context', {})
        
        logger.info(f"Query: {query}")
        
        # Simple keyword-based answering
        answer = "Maaf, saya tidak bisa menjawab pertanyaan tersebut."
        confidence = 0
        
        # Product questions
        if any(word in query for word in ['produk', 'product', 'barang', 'terlaris', 'best']):
            if context.get('products'):
                best_product = max(context['products'], 
                                 key=lambda x: sum(1 for p in context.get('orders', []) 
                                                 for item in p.get('items', [])
                                                 if item['product_id'] == x['id']))
                answer = f"Produk terlaris adalah {best_product['name']}"
                confidence = 85
        
        # Sales questions
        elif any(word in query for word in ['penjualan', 'sales', 'revenue', 'pendapatan']):
            orders = context.get('orders', [])
            total_sales = sum(o['total'] for o in orders)
            recent_orders = len(orders)
            answer = f"Total pendapatan: Rp {total_sales:,.0f} dari {recent_orders} pesanan"
            confidence = 90
        
        # Stock questions
        elif any(word in query for word in ['stok', 'stock', 'tersedia', 'available']):
            products = context.get('products', [])
            low_stock = sum(1 for p in products if 
                          p.get('stock', {}).get('dus', 0) < 10 or
                          p.get('stock', {}).get('pack', 0) < 20)
            answer = f"Ada {low_stock} produk dengan stok rendah"
            confidence = 88
        
        return jsonify({
            'status': 'success',
            'answer': answer,
            'confidence': confidence
        })
        
    except Exception as e:
        logger.error(f"Error in query: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

if __name__ == '__main__':
    logger.info("Starting ML Analytics API...")
    app.run(host='0.0.0.0', port=5000, debug=True)

