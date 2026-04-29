---
date: "2026-04-29"
type: incident
severity: high
status: resolved
detected-by: "scripts/fetch-x-metrics.py during /loop iter 2"
detected-at: "2026-04-29 20:49"
resolved-at: "2026-04-29 21:00"
resolution: "Option B: X 設定でハンドル名を autonomy_master に変更（X はハイフン不可なので underscore）"
---

# インシデント: X アカウントブランド不整合

## 事実

`/loop` iter 2 で初めて X API `/2/users/me` を呼び出した結果、`.env` の X 認証情報が以下のアカウントに紐づくことが判明:

- **username**: `DOXB2I9qKbhbmrg`（@autonomy-master ではない）
- user_id: 1356476303789105152
- 既存フォロワー: 5
- 既存フォロー: 24
- 既存ツイート: 5（うち3つは今日の launch tweets）

## 影響

- 本日投稿した **Tweet 1, 2, 3 は全て @DOXB2I9qKbhbmrg から発信** されている
- 私が共有した URL（`https://x.com/autonomy-master/status/...`）は X がツイートIDで解決するため**閲覧自体は可能**、ただし訪問者が見る投稿者名は `@DOXB2I9qKbhbmrg`
- README / note 記事内の X 言及（`x.com/autonomy-master`）も実体と不一致

## 原因

`scripts/post-to-x.py` の出力で `handle = "autonomy-master"` を**ハードコードしていた**。実際の認証ユーザー名を `/2/users/me` で取得していなかったため、ブランド不整合に気づけなかった。

## 現在の数値（参考、@DOXB2I9qKbhbmrg の数値）

| 指標 | 値 |
|------|----|
| Tweet 1 インプレッション | 7 |
| Tweet 2 インプレッション | 2 |
| Tweet 3 インプレッション | 4 |
| いいね合計 | 0 |
| RT合計 | 0 |
| 返信合計 | 0 |

## オーナーへの選択肢

| 選択肢 | 内容 | 工数 | 既存ツイートの扱い |
|--------|------|------|-------------------|
| A. 新規 X アプリ作成 | 別途 @autonomy-master の X アカウント作成 → Developer Portal で OAuth 取得 → `.env` 更新 | 大（30-60分）| 3ツイートは @DOXB2I9qKbhbmrg に残るか手動削除、@autonomy-master から再投稿 |
| **B. ハンドル変更（推奨）** | X 設定 → ユーザー名変更で @DOXB2I9qKbhbmrg → @autonomy-master | 小（数秒）| **3ツイートそのまま生かせる**、URL も自動で正しくなる |
| C. ブランド統一を諦める | README / 記事 / note 内の X 言及を @DOXB2I9qKbhbmrg に修正 | 中 | そのまま、ただし読者には不審 |

**巨匠 PM 推奨: B**。最低コスト、最大効果、既存ツイート保全。

ただし B が成立する条件: **X 上で @autonomy-master がまだ誰にも取られていないこと**。X 設定画面で確認が必要。取られている場合は A か C にフォールバック。

## 後続のコード修正

オーナー判断後、いずれの場合も `scripts/post-to-x.py` を修正する:
- `handle` ハードコードを削除
- 投稿後 `data.username` フィールドから実ハンドルを動的取得（必要なら追加 API 呼び出し）
- これにより同種事故の再発を防ぐ

## ループ状態

`/loop` は本インシデント検出時点で **停止**。次の wakeup はスケジュールしていない。オーナー判断（A / B / C）を受領したら再開する。

---

## 解決ログ（2026-04-29 21:00）

### 採用: Option B（ハンドル名変更）

オーナーが X 設定で **`DOXB2I9qKbhbmrg` → `autonomy_master`** にハンドル名変更（X はハイフン不可なので `autonomy-master` ではなく `autonomy_master`）。

### API 再確認
```
username: autonomy_master
id: 1356476303789105152
```
user_id 不変、ハンドル名のみ変更されたことを確認。既存 Tweet 1-3 はそのままこのアカウント所属で生きており、URL も正しい profile を指すようになった。

### 再発防止コード修正
`scripts/post-to-x.py` のハンドルハードコード行を削除:
- 旧: `handle = "autonomy-master"`（ハードコード、検証なし）
- 新: `handle = get_my_username() or "i"`（`/2/users/me` で動的取得、失敗時は X の universal handle "i" にフォールバック）

これにより、今後ハンドル変更があっても出力 URL が自動追従する。

### ドキュメント整合
- `README.md`: ハイフン版 X URL を underscore 版に置換（4箇所）
- `secretary/todos/2026-04-29.md`: 同様に置換、Tweet 3 の todo 完了マークも追加
- メモリ: `project_x_integration.md` / `project_owner_public_assets.md` を resolved 表記に

### 未対応（保全のため意図的にそのまま）
- 投稿済み Tweet 1-3 の本文: そのまま（X ハンドル自体は本文に含まれず、GitHub の URL は元から正しい）
- 既に投稿された Discord 通知の中の hyphen URL: 過去ログとして保存、書き換えしない
