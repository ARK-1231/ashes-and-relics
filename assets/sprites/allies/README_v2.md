# 味方画像 v2

組み込み image_gen ツールでキャラクターごとに生成した透過PNGです。既存のv1画像は保存しています。

- `mira_v2.png`: 金色のフードと杖を持つ回復役ミラ。
- `leon_v2.png`: 青灰色の鎧、剣と盾を持つ灰騎士レオン。
- `noa_v2.png`: 銀髪と紫のローブ、星の杖を持つ星詠みノア。
- `source_*_v2.png`: 各キャラクターの生成原画。

ゲーム内では96×96の静止スプライトとして、合流前・同行中の両方に表示します。足元と名前の識別色は取得前後で共通です。`tools/prepare_ally_sprites.ps1`で透明度を保持し、全身を80×80以内に収め、足元をy=84に揃えています。

生成プロンプト（実際に使用した全文）:

## mira

Use case: stylized-concept. Asset type: transparent PNG sprite for an existing top-down 2D dark fantasy RPG. Generate ONE character only: Mira, a female healer with a brown braid, cream robes, golden hood and cape, holding a small gold staff with amber crystal. Dominant warm gold #e7b94c. Style: detailed crisp pixel art, 3-head-tall proportions, matches a small gray-haired armored JRPG explorer sprite, readable at 96x96. Full-body front view seen slightly from above, feet together near bottom, centered, entire weapon visible, generous transparent padding. Character occupies 75% of height. Transparent background with actual alpha. No ground, no shadow, no frame, no text, no watermark, no other characters. Square canvas.

## leon

Use case: stylized-concept. Asset type: transparent PNG sprite for an existing top-down 2D dark fantasy RPG. Generate ONE character only: Leon, an ash knight in worn silver and blue-gray armor, short dark hair, sword held downward and compact shield. Dominant blue-gray #9aa7bd. Style: detailed crisp pixel art, 3-head-tall proportions, matches a small gray-haired armored JRPG explorer sprite, readable at 96x96. Full-body front view seen slightly from above, feet together near bottom, centered, entire weapon visible, generous transparent padding. Character occupies 75% of height. Transparent background with actual alpha. No ground, no shadow, no frame, no text, no watermark, no other characters. Square canvas.

## noa

Use case: stylized-concept. Asset type: transparent PNG sprite for an existing top-down 2D dark fantasy RPG. Generate ONE character only: Noa, a star mage with silver hair, violet and midnight blue robes, star-tipped staff. Dominant violet #9d7de2. Style: detailed crisp pixel art, 3-head-tall proportions, matches a small gray-haired armored JRPG explorer sprite, readable at 96x96. Full-body front view seen slightly from above, feet together near bottom, centered, entire weapon visible, generous transparent padding. Character occupies 75% of height. Transparent background with actual alpha. No ground, no shadow, no frame, no text, no watermark, no other characters. Square canvas.

