from flask import Flask, render_template, request, g
from redis import Redis
import socket
import json
import logging

# Configuración de la aplicación Flask
hostname = socket.gethostname()
app = Flask(__name__)

# Configuración del registro de errores
gunicorn_error_logger = logging.getLogger('gunicorn.error')
app.logger.handlers.extend(gunicorn_error_logger.handlers)
app.logger.setLevel(logging.INFO)

# Configuración de la conexión Redis
def get_redis():
    if not hasattr(g, 'redis'):
        g.redis = Redis(host="redis", db=0, socket_timeout=5)
    app.logger.info("Redis connection established successfully")
    return g.redis

# Funciones para el sistema de recomendación
users = {
    "Angelica": {"Blues Traveler": 3.5, "Broken Bells": 2.0, "Norah Jones": 4.5, "Phoenix": 5.0, "Slightly Stoopid": 1.5, "The Strokes": 2.5, "Vampire Weekend": 2.0},
    "Bill": {"Blues Traveler": 2.0, "Broken Bells": 3.5, "Deadmau5": 4.0, "Phoenix": 2.0, "Slightly Stoopid": 3.5, "Vampire Weekend": 3.0},
    "Chan": {"Blues Traveler": 5.0, "Broken Bells": 1.0, "Deadmau5": 1.0, "Norah Jones": 3.0, "Phoenix": 5, "Slightly Stoopid": 1.0},
    "Dan": {"Blues Traveler": 3.0, "Broken Bells": 4.0, "Deadmau5": 4.5, "Phoenix": 3.0, "Slightly Stoopid": 4.5, "The Strokes": 4.0, "Vampire Weekend": 2.0},
    "Hailey": {"Broken Bells": 4.0, "Deadmau5": 1.0, "Norah Jones": 4.0, "The Strokes": 4.0, "Vampire Weekend": 1.0},
    "Jordyn": {"Broken Bells": 4.5, "Deadmau5": 4.0, "Norah Jones": 5.0, "Phoenix": 5.0, "Slightly Stoopid": 4.5, "The Strokes": 4.0, "Vampire Weekend": 4.0},
    "Sam": {"Blues Traveler": 5.0, "Broken Bells": 2.0, "Norah Jones": 3.0, "Phoenix": 5.0, "Slightly Stoopid": 4.0, "The Strokes": 5.0},
    "Veronica": {"Blues Traveler": 3.0, "Norah Jones": 5.0, "Phoenix": 4.0, "Slightly Stoopid": 2.5, "The Strokes": 3.0}
}

def manhattan(rating1, rating2):
    """Calculates the Manhattan distance between two dictionaries of ratings"""
    distance = 0
    commonRatings = False
    for key in rating1:
        if key in rating2:
            distance += abs(rating1[key] - rating2[key])
            commonRatings = True
    if commonRatings:
        return distance
    else:
        return -1  # Indicates no common ratings

def computeNearestNeighbor(username, users):
    """Creates a sorted list of users based on their distance to the given username"""
    distances = []
    for user in users:
        if user != username:
            distance = manhattan(users[user], users[username])
            distances.append((distance, user))
    distances.sort()  # Sort distances
    return distances

def recommend(username, users):
    """Generates recommendations for a given user"""
    nearest = computeNearestNeighbor(username, users)[0][1]  # Find nearest neighbor
    recommendations = []
    neighborRatings = users[nearest]
    userRatings = users[username]
    for artist in neighborRatings:
        if artist not in userRatings:
            recommendations.append((artist, neighborRatings[artist]))
    return sorted(recommendations, key=lambda artistTuple: artistTuple[1], reverse=True)

# Rutas de la aplicación Flask
@app.route("/", methods=['POST','GET'])
def hello():
    # Manejo de la identificación del votante
    if request.method == 'POST':
        selected_user = request.form.get('selected_user')
        if selected_user:
            # Obtener recomendaciones para el usuario seleccionado
            recs = recommend(selected_user, users)
            
            # Convertir las recomendaciones a formato JSON
            recs_json = json.dumps(recs)
            
            # Guardar las recomendaciones en Redis
            redis_conn = get_redis()
            redis_conn.rpush('recommendations', recs_json)

            app.logger.info("Recommendations for user '%s': %s", selected_user, recs_json)
            app.logger.info("Recommendations for user '%s': %s", selected_user, recs_json)

            
            return render_template('recommendation.html', username=selected_user, recommendations=recs)

    # Obtener nombres de usuarios para mostrar en los botones
    user_names = list(users.keys())

    return render_template('index.html', user_names=user_names)


if __name__ == "__main__":
    app.run(host='0.0.0.0', port=80, debug=True, threaded=True)
