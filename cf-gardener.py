import datetime
import git
import os
import requests
import sqlite3
import time
import json

from bs4 import BeautifulSoup


# ユーザーの提出全部取得
# https://codeforces.com/apiHelp/methods#user.status
def get_all_user_status(handle: str) -> dict:
    url_user_status = 'https://codeforces.com/api/user.status'
    par = {'handle': handle}
    ret_user_status = requests.get(url_user_status, params=par)
    if ret_user_status.ok:
        return ret_user_status.json()
    else:
        raise Exception('Request "user.status" failed')


# contest id, 提出idからソースコード取得
def get_source(contest_id: int, id_: int) -> str:
    url_submission = f'https://codeforces.com/contest/{contest_id}/submission/{id_}'
    print(url_submission)
    html = requests.get(url_submission)
    if html.ok:
        soup = BeautifulSoup(html.content, 'html.parser')
        return soup.find(id='program-source-text').getText()
    else:
        # エラー内容書く
        raise Exception('error!')


# try-exceptでエラー時処理書く
# contest_idからコンテスト名取得
# ローカルのdbにあるならそこから取得
def get_contest_name(contest_id: int) -> str:
    dbname = f"{os.path.dirname(__file__)}/contest_name.db"
    with sqlite3.connect(dbname) as conn:
        cur = conn.cursor()

        # テーブル"contest"が存在しないなら作る
        create_table = 'CREATE TABLE IF NOT EXISTS contest (contest_id int NOT NULL PRIMARY KEY, contest_name varchar)'
        # print(create_table)
        cur.execute(create_table)

        # contest_id={contest_id}な行が存在するなら1 しないなら0
        exists = f'SELECT EXISTS (SELECT * FROM contest WHERE contest_id={contest_id})'
        # print(exists)
        ret_exists = cur.execute(exists)

        if ret_exists.fetchone()[0] == 0:
            # 存在しない
            # print("not found")
            # コンテストのdashboardページからコンテスト名取得
            url_dashboard = f'https://codeforces.com/contest/{contest_id}'
            html = requests.get(url_dashboard)
            if html.ok:
                soup = BeautifulSoup(html.content, 'html.parser')
                str_contest_name = soup.select_one(
                    '#sidebar > div:nth-child(1) > table > tbody > tr:nth-child(1) > th > a').getText()
            else:
                # エラー内容書く
                raise Exception('requests.get failed')

            # insert
            insert = f"INSERT INTO contest values({contest_id}, '{str_contest_name}')"
            # print(insert)
            cur.execute(insert)
            return str_contest_name
        else:
            # 存在する
            select = f'SELECT contest_name FROM contest WHERE contest_id={contest_id}'
            # print(select)
            ret_select = cur.execute(select)
            return ret_select.fetchone()[0]


# programmingLanguageからソースコードのファイル名を取得
# 間違っている可能性あり
# 情報求む
def get_filename(lang: str) -> str:
    if lang in 'GNU C11':
        return 'program.c'
    if lang in (
            'Clang++17 Diagnostics', 'GNU C++11', 'GNU C++14', 'GNU C++17', 'MS C++', 'MS C++ 2017', 'GNU C++17 (64)'):
        return 'program.cpp'
    if lang in ('.NET Core C#', 'Mono C#', 'MS C#'):
        return 'Program.cs'
    if lang in 'D':
        return 'program.d'
    if lang in 'Go':
        return 'program.go'
    if lang in 'Haskell':
        return 'program.hs'
    if lang in ('Java 11', 'Java 8'):
        return 'program.java'
    if lang in 'Kotlin':
        return 'program.kt'
    if lang in 'Ocaml':
        return 'program.ml'
    if lang in 'Delphi':
        return 'program.dpr'
    if lang in ('FPC', 'PascalABC.NET'):
        return 'program.pas'
    if lang in 'Perl':
        return 'program.pl'
    if lang in 'PHP':
        return 'program.php'
    if lang in ('Python 2', 'Python 3', 'PyPy 2', 'PyPy 3'):
        return 'program.py'
    if lang in 'Ruby 3':
        return 'program.rb'
    if lang in 'Rust':
        return 'program.rs'
    if lang in 'Scala':
        return 'program.scala'
    if lang in ('JavaScript', 'Node.js'):
        return 'program.js'
    raise Exception(f"unknown language:'{lang}'")


# 処理の失敗時 git cleanして元に戻す
def git_clean(r: git.Repo):
    print('git clean')
    r.git.clean('-fdx')


if __name__ == '__main__':
    pwd = os.path.dirname(__file__)

    with open(f'{pwd}/config.json', 'r') as f:
        js = json.load(f)
        git_url = js['upstream_url']
        user_name = js['handle']
    path = f'{pwd}/submissions'
    # リポジトリ用意
    try:
        repo = git.Repo(path)
        repo.git.pull()
    except git.NoSuchPathError:
        print('git clone')
        repo = git.Repo.clone_from(git_url, path,)

    changed = False
    try:
        # 全提出取得
        js = get_all_user_status(user_name)
        # 失敗したら raiseで止まる
        if js['status'] != 'OK':
            raise Exception("status is not 'OK'")
        success = True
        ret = js['result']

        cnt = 0

        for submit in reversed(ret):
            try:
                # コンテストの提出じゃない
                if 'contestId' not in submit:
                    continue
                # ACじゃない
                if submit['verdict'] != 'OK':
                    continue

                contestId = submit['contestId']
                index = submit['problem']['index']
                name = submit['problem']['name'].replace(' ', '_')
                subId = submit['id']

                filename = get_filename(submit['programmingLanguage'])
                contest_name = get_contest_name(contestId).replace(' ', '_')
                directory = f'{path}/{contest_name}/{index}_{name}/{subId}'
                if os.path.isfile(f'{directory}/{filename}'):
                    # ファイルがある
                    continue

                # ファイルが無いならスクレイピング
                print(f'download {contest_name}/{index}_{name}/{subId}')
                source_code = get_source(contestId, subId)
                os.makedirs(directory, exist_ok=True)
                with open(f'{directory}/{filename}', mode='w') as f:
                    f.write(source_code)
                cnt += 1
                changed = True
                # codeforcesに怒られるのでスクレイピングは50回まで
                if cnt >= 50:
                    break
                # codeforcesに怒られないように待つ
                time.sleep(2)

            # どの種類のエラーが出る?
            except Exception as e:
                # 失敗
                print(e)
                git_clean(repo)
                exit()
    except KeyboardInterrupt:
        git_clean(repo)
        exit()

    # 成功

    if changed:
        print('git add')
        repo.git.add(all=True)
        # git commit
        print('git commit')
        repo.index.commit(str(datetime.datetime.now()))
        # git push
        print('git push')
        origin = repo.remote(name='origin')
        origin.push()
        # end
        print('success')
