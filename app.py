import pickle
from flask import Flask, request, jsonify, render_template

app = Flask(__name__)

# Load model and scaler
with open('kmeans_model.pkl', 'rb') as f:
    model = pickle.load(f)

with open('scaler.pkl', 'rb') as f:
    scaler = pickle.load(f)


@app.route('/')
def home():
    return render_template('interface.html')

@app.route('/predict_api', methods=['POST'])
def predict_api():
    try:
        request_data = request.get_json(force=True)
        data = request_data.get('data', request_data)  # <-- handle both cases

        features = [
            data['Income'],
            data['Recency'],
            data['MntWines'],
            data['MntFruits'],
            data['MntMeatProducts'],
            data['MntFishProducts'],
            data['MntSweetProducts'],
            data['MntGoldProducts']
        ]

        scaled_data = scaler.transform([features])
        prediction = model.predict(scaled_data)

        return jsonify({
            'cluster': int(prediction[0]),
            'cluster_name': f'Cluster {int(prediction[0])}',
            'recommended_product': 'Wine',
            'similarity_score': 0.85
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500



if __name__ == '__main__':
    app.run(debug=True)


