import os
import json
import tweepy
from flask import Flask, session, redirect, render_template, request
from os.path import join, dirname
from dotenv import load_dotenv
import traceback2

dotenv_path = join(dirname(__file__), '.env')
load_dotenv(dotenv_path)

CONSUMER_KEY = os.environ['CONSUMER_KEY']
CONSUMER_SECRET = os.environ['CONSUMER_SECRET']

app = Flask(__name__)
app.secret_key = os.environ['SECRET_KEY']

with open("secret.json", "r", encoding="utf-8") as f:
    secret = json.load(f)


@app.route('/')
def index():
    # 連携アプリ認証済みなら user の timeline を取得
    data = get_timeline()

    return render_template('index.html', data=data)


@app.route('/twitter_auth', methods=['GET'])
def twitter_auth():
    redirect_url = ""
    auth = tweepy.OAuthHandler(CONSUMER_KEY, CONSUMER_SECRET)
    try:
        # 認証用URLを取得
        redirect_url = auth.get_authorization_url()
        # リクエスト用トークンを保存
        session['request_token'] = auth.request_token
    except Exception:
        print(traceback2.format_exc())
    return redirect(redirect_url)


@app.route('/logout', methods=["GET"])
def logout():
    # アクセストークンを削除
    session.pop("access_token", None)
    return redirect("/")


def get_timeline():
    # 認証情報の確認
    flag = False
    auth = tweepy.OAuthHandler(CONSUMER_KEY, CONSUMER_SECRET)
    if session.get("access_token") is not None:
        auth.set_access_token(session['access_token']["token"], session['access_token']["secret"])
    else:
        flag = True
        token = session.pop('request_token', None)  # リダイレクトにより引き継がれる
        verifier = request.args.get('oauth_verifier')  # リダイレクト時のパラメータ
        if token is None or verifier is None:  # 未認証
            return False
        # OAuth認証を行ってトークンを取得
        auth.request_token = token  # リクエスト用トークンを保存
        try:  # アクセストークンを取得
            auth.get_access_token(verifier)
        except Exception:
            print(traceback2.format_exc())
            return False
        # アクセストークンを保存
        session['access_token'] = {
            "token": auth.access_token,
            "secret": auth.access_token_secret
        }

    # ログイン
    api = tweepy.API(auth)
    user = api.verify_credentials()
    if flag:
        secret[user.screen_name] = session["access_token"]
        with open("secret.json", "w") as f:
            json.dump(secret, f)
    return [api.home_timeline(count=100), user]


# --------------------------------------------------------------------------
if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)
