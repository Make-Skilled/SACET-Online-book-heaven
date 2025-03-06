import base64
from pymongo import MongoClient
from flask import Flask,render_template,session,request,redirect,send_file,url_for, flash
from bson.objectid import ObjectId
from werkzeug.utils import secure_filename
import os
import io
from datetime import datetime

database=MongoClient("mongodb+srv://shaikfaraha:Farha17@cluster0.h4dnl.mongodb.net/")
users=database['users']
books=users['books'] 
stock=users['stock']
orders=users['orders']
 
app=Flask(__name__)

app.secret_key='50000'
app.config['uploads']="uploads"
# session['flag']=0

@app.route('/') 
def home():
    return render_template('Login.html')

@app.route('/reg')
def loadReg():
    return render_template('Register.html')


@app.route('/register',methods=['post','get'])
def register():
    username=request.form['username']
    phone=request.form['phone']
    mail=request.form['mail']
    password=request.form['password']
    confirmpass=request.form['confirmpass']
    if(password!=confirmpass):
        return render_template('register.html',res='Passwords do not match')
    # Create user document with required structure
    k = {
        "username": username,
        "phone": phone,
        "mail": mail,
        "password": password,
        "address": None,
        "profile_picture": None,
        "cart": []
    }
    
    res=books.find()
    for data in res:
        x=dict(data)
        if(x['username']==username):
            return render_template('register.html',res='Username already exists')
        if(x['mail']==mail):
         return render_template('register.html',res='Email already exists')
        if(password!=confirmpass):
            return render_template('register.html',res='Passwords do not match')
        if(len(password)<8):
            return render_template('register.html',res='Password should have atlest 8 characters')           
    else:
        books.insert_one(k)
        return render_template('register.html',res='Registration successful')

@app.route("/adminlogin",methods=['post','get'])
def adminlogin():
    user=request.form['name']
    password=request.form['pass']

    data=stock.find()
    if(user=="admin" and password=="1234567890"):
        session['name']=user
        return redirect(url_for('admindashboard'))
    else:
        return render_template('Admin.html',status='User does not exist or wrong password')

@app.route('/admindashboard')
def admindashboard():
    if 'name' not in session or session['name'] != 'admin':
        return redirect(url_for('admin'))
    
    data = stock.find()
    return render_template('adminindex.html', data=data)

@app.route('/login', methods=['POST', 'GET'])
def login():
    user = request.form['name']
    password = request.form['pass']
    session['name'] = user
    flag = 0
    res = books.find()
    res1 = books.find_one({"username": user})
    
    if res1:
        res1 = dict(res1)
        count = len(list(res1.get('cart', [])))
    else:
        count = 0

    for x in res:
        i = dict(x)
        if user == i['username'] and password == i['password']:
            session['name'] = user
            flag = 1
            break
    
    if flag == 1:
        return redirect(url_for('userdashboard'))
    else:
        return render_template('login.html', status='User does not exist or wrong password')

@app.route('/userdashboard')
def userdashboard():
    if 'name' not in session:
        return redirect(url_for('login'))
    
    user = session['name']
    res1 = books.find_one({"username": user})
    
    if res1:
        res1 = dict(res1)
        count = len(list(res1.get('cart', [])))
    else:
        count = 0
    
    return render_template('index.html', count=count)

@app.route('/cart')
def cart():
    if 'name' not in session:
        return redirect(url_for('login'))
        
    user_data = books.find_one({"username": session['name']})
    if not user_data:
        return redirect(url_for('login'))
        
    cart_items = user_data.get('cart', [])
    
    # Calculate total and organize cart items
    total = 0
    organized_cart = {}
    
    for item in cart_items:
        item_id = str(item['_id'])
        if item_id in organized_cart:
            organized_cart[item_id]['count'] += 1
            organized_cart[item_id]['subtotal'] = organized_cart[item_id]['count'] * item['price']
        else:
            organized_cart[item_id] = {
                'title': item['title'],
                'author': item['author'],
                'genre': item['genre'],
                'price': item['price'],
                'image': item['image'],
                'mimetype': item['mimetype'],
                'count': 1,
                'subtotal': item['price']
            }
        total += item['price']
    
    return render_template('Cart.html', data=organized_cart, total=total)

@app.route('/update_cart', methods=['POST'])
def update_cart():
    if 'name' not in session:
        return {'success': False, 'message': 'Please login first'}
        
    book_id = request.form.get('book_id')
    action = request.form.get('action')
    
    if not book_id or not action:
        return {'success': False, 'message': 'Invalid request'}
        
    user_data = books.find_one({"username": session['name']})
    if not user_data:
        return {'success': False, 'message': 'User not found'}
        
    cart_items = user_data.get('cart', [])
    
    if action == 'remove':
        # Remove all instances of the book
        cart_items = [item for item in cart_items if str(item['_id']) != book_id]
    elif action == 'increase':
        # Add one more instance
        book = stock.find_one({"_id": ObjectId(book_id)})
        if book:
            cart_items.append(book)
    elif action == 'decrease':
        # Remove one instance
        found = False
        for i, item in enumerate(cart_items):
            if str(item['_id']) == book_id:
                cart_items.pop(i)
                found = True
                break
    
    # Update user's cart
    books.update_one(
        {"username": session['name']},
        {"$set": {"cart": cart_items}}
    )
    
    return {'success': True, 'message': 'Cart updated successfully'}

@app.route('/checkout')
def checkout():
    if 'name' not in session:
        return redirect(url_for('login'))
        
    user_data = books.find_one({"username": session['name']})
    if not user_data:
        return redirect(url_for('login'))
        
    # Clear the cart after successful checkout
    books.update_one(
        {"username": session['name']},
        {"$set": {"cart": []}}
    )
    
    return render_template('Checkout.html')

@app.route('/profile')
def profile():
    if 'name' not in session:
        return redirect(url_for('login'))
    
    user = books.find_one({"username": session['name']})
    if not user:
        return redirect(url_for('login'))
    
    return render_template('Profile.html', user=user)

@app.route('/sortbyauthor')
def sortbyauthor():
    return render_template('Author.html')

@app.route('/sortbygenere')
def sortbygenere():
    return render_template('Genere.html')

@app.route('/forgot')
def forgot():
    return render_template('Forgot.html')

@app.route('/forget')
def forget():
    email=request.form['email']
    res=books.find_one({'email': email})
    if not res:
        return render_template('Forgot.html',status='Email not found')
    else:
        mail=res['password']
        return render_template('Password.html',pas=mail)

@app.route('/add')
def deff():
    return render_template('Book.html')

@app.route('/addbook',methods=['post'])
def book():
    name = request.form['title']
    author = request.form['author']
    genre = request.form['genre']
    price = request.form['price']
    stock_count = request.form['stock']
    image_file = request.files['image']
    pdf_file = request.files['pdf']
    
    # Create static/uploads directory if it doesn't exist
    upload_folder = os.path.join('static', 'uploads')
    if not os.path.exists(upload_folder):
        os.makedirs(upload_folder)
    
    # Generate timestamped filenames
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    image_filename = f"{timestamp}_img_{secure_filename(image_file.filename)}"
    pdf_filename = f"{timestamp}_pdf_{secure_filename(pdf_file.filename)}"
    
    # Save files with secure filenames
    image_path = os.path.join(upload_folder, image_filename)
    pdf_path = os.path.join(upload_folder, pdf_filename)
    image_file.save(image_path)
    pdf_file.save(pdf_path)
    
    di = {}
    di['title'] = name
    di['genre'] = genre
    di['author'] = author 
    di['price'] = int(price)
    di['stock'] = int(stock_count)
    di['image'] = image_filename
    di['pdf'] = pdf_filename
    di['mimetype'] = image_file.mimetype.split('/')[-1]
    stock.insert_one(di) 
    return redirect(url_for('allbooks'))


@app.route('/admin')
def admin():
    return render_template('Admin.html')

@app.route('/addtocart',methods=['get'])
def addtocart():
    id=request.args.get("id")
    res=stock.find_one({"_id":ObjectId(id)})
    books.update_one({"username":session['name']},{"$push":{"cart":res}})
    data=books.find_one({"username":session['name']})['cart']
    di={}
    res1=dict(books.find_one({"username":session['name']}))
    count=(len(list(res1['cart'])))
    data=stock.find()
    print(data)
    total=0
    for i in data:
        if i["_id"] in di:
            di[i["_id"]]['count']+=1
        else:
            x=dict(i)
            x['count']=1
            di[i["_id"]]=x
        total+=int(i['price'])
    return render_template("index.html",data=data,count=count)

@app.route('/filter',methods=['get','post'])
def filter():
    filter=request.form['search']
    data=stock.find()
    for i in data:
        x=dict(i)
        if x['author']==filter:
            data=stock.find({'author':i['author']})
            
            return render_template('aindex.html',data)
        elif x['genre']==filter:
            data=stock.find({"genre":filter})
            return render_template('gindex.html',data)
        elif x['title']==filter:
            data=stock.find({"title":filter})
            return render_template('tindex.html',data)
        else: 
            return render_template('index.html')
        

@app.route("/book")
def booking():
    return render_template("/Book.html")

@app.route('/logout')
def logout():
    session['name']=''
    return redirect('/')

@app.route('/img/<name>/<mimetype>')
def load(name,mimetype):
    with open('./uploads/'+name,'rb') as f:
        x=f.read()
        return send_file(
            io.BytesIO(x),
            mimetype='image/'+mimetype,
            as_attachment=True,
            download_name=name
        )

@app.route('/blog')
def blog():
    return render_template('blog.html')

@app.route('/shop')
def shop():
    if 'name' not in session:
        return redirect(url_for('login'))
    
    # Get user's cart count
    user = session['name']
    res1 = books.find_one({"username": user})
    count = len(list(res1.get('cart', []))) if res1 else 0
    
    # Get all books from stock
    all_books = list(stock.find())
    
    # Get unique categories and authors for filters
    categories = list(set(book['genre'] for book in all_books))
    authors = list(set(book['author'] for book in all_books))
    
    return render_template('shop.html', books=all_books, categories=categories, authors=authors, count=count)

@app.route('/aboutus')
def aboutus():
    return render_template('aboutus.html')

@app.route('/contact')
def contact():
    return render_template('contact.html')

@app.route('/send_message', methods=['POST'])
def send_message():
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        subject = request.form.get('subject')
        message = request.form.get('message')
        
        # Here you would typically save the message to a database
        # For now, we'll just redirect with a success message
        flash('Thank you for your message! We will get back to you soon.', 'success')
        return redirect(url_for('contact'))

@app.route('/allbooks')
def allbooks():
    if 'name' not in session or session['name'] != 'admin':
        return redirect(url_for('admin'))
    
    # Get all books from stock
    all_books = list(stock.find())
    
    # Get unique genres
    genres = sorted(list(set(book['genre'] for book in all_books)))
    
    # Get search query and filters
    search_query = request.args.get('search', '').lower()
    genre_filter = request.args.get('genre', '')
    price_filter = request.args.get('price', '')
    
    # Apply filters
    filtered_books = all_books
    if search_query:
        filtered_books = [
            book for book in filtered_books 
            if search_query in book['title'].lower() 
            or search_query in book['author'].lower()
            or search_query in book['genre'].lower()
        ]
    
    if genre_filter:
        filtered_books = [book for book in filtered_books if book['genre'] == genre_filter]
    
    if price_filter:
        if price_filter == 'under500':
            filtered_books = [book for book in filtered_books if book['price'] < 500]
        elif price_filter == '500to1000':
            filtered_books = [book for book in filtered_books if 500 <= book['price'] <= 1000]
        elif price_filter == 'over1000':
            filtered_books = [book for book in filtered_books if book['price'] > 1000]
    
    return render_template('allbooks.html', books=filtered_books, genres=genres)

@app.route('/editbook/<book_id>', methods=['GET', 'POST'])
def editbook(book_id):
    if 'name' not in session or session['name'] != 'admin':
        return redirect(url_for('admin'))
    
    if request.method == 'GET':
        # Get book details for editing
        book = stock.find_one({"_id": ObjectId(book_id)})
        if not book:
            return redirect(url_for('allbooks'))
        return render_template('editbook.html', book=book)
    
    elif request.method == 'POST':
        # Update book details
        name = request.form['bookname']
        author = request.form['author']
        genre = request.form['genre']
        price = request.form['price']
        stock_count = request.form['stock']
        
        update_data = {
            'title': name,
            'author': author,
            'genre': genre,
            'price': int(price),
            'stock': int(stock_count)
        }
        
        # Handle image upload if a new image is provided
        if 'image' in request.files:
            image_file = request.files['image']
            if image_file.filename:
                # Generate timestamped filename
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                image_filename = f"{timestamp}_img_{secure_filename(image_file.filename)}"
                
                # Create static/uploads directory if it doesn't exist
                upload_folder = os.path.join('static', 'uploads')
                if not os.path.exists(upload_folder):
                    os.makedirs(upload_folder)
                
                # Save file with secure filename
                image_path = os.path.join(upload_folder, image_filename)
                image_file.save(image_path)
                
                # Delete old image if it exists
                old_book = stock.find_one({"_id": ObjectId(book_id)})
                if old_book and 'image' in old_book:
                    try:
                        old_image_path = os.path.join(upload_folder, old_book['image'])
                        if os.path.exists(old_image_path):
                            os.remove(old_image_path)
                    except:
                        pass
                
                update_data['image'] = image_filename
                update_data['mimetype'] = image_file.mimetype.split('/')[-1]
        
        # Handle PDF upload if a new PDF is provided
        if 'pdf' in request.files:
            pdf_file = request.files['pdf']
            if pdf_file.filename:
                # Generate timestamped filename
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                pdf_filename = f"{timestamp}_pdf_{secure_filename(pdf_file.filename)}"
                
                # Save file with secure filename
                pdf_path = os.path.join(upload_folder, pdf_filename)
                pdf_file.save(pdf_path)
                
                # Delete old PDF if it exists
                old_book = stock.find_one({"_id": ObjectId(book_id)})
                if old_book and 'pdf' in old_book:
                    try:
                        old_pdf_path = os.path.join(upload_folder, old_book['pdf'])
                        if os.path.exists(old_pdf_path):
                            os.remove(old_pdf_path)
                    except:
                        pass
                
                update_data['pdf'] = pdf_filename
        
        # Update the book in database
        stock.update_one(
            {"_id": ObjectId(book_id)},
            {"$set": update_data}
        )
        
        return redirect(url_for('allbooks'))

@app.route('/deletebook/<book_id>')
def deletebook(book_id):
    if 'name' not in session or session['name'] != 'admin':
        return redirect(url_for('admin'))
    
    # Get book details to delete the image file
    book = stock.find_one({"_id": ObjectId(book_id)})
    if book:
        # Delete the image file from uploads directory
        try:
            os.remove(os.path.join(app.config['uploads'], book['image']))
        except:
            pass  # Ignore if file doesn't exist
        
        # Delete the book from database
        stock.delete_one({"_id": ObjectId(book_id)})
    
    return redirect(url_for('allbooks'))

@app.route('/myorders')
def myorders():
    if 'name' not in session:
        return redirect(url_for('login'))
    
    user = session['name']
    print("Current user:", user)  # Debug print
    user_orders = list(orders.find({"user": user}).sort("order_date", -1))
    print("Found orders:", len(user_orders))  # Debug print
    for order in user_orders:  # Debug print
        print("Order:", order['_id'], "Date:", order['order_date'], "Status:", order['status'])
    return render_template('myorders.html', user_orders=user_orders)

@app.route('/create_order', methods=['POST'])
def create_order():
    if 'name' not in session:
        return {'success': False, 'message': 'Please login first'}
    
    user = session['name']
    user_data = books.find_one({"username": user})
    if not user_data:
        return {'success': False, 'message': 'User not found'}
    
    cart_items = user_data.get('cart', [])
    if not cart_items:
        return {'success': False, 'message': 'Cart is empty'}
    
    # Calculate total and organize cart items
    total = 0
    order_items = []
    
    for item in cart_items:
        item_id = str(item['_id'])
        # Check if item already exists in order_items
        existing_item = next((x for x in order_items if str(x['book_id']) == item_id), None)
        if existing_item:
            existing_item['quantity'] += 1
            existing_item['subtotal'] = existing_item['quantity'] * existing_item['price']
        else:
            order_items.append({
                'book_id': ObjectId(item_id),
                'title': item['title'],
                'author': item['author'],
                'genre': item['genre'],
                'price': item['price'],
                'quantity': 1,
                'subtotal': item['price']
            })
        total += item['price']
    
    # Create order document with items as a list
    order = {
        'user': user,
        'user_details': {
            'username': user_data['username'],
            'email': user_data['mail'],
            'phone': user_data.get('phone', ''),
            'address': user_data.get('address', '')
        },
        'order_items': order_items,
        'total_amount': total,
        'status': 'pending',
        'payment_status': 0,  # 0 for unpaid, 1 for paid
        'order_date': datetime.now(),
        'shipping_address': user_data.get('address', ''),
        'contact': user_data.get('phone', '')
    }
    
    # Insert order into orders collection
    orders.insert_one(order)
    
    # Clear user's cart
    books.update_one(
        {"username": user},
        {"$set": {"cart": []}}
    )
    
    # Update book stock
    for item in order_items:
        stock.update_one(
            {"_id": item['book_id']},
            {"$inc": {"stock": -item['quantity']}}
        )
    
    return {'success': True, 'redirect': True}

@app.route('/edit_profile', methods=['GET', 'POST'])
def edit_profile():
    if 'name' not in session:
        return redirect(url_for('login'))
    
    user = books.find_one({"username": session['name']})
    if not user:
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        # Handle profile picture upload
        profile_picture = None
        if 'profile_picture' in request.files:
            file = request.files['profile_picture']
            if file and file.filename:
                # Create uploads directory if it doesn't exist
                upload_folder = os.path.join('static', 'uploads')
                if not os.path.exists(upload_folder):
                    os.makedirs(upload_folder)
                
                # Generate timestamped filename
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                filename = f"{timestamp}_profile_{secure_filename(file.filename)}"
                file_path = os.path.join(upload_folder, filename)
                file.save(file_path)
                profile_picture = filename
                
                # Delete old profile picture if exists
                if user.get('profile_picture'):
                    try:
                        old_path = os.path.join(upload_folder, user['profile_picture'])
                        if os.path.exists(old_path):
                            os.remove(old_path)
                    except:
                        pass
        
        # Update user data
        update_data = {
            "phone": request.form.get('phone'),
            "address": request.form.get('address')
        }
        
        # Only update profile picture if a new one was uploaded
        if profile_picture:
            update_data['profile_picture'] = profile_picture
        
        books.update_one(
            {"username": session['name']},
            {"$set": update_data}
        )
        
        return redirect(url_for('profile'))
    
    return render_template('edit_profile.html', user=user)

@app.route('/allorders')
def allorders():
    if 'name' not in session or session['name'] != 'admin':
        return redirect(url_for('admin'))
    
    # Get all orders sorted by date (newest first)
    all_orders = list(orders.find().sort("order_date", -1))
    return render_template('allorders.html', all_orders=all_orders)

@app.route('/update_order_status/<order_id>', methods=['POST'])
def update_order_status(order_id):
    if 'name' not in session or session['name'] != 'admin':
        return redirect(url_for('admin'))
    
    new_status = request.form.get('status')
    if new_status not in ['pending', 'shipped', 'delivered', 'cancelled']:
        return redirect(url_for('allorders'))
    
    # Get the current order
    order = orders.find_one({"_id": ObjectId(order_id)})
    if not order:
        return redirect(url_for('allorders'))
    
    # If status is changing to delivered, update stock
    if new_status == 'delivered' and order['status'] != 'delivered':
        # Update stock for each book in the order
        for item in order['order_items']:
            # Decrease stock by the quantity ordered
            stock.update_one(
                {"_id": item['book_id']},
                {"$inc": {"stock": -item['quantity']}}
            )
    
    # If status was delivered and is being changed to cancelled, restore stock
    elif new_status == 'cancelled' and order['status'] == 'delivered':
        # Restore stock for each book in the order
        for item in order['order_items']:
            # Increase stock by the quantity that was delivered
            stock.update_one(
                {"_id": item['book_id']},
                {"$inc": {"stock": item['quantity']}}
            )
    
    # Update the order status
    orders.update_one(
        {"_id": ObjectId(order_id)},
        {"$set": {"status": new_status}}
    )
    
    return redirect(url_for('allorders'))

@app.route('/payment/<order_id>')
def payment(order_id):
    if 'name' not in session:
        return redirect(url_for('login'))
    
    order = orders.find_one({"_id": ObjectId(order_id)})
    
    if not order or order['user'] != session['name']:
        return redirect(url_for('myorders'))
    
    if order['status'] != 'delivered':
        return redirect(url_for('myorders'))
    
    # Update payment status
    orders.update_one(
        {"_id": ObjectId(order_id)},
        {"$set": {'payment_status': 1}}
    )
    
    return render_template('payment.html', order=order)

if __name__=="__main__":
    app.run(debug=True,host='0.0.0.0')