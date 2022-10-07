import gpt_2_simple as gpt2
import sys
from flask import Flask, render_template, send_from_directory, jsonify

app = Flask(__name__)

# ----------- web ----------------- #

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/static')
def staticfiles(path):
    return send_from_directory('static', path)

# ----------- model --------------- #

transcripts_fname = 'transcripts.txt'
model_name = "124M"
i = 50

def train_model():
    sess = gpt2.start_tf_sess()
    gpt2.finetune(sess,
                  transcripts_fname,
                  model_name=model_name,
                  steps=i)
    return sess, gpt2

def load_and_run_model(prefix, temperature=.8, length=500):
    print('*****************************')
    print('*****************************')
    print('Prefix: ', prefix)
    print('Temp: ', temperature)
    print('Length: ', length)
    print('*****************************')
    print('*****************************')
    sess = gpt2.start_tf_sess()
    gpt2.load_gpt2(sess)
    gpt2.generate(
        sess,
        length=length,
        truncate='<|endoftext|>',
        prefix=prefix
    )

def train():
    sess, gpt2 = train_model()
    gpt2.generate(sess)

if __name__ == '__main__':
    arg = None
    try:
        arg = sys.argv[1]
    except IndexError:
        pass
    if arg is None:
        app.run(host='0.0.0.0', port=8000, debug=True)
    elif arg == 'train':
        train()
    elif arg == 'run':
        prefix = None
        temperature = 1.0
        length = 500
        try:
            prefix = sys.argv[2]
        except IndexError:
            pass

        try:
            temperature = sys.argv[3]
        except IndexError:
            pass

        try:
            length = int(sys.argv[4])
        except IndexError:
            pass

        load_and_run_model(prefix, temperature, length)

    else:
        raise ValueError('Only train or run')
