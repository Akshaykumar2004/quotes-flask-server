from datetime import timedelta
from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity
from utils import quotes,primary_emotion,secondary_emotion,jwt_key
import sqlite3
import json
import time

app = Flask(__name__)
app.config['JWT_SECRET_KEY'] = jwt_key
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(days=365)
jwt = JWTManager(app)
CORS(app)

# Register endpoint
@app.route('/register', methods=['POST'])
def register():
    time.sleep(1)
    data = request.get_json()
    username = data['username']
    password = data['password']
    email = data['email']
    conn = sqlite3.connect('./quotes.db')
    c = conn.cursor()
    c.execute("INSERT INTO Users (username, password, email) VALUES (?, ?, ?)", (username, password, email))
    conn.commit()
    conn.close()
    response = jsonify({"message": "Registration successful"})
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Methods', 'POST')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type')
    return response

# Login endpoint
@app.route('/login', methods=['POST'])
def login():
    time.sleep(1)
    data = request.get_json()
    print(data)
    username_or_email = data['username']
    password = data['password']
    conn = sqlite3.connect('./quotes.db')
    c = conn.cursor()
    
    # First, try to find the user by username
    c.execute("SELECT * FROM Users WHERE username=? AND password=?", (username_or_email, password))
    user = c.fetchone()
    
    # If not found, try to find the user by email
    if not user:
        c.execute("SELECT * FROM Users WHERE email=? AND password=?", (username_or_email, password))
        user = c.fetchone()
    
    conn.close()
    
    if user:
        access_token = create_access_token(identity=user[1])  # Assuming user[1] is the username
        token = {"access_token": access_token}
        print(token)
        response_data = {'message': 'OK', 'token': token}
        response = jsonify(response_data)
        response.headers.add('Access-Control-Allow-Origin', '*')
        return response, 200
    else:
        response_data = {'message': 'Invalid username or password'}
        response = jsonify(response_data)
        response.headers.add('Access-Control-Allow-Origin', '*')
        return response, 401

    
def create_connection():
    return sqlite3.connect('./quotes.db')

# Store status and emotions endpoint
@app.route('/receive_post', methods=['POST'])
@jwt_required()
def receive_post():
    time.sleep(2)
    # print(data)
    try:
        data = request.get_json()
        print(data  )
        print("Received data:", data)
        current_user = get_jwt_identity()
        print(current_user)

        # Store emotions data in the Emotions table
        save_status(data, current_user)

        # Extract selected secondary emotions from received data
        selected_secondary_emotions = data['emo']['selectedSecondaryEmotions']
        # Calculate weights for secondary emotions
        n = len(selected_secondary_emotions)
        weights = {}
        for i in range(n):
            weights[selected_secondary_emotions[i]] = n - i

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
        print(tert)
        # Retrieve quotes for each emotion
        resp_quotes = []
        for emotion in tert:
            resp_quotes.append(get_quotes_for_emotion(emotion))
        max_number_quotes = max([len(i) for i in resp_quotes])
        i=0
        cycle_quote = []
        while i<max_number_quotes:
            for quotes in resp_quotes:
                try:
                    # print(quotes[i])
                    cycle_quote.append(quotes[i])
                except:
                    continue
            i+=1

        # Store quotes in the Quotes table
        conn = create_connection()
        store_quotes_in_db(conn, cycle_quote, current_user)

        response_data = {'message': 'OK', 'quotes': cycle_quote}
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

# Helper function to save status data in the Emotions table
def save_status(data, user_id):
    try:
        data = json.dumps(data)
        conn = create_connection()
        c = conn.cursor()
        c.execute("INSERT INTO Emotions (user_id, emotion) VALUES (?, ?);", (user_id, data))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print("Error:", str(e))
        return False

def get_quotes_for_emotion(emotion):
    try:
        print('emo----:',emotion)
        conn = create_connection()
        c = conn.cursor()
        c.execute("SELECT quote FROM AllQuotes WHERE emotion=?", (emotion,))
        quotes = [row[0] for row in c.fetchall()]
        conn.close()
        return quotes
    except Exception as e:
        print("Error:", str(e))
        return []

# Helper function to store quotes in the Quotes table
def store_quotes_in_db(conn, quotes, user_id):
    try:

        c = conn.cursor()
        c.execute("DELETE FROM Quotes WHERE user_id=?",(user_id,))
        for quote in quotes:
            c.execute("INSERT INTO Quotes (user_id, quote) VALUES (?, ?)", (user_id, quote))

        c.executescript(f"""DROP TABLE IF EXISTS {user_id}_quotes ;
                        CREATE TABLE {user_id}_quotes AS SELECT * FROM Quotes WHERE user_id='{user_id}'""")
        conn.commit()
    except Exception as e:
        print("Error:", str(e))


# Endpoint to fetch a quote for the authenticated user
@app.route('/get_quote', methods=['GET'])
@jwt_required()
def get_quote():
    try:
        current_user = get_jwt_identity()

        # Retrieve user's stored quotes from the database
        conn = create_connection()
        c = conn.cursor()
        c.execute(f"SELECT quote FROM {current_user}_quotes WHERE user_id=?", (current_user,))
        user_quotes = c.fetchall()
        
        if user_quotes:
            # Extract quotes from database result
            quotes = [quote[0] for quote in user_quotes]

            # Fetch the first quote
            next_quote = quotes[0]

            # Remove the fetched quote from the database to avoid sending it again
            c.execute(f"DELETE FROM {current_user}_quotes WHERE user_id=? AND quote=?", (current_user, next_quote))
            c.execute(f"INSERT INTO {current_user}_quotes (user_id, quote) VALUES (?, ?)", (current_user, next_quote))

            conn.commit()
            conn.close()

            response_data = {'quote': next_quote}
            response = jsonify(response_data)
            response.headers.add('Access-Control-Allow-Origin', '*')
            return response, 200
        else:
            conn.close()
            response_data = {'error': 'No quotes available for the user'}
            response = jsonify(response_data)
            response.headers.add('Access-Control-Allow-Origin', '*')
            return response, 404
    except Exception as e:
        print("Error:", str(e))
        response_data = {'error': 'An error occurred'}
        response = jsonify(response_data)
        response.headers.add('Access-Control-Allow-Origin', '*')
        return response, 500

@app.route('/get_all_quotes', methods=['GET'])
@jwt_required()
def get_all_quotes():
    time.sleep(2)
    current_user = get_jwt_identity()
    try:
        conn = create_connection()
        c = conn.cursor()
        c.execute("SELECT quote FROM quotes WHERE user_id=?",(current_user,))
        all_quotes = c.fetchall()
        print(all_quotes)
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


if __name__ == '__main__':
    app.run(host='0.0.0.0',port='5000',debug=True)
