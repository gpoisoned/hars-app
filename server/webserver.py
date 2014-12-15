from flask import Flask, jsonify

app = Flask(__name__)

@app.route("/")
def root():
    return jsonify(status="Web server is running!")

@app.route("/health")
def health():
    return jsonify(heath="It's all good :)")

if __name__ == "__main__":
    app.debug = True
    app.run()
