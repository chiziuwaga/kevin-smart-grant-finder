"""
Main application entry point for the Smart Grant Finder.
"""

from flask import Flask, jsonify
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = Flask(__name__)

@app.route('/')
def index():
    return jsonify({
        'status': 'online',
        'service': 'Smart Grant Finder',
        'version': '0.1.0'
    })

@app.route('/health')
def health_check():
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat()
    })

if __name__ == '__main__':
    app.run(debug=True)