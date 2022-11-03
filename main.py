import gpt_2_simple as gpt2
import os
import multiprocessing as mp
import sys
from flask import Flask, render_template, send_from_directory, jsonify, request
import string
import time
import random
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from sqlalchemy import and_


PROJECT_ROOT = os.path.dirname(os.path.realpath(__file__))
sys.path.append(PROJECT_ROOT)

app = Flask(__name__)

# ----------- db ------------------ #

app.config['SQLALCHEMY_DATABASE_URI'] = ''.join((
    'sqlite:////', os.path.join(PROJECT_ROOT, 'zoe.db')
))
db = SQLAlchemy(app)
migrate = Migrate(app, db)


class Quote(db.Model):
    id = db.Column(
        db.String,
        default=lambda: ''.join([
            random.choice(string.ascii_letters + string.digits) for n in range(15)
        ]),
        primary_key=True
    )
    # poor man's enum. bools don't seem to work in sqlalchemy
    claimed_by_worker = db.Column(db.Integer, default=0)
    prefix = db.Column(db.String, nullable=False)
    temperature = db.Column(db.Float, nullable=False)
    length = db.Column(db.Integer, nullable=False)
    text = db.Column(db.Text)
    upvotes = db.Column(db.Integer, default=0)
    downvotes = db.Column(db.Integer, default=0)
    date = db.Column(db.Float, default=lambda: time.time(), nullable=False)

# ----------- workers ------------- #

PROCESSES = mp.cpu_count()
REST_SECONDS = 5


def queue_quotes():
    for q in quotes:
        QUEUE.put(p)

def generate_next_quote(quote_id):
    print('Worker online')
    with app.app_context():
        quote = Quote.query.filter(Quote.id==quote_id).first()
        if quote is None:
            return
        print(f'Claiming quote {quote}')
        quote.claimed_by_worker = 1
        db.session.add(quote)
        db.session.commit()
        quote.text = load_and_run_model(
            quote.prefix,
            quote.temperature,
            quote.length
        )
        db.session.add(quote)
        db.session.commit()

def work():
    while True:
        with app.app_context():
            quotes = Quote.query.filter(
                Quote.text.is_(None),
                Quote.claimed_by_worker==0
            ).all()
            quotes = [q.id for q in quotes]
        try:
            print('MAIN THREAD STARTING')
            print(f'QUOTES: {len(quotes)}')
            pool = mp.Pool(PROCESSES)
            pool.map(generate_next_quote, quotes)
            pool.close()
            pool.join()
            print('MAIN THREAD SLEEPING')
            time.sleep(REST_SECONDS)
        except Exception as e:
            print(f'Exception in main thread \n {e}')
            print('Ignoring and sleeping')
            time.sleep(REST_SECONDS)

# ----------- web ----------------- #

@app.route('/')
def index():
    is_zoe = request.args.get('is_zoe')
    if is_zoe:
        is_zoe = 'true'
    else:
        is_zoe = 'false'
    return render_template('index.html', is_zoe=is_zoe)

def get_waiting_quote():
    quote = Quote.query.filter(
        Quote.upvotes >= Quote.downvotes
    ).all()
    return_data = {
        'id': None,
        'text': None
    }
    if quote:
        quote = random.choice(quote)
        return_data['id'] = quote.id
        return_data['text'] = quote.text

    return return_data

@app.route('/vote/<string:quote_id>')
def vote(quote_id):
    vote = request.args.get('vote')
    quote = Quote.query.filter(
        Quote.id==quote_id
    ).first()
    if quote is not None:
        if vote == 'up':
            quote.upvotes += 1
            db.session.add(quote)
        elif vote == 'down':
            quote.downvotes += 1
            db.session.add(quote)
        db.session.commit()
    new_quote = get_waiting_quote()
    return jsonify(new_quote)


@app.route('/waiting/<string:quote_id>')
def waiting(quote_id):
    quote = Quote.query.filter(
        Quote.id==quote_id
    ).first()
    result = {
        'success': True,
        'finished': False,
        'wait_time': None,
        'body': None
    }
    if quote is None:
        result['finished'] = True
        result['success'] = False
        result['message'] = 'No such quote'
    else:
        result['success'] = True
        if quote.text is not None:
            result['finished'] = True
            result['body'] = quote.text
        else:
            result['wait_time'] = len(
                Quote.query.filter(
                    and_(
                        Quote.date < quote.date,
                        Quote.text.is_(None)
                    )
                ).all()
            )
    return jsonify(result)


@app.route('/talk', methods=['POST'])
def talk():
    data = request.get_json(force=True)
    is_zoe = data['is_zoe']
    if not is_zoe:
        if data['length'] > 1000:
            return jsonify('Length must be less than 1000')
    q = Quote(
            length=data['length'],
            temperature=data['temperature'],
            prefix=data['prefix'],
        )
    db.session.add(q)
    db.session.commit()
    return jsonify({
        'id': q.id,
        'waiting_quote': get_waiting_quote()
    })

@app.route('/static')
def staticfiles(path):
    return send_from_directory('static', path)

# ----------- model --------------- #

transcripts_fname = 'transcripts.txt'
model_name = "124M"
i = 50
sess = gpt2.start_tf_sess()
gpt2.load_gpt2(sess)

def train_model():
    sess = gpt2.start_tf_sess()
    gpt2.finetune(sess,
                  transcripts_fname,
                  model_name=model_name,
                  steps=i)
    return sess, gpt2

def load_and_run_model(prefix, temperature=.8, length=500):
    return gpt2.generate(
        sess,
        length=length,
        truncate='<|endoftext|>',
        prefix=prefix,
        return_as_list=True
    )

def train():
    sess, gpt2 = train_model()
    gpt2.generate(sess)

if __name__ == '__main__':
    work()
