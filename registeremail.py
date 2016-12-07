
from flask import Flask, render_template, request, g, session, flash, redirect, url_for, abort
from flask_mail import Mail
# from flask_openid import OpenID
from flask.ext.oidc import OpenIDConnect
from flask.ext.mail import Message

from pkg_resources import resource_filename

from sqlalchemy import create_engine, Column, Integer, String, Boolean
from sqlalchemy.orm import scoped_session, sessionmaker
from sqlalchemy.ext.declarative import declarative_base

from itsdangerous import URLSafeTimedSerializer

# setup flask
app = Flask(__name__)
app.config.update(
    DATABASE_URI = 'sqlite:///flask-openid.db',
    SECRET_KEY = 'dev key',
    DEBUG = True,
)
app.config.update({
    'OIDC_CLIENT_SECRETS': resource_filename(__name__, 'client_secrets.json'),
    'SECRET_KEY': 'SomethingNotEntirelySecret',
    'TESTING': True,
    'DEBUG': True,
    'OIDC_ID_TOKEN_COOKIE_SECURE': False,
    'OIDC_REQUIRE_VERIFIED_EMAIL': False,
    'OIDC_OPENID_REALM': 'http://localhost:5000/oidc_callback'
})

# setup flask-openid
# oid = OpenID(app, safe_roots=[])
oid = OpenIDConnect(app)

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
    __tablename__ = 'usersnew3'
    id = Column(Integer, primary_key=True)
    id_url = Column(String(200))
    email = Column(String(200))
    email_confirmed = Column(Boolean)
    conf_token = Column(String(200))
    salt = Column(String(200))
    openid = Column(String(200))

    def __init__(self, id_url, email, openid):
        self.id_url = id_url
        self.email = email
        self.salt = create_salt()
        self.conf_token = gen_conf_token(self.email, self.salt)
        self.email_confirmed = 'N'
        self.openid = openid

def create_salt():
    return "saltesalte"

def secret_key():
    return "secret key"

def gen_conf_token(email, salt):
    serializer = URLSafeTimedSerializer(secret_key())
    return serializer.dumps(email, salt=salt)

def read_conf_token(token, expiration=3600):
    serializer = URLSafeTimedSerializer(secret_key())
    try:
        email = serializer.loads(
            token,
            salt=app.config['SECURITY_PASSWORD_SALT'],
            max_age=expiration
        )
    except:
        return False
    return email

@app.route('/confirm/<token>')
def confirm_email(token):
    try:
        email = read_conf_token(token)
    except:
        flash('The confirmation link is invalid or has expired.', 'danger')
    user = User.query.filter_by(email=email).first_or_404()
    if user.email_confirmed:
        flash('Already confirmed.', 'success')
    else:
        user.email_confirmed = True
        db_session.add(user)
        db_session.commit()
        flash('You have confirmed your email.', 'success')
    return redirect(url_for('index'))

def get_bodytext(conf_token):
    return "Foo bar baz\n\n{}\n\nbaz bar foo".format("ting")

def send_email(to, subject, body):
    msg = Message(
        subject,
        recipients=[to],
        body=body,
        sender="tt@ulrik.uio.no"
    )
    mail.send(msg)

@app.before_request
def lookup_current_user():
    g.user = None
    if 'openid' in session:
        openid = session['openid']
        g.user = User.query.filter_by(openid=openid).first()

@app.after_request
def after_request(response):
    db_session.remove()
    return response

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login')
@oid.require_login
def login():
    info = oid.user_getinfo(['email', 'openid_id'])
    return ('Hello, %s (%s)! <a href="/">Return</a>' %
(info.get('email'), info.get('openid_id')))
# def login():
#     if g.user is not None:
#         return redirect(oid.get_next_url())
#     if request.method == 'POST':
#         # openid = request.form.get('openid')
#
#         if openid:
#             return oid.try_login(openid, ask_for=['email'])
#     return render_template('login.html', next=oid.get_next_url(),
# error=oid.fetch_error())

# @oid.after_login
def create_or_login(resp):
    session['openid'] = resp.identity_url
    user = User.query.filter_by(openid=resp.identity_url).first()
    if user is not None:
        flash(u'Successfully signed in')
        g.user = user
        return redirect(oid.get_next_url())
    print "====="
    print resp.identity_url
    return redirect(url_for('create_profile', next=oid.get_next_url(),
                            id_url=resp.identity_url,
                            email=resp.email))

@app.route('/create-profile', methods=['GET', 'POST'])
def create_profile():
    if g.user is not None or 'openid' not in session:
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
            user = User(id_url, email, session['openid'])
            db_session.add(user)
            db_session.commit()
            send_email(user.email, "foobar", get_bodytext(user.conf_token))
            return redirect(oid.get_next_url())
    return  render_template('create_profile.html', next_url=oid.get_next_url())

@app.route('/edit-profile', methods=['GET', 'POST'])
def edit_profile():
    return render_template('edit_profile.html', form=None)

@app.route('/logout')
def logout():
    session.pop('openid', None)
    flash(u'You have been logged out')
    return redirect(oid.get_next_url())

if __name__ == '__main__':
    init_db()
    app.run()
