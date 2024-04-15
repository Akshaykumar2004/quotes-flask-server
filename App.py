from flask import Flask, request, jsonify
from flask_cors import CORS
import sqlite3 as lite
import json

app = Flask(__name__)
CORS(app)

# Global variable to store the index of the last fetched quote
last_quote_index = 0


def create_connection():
    return lite.connect(r'quotes.db')


def store_quotes_in_db(conn, quotes):
    global last_quote_index  # Accessing the global variable
    c = conn.cursor()
    c.execute("DELETE FROM quotes;")
    for quote in quotes:
        c.execute("INSERT INTO quotes (quote) VALUES (?);", (quote,))
    conn.commit()
    last_quote_index = 0  # Resetting the index to 0


def get_quote_from_db(index):
    conn = create_connection()
    c = conn.cursor()
    c.execute("SELECT quote FROM quotes LIMIT 1 OFFSET ?;", (index,))
    quote = c.fetchone()
    conn.close()
    return quote[0] if quote else None

@app.route('/get_status', methods=['GET'])
def get_status():
    try:
        conn = create_connection()
        c = conn.cursor()
        c.execute("SELECT emotions_json FROM user_info ORDER BY id DESC LIMIT 1;")
        last_emotions_json = c.fetchone()
        conn.close()

        if last_emotions_json:
            response_data = {'status': last_emotions_json[0]}
            response = jsonify(response_data)
            response.headers.add('Access-Control-Allow-Origin', '*')
            return response, 200
        else:
            response_data = {'error': 'No status available'}
            response = jsonify(response_data)
            response.headers.add('Access-Control-Allow-Origin', '*')
            return response, 404
    except Exception as e:
        print("Error:", str(e))
        response_data = {'error': 'An error occurred'}
        response = jsonify(response_data)
        response.headers.add('Access-Control-Allow-Origin', '*')
        return response, 500

def save_status(data):
    try:
        data = json.dumps(data)
        conn = create_connection()
        c = conn.cursor()
        c.execute("INSERT INTO user_info (emotions_json) VALUES (?);", (data,))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print("Error:", str(e))
        return False

@app.route('/receive_post', methods=['POST'])
def receive_post():
    try:
        data = request.get_json()
        print("Received data:", data)

        # Extract selected secondary emotions from received data
        selected_secondary_emotions = data['emo']['selectedSecondaryEmotions']

        # Calculate weights for secondary emotions
        n = len(selected_secondary_emotions)
        weights = {}
        for i in range(n):
            weights[selected_secondary_emotions[i]] = n-i

        # Calculate total weights for tertiary emotions
        print(selected_secondary_emotions, weights)

        total_weights = {}
        for i, j in primary_emotion.items():
            for k, l in weights.items():
                if k in j:
                    if i not in total_weights:
                        total_weights[i] = l
                    else:
                        total_weights[i] += l

        sorted_weights = dict(sorted(total_weights.items(), key=lambda item: item[1], reverse=True))

        ordered_emotions = []
        for i in sorted_weights:
            for j in selected_secondary_emotions:
                if j in primary_emotion[i]:
                    ordered_emotions.append(j)

        # Flatten the list of tertiary emotions
        tert = [j for i in ordered_emotions for j in secondary_emotion[i]]
        resp_quotes = []
        for i in range(5):
            for j in tert:
                resp_quotes.append(quotes[j][i])

        conn = create_connection()
        store_quotes_in_db(conn, resp_quotes)
        save_status(data)

        response_data = {'message': 'OK', 'quotes': resp_quotes}
        response = jsonify(response_data)
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Methods', 'POST')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type')
        conn.close()
        return response, 200
    except Exception as e:
        print("Error:", str(e))
        response_data = {'error': 'An error occurred'}
        response = jsonify(response_data)
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Methods', 'POST')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type')
        return response, 500


@app.route('/get_quote', methods=['GET'])
def get_quote():
    global last_quote_index
    quote = get_quote_from_db(last_quote_index)
    if quote:
        last_quote_index = (last_quote_index + 1) % len(quotes)  # Cycling the index
        response_data = {'quote': quote}
        response = jsonify(response_data)
        response.headers.add('Access-Control-Allow-Origin', '*')
        return response, 200
    else:
        # If there are no quotes available, reset the index to 0 and try again
        last_quote_index = 0
        quote = get_quote_from_db(last_quote_index)
        if quote:
            last_quote_index += 1
            response_data = {'quote': quote}
            response = jsonify(response_data)
            response.headers.add('Access-Control-Allow-Origin', '*')
            return response, 200
        else:
            response_data = {'error': 'No quotes available'}
            response = jsonify(response_data)
            response.headers.add('Access-Control-Allow-Origin', '*')
            return response, 404
        
@app.route('/get_all_quotes', methods=['GET'])
def get_all_quotes():
    try:
        conn = create_connection()
        c = conn.cursor()
        c.execute("SELECT quote FROM quotes;")
        all_quotes = c.fetchall()
        conn.close()

        if all_quotes:
            all_quotes = [quote[0] for quote in all_quotes]
            response_data = {'quotes': all_quotes}
            response = jsonify(response_data)
            response.headers.add('Access-Control-Allow-Origin', '*')
            return response, 200
        else:
            response_data = {'error': 'No quotes available'}
            response = jsonify(response_data)
            response.headers.add('Access-Control-Allow-Origin', '*')
            return response, 404
    except Exception as e:
        print("Error:", str(e))
        response_data = {'error': 'An error occurred'}
        response = jsonify(response_data)
        response.headers.add('Access-Control-Allow-Origin', '*')
        return response, 500
    
@app.route('/get_status', methods=['GET'])
def get_user_status():
    try:
        conn = create_connection()
        c = conn.cursor()
        c.execute("SELECT emotions_json FROM user_info ORDER BY id DESC LIMIT 1;")
        last_emotions_json = c.fetchone()
        conn.close()

        if last_emotions_json:
            response_data = json.loads(last_emotions_json[0])  # Parse JSON string to Python dict
            response = jsonify(response_data)
            response.headers.add('Access-Control-Allow-Origin', '*')
            return response, 200
        else:
            response_data = {'error': 'No status available'}
            response = jsonify(response_data)
            response.headers.add('Access-Control-Allow-Origin', '*')
            return response, 404
    except Exception as e:
        print("Error:", str(e))
        response_data = {'error': 'An error occurred'}
        response = jsonify(response_data)
        response.headers.add('Access-Control-Allow-Origin', '*')
        return response, 500

    


if __name__ == '__main__':
    # app.run(debug=True, host='0.0.0.0', port=8200)
    # ssl_context = ('localhost.crt', 'localhost.key')
    app.run(debug=True, host='0.0.0.0', port=8200)#, ssl_context=ssl_context)
