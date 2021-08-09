# cf-gardener

Codeforcesの提出をGitHubに上げるやつ

## 使い方

config.jsonに以下のように書き込む

```json
{
  "upstream_url": "https://<token>:x-oauth-basic@github.com/<user>/<repo>.git",
  "handle": "<CodeForcesのhandle>"
}
```

必要なパッケージインストール

```sh
$pip install GitPython beautifulsoup4 requests
$python cf-gardener.py
```

実行

``` sh
$python cf-gardener.py
```

## 注意

Codeforcesに負荷をかけないようにスクレイピングを50回までに制限しています。  
提出が大量にある場合、時間を空けて複数回実行してください