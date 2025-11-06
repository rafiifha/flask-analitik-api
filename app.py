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
        if len(data) < window:
            return np.mean(data) if data else 0
        return np.mean(data[-window:])

    @staticmethod
    def predict_sales(historical_orders, days_ahead=1):
        if not historical_orders:
            return {'value': 0, 'confidence': 0}

        daily_counts = Counter()
        for order in historical_orders:
            date = datetime.fromisoformat(order['created_at']).date()
            daily_counts[date] += 1

        last_date = max(daily_counts.keys())
        recent_data = [daily_counts.get(last_date - timedelta(days=i), 0) for i in range(14)]
        recent_data.reverse()

        ma_7 = SimpleMLModel.calculate_moving_average(recent_data, 7)
        trend = (recent_data[-1] - recent_data[0]) / len(recent_data) if len(recent_data) >= 2 else 0

        prediction = ma_7 + (trend * days_ahead)
        confidence = 85 if days_ahead == 1 else 75 if days_ahead == 7 else 65

        return {'value': max(0, int(prediction)), 'confidence': confidence}


@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({
        'status': 'healthy',
        'service': 'ML Analytics API',
        'version': '1.0.0'
    })


@app.route('/api/analyze', methods=['POST'])
def analyze():
    try:
        data = request.json
        orders = data.get('orders', [])
        predictions = {
            'next_day': SimpleMLModel.predict_sales(orders, 1)['value'],
            'next_week': SimpleMLModel.predict_sales(orders, 7)['value'],
            'next_month': SimpleMLModel.predict_sales(orders, 30)['value']
        }

        return jsonify({
            'status': 'success',
            'predictions': predictions,
            'message': 'Analysis completed successfully (no DB mode)'
        })

    except Exception as e:
        logger.error(f"Error in analyze: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500


if __name__ == '__main__':
    logger.info("Starting ML Analytics API (no DB mode)...")
    app.run(host='0.0.0.0', port=5000, debug=True)
