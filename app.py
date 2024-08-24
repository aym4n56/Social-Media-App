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
    tip_title = data.get('tip_title')
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
        search_email = request.form.get('search_email', '').strip()

        if not search_email:
            return '<p>Please enter an email to search.</p>'

        conn = db_connection()
        cursor = conn.cursor(dictionary=True)

        try:
            # Search for users whose email matches the search query and exclude the current user
            search_query = '''
                SELECT email, name, profile_pic
                FROM logins
                WHERE email LIKE %s AND email != %s
            '''
            cursor.execute(search_query, (f"%{search_email}%", current_user_email))
            search_results = cursor.fetchall()

            if not search_results:
                return '<p>No users found matching the search criteria.</p>'

            # Extract the emails from the search results
            searched_emails = [user['email'] for user in search_results]

            # Now, check which of these users are already friends with the current user
            # We'll use parameterized queries with IN clause
            format_strings = ','.join(['%s'] * len(searched_emails))  # e.g., '%s,%s,%s'
            friendship_query = f'''
                SELECT 
                    CASE
                        WHEN email1 = %s THEN email2
                        ELSE email1
                    END AS friend_email
                FROM friend_list
                WHERE (email1 = %s AND email2 IN ({format_strings}))
                   OR (email2 = %s AND email1 IN ({format_strings}))
            '''

            # Parameters for the friendship query
            friendship_params = [current_user_email, current_user_email] + searched_emails + [current_user_email] + searched_emails

            cursor.execute(friendship_query, friendship_params)
            friends_records = cursor.fetchall()

            # Create a set of emails that are already friends
            friends_set = set(record['friend_email'] for record in friends_records)

            # Generate HTML for search results
            html = ''
            for user in search_results:
                email = user['email']
                name = user['name']
                profile_pic = user['profile_pic'] if user['profile_pic'] else 'default_profile_pic_url'  # Replace with actual default
                if email in friends_set:
                    # User is already a friend
                    button_html = f'<button class="added-friend" disabled>Added</button>'
                else:
                    # User is not a friend yet
                    button_html = f'<button class="add-friend" data-email="{email}">Add Friend</button>'

            html += f'''
                <div class="card" style="border: 1px solid #ddd; border-radius: 8px; padding: 20px; margin-bottom: 20px; max-width: 400px; text-align: left;">
                    <div style="display: flex; align-items: center; margin-bottom: 15px;">
                        <img src="{profile_pic}" alt="{name}'s Profile Picture" style="width: 60px; height: 60px; border-radius: 50%; margin-right: 15px;">
                    <div>
                        <h3 style="margin: 0; font-size: 1.2em; color: #333;">{name}</h3>
                        <p style="color: #777; font-size: 0.9em;">{email}</p>
                        {button_html}
                    </div>
                    </div>
                </div>
            '''
            
        except mysql.connector.Error as err:
            print(f"Database error: {err}")
            html = '<p>An error occurred while retrieving search results.</p>'
        finally:
            cursor.close()
            conn.close()

        return html

    # For GET requests, render the friends search page
    return render_template('friends.html')


@app.route('/add_friend', methods=['POST'])
def add_friend():
    if 'email' not in session:
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401

    friend_email = request.form.get('friend_email')
    current_user_email = session['email']

    if not friend_email:
        return jsonify({'success': False, 'message': 'No friend email provided.'}), 400

    if friend_email == current_user_email:
        return jsonify({'success': False, 'message': 'You cannot add yourself as a friend.'}), 400

    conn = db_connection()
    cursor = conn.cursor()

    try:
        # Check if the friendship already exists
        check_query = '''
            SELECT * FROM friend_list
            WHERE (email1 = %s AND email2 = %s) OR (email1 = %s AND email2 = %s)
        '''
        cursor.execute(check_query, (current_user_email, friend_email, friend_email, current_user_email))
        existing_friendship = cursor.fetchone()

        if existing_friendship:
            return jsonify({'success': False, 'message': 'You are already friends with this user.'}), 400

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
    
    # Updated query to order by created_at in descending order
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
        ORDER BY tips.created_at DESC
    """, (current_user_email, current_user_email, current_user_email))
    
    pins = cursor.fetchall()
    cursor.close()
    conn.close()
    
    # Render feed with names and profile pictures
    return render_template('feed.html', pins=pins)



@app.route('/profile', methods=['GET'])
def profile():
    if 'email' not in session:
        return redirect(url_for('login'))  # Redirect to login if no user is logged in
    
    email = session['email']
    
    conn = db_connection()
    cursor = conn.cursor(dictionary=True)
    
    cursor.execute('SELECT name, profile_pic, votes FROM logins WHERE email = %s', (email,))
    user = cursor.fetchone()

    # Fetch the number of tips
    cursor.execute('SELECT COUNT(*) as tip_count FROM tips WHERE email = %s', (email,))
    tip_count = cursor.fetchone()['tip_count']
    
    # Add tip_count to the user dictionary
    user['tip_count'] = tip_count
    
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
    
    cursor.execute('SELECT lat, lon, tip_title, tip FROM tips WHERE email = %s ORDER BY created_at DESC', (email,))
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

@app.route('/messages', methods=['GET', 'POST'])
def messages():
    if 'email' not in session:
        return redirect(url_for('login'))

    current_user_email = session['email']
    conn = db_connection()
    cursor = conn.cursor(dictionary=True)

    # Handle search query from the form
    search_query = request.form.get('search_query', '').strip()

    # Get all users that are friends with the current user
    # We use a UNION to ensure we capture both directions of the friendship
    friendship_query = '''
        SELECT 
            CASE
                WHEN email1 = %s THEN email2
                ELSE email1
            END AS friend_email
        FROM friend_list
        WHERE email1 = %s OR email2 = %s
    '''

    cursor.execute(friendship_query, (current_user_email, current_user_email, current_user_email))
    friends_emails = [row['friend_email'] for row in cursor.fetchall()]

    if friends_emails:
        format_strings = ','.join(['%s'] * len(friends_emails))

        # Filter friends by search query if provided
        if search_query:
            friends_query = f'''
                SELECT email, name, profile_pic
                FROM logins
                WHERE email IN ({format_strings})
                AND (name LIKE %s OR email LIKE %s)
            '''
            cursor.execute(friends_query, (*friends_emails, f"%{search_query}%", f"%{search_query}%"))
        else:
            friends_query = f'''
                SELECT email, name, profile_pic
                FROM logins
                WHERE email IN ({format_strings})
            '''
            cursor.execute(friends_query, (*friends_emails,))
        
        friends = cursor.fetchall()
    else:
        friends = []

    cursor.close()
    conn.close()

    return render_template('messages.html', friends=friends, search_query=search_query)

@app.route('/chat/<friend_email>', methods=['GET'])
def chat(friend_email):
    if 'email' not in session:
        return redirect(url_for('login'))

    current_user_email = session['email']
    conn = db_connection()
    cursor = conn.cursor(dictionary=True)

    # Fetch chat room ID
    cursor.execute("""
        SELECT id 
        FROM chat_room 
        WHERE (user1_email = %s AND user2_email = %s) 
           OR (user1_email = %s AND user2_email = %s)
    """, (current_user_email, friend_email, friend_email, current_user_email))
    
    chat_room = cursor.fetchone()

    if not chat_room:
        return "Chat room does not exist.", 404

    chat_room_id = chat_room['id']

    # Fetch messages for the chat room
    cursor.execute("""
        SELECT * FROM message
        WHERE chat_room_id = %s
        ORDER BY created_at ASC
    """, (chat_room_id,))

    messages = cursor.fetchall()

    # Fetch friend details
    cursor.execute("""
        SELECT * FROM logins WHERE email = %s
    """, (friend_email,))
    friend = cursor.fetchone()

    cursor.close()
    conn.close()

    return render_template('chat.html', messages=messages, friend=friend, current_user_email=current_user_email)



@app.route('/send_message', methods=['POST'])
def send_message():
    if 'email' not in session:
        return redirect(url_for('login'))

    sender_email = session['email']
    receiver_email = request.form.get('receiver_email')
    content = request.form.get('content')

    if not receiver_email or not content:
        return "Recipient email and message content are required", 400

    conn = db_connection()
    cursor = conn.cursor()

    # Check if a chat room already exists
    cursor.execute("""
        SELECT id 
        FROM chat_room 
        WHERE (user1_email = %s AND user2_email = %s) 
           OR (user1_email = %s AND user2_email = %s)
    """, (sender_email, receiver_email, receiver_email, sender_email))

    chat_room = cursor.fetchone()

    if chat_room is None:
        # Create a new chat room if none exists
        cursor.execute("""
            INSERT INTO chat_room (user1_email, user2_email)
            VALUES (%s, %s)
        """, (sender_email, receiver_email))
        conn.commit()

        chat_room_id = cursor.lastrowid
    else:
        chat_room_id = chat_room[0]  # Access the first element of the tuple

    # Insert the message
    cursor.execute("""
        INSERT INTO message (chat_room_id, sender_email, receiver_email, content)
        VALUES (%s, %s, %s, %s)
    """, (chat_room_id, sender_email, receiver_email, content))
    conn.commit()

    cursor.close()
    conn.close()

    return redirect(url_for('chat', friend_email=receiver_email))



if __name__ == '__main__':
    app.run(debug=True)
