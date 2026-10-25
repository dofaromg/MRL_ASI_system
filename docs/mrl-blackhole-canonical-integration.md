---
description: 'MRL blackhole canonical integration, lineage and separate acceptance gates'
---
# MRL 黑洞模型 canonical 承接增補

origin_signature: MrLiouWord
canonical_authority: Mr.liou
record_mode: APPEND_ONLY
source_head: 5d8ddd670fe095768a2d988110583fbe2167aa3b

## 五層結構的承接
既有頂層總覽 3ede7f4e6c558064a840e3a531cb2aef、母體
3e9e7f4e6c5580e49f3dc8292dda835a 沿用。五層是此任務的流程角色，
不是替原資料庫改名、改寫原語义或建立新的 canonical 母體。

| 流程層 | 沿用／增補節點 | 保留的 title property |
|---|---|---|
| Event Horizon | MRL 檔案整合資料庫｜來源與承接 | 原始名稱 |
| Accretion Disk | 🗂️ Claude.ai 專案總覽資料庫（完整 schema 版本） | 專案名稱 |
| Singularity | 📦 文物分類資料庫（完整 schema 版本） | 文物名稱 |
| Hawking Radiation | 母體下查找同名節點；確實缺少才建 L4 | 輸出 Output |
| Return Ledger | 🔗 關聯索引資料庫（完整 schema 版本） | 關聯名稱 |

工具箱另有四個同名但僅 Name 欄位的資料庫；保留原件，不拿它們
取代上表的完整 schema 版本。ID 與 data source ID 分開保存於
mrl_blackhole/canonical_bindings.json。尚未寫入的 ID 保持 null，
不可用模擬 ID 當 live 證據。

既有 title 欄位保持原名，新增黑洞屬性只作用於
mrl_model_scope = MRL_BLACKHOLE_CANONICAL_V1 的新紀錄。
原歷史資料不自動回填、不改 Return ID、不改原始時間或版本。
原 select 選項、關係名稱與資料庫位置保留。

## Builder 與重跑
canonical.py 提供新 builder；原 model.py、builder.py、snapshot.py、
conservation.py 保留原件。cli.py 以追加實作承接原指令名稱。
黑洞 snapshot 必須寫到指定本地檔，不將內容印到平台。

- API 版本固定 2025-09-03；data source 負責 schema、query、relations。
- 指定的既有資料庫按 ID 讀回、核對 parent 與 data source membership。
- L4 缺 ID 時完整分頁列母體 child databases；同名多筆即停止。
- 不新建 root；錯誤 parent、origin、scope 或 manifest binding 於寫入前拒絕。
- 只 PATCH 缺少屬性；現有欄位型別、relation target 或 enum 不相容即停止。
- 關係採 one-way，避免每次建立匿名 reciprocal 欄位。
- 每個 acknowledged 新資料庫 ID、data source ID 與增補步驟均保存 checkpoint。
- 保留每次 checkpoint 歷史；current manifest 用 fsync + atomic replace。
- 單機 exclusive lock，並行或殘留 lock 必須先查明，不自動清除。
- POST timeout 不盲目重送；再次 Existing Node Lookup 再核對來源。
- 不是跨主機分散式鎖；同一工作區需單一授權 executor。

## Lineage／Return ID
五層新紀錄保存 source_id、original_name、original_author、source_times、
version_revision、parent_source、derived_from、canonical_target、
origin_signature、content_sha256；未知內容雜湊或上游欄位不捏造。
每個非 L1 節點有來源登錄 Source Registry relation。

make_lineage_return_id 使用 JSON 編碼的 source ID、原始時間、版本及
完整 SHA256；舊 make_return_id 與已有 RID 原樣保留，禁止重算覆寫。
同一流程的五層紀錄必須沿用同一 Return ID。

## 守恆稽核
snapshot 明確 query scope 並讀取全部五層；缺分頁 cursor／循環 cursor、
截斷 property／關係或缺層直接停止，不把部分輸入當完整證據。
audit_snapshot 核對基礎守恆、每層 RID、來源、三段流程關係、
來源登錄 relation、Ledger 的入境／輸出 relation 與交付時間。
空資料、pending 不當成 runtime acceptance PASS。
mock PASS 不代表正式 Notion 已建構，也不代表 main 已合併。

## 本地使用
使用現有 Notion integration 的合法 token；不列印、不提交金鑰。
在 DL580 的既有 repo checkout 執行，輸出全部保存在 D 槽：
```powershell
python -m mrl_blackhole.canonical plan --manifest D:\MRL_Mother\Blackhole\canonical_manifest.json
python -m mrl_blackhole.canonical build --manifest D:\MRL_Mother\Blackhole\canonical_manifest.json
python -m mrl_blackhole.canonical snapshot --manifest D:\MRL_Mother\Blackhole\canonical_manifest.json --snapshot D:\MRL_Mother\Blackhole\snapshot.json
python -m mrl_blackhole.canonical audit --manifest D:\MRL_Mother\Blackhole\canonical_manifest.json --snapshot D:\MRL_Mother\Blackhole\snapshot.json
```

## 分開驗收
1. exact-head CI：原 21 項加 canonical synthetic regression；無 Notion token、
   無正式資料、無 private runner 或部署動作。
2. 正式結構：live schema、ID、原欄位與名稱保留、五層關係讀回，
   第二次 preflight 無新增 schema；builder 本身的 live 執行另記回執。
3. 實際內容往返：五層資料鏈、Return ID、source lineage、交付時間、
   實際交付與接收證據；合成案例不冒充使用者確認。
4. main 合併：獨立裁定；draft 不自動轉 ready，不合併。

## 2026-10-11 正式 schema 讀回
經已授權 Notion connector 正式建立／增補並重新 fetch：
沿用 4 個資料庫，新建 L4 一個（database d3c4153040744e4182a1ffdb8c24c0f0；
data source a51f678c-6265-4293-bcae-8e8a40efff3b）。
既有 49 個欄位完整保留；5 層所需 97 個欄位及 9 條 relation 全部讀回匹配。
第二次 schema preflight：missing 0、mismatch 0、待新增 0。
Python builder 的 live API 執行／並行與 timeout 重播仍未實測；
以上是 connector 正式 schema 寫入與讀回，不冒充 Python builder 執行回執。
黑洞 scope rows 全部為 0；沒有新增合成資料列，沒有宣告內容交付或 owner ACK。
main 尚未合併；正式資料往返 runtime_acceptance 維持 HOLD。

## Exact-head 與 Neural Branch Sync
既有 Neural Branch Sync 在 push 後可能再追加只含 neural-links 的 bot commit。
此 workflow 不停止／修改原同步；先驗原事件 head，再等同 head 的同步 jobs 完成，
fetch 最終分支，核對其包含原 head 且期間差異僅限兩個 neural-links 檔，
明示 SETTLED_EXACT_HEAD，再對此實際 checkout 重跑全部黑洞測試。
若有人同時改其他檔案，gate 直接 FAIL，不用舊測試覆蓋新程式。
