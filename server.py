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


# メインページ
@app.route('/')
def index():
    data = get_data()

    return render_template('index.html', data=data)


# Twitter連携用ページ(ログイン用URLにリダイレクトさせる)
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


# ログアウト用ページ
@app.route('/logout', methods=["GET"])
def logout():
    # クッキーからアクセストークンを削除
    session.pop("access_token", None)
    return redirect("/")


# 過去にログインしたアカウントの履歴を表示するデバッグ用ページ
@app.route('/history', methods=["GET"])
def history():
    return ", ".join(secret.keys())


# 特定のアカウントとして表示するデバッグ用ページ
@app.route("/dev", methods=["GET"])
def dev():
    if request.args.get('key') != os.environ["KEY"]:
        return redirect("/")
    user = request.args.get('user')
    if user not in secret:
        return "User Not Found"
    auth = tweepy.OAuthHandler(CONSUMER_KEY, CONSUMER_SECRET)
    auth.set_access_token(secret[user]["token"], secret[user]["secret"])
    api = tweepy.API(auth)
    user = api.verify_credentials()
    if (name := request.args.get('account')) is not None:
        timeline = get_account(api, name)
    else:
        timeline = get_timeline(api)
    return render_template('index.html', data=[timeline, user])


# メインページ表示のための関数
def get_data():
    flag = False
    auth = tweepy.OAuthHandler(CONSUMER_KEY, CONSUMER_SECRET)
    # -- 1. クッキーにログイン情報が保存されている場合 --
    if session.get("access_token") is not None:
        auth.set_access_token(session['access_token']["token"], session['access_token']["secret"])
    # -- 2. 未ログイン または ログイン後リダイレクトでやってきた場合 --
    else:
        flag = True
        # リダイレクトにより渡されたパラメータを取得
        token = session.pop('request_token', None)
        verifier = request.args.get('oauth_verifier')
        # -- 2-1 未ログイン --
        if token is None or verifier is None:
            return False
        # OAuth認証を行ってリクエストトークンからアクセストークンを取得
        auth.request_token = token
        try:
            auth.get_access_token(verifier)
        except Exception:
            print(traceback2.format_exc())
            return False
        # -- 2.2 ログイン完了 --
        # アクセストークンを保存
        session['access_token'] = {
            "token": auth.access_token,
            "secret": auth.access_token_secret
        }

    # アクセストークンでログイン
    api = tweepy.API(auth)
    user = api.verify_credentials()
    if flag:  # 新規ログイン(2.2)の場合はデータベースに保存
        secret[user.screen_name] = session["access_token"]
        with open("secret.json", "w") as f:
            json.dump(secret, f)

    timeline = get_timeline(api)
    return [timeline, user]


def get_timeline(api) -> list:
    timeline = []
    for status in api.home_timeline(count=100):
        if 'media' in status.entities:
            for media in status.extended_entities['media']:
                status.text = status.text.replace(media["url"], "")
        timeline.append(status)
    return timeline


def get_account(api, name) -> list:
    timeline = []
    for status in tweepy.Cursor(api.user_timeline, screen_name=name).items(100):
        if 'media' in status.entities:
            for media in status.extended_entities['media']:
                status.text = status.text.replace(media["url"], "")
        timeline.append(status)
    return timeline


# --------------------------------------------------------------------------
if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)
