import base64
from pymongo import MongoClient
from flask import Flask,render_template,session,request,redirect,send_file,url_for, flash
from bson.objectid import ObjectId
from werkzeug.utils import secure_filename
import os;
import io

database=MongoClient("mongodb+srv://kr4785543:1234567890@cluster0.220yz.mongodb.net/")
users=database['users']
books=users['books'] 
stock=users['stock']
 
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
    k={}
    k['username']=username
    k['phone']=phone
    k['mail']=mail
    k['password']=password
    k['confirmpass']=confirmpass  
    k['cart']=[]
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
    if(user=="admin" and password=="nimda"):
        session['name']=user
        return render_template('AdminIndex.html',data=data)
    else:
        return render_template('Admin.html',status='User does not exist or wrong password')



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
    
    # Get all books from stock
    data = list(stock.find())
    
    # Featured books (get from database if possible)
    featured_books = []
    for book in data:
        if len(featured_books) < 4:  # Limit to 4 featured books
            featured_books.append({
                'title': book['title'],
                'author': book['author'],
                'genre': book['genre'],
                'price': book['price'],
                'image': book['image'],
                'mimetype': book['mimetype'],
                'description': book.get('description', 'A captivating book that will keep you engaged from start to finish.'),
                '_id': book['_id']
            })
    
    return render_template('index.html', data=data, count=count, featured_books=featured_books)

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
    return render_template('Profile.html')

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
    name=request.form['bookname']
    author=request.form['author']
    genre=request.form['genre']
    price=request.form['price']
    chooseFile=request.files['image']
    doc=secure_filename(chooseFile.filename)
    chooseFile.save(app.config['uploads']+'/'+doc)
    di={}
    di['title']=name
    di['genre']=genre
    di['author']=author 
    di['price']=int(price)
    di['image']=chooseFile.filename
    di['mimetype'] = chooseFile.mimetype.split('/')[-1]
    stock.insert_one(di) 
    return render_template('Book.html',status="book inserted")


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

if __name__=="__main__":
    app.run(debug=True)