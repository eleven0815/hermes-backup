---
name: a-share-shareholder-data
description: Query Chinese A-share stock shareholder data (top 10 holders, float shareholders, fund holdings, shareholder counts) via East Money F10 API and cninfo stock code lookup.
category: productivity
tags: [chinese-stocks, a-share, shareholder, east-money, financial-data]
trigger: When user asks about Chinese A-share stock shareholder data, top shareholders, float holders, fund positions, or related financial data for any A-share stock.
---

# Chinese A-Share Shareholder Data Lookup

Query shareholder data for Chinese A-share stocks (科创板、主板、创业板) using East Money's F10 API.

## 1. Find Stock Code

If stock code is unknown, search via **cninfo API** (巨潮资讯网):

```bash
curl -s "http://www.cninfo.com.cn/new/fulltextSearch/full?searchkey=公司名称&sdate=&edate=&isfulltext=false&sortName=nothing&sortType=desc&pageNum=1" \
  -H "User-Agent: Mozilla/5.0"
```

Look for `secCode` in the response (e.g., `688479` for 科创板, `000001` for 深交所).

**Code prefix:**
- 上交所 (SH): prepend `SH` → `SH688479`
- 深交所 (SZ): prepend `SZ` → `SZ000001`
- 北交所 (BJ): prepend `BJ` → `BJ430001`

## 2. Query Shareholder Data

**Primary endpoint (F10 Shareholder Research):**
```bash
curl -s "https://emweb.securities.eastmoney.com/PC_HSF10/ShareholderResearch/PageAjax?code=SH688479" \
  -H "User-Agent: Mozilla/5.0"
```

**Response fields:**
| Field | Description |
|-------|-------------|
| `sdgd` | 十大股东 (Top 10 shareholders, all types) |
| `sdltgd` | 十大流通股东 (Top 10 float shareholders) |
| `jjcg` | 基金持仓 (Fund holdings) |
| `gdrs` | 股东户数汇总 (Shareholder count summary) |
| `jgcc` | 机构持仓 (Institutional holdings) |
| `ltgf` | 流通股份 (Float share structure) |
| `sjkzr` | 实控人 (Actual controller) |

**Example key fields per holder:**
- `HOLDER_NAME`: shareholder name
- `HOLD_NUM`: number of shares held
- `HOLD_NUM_RATIO`: percentage of total shares
- `FREE_HOLDNUM_RATIO`: percentage of float shares
- `HOLD_NUM_CHANGE`: 变动 ("不变"=unchanged, "新进"=new entry, "增加"/"减少")

## 3. Parse & Format

Extract the relevant arrays. Key data points to present:

1. **十大流通股东** (`sdltgd`): float shareholders with share counts and percentages
2. **十大股东** (`sdgd`): all shareholders including restricted shares
3. **股东总户数** from `gdrs` (most recent date): total shareholder count, 户均持股
4. **基金持仓** (`jjcg`): fund positions
5. **股本结构** (`ltgf`): total shares, restricted shares ratio, float shares ratio

## 4. Known Working APIs

| Data Type | API |
|-----------|-----|
| Stock code search | `http://www.cninfo.com.cn/new/fulltextSearch/full?searchkey=...` |
| Shareholder/F10 data | `https://emweb.securities.eastmoney.com/PC_HSF10/ShareholderResearch/PageAjax?code=SH...` |
| Financial indicators | `https://datacenter-web.eastmoney.com/api/data/v1/get?reportName=RPT_LICO_FN_CPD&filter=(SECUCODE%3D%22...%22)` |

## Pitfalls

- Some East Money datacenter APIs return "报表配置不存在" — use the F10 page API instead for shareholder data
- cninfo API requires proper User-Agent header or returns empty results
- Q1 data is typically available after ~4/25 of that year
- 科创板 stocks use `SH` prefix; 深交所 uses `SZ`; 北交所 uses `BJ`
- East Money F10 API returns `END_DATE` in "2026-03-31 00:00:00" format — filter by most recent date for latest quarter
