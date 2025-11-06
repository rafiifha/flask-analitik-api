from flask import Flask, jsonify, request
from flask_cors import CORS
import mysql.connector
from mysql.connector import Error
from datetime import datetime, timedelta
from decimal import Decimal
import os
from functools import wraps
import math

app = Flask(__name__)
CORS(app)  # Enable CORS untuk akses dari frontend

# Database configuration dari environment variables
DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'port': int(os.getenv('DB_PORT', 3306)),
    'database': os.getenv('DB_DATABASE', 'projekskripsi'),
    'user': os.getenv('DB_USERNAME', 'root'),
    'password': os.getenv('DB_PASSWORD', ''),
}

# API Key untuk authentication (opsional)
API_KEY = os.getenv('API_KEY', None)


def get_db_connection():
    """Membuat koneksi ke database MySQL"""
    try:
        connection = mysql.connector.connect(**DB_CONFIG)
        return connection
    except Error as e:
        print(f"Error connecting to MySQL: {e}")
        return None


def require_api_key(f):
    """Decorator untuk API key authentication (opsional)"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if API_KEY:
            api_key = request.headers.get('X-API-Key') or request.args.get('api_key')
            if not api_key or api_key != API_KEY:
                return jsonify({
                    'success': False,
                    'message': 'Unauthorized. API key required.'
                }), 401
        return f(*args, **kwargs)
    return decorated_function


@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'service': 'AI Analytics API',
        'timestamp': datetime.now().isoformat()
    })


@app.route('/api/ai/analytics/sales-trend', methods=['GET'])
@require_api_key
def sales_trend():
    """Analisis trend penjualan"""
    try:
        days = int(request.args.get('days', 30))
        
        conn = get_db_connection()
        if not conn:
            return jsonify({
                'success': False,
                'message': 'Database connection failed'
            }), 500
        
        cursor = conn.cursor(dictionary=True)
        
        # Periode sekarang
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        # Periode sebelumnya
        previous_start_date = start_date - timedelta(days=days)
        previous_end_date = start_date - timedelta(days=1)
        
        # Query penjualan periode sekarang
        query_current = """
            SELECT COALESCE(SUM(total_pesanan), 0) as total
            FROM pesanan
            WHERE status_pesanan IN ('selesai', 'siap_diambil', 'dikonfirmasi', 'diproses')
            AND created_at BETWEEN %s AND %s
        """
        cursor.execute(query_current, (start_date, end_date))
        current_sales = cursor.fetchone()['total'] or 0
        
        # Query penjualan periode sebelumnya
        cursor.execute(query_current, (previous_start_date, previous_end_date))
        previous_sales = cursor.fetchone()['total'] or 0
        
        # Hitung perbedaan dan persentase
        difference = float(current_sales) - float(previous_sales)
        percentage_change = (difference / float(previous_sales) * 100) if previous_sales > 0 else 0
        
        # Rule-based analysis
        trend = 'stabil'
        confidence = 'medium'
        
        if abs(percentage_change) > 20:
            trend = 'naik_signifikan' if percentage_change > 0 else 'turun_signifikan'
            confidence = 'high'
        elif abs(percentage_change) > 10:
            trend = 'naik' if percentage_change > 0 else 'turun'
            confidence = 'medium'
        
        # Rekomendasi
        if trend == 'naik_signifikan':
            recommendation = 'Penjualan meningkat signifikan. Pertimbangkan untuk meningkatkan stok dan promosi.'
        elif trend == 'turun_signifikan':
            recommendation = 'Penjualan menurun signifikan. Evaluasi strategi pemasaran dan cek kompetitor.'
        elif trend == 'naik':
            recommendation = 'Penjualan menunjukkan tren positif. Pertahankan strategi yang ada.'
        elif trend == 'turun':
            recommendation = 'Penjualan sedikit menurun. Monitor lebih lanjut dan pertimbangkan promosi.'
        else:
            recommendation = 'Penjualan stabil. Pertahankan performa yang ada.'
        
        cursor.close()
        conn.close()
        
        return jsonify({
            'success': True,
            'data': {
                'trend': trend,
                'current_period': {
                    'start': start_date.strftime('%Y-%m-%d'),
                    'end': end_date.strftime('%Y-%m-%d'),
                    'total': float(current_sales)
                },
                'previous_period': {
                    'start': previous_start_date.strftime('%Y-%m-%d'),
                    'end': previous_end_date.strftime('%Y-%m-%d'),
                    'total': float(previous_sales)
                },
                'difference': difference,
                'percentage_change': round(percentage_change, 2),
                'confidence': confidence,
                'recommendation': recommendation
            },
            'message': 'Analisis trend penjualan berhasil diambil'
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Gagal mengambil analisis trend: {str(e)}'
        }), 500


@app.route('/api/ai/analytics/sales-prediction', methods=['GET'])
@require_api_key
def sales_prediction():
    """Prediksi penjualan berdasarkan moving average"""
    try:
        days_ahead = int(request.args.get('days_ahead', 7))
        lookback_days = int(request.args.get('lookback_days', 30))
        
        conn = get_db_connection()
        if not conn:
            return jsonify({
                'success': False,
                'message': 'Database connection failed'
            }), 500
        
        cursor = conn.cursor(dictionary=True)
        
        end_date = datetime.now()
        start_date = end_date - timedelta(days=lookback_days)
        
        # Ambil penjualan harian
        query = """
            SELECT DATE(created_at) as date, SUM(total_pesanan) as total
            FROM pesanan
            WHERE status_pesanan IN ('selesai', 'siap_diambil', 'dikonfirmasi', 'diproses')
            AND created_at >= %s
            GROUP BY DATE(created_at)
            ORDER BY date ASC
        """
        cursor.execute(query, (start_date,))
        daily_sales = cursor.fetchall()
        
        if not daily_sales:
            cursor.close()
            conn.close()
            return jsonify({
                'success': True,
                'data': {
                    'prediction': 0,
                    'confidence': 'low',
                    'method': 'insufficient_data'
                },
                'message': 'Prediksi penjualan berhasil diambil'
            })
        
        # Hitung moving average
        total_sales = sum(float(day['total'] or 0) for day in daily_sales)
        total_days = len(daily_sales)
        average_daily = total_sales / total_days if total_days > 0 else 0
        
        # Hitung variasi untuk confidence
        variance = sum((float(day['total'] or 0) - average_daily) ** 2 for day in daily_sales) / total_days
        std_dev = math.sqrt(variance)
        coefficient_of_variation = (std_dev / average_daily * 100) if average_daily > 0 else 0
        
        # Prediksi
        predicted_sales = average_daily * days_ahead
        
        # Confidence level
        if coefficient_of_variation < 20:
            confidence = 'high'
        elif coefficient_of_variation > 50:
            confidence = 'low'
        else:
            confidence = 'medium'
        
        cursor.close()
        conn.close()
        
        return jsonify({
            'success': True,
            'data': {
                'prediction': round(predicted_sales, 2),
                'average_daily': round(average_daily, 2),
                'days_ahead': days_ahead,
                'confidence': confidence,
                'coefficient_of_variation': round(coefficient_of_variation, 2),
                'method': 'moving_average',
                'data_points': total_days
            },
            'message': 'Prediksi penjualan berhasil diambil'
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Gagal mengambil prediksi: {str(e)}'
        }), 500


@app.route('/api/ai/analytics/product-recommendations', methods=['GET'])
@require_api_key
def product_recommendations():
    """Rekomendasi produk berdasarkan penjualan dan stok"""
    try:
        limit = int(request.args.get('limit', 10))
        days = 30
        
        conn = get_db_connection()
        if not conn:
            return jsonify({
                'success': False,
                'message': 'Database connection failed'
            }), 500
        
        cursor = conn.cursor(dictionary=True)
        
        start_date = datetime.now() - timedelta(days=days)
        
        # Produk terlaris
        query = """
            SELECT 
                dp.produk_id,
                SUM(dp.jumlah) as total_terjual,
                SUM(dp.subtotal) as total_pendapatan
            FROM detail_pesanan dp
            INNER JOIN pesanan p ON dp.pesanan_id = p.id
            WHERE p.status_pesanan IN ('selesai', 'siap_diambil', 'dikonfirmasi', 'diproses')
            AND p.created_at >= %s
            GROUP BY dp.produk_id
            ORDER BY total_terjual DESC
            LIMIT %s
        """
        cursor.execute(query, (start_date, limit))
        top_products = cursor.fetchall()
        
        recommendations = []
        
        for item in top_products:
            # Ambil detail produk
            cursor.execute("""
                SELECT id, nama_produk, stok_dus, stok_pack, stok_satuan, is_active
                FROM produk
                WHERE id = %s
            """, (item['produk_id'],))
            produk = cursor.fetchone()
            
            if not produk:
                continue
            
            # Hitung rata-rata penjualan harian
            average_daily_sales = float(item['total_terjual']) / days
            total_stock = float(produk['stok_dus'] or 0) + float(produk['stok_pack'] or 0) + float(produk['stok_satuan'] or 0)
            days_until_stockout = (total_stock / average_daily_sales) if average_daily_sales > 0 else 0
            
            recommendation = {
                'produk_id': produk['id'],
                'nama_produk': produk['nama_produk'],
                'total_terjual': float(item['total_terjual']),
                'total_pendapatan': float(item['total_pendapatan']),
                'stok_dus': float(produk['stok_dus'] or 0),
                'stok_pack': float(produk['stok_pack'] or 0),
                'stok_satuan': float(produk['stok_satuan'] or 0),
                'days_until_stockout': round(days_until_stockout, 1),
                'actions': []
            }
            
            # Rule: Restock urgent jika stok < 7 hari
            if days_until_stockout < 7 and days_until_stockout > 0:
                recommendation['actions'].append({
                    'type': 'restock_urgent',
                    'priority': 'high',
                    'message': f'Stok akan habis dalam {round(days_until_stockout, 1)} hari',
                    'recommended_quantity': round(average_daily_sales * 14, 0)
                })
            elif days_until_stockout < 14 and days_until_stockout > 0:
                recommendation['actions'].append({
                    'type': 'restock',
                    'priority': 'medium',
                    'message': f'Stok akan habis dalam {round(days_until_stockout, 1)} hari',
                    'recommended_quantity': round(average_daily_sales * 14, 0)
                })
            
            # Rule: Aktifkan produk jika tidak aktif tapi ada penjualan
            if not produk['is_active'] and item['total_terjual'] > 0:
                recommendation['actions'].append({
                    'type': 'activate',
                    'priority': 'medium',
                    'message': 'Produk memiliki penjualan historis yang baik'
                })
            
            # Rule: Promosi untuk produk terlaris
            if top_products and item['total_terjual'] > (float(top_products[0]['total_terjual']) * 0.5):
                recommendation['actions'].append({
                    'type': 'promote',
                    'priority': 'low',
                    'message': 'Produk terlaris, pertimbangkan untuk promosi'
                })
            
            recommendations.append(recommendation)
        
        cursor.close()
        conn.close()
        
        return jsonify({
            'success': True,
            'data': recommendations,
            'message': 'Rekomendasi produk berhasil diambil'
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Gagal mengambil rekomendasi: {str(e)}'
        }), 500


@app.route('/api/ai/analytics/customer-analysis', methods=['GET'])
@require_api_key
def customer_analysis():
    """Analisis pelanggan berdasarkan frekuensi dan nilai transaksi"""
    try:
        limit = int(request.args.get('limit', 10))
        days = 90
        
        conn = get_db_connection()
        if not conn:
            return jsonify({
                'success': False,
                'message': 'Database connection failed'
            }), 500
        
        cursor = conn.cursor(dictionary=True)
        
        start_date = datetime.now() - timedelta(days=days)
        
        query = """
            SELECT 
                p.user_id,
                COUNT(*) as total_pesanan,
                SUM(p.total_pesanan) as total_pendapatan
            FROM pesanan p
            WHERE p.status_pesanan IN ('selesai', 'siap_diambil', 'dikonfirmasi', 'diproses')
            AND p.created_at >= %s
            AND p.user_id IS NOT NULL
            GROUP BY p.user_id
            ORDER BY total_pendapatan DESC
            LIMIT %s
        """
        cursor.execute(query, (start_date, limit))
        customers = cursor.fetchall()
        
        analysis = []
        
        for customer in customers:
            # Ambil data user
            cursor.execute("SELECT name, email FROM users WHERE id = %s", (customer['user_id'],))
            user = cursor.fetchone()
            
            if not user:
                continue
            
            avg_order_value = float(customer['total_pendapatan']) / customer['total_pesanan'] if customer['total_pesanan'] > 0 else 0
            frequency = customer['total_pesanan'] / (days / 30)  # Pesanan per bulan
            
            # Rule-based segmentation
            segment = 'regular'
            if avg_order_value > 500000 and frequency > 4:
                segment = 'vip'
            elif avg_order_value > 300000 or frequency > 2:
                segment = 'premium'
            
            # Rekomendasi
            if segment == 'vip':
                recommendation = 'Pelanggan VIP - Berikan layanan prioritas dan program loyalitas khusus.'
            elif segment == 'premium':
                recommendation = 'Pelanggan Premium - Tawarkan diskon dan program loyalitas.'
            elif frequency < 1:
                recommendation = 'Pelanggan jarang - Kirim promosi untuk meningkatkan frekuensi pembelian.'
            else:
                recommendation = 'Pelanggan reguler - Pertahankan dengan layanan yang baik.'
            
            analysis.append({
                'user_id': customer['user_id'],
                'nama': user['name'],
                'email': user['email'],
                'total_pesanan': customer['total_pesanan'],
                'total_pendapatan': float(customer['total_pendapatan']),
                'rata_rata_transaksi': round(avg_order_value, 2),
                'frekuensi_per_bulan': round(frequency, 2),
                'segment': segment,
                'recommendation': recommendation
            })
        
        cursor.close()
        conn.close()
        
        return jsonify({
            'success': True,
            'data': analysis,
            'message': 'Analisis pelanggan berhasil diambil'
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Gagal mengambil analisis pelanggan: {str(e)}'
        }), 500


@app.route('/api/ai/analytics/time-analysis', methods=['GET'])
@require_api_key
def time_analysis():
    """Analisis waktu penjualan (jam dan hari terbaik)"""
    try:
        days = 30
        start_date = datetime.now() - timedelta(days=days)
        
        conn = get_db_connection()
        if not conn:
            return jsonify({
                'success': False,
                'message': 'Database connection failed'
            }), 500
        
        cursor = conn.cursor(dictionary=True)
        
        # Analisis per jam
        query_hourly = """
            SELECT 
                HOUR(created_at) as hour,
                COUNT(*) as jumlah_pesanan,
                SUM(total_pesanan) as total_pendapatan
            FROM pesanan
            WHERE status_pesanan IN ('selesai', 'siap_diambil', 'dikonfirmasi', 'diproses')
            AND created_at >= %s
            GROUP BY HOUR(created_at)
            ORDER BY total_pendapatan DESC
        """
        cursor.execute(query_hourly, (start_date,))
        hourly_sales = cursor.fetchall()
        
        # Analisis per hari
        query_daily = """
            SELECT 
                DAYOFWEEK(created_at) as day_of_week,
                DAYNAME(created_at) as day_name,
                COUNT(*) as jumlah_pesanan,
                SUM(total_pesanan) as total_pendapatan
            FROM pesanan
            WHERE status_pesanan IN ('selesai', 'siap_diambil', 'dikonfirmasi', 'diproses')
            AND created_at >= %s
            GROUP BY DAYOFWEEK(created_at), DAYNAME(created_at)
            ORDER BY total_pendapatan DESC
        """
        cursor.execute(query_daily, (start_date,))
        daily_sales = cursor.fetchall()
        
        # Format hourly
        hourly_data = [{
            'hour': item['hour'],
            'hour_label': f"{item['hour']}:00",
            'jumlah_pesanan': item['jumlah_pesanan'],
            'total_pendapatan': float(item['total_pendapatan'])
        } for item in hourly_sales]
        
        # Format daily
        daily_data = [{
            'day_of_week': item['day_of_week'],
            'day_name': item['day_name'],
            'jumlah_pesanan': item['jumlah_pesanan'],
            'total_pendapatan': float(item['total_pendapatan'])
        } for item in daily_sales]
        
        # Best hour dan day
        best_hour = hourly_data[0] if hourly_data else None
        best_day = daily_data[0] if daily_data else None
        
        # Rekomendasi
        recommendations = []
        if best_hour:
            recommendations.append(f"Jam terbaik untuk penjualan: {best_hour['hour_label']}. Pastikan staf dan stok siap pada jam ini.")
        if best_day:
            recommendations.append(f"Hari terbaik untuk penjualan: {best_day['day_name']}. Rencanakan promosi atau event pada hari ini.")
        
        cursor.close()
        conn.close()
        
        return jsonify({
            'success': True,
            'data': {
                'hourly': hourly_data,
                'daily': daily_data,
                'best_hour': {
                    'hour': best_hour['hour'],
                    'hour_label': best_hour['hour_label'],
                    'total_pendapatan': best_hour['total_pendapatan']
                } if best_hour else None,
                'best_day': {
                    'day_name': best_day['day_name'],
                    'total_pendapatan': best_day['total_pendapatan']
                } if best_day else None,
                'recommendation': recommendations
            },
            'message': 'Analisis waktu penjualan berhasil diambil'
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Gagal mengambil analisis waktu: {str(e)}'
        }), 500


@app.route('/api/ai/analytics/comprehensive', methods=['GET'])
@require_api_key
def comprehensive_analysis():
    """Analisis komprehensif (semua analisis sekaligus)"""
    try:
        # Panggil semua fungsi dan extract data dari response
        trend_response = sales_trend()
        prediction_response = sales_prediction()
        product_response = product_recommendations()
        customer_response = customer_analysis()
        time_response = time_analysis()
        
        # Extract data dari response (response adalah tuple (jsonify_object, status_code))
        trend_data = trend_response[0].get_json()['data']
        prediction_data = prediction_response[0].get_json()['data']
        product_data = product_response[0].get_json()['data']
        customer_data = customer_response[0].get_json()['data']
        time_data = time_response[0].get_json()['data']
        
        return jsonify({
            'success': True,
            'data': {
                'sales_trend': trend_data,
                'sales_prediction': prediction_data,
                'product_recommendations': product_data,
                'customer_analysis': customer_data,
                'time_analysis': time_data,
                'generated_at': datetime.now().isoformat()
            },
            'message': 'Analisis komprehensif berhasil diambil'
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Gagal mengambil analisis komprehensif: {str(e)}'
        }), 500


if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)

