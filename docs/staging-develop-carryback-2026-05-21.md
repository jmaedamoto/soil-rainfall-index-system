# staging -> develop Carryback Inventory (2026-05-21)

## Done Today

- Session reload / stale load fixes
  - `85b18c7` Guard production session state against stale loads
  - `94260a8` Guard incomplete session risk-at-time responses
  - `6dac81c` Always return mesh coords from risk endpoint
  - `91fbeb1` Refetch prefecture data for new sessions
- Prefecture ordering / session payload fixes
  - `7fd7799` Load prefectures from CSV master
  - `8b3763d` Align rainfall modal prefecture order
  - `6135dbe` Use session payload for rainfall modal order
- Rainfall / risk-rule fixes
  - `b1b2293` Compute 3h SWI with hourly uniform rainfall
  - `3f3ae4e` Add peak-mesh fill mode for 24h rainfall adjustment
  - `4b6e295` Fix missing Optional import in rainfall adjustment service
  - `a44063e` Show SWI and 3h rainfall in risk timeline
  - `bda6282` Show minimum level4 threshold in timeline labels
  - `4eae356` Fix lead-time risk rule classification
  - `a23a77f` Align lead-time rule with first and last level4
  - `02540f3` Fix rainfall adjustment risk rule handling for staging
- Cache / session hardening
  - `8a9b5da` Write session references atomically
  - `3f065c5` Wait for cache when restoring shared sessions
  - `6a4bc9c` Restore cached sessions across workers
  - `4b79bfc` Harden cache writes and calculation locks
  - `c4c273a` Wait for cache materialization before serving
  - `1ca02a2` Wait for gz completion before responding
  - `2109e4a` Fix partial cache materialization race
  - `7912b8f` Harden cache writes before materialized reads
  - `813f65c` Clean up failed calculation locks
  - `698d6ed` Fix completed cache lock detection
- Carryback-only follow-up
  - `87d94a4` Align carried-back risk endpoint behavior

## Remaining Mainline Candidates

- Cache / session hardening
  - `1017d28`
  - `f59e7f6`
  - `eb2f4ee`
  - `f15940c`
  - `12572f6`

## staging-only / Do Not Carry Back

- Deploy / Apache / route-profile / proxy
  - `107b841`
  - `33ac6d9`
  - `8eb309b`
  - `e799207`
- Promotion cleanup / staging packaging
  - `6477b54`
- Investigation-only traces / production debug logging
  - `429376b`
  - `8a39395`
  - `8513afa`
- Local investigation artifacts
  - `server/data/2nd.txt`
  - `server/data/3rd.txt`

## Notes

- `35f966e` is superseded by later session fixes and should not be carried alone.
- `0d24d51`, `abf1e61`, `0806ded`, `a733d98` have already been incorporated on `develop` under different hashes.
- `git log --cherry-pick --right-only develop...staging` still shows some carried commit hashes because conflicts changed patch-ids during carryback.
- Remaining mainline candidates should be carried in grouped PRs, not mixed with staging-only changes.
