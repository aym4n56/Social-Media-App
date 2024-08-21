from flask import Flask, request, redirect, url_for, render_template, session, jsonify
import mysql.connector

app = Flask(__name__)
app.secret_key = 'ayman123'  # Change this to a random secret key

# Connect to MySQL Database
def db_connection():
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="ayman123",
        database="pintip",
        port=3306
    )

@app.route('/', methods=['GET'])
def index():
    return render_template('signup.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')

        conn = db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM logins WHERE email = %s AND password = %s', 
                       (email, password))
        login = cursor.fetchone()
        cursor.close()
        conn.close()

        if login:
            # Store user email in session
            session['email'] = email
            return redirect(url_for('home'))
        else:
            return redirect(url_for('login'))  # Redirect to login page on failure
    
    return render_template('login.html')

@app.route('/home', methods=['GET'])
def home():
    if 'email' not in session:
        return redirect(url_for('login'))  # Redirect to login if not authenticated
    
    # Get the email from the session
    email = session['email']

    # Connect to the database and fetch the user's name
    conn = db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute('SELECT name FROM logins WHERE email = %s', (email,))
    user = cursor.fetchone()
    cursor.close()
    conn.close()

    # Check if the user was found and extract their name
    if user:
        user_name = user['name']
    else:
        user_name = 'User'

    # Render the home page template with the user's name
    return render_template('home.html', user_name=user_name)

@app.route('/signup', methods=['GET','POST'])
def signup():
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        password = request.form.get('password')
        password_confirmation = request.form.get('password_confirmation')

        if password != password_confirmation:
            return redirect(url_for('index'))  # Redirect back to signup page if passwords don't match

        conn = db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute('INSERT INTO logins (name, email, password) VALUES (%s, %s, %s)', (name, email, password))
            conn.commit()
        except mysql.connector.Error as err:
            conn.rollback()
        finally:
            cursor.close()
            conn.close()
        
        return redirect(url_for('login'))  # Redirect to login page after successful signup

    return render_template('signup.html')

@app.route('/api/pins', methods=['GET'])
def get_pins():
    if 'email' not in session:
        return jsonify([])  # Return an empty list if the user is not authenticated

    current_user_email = session['email']

    conn = db_connection()
    cursor = conn.cursor(dictionary=True)
    
    cursor.execute("""
        SELECT tips.lat, tips.lon, tips.tip_title, tips.tip, tips.email 
        FROM tips
        WHERE tips.email = %s 
        OR tips.email IN (
            SELECT 
                CASE
                    WHEN email1 = %s THEN email2
                    ELSE email1
                END
            FROM friend_list
            WHERE email1 = %s OR email2 = %s
        )
    """, (current_user_email, current_user_email, current_user_email, current_user_email))

    pins = cursor.fetchall()
    cursor.close()
    conn.close()

    return jsonify(pins)


@app.route('/api/add_pin', methods=['POST'])
def add_pin():
    if 'email' not in session:
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401

    data = request.json
    lat = data.get('lat')
    lon = data.get('lon')
    tip_title = data.get('tip_title')  # New
    tip = data.get('tip')
    email = session['email']

    if not (lat and lon and tip and tip_title):
        return jsonify({'success': False, 'message': 'Invalid data'}), 400

    conn = db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute('INSERT INTO tips (lat, lon, tip_title, tip, email) VALUES (%s, %s, %s, %s, %s)', 
                       (lat, lon, tip_title, tip, email))
        conn.commit()
        return jsonify({'success': True})
    except mysql.connector.Error as err:
        conn.rollback()
        return jsonify({'success': False, 'message': str(err)})
    finally:
        cursor.close()
        conn.close()


@app.route('/friends', methods=['GET', 'POST'])
def friends():
    if 'email' not in session:
        return redirect('/login')  # Redirect to login if not authenticated

    current_user_email = session['email']

    if request.method == 'POST':
        search_email = request.form.get('search_email')

        conn = db_connection()
        cursor = conn.cursor(dictionary=True)
        
        try:
            query = '''
                SELECT email 
                FROM logins 
                WHERE email LIKE %s AND email != %s
            '''
            cursor.execute(query, ('%' + search_email + '%', current_user_email))
            results = cursor.fetchall()

            # Check which results are already friends
            friend_query = '''
                SELECT email1, email2
                FROM friend_list
                WHERE (email1 = %s AND email2 IN (%s)) 
                   OR (email2 = %s AND email1 IN (%s))
            '''
            cursor.execute(friend_query, (current_user_email, ','.join(r['email'] for r in results), current_user_email, ','.join(r['email'] for r in results)))
            friends = set(email for row in cursor.fetchall() for email in row.values())
            
            # Generate HTML for search results
            html = ''
            for result in results:
                email = result['email']
                button_text = 'Added' if email in friends else 'Add Friend'
                html += f'''
                    <div class="card">
                        <h4>{email}</h4>
                        <button class="add-friend" data-email="{email}">{button_text}</button>
                    </div>
                '''
        except mysql.connector.Error as err:
            html = '<p>Error retrieving search results.</p>'
        finally:
            cursor.close()
            conn.close()

        return html

    return render_template('friends.html')

@app.route('/add_friend', methods=['POST'])
def add_friend():
    if 'email' not in session:
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401

    friend_email = request.form.get('friend_email')
    current_user_email = session['email']

    conn = db_connection()
    cursor = conn.cursor()
    
    try:
        # Insert the friendship into the database
        cursor.execute('INSERT INTO friend_list (email1, email2) VALUES (%s, %s)', 
                       (current_user_email, friend_email))
        conn.commit()
        result = {'success': True, 'message': 'Friend added successfully.'}
    except mysql.connector.Error as err:
        conn.rollback()
        result = {'success': False, 'message': str(err)}
    finally:
        cursor.close()
        conn.close()

    return jsonify(result)

@app.route('/remove_friend', methods=['POST'])
def remove_friend():
    friend_email = request.form.get('friend_email')
    current_user_email = session['email']

    conn = db_connection()
    cursor = conn.cursor()
    
    try:
        query = '''
            DELETE FROM friend_list 
            WHERE (email1 = %s AND email2 = %s) 
            OR (email1 = %s AND email2 = %s)
        '''
        cursor.execute(query, (current_user_email, friend_email, friend_email, current_user_email))
        conn.commit()
        
        return jsonify({'success': True, 'message': 'Friend removed successfully'})
    except mysql.connector.Error as err:
        conn.rollback()
        return jsonify({'success': False, 'message': str(err)})
    finally:
        cursor.close()
        conn.close()

@app.route('/feed', methods=['GET'])
def feed():
    if 'email' not in session:
        return redirect(url_for('login'))  # Redirect to login if not authenticated
    
    current_user_email = session['email']

    conn = db_connection()
    cursor = conn.cursor(dictionary=True)
    
    # Query to get pins from friends, their names, and profile pictures
    cursor.execute("""
        SELECT tips.lat, tips.lon, tips.tip, tips.tip_title, logins.name, logins.profile_pic
        FROM tips
        JOIN logins ON tips.email = logins.email
        WHERE tips.email IN (
            SELECT 
                CASE
                    WHEN email1 = %s THEN email2
                    ELSE email1
                END
            FROM friend_list
            WHERE email1 = %s OR email2 = %s
        )
    """, (current_user_email, current_user_email, current_user_email))
    
    pins = cursor.fetchall()
    cursor.close()
    conn.close()

    # Render feed with names and profile pictures
    return render_template('feed.html', pins=pins)



@app.route('/profile', methods=['GET'])
def profile():
    if 'email' not in session:
        return redirect(url_for('login'))  # Redirect to login if not authenticated
    
    email = session['email']
    
    conn = db_connection()
    cursor = conn.cursor(dictionary=True)
    
    cursor.execute('SELECT name, profile_pic FROM logins WHERE email = %s', (email,))
    user = cursor.fetchone()
    
    cursor.execute("""
        SELECT 
            CASE
                WHEN email1 = %s THEN email2
                ELSE email1
            END AS friend_email
        FROM friend_list
        WHERE email1 = %s OR email2 = %s
    """, (email, email, email))
    
    friend_emails = [row['friend_email'] for row in cursor.fetchall()]

    friends = []
    for friend_email in friend_emails:
        cursor.execute('SELECT name, profile_pic FROM logins WHERE email = %s', (friend_email,))
        friend = cursor.fetchone()
        if friend:
            friends.append({
                'email': friend_email,
                'name': friend['name'],
                'profile_pic': friend['profile_pic']
            })
    
    cursor.execute('SELECT lat, lon, tip_title, tip FROM tips WHERE email = %s', (email,))
    tips = cursor.fetchall()
    
    cursor.close()
    conn.close()

    return render_template('profile.html', user=user, tips=tips, friends=friends)

@app.route('/api/remove_tip', methods=['POST'])
def remove_tip():
    if 'email' not in session:
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401

    data = request.get_json()
    lat = data.get('lat')
    lon = data.get('lon')
    tip = data.get('tip')
    email = session['email']

    if not (lat and lon and tip):
        return jsonify({'success': False, 'message': 'Invalid data'}), 400

    conn = db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute('DELETE FROM tips WHERE lat = %s AND lon = %s AND tip = %s AND email = %s', 
                       (lat, lon, tip, email))
        conn.commit()
        if cursor.rowcount > 0:
            return jsonify({'success': True})
        else:
            return jsonify({'success': False, 'message': 'Tip not found or already removed'})
    except mysql.connector.Error as err:
        conn.rollback()
        return jsonify({'success': False, 'message': str(err)})
    finally:
        cursor.close()
        conn.close()

@app.route('/api/update_profile_pic', methods=['POST'])
def update_profile_pic():
    if 'email' not in session:
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401

    data = request.get_json()
    profile_pic = data.get('profile_pic')
    email = session['email']

    if not profile_pic:
        return jsonify({'success': False, 'message': 'Invalid data'}), 400

    conn = db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute('UPDATE logins SET profile_pic = %s WHERE email = %s', (profile_pic, email))
        conn.commit()
        return jsonify({'success': True})
    except mysql.connector.Error as err:
        conn.rollback()
        return jsonify({'success': False, 'message': str(err)})
    finally:
        cursor.close()
        conn.close()

if __name__ == '__main__':
    app.run(debug=True)
