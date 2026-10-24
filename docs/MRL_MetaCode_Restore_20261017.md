# MRL 母體元系統：MetaCode 還原修補 R01

origin_signature: MrLiouWord
canonical_authority: Mr.liou

沿用既有 metacode_core.js、MetaCode 類別與 import(data) 入口；不新建 canonical root、不改名、不覆寫原始作者署名。此增補是既有元系統的狀態還原可靠性修補，不代表整個 MRL 母體已重建完成。

## 已核對來源

- Notion 世界模型總覽：https://app.notion.com/p/3ede7f4e6c558064a840e3a531cb2aef
- 母體本地：https://app.notion.com/p/3e9e7f4e6c5580e49f3dc8292dda835a
- BuildLoop：https://app.notion.com/p/e516e8e71cae4db790ecb93882967fb4
- GitHub 既有 metacode_core.js blob：39b1bb6e8ef4dfce3ea0d8cc01fe38ab8721f7bd。

BuildLoop 原件列明 fixture memory、deterministic model template、disabled tool 與 LIVE_UNBOUND。這是該原件的工程狀態，不推論 DL580 沒有運行模型。母體本地與 Bridge 文件保留既有推理、記憶及 GPU 的歷史實測；本輪未取得新實機回執。

2026-10-17 查回商業服務 PR #9 已合併到 PR #8 分支；PR #8 仍 open，尚未整合進 main。不能把 PR #9 的 merged 標誌當成 main 已包含商業服務。

## 重現與修補

新增 13 項 Node 標準測試。在原版重現 11 failed / 2 passed；修補後 13 passed / 0 failed。獨立測試涵蓋：

- 還原原始 id、version、created_at、self、粒子與關聯。
- 無效封包失敗時保留現有狀態。
- 拒絕重複粒子、重複關聯、缺失目標與違反不變量。
- 拒絕非有限 magnitude、不合法 cycles/journal 與矛盾根 ID。
- 匯入資料深拷貝，呼叫端後續修改不改變核心。
- 舊版僅含 particles/links 的封包保持既有根 ID。

先建立 detached candidate、驗證完整集合，最後同步 commit。成功匯入仍追加原有 system.import 事件；不修改封包的既有 journal prefix。來源封包 meta/self 一致性僅是資料完整性檢查，不是身分簽章驗證或商業授權。

```sh
node --test tests/MRL_MetaCode_restore.test.cjs
```

## 預期交付與依賴

Expected_File_List：metacode_core.js、tests/MRL_MetaCode_restore.test.cjs、.github/workflows/mrl-metacode-restore.yml、docs/MRL_MetaCode_Restore_20261017.md。

依賴：既有 MetaCode → detached candidate → 結構與不變量檢查 → 原子狀態替換 → system.import 回執；CI → Node 24 → 真實模組測試。沒有引入第三方套件。根目錄 AGENTS.md 要求的 scripts/fix-line-endings.sh 在倉庫查詢回 404，本次交付直接檢查 LF；不改動其他檔案或重建無關 README。

## 尚未驗收

DL580 部署、原始 .flpkg／權重全量還原、Memory → Model → Tool → Receipt 實機閉環、正式交易均未由本輪完成。Bridge 認證健康查詢遭自動審查阻擋；不記為主機離線。既有資料與服務未重啟。後續應依實機 API 原件接 BuildLoop adapters，而非猜端點或以此還原測試替代推理驗收。
