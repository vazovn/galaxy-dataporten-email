
from flask import Flask, render_template, request, g, session, flash, redirect, url_for, send_from_directory, render_template_string
from flask_mail import Mail
from flask_mail import Message

from authomatic.providers import oauth2
from authomatic.extras.flask import FlaskAuthomatic

import ConfigParser

import os.path
import random
import string
import sys

from sqlalchemy import create_engine, Column, Integer, String, Boolean
from sqlalchemy.orm import scoped_session, sessionmaker
from sqlalchemy.ext.declarative import declarative_base

from itsdangerous import URLSafeTimedSerializer

def create_random_string(length=10):
    return "".join(random.choice(string.lowercase) for i in range(length))

config = ConfigParser.ConfigParser()
if os.path.isfile(sys.path[0] + '/config.cfg'):
    config.read(sys.path[0] + '/config.cfg')
else:
    config.add_section('dp')
    config.set('dp', 'consumer_key', '')
    config.set('dp', 'consumer_secret', '')
    config.add_section('secrets')
    config.set('secrets', 'app_secret_key', create_random_string())
    config.set('secrets', 'ser_secret_key', create_random_string())
    config.set('secrets', 'salt', create_random_string())
    config.add_section('db')
    config.set('db', 'uri', '')
    config.add_section('senders')
    config.set('senders', 'lifeportal', 'lifeportal-help@usit.uio.no')
    config.add_section('sendersname')
    with open(sys.path[0] + '/config.cfg', 'wb') as configfile:
        config.write(configfile)

if not config.get('dp', 'consumer_key'):
    raise ValueError("Please fill in config.cfg")

# setup flask
app = Flask(__name__, static_url_path='/static')
app.config.update(
    DATABASE_URI = config.get('db', 'uri'),
    # '''sqlite:///flask-openid.db',
    SECRET_KEY = config.get('secrets', 'app_secret_key'),
    DEBUG = True,
)


dp = FlaskAuthomatic(
    config={
        'dp': {
            'class_': oauth2.Dataporten,
            'consumer_key': config.get('dp', 'consumer_key'),
            'consumer_secret': config.get('dp', 'consumer_secret')
        }
    },
    secret=app.config['SECRET_KEY'],
    debug=True,
)

# setup Mail

mail = Mail(app)

# setup sqlalchemy
engine = create_engine(app.config['DATABASE_URI'])
db_session = scoped_session(sessionmaker(autocommit=False,
                                         autoflush=True,
                                         bind=engine))
Base = declarative_base()
Base.query = db_session.query_property()

def init_db():
    Base.metadata.create_all(bind=engine)

class User(Base):
    __tablename__ = 'usersnew'
    id = Column(Integer, primary_key=True)
    id_url = Column(String(200))
    email = Column(String(200))
    email_confirmed = Column(Boolean)
    conf_token = Column(String(200))
    # salt = Column(String(200))
    openid = Column(String(200))

    def __init__(self, id_url, email, openid):
        self.id_url = id_url
        self.email = email
        # self.salt = create_random_string()
        self.conf_token = create_random_string()
        self.email_confirmed = False
        self.openid = openid

def secret_key():
    return "secret key"

def gen_conf_token(conf_string):
    serializer = URLSafeTimedSerializer(app.config['SECRET_KEY'])
    return serializer.dumps(conf_string, salt=config.get('secrets', 'salt'))

def read_conf_token(token, expiration=3600):
    serializer = URLSafeTimedSerializer(app.config['SECRET_KEY'])
    try:
        conf_token = serializer.loads(
            token,
            salt=config.get('secrets', 'salt'),
            max_age=expiration
        )
    except:
        return False
    print "Conf token", conf_token
    print "token", token
    return conf_token

@app.route('/confirm/<token>')
def confirm_email(token):
    print "token:", token
    conf_token = read_conf_token(token)
    print conf_token
    print token
    user = User.query.filter_by(conf_token=conf_token).first()
    print user.email
    print user
    if user.email_confirmed:
        flash('Already confirmed.', 'success')
    else:
        user.email_confirmed = True
        db_session.add(user)
        db_session.commit()
    return redirect(url_for('confirmed'))

def get_bodytext(conf_token):
    email_file = sys.path[0] + "/email-template.txt"
    if request.args.get('service') == 'lifeportal':
        email_file = sys.path[0] + "/email-lifeportal.txt"
    with open (email_file) as f:
        bodytext = f.read()
    bodytext = render_template_string(bodytext,
                                      url=config.get('general', 'url'),
                                      token=gen_conf_token(conf_token))
    return bodytext

def get_sender():
    """
    :return: tuple if both sender and sender name is set, else string
    """
    email = config.get('senders',
                       request.args.get('service') or "default")
    name = None
    if config.has_option('sendersname',
                       request.args.get('service') or "default"):
        name = config.get('sendersname',
                          request.args.get('service') or "default")
    if name:
        return name, email
    return email

def send_email(to, subject, body):
    msg = Message(
        subject,
        recipients=[to],
        body=body,
        sender=config.get('senders',
               request.args.get('service') or "default")
    )
    mail.send(msg)

@app.before_request
def lookup_current_user():
    g.user = None
    if 'dp' in session:
        dp = session['dp']
        g.user = dp.result.user
        # g.user = User.query.filter_by(openid=dp.result).first()

@app.after_request
def after_request(response):
    db_session.remove()
    return response

@app.route('/')
def index():
    # print "Service:", request.args.get('service')
    return render_template('index.html')

@app.route('/login')
@dp.login('dp')
def login():
    if dp.result:
        if dp.result.error:
            return dp.result.error.message
        elif dp.result.user:
            if not (dp.result.user.name and dp.result.user.id):
                dp.result.user.update()
            print "Redirects to: {}".format(request.args.get("next"))
            return redirect(url_for('create_profile'))
            # return jsonify(name=dp.result.user.name, id=dp.result.user.id)
    else:
        return dp.response

@app.route('/email-sent')
def email_sent():
    return render_template('email-sent.html')

@app.route('/confirmed')
def confirmed():
    return render_template('confirmed.html')

@app.route('/create-profile', methods=['GET', 'POST'])
def create_profile():
    print u"Create profile for {}".format(dp.result.user.name)
    if not dp.result.user: # or 'openid' not in session:
        return redirect(url_for('index'))
    if request.method == 'POST':
        id_url = request.form['id_url']
        email = request.form['email']
        if '@' not in email:
            flash(u'Error: Email is required')
        elif not id_url:
            flash(u'No OpenID identity url')
        else:
            flash(u'Registered')
            user = User(id_url, email, dp.result.user.id)
            db_session.add(user)
            db_session.commit()
            send_email(user.email,
                       config.get('general', 'email_subject'),
                       get_bodytext(user.conf_token))
            print "E-post sent"
            return redirect(url_for('email_sent'))
    return render_template('create_profile.html')

@app.route('/edit-profile', methods=['GET', 'POST'])
def edit_profile():
    return render_template('edit_profile.html', form=None)

@app.route('/<path:filename>')
def send_css(filename):
    return send_from_directory('static', filename)

if __name__ == '__main__':
    init_db()
    app.run()
