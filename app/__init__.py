"""
Semantic description:
Scripts that navigate routes and direct the user, also
handels file transfers.
"""
# TODO: Split up in to different files
# TODO: Add abort / error handeling

import datetime
import errno
import os
import sys
import uuid

import librosa
import numpy as np
from flask import (
    Flask,
    flash,
    json,
    redirect,
    render_template,
    request,
    session, url_for
)
from flask_bcrypt import Bcrypt
import flask_login
from flask_login import (
    LoginManager,
    UserMixin,
    current_user,
    login_required,
    login_user, logout_user
)
from PIL import Image
from py2neo import Graph, Node, NodeMatcher, Relationship
from resizeimage import resizeimage
from werkzeug.utils import secure_filename

from config import Config

# from .forms import LoginForm, RegistrationForm

appvar = Flask(__name__)
appvar.config.from_object(Config)
appvar.secret_key = 'some_secret'
# set the port dynamically with a default of 3000 for local development
port = int(os.getenv('PORT', '3000'))

resource_path = os.path.join(appvar.root_path, 'static')


ALLOWED_EXTENSIONS = set(['csv', 'jpg', 'jpeg', 'png'])

login_var = LoginManager(appvar)
login_var.login_view = 'login'

"""
Set up Neo4j connection.
"""

NEO4J_BOLT = os.environ["NEO4J_BOLT"] if "NEO4J_BOLT" in os.environ else 'bolt://localhost:11005'
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
        """
        Initializes user.
        """
        self.id = id
        self.active = active

    def is_active(self):
        """
        Returns user is active status.
        """
        # Here you should write whatever the code is
        # that checks the database if your user is active
        return self.active

    def is_anonymous(self):
        """
        Returns False.
        """
        return False

    def is_authenticated(self):
        """
        Returns True.
        """
        return True

    def find_user(self):
        """
        Verifies if the entered password the user has entered is the same
        as the one from the KG db.
        """
        create_user_cypher = "MATCH (a: User {user_id:'%s' }) RETURN a;" % (
            self.id)
        user_loaded = GRAPH_INIT.run(create_user_cypher).data()
        if user_loaded:
            # user_loaded[0]['a']['username']
            user_loaded = user_loaded[0]
            return user_loaded
        return None

    def verify_password(self, password_in):
        """
        Retrieves a user from the KG based on the user_id.
        """
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


@appvar.route('/gallery_json', endpoint='gallery_json_end_point')
# Reason for rename,there was an endpoint probl
def gallery_json_end_point():
    """
    Semantic description:
        # TODO: step by step description
    Returns: a json containing all the image information

    Gets the json file stored at `appvar.root_path` reads
    the data and returns it.
    """
    json_path = os.path.join(appvar.root_path, 'gallery.json')
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

        session['file_location'] = audio_path
        session['file_name'] = file_var.filename
        # Creates users dir if it does not exist
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

        to_mfcc(audio_path)
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
    """
    Logs the user out of the system
    """
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
    if current_user.is_authenticated:
        # TODO: Add already logged in page
        return redirect(url_for('index'))
    if request.method == 'POST':
        # TODO: Add language used and first language
        # User input variables
        username = request.form['username']
        password = request.form['psw']
        email = request.form['email']
        gender = request.form['gender']
        location = request.form['location']
        firstlanguage = request.form['firstlanguage']
        inputlanguage = request.form['inputlanguage']
        age = request.form['age']
        user_id = username.split()[0][0]
        print(gender)
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
        elif len(firstlanguage) < 1:
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

            create_user_cypher = "MERGE (a: User {password:'%s',username:'%s',password:'%s',gender:'%s',location:'%s',first_language:'%s',input_language:'%s',age:'%s',user_id:'%s' });" % (
                email, username, pw_hash_cleaned, gender, location, firstlanguage, inputlanguage, age, user_id)
            print(create_user_cypher)
            GRAPH_INIT.run(create_user_cypher)
            return redirect(url_for('index'))

    return render_template('register.html', title='Register')


@appvar.route('/secret')
@login_required
def hidden_page():
    """
    Secret page for adventures users.
    """
    return render_template('secret.html', title="Super Secret",
                           user=current_user)


def allowed_file(filename):
    """
    Returns extensions of what files are allowed
    """
    return '.' in filename
    filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@appvar.route('/upload', methods=['GET', 'POST'])
@login_required
def upload_page():
    """
    Renders upload.html.
    POST: GETS uploaded file loaded by the user
    resizes it and sends it to the backend for storage.

    """
    if request.method == "POST":
         # User input variables
        album = request.form['album']
        title_of_image = request.form['title_of_image']
        description = request.form['description']

        if 'file' not in request.files:
            flash("No file attached")
            return redirect(request.url)
        i = 0
        for f in request.files.getlist('file'):
            i = i+1
            file = f
            if file.filename == "":
                flash("No file attached")
                return redirect(request.url)

            if file and allowed_file(file.filename):

                fname, ext = os.path.splitext(file.filename)
                name_rand = str(i)+"_" + title_of_image + \
                    "_" + fname + str(uuid.uuid4()) + ext
                filename = secure_filename(name_rand)

                album_name = album
                # Upload file store location file path
                uploadfile_path = os.path.join(
                    appvar.root_path, "static", "images", session['username'], album_name, filename)
                # Creates users dir if it does not exist
                if not os.path.exists(os.path.dirname(uploadfile_path)):
                    try:
                        os.makedirs(os.path.dirname(uploadfile_path))
                    except OSError as exc:  # Guard against race condition
                        if exc.errno != errno.EEXIST:
                            raise
                # Save file
                file.save(os.path.join(uploadfile_path))
                # Resize image and create thumbnail
                filename_thumbnail = str(i)+"_"+title_of_image+"_" + \
                    "_thumbnail_" + fname + str(uuid.uuid4()) + ext
                filename_thumbnail_secure = secure_filename(filename_thumbnail)

                uploadfile_path_thumbnail = os.path.join(
                    appvar.root_path, "static", "images", session['username'], album_name, filename_thumbnail_secure)
                with Image.open(file) as image:
                    cover = resizeimage.resize_cover(image, [180, 180])
                    cover.save(os.path.join(
                        uploadfile_path_thumbnail), image.format)

                # TODO: Send to json formatter

                # Update KG
                # Clean URL's
                uploadfile_path_short = os.path.join(
                    "images", session['username'], album_name, filename)
                uploadfile_path_thumbnail_short = os.path.join(
                    "images", session['username'], album_name, filename_thumbnail_secure)

                update_kg_image(filename, description, album_name,
                                uploadfile_path_short, uploadfile_path_thumbnail_short)

    return render_template('upload.html', title="Upload Form Example")

# TODO: Shorten


def update_kg_image(image_name, description, album, image_location,
                    image_thumbnail_location):
    """
    Returns:
    Ingests image from user and updates
    the neo4j database (representing image as a node).
    """
    # TODO: add file name cleaner 's => \'s
    title = image_name.split("_")
    title_multiple = title[0]+"_"+title[1]
    title_thumbnail = title[0]+"_"+title[1]+"_thumbnail"
    username = session['username']
    image_upload_name = ' '.join(title[2:])
    create_image_cypher = (("MERGE (a: Image {uploaded_by_user:'%s',image_title_given:'%s',"
                            "image_title_thumbnail:'%s',"
                            "description:'%s',album:'%s',image_location:'%s',"
                            "image_thumbnail_location:'%s',image_title_long:'%s',image_title:'%s'})")
                           % (username, title_multiple, title_thumbnail, description, album,
                              image_location, image_thumbnail_location, image_name, image_upload_name))

    GRAPH_INIT.run(create_image_cypher)
    return True


def generate_gallery_json(album, title_of_image, description, url, thumb_url, file_path):
    """
    Converts image meta data to json that the gallery functions
    requires to load the carousel

    Creates : <album>_<date>.json
    """
    # TODO: Use KG to generate data
    # file_path
    now = datetime.datetime.now()
    date_time = now.strftime("%m/%d/%Y, %H:%M:%S")
    gallery_file_json_output_album = {}
    gallery_file_json_output_photos = {}

    gallery_file_json_output_album["name"] = album

    gallery_file_json_output_photos['id'] = "1"
    gallery_file_json_output_photos['url'] = url
    gallery_file_json_output_photos['thumb_url'] = thumb_url
    gallery_file_json_output_photos['title'] = title_of_image
    gallery_file_json_output_photos['date'] = date_time
    gallery_file_json_output_photos['description'] = description

    listoflists = []
    listoflists.append(gallery_file_json_output_photos)
    listoflists.append(gallery_file_json_output_photos)
    print(listoflists)
    merged = {}
    merged["album"] = gallery_file_json_output_album
    merged["photos"] = listoflists

    with open("gallery.json", "w") as f:
        json.dump(merged, f, indent=4)

    return json.dumps(merged, indent=4)


def to_mfcc(audio_file_path):
    """
    Convert audio to MFCC and stores in a matrix.
    Exports matrix as '.txt'.
    """
    y, sr = librosa.load(audio_file_path)
    # Let's make and display a mel-scaled power (energy-squared) spectrogram
    S = librosa.feature.melspectrogram(y, sr=sr, n_mels=128)

    # Convert to log scale (dB). We'll use the peak power (max) as reference.
    log_S = librosa.power_to_db(S, ref=np.max)
    # Next, we'll extract the top 13 Mel-frequency cepstral coefficients (MFCCs)
    mfcc = librosa.feature.mfcc(S=log_S, n_mfcc=13)

    # Let's pad on the first and second deltas while we're at it
    delta_mfcc = librosa.feature.delta(mfcc)
    delta2_mfcc = librosa.feature.delta(mfcc, order=2)

    # For future use, we'll stack these together into one matrix
    # .txt
    mfcc_matrix = np.vstack([mfcc, delta_mfcc, delta2_mfcc])

    mfcc_file_name_txt = 'MFCC_'+session['file_name'][:-4] + '.txt'

    mfcc_path_txt = os.path.join(
        appvar.root_path, "static", "audio", session['username'], mfcc_file_name_txt)
    f = open(mfcc_path_txt, "w")
    np.savetxt(f, mfcc_matrix, fmt='%1.10f')
    f.close()

    # .csv
    mfcc_file_name_csv = 'MFCC_'+session['file_name'][:-4] + '.csv'

    mfcc_path_csv = os.path.join(
        appvar.root_path, "static", "audio", session['username'], mfcc_file_name_csv)
    np.savetxt(mfcc_path_csv, mfcc_matrix, delimiter=",")

    return mfcc_matrix


@appvar.route('/audio_labeling', methods=['GET', 'POST'])
@login_required
def audio_labeling():
    """
    Used by Audiophile to lable audio files, and
    renders audioLabeling.html.
    Exports matrix as '.txt'.
    """

    return render_template('audio_labeling.html', title="Audio Labler")

    # TODO: Beautify comments


"""
┌──────────────────────────────────────────────┐
│               Error Handeling                │
└──────────────────────────────────────────────┘
"""


@appvar.errorhandler(401)
def page_unauthorized(error):
    """
    Renders 401.html when a Page is unauthorized.
    """
    print(error)
    return render_template('401.html'), 401


@appvar.errorhandler(403)
def page_forbidden(error):
    """
    Renders 403.html when a Page is forbidden.
    """
    print(error)
    return render_template('403.html'), 403


@appvar.errorhandler(404)
def page_not_found(error):
    """
    Renders 404.html when a Page was not found.
    """
    print(error)
    return render_template('404.html'), 404


@appvar.errorhandler(410)
def page_deleted(error):
    """
    Renders 410.html when a Page was deleted.
    """
    print(error)
    return render_template('410.html'), 410


@appvar.errorhandler(500)
# TODO: add contact admin
def page_error(error):
    """
    Renders 500.html when a Internal Server Error occurs.
    """
    print(error)
    return render_template('500.html'), 500


if __name__ == '__main__':
    # appvar.run(debug=True)
    # TODO : change port
    appvar.run(ost='0.0.0.0', port=port)
