---
created: "2026-04-29"
type: tweet-draft
status: pending-publication
target-tweet: "Tweet 6 (第4回 article announce)"
trigger: "第4回 note 公開後、URL を差し替えて自動発射"
chair: copywriter
---

# Tweet 6 暫定ドラフト

## 本文

```
連載第4回を公開しました。

『数字が0のまま、AI が走り続けた夜』

フォロワーも、いいねも、まだゼロ。それでも AI 集団は議事録を書き、戦略を組み、コピーを練り、未来の記事を温める。Day 1 の夜に何が起きていたかの記録です。

[ここに note URL を貼る]
```

## メタ情報

- 文字数: 約145文字（Japanese-weighted、URL 含む）
- 媒体: X（@autonomy_master）
- ハッシュタグ: 必要に応じて Primary set（#個人開発 #AIエージェント #note書きました）を末尾追加

## コピーライター意図

1. **「フォロワーも、いいねも、まだゼロ」を冒頭** に置く: 第4回タイトル「数字が0のまま」と整合、誠実トーン
2. 「**それでも**」で転換、AI 集団の動詞リスト（書く・組む・練る・温める）→ 連載のメタ性を凝縮
3. CTA は「フォロー」を直接書かず、記事リンクで自然誘導 ← Tweet 2/4 と同じ控えめスタイル

## トリガー

オーナーが第4回を note 公開した直後、URL を確定して `post-to-x.py` で発射。
発射スクリプト例:
```bash
./scripts/post-to-x.py "$(cat .company/money/outputs/sns-posts/2026-04-29-tweet-6-draft.md | sed -n '/```$/,/```$/p' | head -10 | tail -8 | sed 's|\\[ここに note URL を貼る\\]|<実URL>|')"
```

簡易には、本文をコピペして `post-to-x.py` に渡せば良い。
