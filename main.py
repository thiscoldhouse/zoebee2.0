import gpt_2_simple as gpt2
import tensorflow as tf
import sys
from flask import Flask, render_template, send_from_directory, jsonify, request

app = Flask(__name__)

# ----------- web ----------------- #

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/talk', methods=['POST'])
def talk():
    data = request.get_json(force=True)
    if data['length'] > 2000:
        return jsonify('Length must be less than 1000')

    text = load_and_run_model(
            data['prefix'],
            data['temperature'],
            data['length']
        )
    print('=========')
    print(f'Run with {data}')
    print(text)
    print('=========')
    return jsonify(text)



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
    app.run(host='0.0.0.0', port=8000, debug=True)
