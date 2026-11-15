# Interoperability test: causes of the failures (worked answer)

| Case | Consumer at fault | What the code does | Kind of cause |
|---|---|---|---|
| B | BI report | Filters the timestamp column with `order_ts <= '2026-09-30'`. Every timestamp on 30 September is later than that text value, so the last day of the quarter is dropped. | time boundary |
| C | notebook | Reads every store and never applies `user_store_access`, so asha sees all six stores. | security context |
| D | notebook | Filters on `region_current`. Store S03 was in the South region in Q1 and is in the West region today, so its Q1 orders are left out. | filter |
| E | BI report | Averages the six store averages. A store with few orders gets the same weight as a store with many. | aggregation |

None of the four fixes would have been needed if the consumer had called the API. The API passes the request to the
semantic layer, which holds the time convention, the security rule, the region dimension and the ratio in one place.
