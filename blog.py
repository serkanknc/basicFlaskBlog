from flask import Flask,render_template,flash,redirect,url_for,session,logging,request
from flask_mysqldb import MySQL
from wtforms import Form,StringField,TextAreaField,PasswordField,validators
from passlib.hash import sha256_crypt
from functools import wraps

#Kullanıcı Giriş Decorator
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "logged_in" in session:
            return f(*args, **kwargs)
        else:
            flash("Bu sayfayı görüntülemek için giriş yapınız.","danger")
            return redirect(url_for("login"))
    return decorated_function

#APP CONFIGURATION
app = Flask(__name__)
app.secret_key = ("blog-secret")

app.config["MYSQL_HOST"] = "localhost"
app.config["MYSQL_USER"] = "root"
app.config["MYSQL_PASSWORD"] = ""
app.config["MYSQL_DB"] = "blogdb"
app.config["MYSQL_CURSORCLASS"] = "DictCursor"

mysql = MySQL(app)

#index
@app.route("/")
def index():
    return render_template('index.html')

#about
@app.route("/about")
def about():
    return render_template("about.html")


#Kullanıcı Kayıt Formu
class RegisterForm(Form):
    name = StringField("Name",validators=[validators.length(min=4,max=25)])
    username = StringField("Username",validators=[validators.length(min=5,max=20),validators.DataRequired(message="Lütfen bir kullanıcı adı giriniz")])
    email = StringField("Email",validators=[validators.Email(message="Lütfen geçerli bir Email adresi giriniz"),validators.DataRequired(message="Lütfen bir Email adresi giriniz")])
    password = PasswordField("Password",validators=[
        validators.DataRequired(message="Lütfen bir parola belirleyin."),
        validators.EqualTo(fieldname="confirm",message="Parolanız uyuşmuyor.")
    ])
    confirm = PasswordField("Password Confirm")

#Register
@app.route("/register", methods=["GET","POST"])
def register():
    form = RegisterForm(request.form)

    if request.method == "POST" and form.validate():
        name = form.name.data
        username = form.username.data
        email = form.email.data
        password = sha256_crypt.encrypt(form.password.data)

        cursor = mysql.connection.cursor()
        sorgu = ("select * from users where username = %s or email = %s")
        cursor.execute(sorgu,(username,email))
        data = cursor.fetchone()
        
        if data:
            db_username = data["username"]
            db_email = data["email"]
            if db_email == email or db_username == username:
                flash("Kullanıcı adı veya email bu sistemde zaten kayıtlı", "warning")
                return redirect(url_for("register"))
                
            else:
                db_username = None
                db_email = None
        else:
            sorgu2 = ("INSERT INTO users (name,email,username,password) VALUES (%s,%s,%s,%s)")
            cursor.execute(sorgu2,(name,email,username,password))
            mysql.connection.commit()
            cursor.close()
            flash("Başarıyla kayıt oldunuz","success")

            return redirect(url_for("login"))
    else:
        return render_template("register.html",form=form)

#LoginForm
class LoginForm(Form):
    username = StringField("Username")
    password = PasswordField("Password")

#Login
@app.route("/login",methods=["GET", "POST"])
def login():

    form = LoginForm(request.form)

    if request.method == "POST":
        username = form.username.data
        password_entered = form.password.data
        cursor = mysql.connection.cursor()
        sorgu = "select * from users where username = %s"
        result = cursor.execute(sorgu,(username,))
        if result > 0:
            data = cursor.fetchone()
            real_password = data["password"]
            if sha256_crypt.verify(password_entered,real_password):
                flash("Kullanıcı girişi başarılı","success")

                session["logged_in"] = True
                session["username"] = username

                return redirect(url_for("index"))
            else:
                flash("Hatalı Şifre","danger")
                return redirect(url_for("login"))
        else:
            flash("Böyle bir kullanıcı bulunamadı","danger")
            return redirect(url_for("login"))

    return render_template("login.html",form=form)

#Logout
@app.route("/logout")
def logout():
    session.clear()
    flash("Çıkış başarılı","warning")
    return redirect(url_for("index"))

#Dashboard
@app.route("/dashboard")
@login_required
def dashboard():
    cursor = mysql.connection.cursor()
    sorgu = ("select * from articles where author = %s")
    result = cursor.execute(sorgu,(session["username"],))
    if result > 0:
        articles = cursor.fetchall()
        return render_template("dashboard.html",articles = articles)
    else:

        return render_template("dashboard.html")

#Makale Form
class ArticleForm(Form):
    title = StringField("Makale Başlığı",validators=[validators.length(min=10, max=40)])
    content = TextAreaField("Makale İçeriği",validators=[validators.length(min=20)])

#Makale Ekle
@app.route("/addarticle", methods=["GET","POST"])
@login_required
def addarticle():
    form = ArticleForm(request.form)

    if request.method == "POST" and form.validate():
        
        title = form.title.data
        content = form.content.data
        username = session["username"]

        cursor = mysql.connection.cursor()
        sorgu = ("insert into articles (title, author, content) values (%s, %s, %s)")
        cursor.execute(sorgu, (title, username, content))
        mysql.connection.commit()
        cursor.close()

        flash("Makale başarıyla eklendi","success")
        return redirect(url_for("dashboard"))
    
    return render_template("addarticle.html",form = form)

#Makale Sil
@app.route("/delete/<string:id>")
@login_required
def delete(id):
    cursor = mysql.connection.cursor()
    sorgu = ("delete from articles where author = %s and id = %s")
    result = cursor.execute(sorgu,(session["username"],id))

    if result > 0:
        sorgu2 = ("delete from articles where id = %s")
        cursor.execute(sorgu2,(id,))
        mysql.connection.commit()

        return redirect(url_for("dashboard"))
    
    else:
        flash("Böyle bir makale yok veya silmeye yetkiniz yok.","danger")
        return redirect(url_for("index"))

#Makale Güncelle
@app.route("/edit/<string:id>",methods= ["GET","POST"])
@login_required
def update(id):
    if request.method =="GET":#GET REQUEST
        cursor = mysql.connection.cursor()

        sorgu = ("select * from articles where id = %s and author = %s")
        result = cursor.execute(sorgu,(id,session["username"]))

        if result ==0:
            flash("Böyle bir makale yok veya buna yetkiniz yok","danger")
            return redirect(url_for("dashboard"))
        else:
            article = cursor.fetchone()
            form = ArticleForm()

            form.title.data = article["title"]
            form.content.data = article["content"]
            return render_template("update.html",form = form)
    else:#POST REQUEST
        form = ArticleForm(request.form)

        newTitle = form.title.data
        newContent = form.content.data

        cursor = mysql.connection.cursor()
        sorgu2 = ("update articles set title = %s, content = %s where id = %s")
        cursor.execute(sorgu2,(newTitle,newContent,id))
        mysql.connection.commit()
        cursor.close()
        flash("Makale başarıyla güncellendi.","success")
        return redirect(url_for("dashboard"))
#Makale Sayfası
@app.route("/articles")
def articles():
    cursor = mysql.connection.cursor()
    sorgu = "select * from articles"
    result = cursor.execute(sorgu)

    if result > 0:
        articles = cursor.fetchall()
        return render_template("articles.html",articles = articles)
    
#Detay Sayfası
@app.route("/article/<string:id>")
def detail(id):
    cursor = mysql.connection.cursor()
    sorgu = ("select * from articles where id = %s")
    result = cursor.execute(sorgu,(id,))

    if result > 0:
        article = cursor.fetchone()
        return render_template("article.html",article = article)
    else:
        return render_template("article.html")
    
#Makale Ara
@app.route("/search",methods= ["GET","POST"])
def search():
    if request.method=="GET":
        return redirect(url_for("index"))
    else:
        keyword = request.form.get("keyword")
        cursor = mysql.connection.cursor()
        sorgu= ("select * from articles where title like '%"+keyword+ "%'")
        result = cursor.execute(sorgu)
        if result ==0:
            flash("Aranan kelimeye uygun makale bulunamadı.","danger")
            return redirect(url_for("articles"))
        else:
            articles = cursor.fetchall()

            return render_template("articles.html",articles = articles)

if __name__=="__main__":
    app.run(debug=True)