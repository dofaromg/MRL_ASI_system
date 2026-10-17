# MRL_CommercialService v0.1

origin_signature: MrLiouWord

此模組將既有 FlowOS 粒子執行接到真實 Node HTTP API，提供客戶 API key 驗證、停用、配額、隔離與本地持久化計量。它不執行模型推理、不宣告付款成功，也不核發 MRL 商業授權。ownerGrantRef 是管理者填入的既有授權參照；程式不驗證其法律或簽章效力。

## 建置與 DL580 啟動

需要 Node 24、TypeScript 5.9.3 與 Node 型別。於含 PR #8 及本 PR 的既有倉庫執行：

```powershell
Set-Location D:\MRL_Mother\MRL_ASI_system\flowos
npm run test:commercial-service
node service/MRL_ProvisionAccount.cjs D:\MRL_Mother\CommercialService\credentials customer01 1000 OWNER_APPROVED_REFERENCE
$env:MRL_ACCOUNTS_FILE='D:\MRL_Mother\CommercialService\credentials\accounts.json'
$env:MRL_DATA_DIR='D:\MRL_Mother\CommercialService\data'
$env:MRL_SERVICE_PORT='7820'
npm run start:commercial-service
```

OWNER_APPROVED_REFERENCE 應替換為 Mr.liou 實際核准的參照。工具只建立初始帳戶，不覆寫既有 accounts.json；後續帳戶、quota、enabled 與 keyHash 由本機管理者修改該設定，重新啟動生效。每個 key 為 256-bit 隨機值，設定只留 SHA-256；原 key 留於 credentials/customer01.key。請由本機 ACL 保護 credentials 與 data，Windows 的檔案 mode 不能代替 ACL。API 不接受遠端帳戶配置或授權升級。

預設僅監聽 127.0.0.1:7820。對外服務須接既有 TLS／存取管控代理；本 PR 不改 DNS、不公開母體記憶，也不自動部署。每次請求建立獨立 FlowOS，回傳當次輸入的粒子與標籤；不讀取 MRL 母體資料。

```powershell
$key=(Get-Content D:\MRL_Mother\CommercialService\credentials\customer01.key -Raw).Trim()
$headers=@{Authorization="Bearer $key";'Idempotency-Key'='customer01-request-001'}
Invoke-RestMethod http://127.0.0.1:7820/health
Invoke-RestMethod http://127.0.0.1:7820/v1/particles/collapse -Method Post -Headers $headers -ContentType application/json -Body (@{content='MRL particle input'}|ConvertTo-Json)
Invoke-RestMethod http://127.0.0.1:7820/v1/usage -Headers $headers
Get-FileHash D:\MRL_Mother\CommercialService\data\usage.jsonl -Algorithm SHA256
```

## API 與計量

| 介面 | 行為 |
|---|---|
| GET /health | 無需 key；回報服務自身 ready/storage_error，不代表 DL580 或母體整體健康 |
| POST /v1/particles/collapse | Bearer key + Idempotency-Key + JSON {content}；執行 create → collapse → FlowLaw → 本地 fsync → 回應 |
| GET /v1/usage | 僅回傳該 key 所屬帳戶的本月用量與配額 |

每次新成功 collapse 計 1 unit。使用 UTC 月曆月；相同帳戶、月份與 Idempotency-Key 重送回原 snapshot，不重複計量；內容不同回 409。跨月同 key 視為新請求。成功寫帳本但回應丟失時，原月重試可恢復。重試窗口與帳本保留期相同；目前不自動清理。服務不設定售價、不建立發票、不扣款。

帳本包含客戶提交內容及結果，限本機保存，管理者負責備份、ACL 和保留政策。啟動時重播帳本恢復 quota 與重試回執；不支援多程序共同寫入。service.lock 阻止第二個寫入者。非正常終止留下鎖時，必須確認原程序已停止，再由管理者移除該鎖。殘缺或無法解析的帳本會阻止啟動；不可直接清空而重置用量。寫入／fsync 失敗會停用後續請求，避免不確定狀態繼續服務。帳本不是加密或防管理者竄改的審計系統。

輸入限 content 8192 bytes、HTTP body 16384 bytes；已設 request/header timeout。單程序同步持久化適用初期小量服務；尚未實作訂閱付款驗證、分散式帳本、退款、稅務或大規模壓力驗收。

## 驗證範圍

自動化測試以實際 loopback HTTP、真實 FlowOS 與暫時檔案帳本驗證成功、驗證失敗、停用、配額、並行、重試、重啟、客戶隔離、月份邊界、獨占鎖及磁碟失敗。所有測試資料為合成資料。此 scoped build 承接 PR #8；既有 src/index.ts Worker 語法錯誤仍需另行修復。

工程測試通過不等於 DL580 已部署、正式對外可用或 FIRST_REALIZED_REVENUE_PASS；這些需對應實機與真實交易回執。
