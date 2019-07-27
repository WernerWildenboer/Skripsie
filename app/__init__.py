"""
Semantic description:
Scripts that navigate routes and direct the user, also
handels file transfers.
"""
import flask_login
import os
import errno
from flask import render_template, redirect, url_for,  flash, request, json, Flask, session
from flask_login import current_user, logout_user, login_required, LoginManager, UserMixin, login_user
from py2neo import Graph, NodeMatcher, Node, Relationship
from flask_bcrypt import Bcrypt
from config import Config
# from .forms import LoginForm, RegistrationForm

appvar = Flask(__name__)
appvar.config.from_object(Config)
appvar.secret_key = 'some_secret'

resource_path = os.path.join(appvar.root_path, 'static')
appvar.config.from_object(Config)

ALLOWED_EXTENSIONS = set(['csv', 'jpg', 'jpeg', 'png'])

login_var = LoginManager(appvar)
login_var.login_view = 'login'

"""
Set up Neo4j connection.
"""

NEO4J_BOLT = os.environ["NEO4J_BOLT"] if "NEO4J_BOLT" in os.environ else 'bolt://localhost:7687'
NEO4J_USERNAME = os.environ["NEO4J_USERNAME"] if "NEO4J_USERNAME" in os.environ else 'neo4j'
NEO4J_PASSWORD = os.environ["NEO4J_PASSWORD"] if "NEO4J_PASSWORD" in os.environ else 'skripsie'
GRAPH_INIT = Graph(NEO4J_BOLT, auth=(NEO4J_USERNAME, NEO4J_PASSWORD))
"""
Set up bcrypt.
"""
bcrypt = Bcrypt(appvar)

"""
Set login manger.
"""
login_manager = flask_login.LoginManager()
login_manager.session_protection = 'strong'
login_manager.init_app(appvar)


def neo4j_connect(neo4j_bolt, neo4j_usrname, neo4j_password):
    """
    Establishes neo4j connection.
    """
    graph_init = Graph(neo4j_bolt, auth=(neo4j_usrname, neo4j_password))
    return graph_init


class UserMain(UserMixin):
    """
    User class
    """

    def __init__(self, id, active=True):
        self.id = id
        self.active = active

    def is_active(self):
        # Here you should write whatever the code is
        # that checks the database if your user is active
        return self.active

    def is_anonymous(self):
        return False

    def is_authenticated(self):
        return True

    def find_user(self):
        create_user_cypher = "MATCH (a: User {user_id:'%s' }) RETURN a;" % (
            self.id)
        user_loaded = GRAPH_INIT.run(create_user_cypher).data()
        if user_loaded:
            # user_loaded[0]['a']['username']
            user_loaded = user_loaded[0]
            return user_loaded
        return None

    def verify_password(self, password_in):
        user = self.find_user()
        if user:
            return bool(bcrypt.check_password_hash(user['a']['password'], password_in))
        else:
            return False


@login_manager.user_loader
def load_user(userid):
    """
    Loads user.
    """
    return UserMain(userid)


@appvar.route('/gallery_json', endpoint='gallery_json2')
def gallery_json2():
    """
    Semantic description:
        # TODO: step by step description
    Returns: a json containing all the image information

    Gets the json file stored at `appvar.root_path` reads
    the data and returns it.
    """
    json_path = os.path.join(appvar.root_path, 'gallery_json.js')
    gallery_json_var = open(json_path).read()
    return json.dumps(gallery_json_var)


@appvar.route('/uploadfile', methods=['GET', 'POST'])
@login_required
def uploadfile():
    """
    Semantic description:
        # TODO: step by step description
    Returns: a redirection url to index.html

    Gets the audio file sent by ajax from submit in audio.js
    and downloads to the static audio folder also runs
    update_kg_audio and renders audio_capturing.html.

    The fuction also passes data on to update_kg_audio.
    """
    if request.method == 'POST':
        file_var = request.files['file']
        audio_path = os.path.join(
            appvar.root_path, "static", "audio", session['username'], file_var.filename)
        # Creates users dir if it does not exist
        session['file_location'] = audio_path
        if not os.path.exists(os.path.dirname(audio_path)):
            try:
                os.makedirs(os.path.dirname(audio_path))
            except OSError as exc:  # Guard against race condition
                if exc.errno != errno.EEXIST:
                    raise
        file_var.save(audio_path)

        # Populates update_kg_audio
        username = session['username']
        create_get_user_cypher = "MATCH (a: User {username:'%s' }) RETURN a;" % (
            username)
        user_loaded = GRAPH_INIT.run(create_get_user_cypher).data()
        language = user_loaded[0]['a']['language']

        image_title = audio_path.split('_')[1]

        file_location = audio_path

        update_kg_audio(username, image_title, language, file_location)

        return redirect(url_for('audio_capturing'))
    # TODO : look at print
    return redirect(url_for('audio_capturing'))


@appvar.route('/audio_capturing', methods=['GET', 'POST'])
@login_required
def audio_capturing():
    """
    Semantic description:
    Returns: a redirection url to audio_capturing.html
    that ingests audio clip tags from the user.
    """
    return render_template('audio_capturing.html', title='Audio Capturing')


def update_kg_audio(username, image_title, language, file_location):
    """
    Returns:
    Ingests audio clips from user and updates
    the neo4j database.
    """
    create_user_audio_cypher = (("MATCH (a: User {username:'%s' }),"
                                 "(b: Image {image_title:'%s' })"
                                 "MERGE (c: Metadata {username:'%s',language:'%s',file_location:'%s',image_title:'%s'})"
                                 "MERGE (c)<-[:LABELLED]-(a)"
                                 "MERGE (c)-[:BELONGSTO]->(b)") % (username, image_title, username, language, file_location, image_title))

    GRAPH_INIT.run(create_user_audio_cypher)
    return True


@appvar.route('/')
@appvar.route('/index')
def index():
    """
    Semantic description:
    Returns: a redirection url to index.html
    """
    return render_template('index.html', title='Home')


@appvar.route('/login', methods=['GET', 'POST'])
def login():
    """
    Renders login.html :
    POST:
        Gets username and password from user
        inputs and checks it against neo4j DB
        stored values:
            if found-> checks if password match
                    -> If user exists
    """
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user_id = username.split()[0][0]

        if not UserMain(user_id).verify_password(password):
            flash('Invalid login.')
            return redirect(url_for('login'))
        else:
            flash('Logged in.')
            session['logged_in'] = True
            user = UserMain(user_id)
            session['username'] = username

            login_user(user, remember=True)
            return redirect(url_for('index'))
    return render_template('login.html', title='Sign In')


@appvar.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))


@appvar.route('/register', methods=['GET', 'POST'])
def register():
    """
    Renders register.html :
    POST:
        Gets all of the users information
        and sends it to neo4j to create a
        user node.
    """
    if request.method == 'POST':
        # User input variables
        username = request.form['username']
        password = request.form['psw']
        email = request.form['email']
        gender = request.form['gender']
        location = request.form['location']
        language = request.form['language']
        age = request.form['age']
        user_id = username.split()[0][0]

        # User input checks
        # TODO: Change strings
        if len(username) < 5:
            flash('Your email must be at least one character.')
        if len(password) < 5:
            flash('Your username must be at least one character.')
        elif len(email) < 5:
            flash('Your password must be at least 5 characters.')
        elif len(gender) < 1:
            flash('Your username must be at least one character.')
        elif len(location) < 1:
            flash('Your username must be at least one character.')
        elif len(language) < 1:
            flash('Your username must be at least one character.')
        elif len(age) < 1:
            flash('Your username must be at least one character.')
        # elif not User(username).register(email, password):
        #    flash('A user with that username or email already exists.')
        else:
            # session['username'] = username
            # flash('Logged in.')

            pw_hash = bcrypt.generate_password_hash(password)
            pw_hash_decoded = pw_hash.decode("utf-8")
            pw_hash_cleaned = pw_hash_decoded.replace('\'', '')

            create_user_cypher = "MERGE (a: User {password:'%s',username:'%s',password:'%s',gender:'%s',location:'%s',language:'%s',age:'%s',user_id:'%s' })" % (
                email, username, pw_hash_cleaned, gender, location, language, age, user_id)
            GRAPH_INIT.run(create_user_cypher)
            return redirect(url_for('index'))

    return render_template('register.html', title='Register')


@appvar.route('/secret')
@login_required
def hidden_page():
    return render_template('secret.html', title="Super Secret",
                           user=current_user)


def allowed_file(filename):
    return '.' in filename
    filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@appvar.route('/upload', methods=['GET', 'POST'])
def upload_page():
    if request.method == "POST":
        if 'file' not in request.files:
            flash("No file attached")
            return redirect(request.url)

        file = request.files['file']

        if file.filename == "":
            flash("No file attached")
            return redirect(request.url)

        if file and allowed_file(file.filename):
            flash("Successfully uploaded!")
            flash(file.filename)

            # Consider saving the file
            # fname, ext = os.path.splitext(file.filename)
            # fname_rand = fname + str(uuid.uuid4()) + ext
            # filename = secure_filename(fname_rand)
            # file.save(os.path.join(appvar.config["UPLOAD_FOLDER"], filename))

    return render_template('upload.html', title="Upload Form Example")


if __name__ == '__main__':
    appvar.run()
